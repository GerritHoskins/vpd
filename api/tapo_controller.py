import sys
import os
import asyncio
import time
from tapo.responses import T31XResult

# Ensure the utils and api modules can be found
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.state import state 
from config.settings import KPA_TOLERANCE, DEVICE_MAP, MAX_HUMIDITY_LEVELS, AIR_EXCHANGE_SETTINGS, HUB_IP, LEAF_TEMP_OFFSET
from utils.calculate import calculate_required_humidity
from api.actions import toggle_dehumidifier, toggle_exhaust, toggle_humidifier
from api.tapo_client import get_tapo_client

async def get_device_info(device_name):
    """Fetch device info dynamically based on device name."""
    if device_name not in DEVICE_MAP:
        raise ValueError(f"❌ Invalid device name: {device_name}")

    device_ip = DEVICE_MAP[device_name]["ip"]
    device_type = DEVICE_MAP[device_name]["type"]

    client = await get_tapo_client()
    device = await getattr(client, device_type)(device_ip)

    return await device.get_device_info()

async def get_device_info_json(device_name):
    """Fetch device info in JSON format."""
    if device_name not in DEVICE_MAP:
        raise ValueError(f"❌ Invalid device name: {device_name}")

    device_ip = DEVICE_MAP[device_name]["ip"]
    device_type = DEVICE_MAP[device_name]["type"]

    client = await get_tapo_client()
    device = await getattr(client, device_type)(device_ip)

    return await device.get_device_info_json()

async def air_exchange_cycle(last_air_exchange, target_vpd_min, target_vpd_max):
    """
    Adjusts air exchange duration & interval dynamically based on selected VPD stage.
    Ensures the exhaust fan runs periodically for fresh air supply.
    """
    
    # Determine which VPD mode is active
    if target_vpd_max <= 0.8:
        stage = "propagation"
    elif target_vpd_max <= 1.2:
        stage = "vegetative"
    else:
        stage = "flowering"

    settings = AIR_EXCHANGE_SETTINGS[stage]
    AIR_EXCHANGE_INTERVAL = settings["interval"]
    AIR_EXCHANGE_DURATION = settings["duration"]

    current_time = time.time()

    # Check if the last air exchange exceeded the set interval
    if current_time - last_air_exchange >= AIR_EXCHANGE_INTERVAL:
        print(f"\n🔄 **Air Exchange Cycle: {stage.capitalize()} mode - Venting Air for {AIR_EXCHANGE_DURATION // 60} minutes...**")

        if not state["exhaust"]:  # Only turn ON if it's OFF
            await toggle_exhaust(True)
            state["everything_ok"] = False

        await asyncio.sleep(AIR_EXCHANGE_DURATION)  # Keep exhaust ON for the duration

        print("✅ **Air Exchange Complete: Restoring previous state.**")
        await toggle_exhaust(False)  # Turn OFF exhaust after the cycle
        state["everything_ok"] = True

        return time.time()  # Update last air exchange timestamp

    return last_air_exchange  # No change if air exchange was not needed

async def get_sensor_data(retries=3, delay=2):
    """Fetch temperature & humidity from the Tapo sensor with retries."""
    client = await get_tapo_client()

    for attempt in range(retries):
        try:
            hub = await client.h100(HUB_IP)  # Ensure SENSOR_IP is correctly set in .env
            child_device_list = await hub.get_child_device_list()

            for child in child_device_list:
                if isinstance(child, T31XResult):
                    air_temp = round(child.current_temperature or 0, 1)
                    leaf_temp = round(max(air_temp - LEAF_TEMP_OFFSET, 0), 1)  # Estimate leaf temperature
                    humidity = round(child.current_humidity or 0, 1)
                    return air_temp, leaf_temp, humidity  # ✅ Successfully retrieved values

            print("⚠️ No valid sensor data found! Using default values (20°C, 18.8°C, 50%).")
            return 20.0, 18.8, 50.0  # Return safe default values

        except Exception as e:
            print(f"⚠️ Error fetching sensor data (attempt {attempt+1}/{retries}): {e}")

        await asyncio.sleep(delay)  # Wait before retrying

    print("❌ Failed to fetch sensor data after multiple attempts. Using default values.")
    return 20.0, 18.8, 50.0  # Return safe defaults after repeated failures

async def adjust_conditions(target_vpd_min, target_vpd_max, vpd_leaf, vpd_air, humidity, tolerance=KPA_TOLERANCE):
    """Gradually adjust humidifier, dehumidifier, and exhaust for smooth transitions, while enforcing max humidity limits."""
    
    air_temp, leaf_temp, humidity = await get_sensor_data()
    target_vpd = (target_vpd_min + target_vpd_max) / 2  # Fix for correct target VPD
    required_humidity = calculate_required_humidity(target_vpd, air_temp, leaf_temp)

    # ✅ Correct the min/max VPD calculation
    vpd_min = round(target_vpd_min - tolerance, 2)
    vpd_max = round(target_vpd_max + tolerance, 2)

    # **Set max allowed humidity based on grow stage**
    grow_stage = state.get("grow_stage", "vegetative")  # Default to vegetative if unknown
    max_humidity_limits = MAX_HUMIDITY_LEVELS
    max_humidity = max_humidity_limits.get(grow_stage, 55)  # Default to vegetative if missing

    print(f"🔍 Grow Stage: {grow_stage} | Max Humidity Allowed: {max_humidity}%")
    print("🔍 Debug: Current State - Exhaust:", state["exhaust"])
    print("🔍 Debug: Current State - Humidifier:", state["humidifier"])
    print("🔍 Debug: Current State - Dehumidifier:", state["dehumidifier"])
    print(f"🔍 Debug: Corrected VPD Min: {vpd_min} | VPD Max: {vpd_max} | Required Humidity: {required_humidity}%")

    humidifier_change = False
    dehumidifier_change = False
    exhaust_change = False

    # **Ensure the exhaust stays ON if air temperature > 26C**
    if air_temp > 26.0 and not state["exhaust"]:
        print("🔥 High Temperature Detected (>26.0°C): Keeping Exhaust ON...")
        await toggle_exhaust(True)
        state["exhaust"] = True
        state["everything_ok"] = False
        exhaust_change = True

    # **Prevent humidity from exceeding the max allowed for the grow stage**
    if required_humidity > max_humidity:
        print(f"⚠️ Required humidity ({required_humidity}%) exceeds stage max ({max_humidity}%). Adjusting target...")
        required_humidity = max_humidity  # Cap at the grow stage limit

    # **If humidity is already too high, turn OFF humidifier and turn ON dehumidifier**
    if humidity > max_humidity:
        if state["humidifier"]:
            print("🚫 Turning OFF Humidifier: Humidity exceeded max limit!")
            await toggle_humidifier(False)
            state["humidifier"] = False
            humidifier_change = True
            state["everything_ok"] = True

        if not state["dehumidifier"]:
            print("🏜️ Humidity TOO HIGH: Turning ON dehumidifier...")
            await toggle_dehumidifier(True)
            state["dehumidifier"] = True
            dehumidifier_change = True
            state["everything_ok"] = False
    else:
        # **Increase humidity if below required range and humidifier is OFF**
        if required_humidity > humidity and not state["humidifier"]:
            print("💦 Increasing humidity - Turning ON humidifier...")
            await toggle_humidifier(True)
            state["humidifier"] = True
            humidifier_change = True
            state["everything_ok"] = False

        elif required_humidity < humidity and state["humidifier"]:
            print("🌬️ Reducing humidity - Turning OFF humidifier...")
            await toggle_humidifier(False)
            state["humidifier"] = False
            state["everything_ok"] = True
            humidifier_change = True

        # **Turn OFF dehumidifier if humidity is back to normal**
        if humidity <= max_humidity and state["dehumidifier"]:
            print("✅ Humidity in range: Turning OFF dehumidifier...")
            await toggle_dehumidifier(False)
            state["dehumidifier"] = False
            state["everything_ok"] = True
            dehumidifier_change = True

    # **Ensure the exhaust turns OFF only when it's not required**
    if vpd_leaf > vpd_max and state["exhaust"] and air_temp <= 26.0:
        print("🔥 VPD TOO HIGH: Turning OFF exhaust and ON humidifier...")
        await toggle_exhaust(False)
        await toggle_humidifier(True)
        state["exhaust"] = False
        state["humidifier"] = True
        exhaust_change = True
        humidifier_change = True
        state["everything_ok"] = False

    elif vpd_leaf < vpd_min and not state["exhaust"]:
        print("💦 VPD TOO LOW: Turning ON exhaust and OFF humidifier...")
        await toggle_humidifier(False)
        await toggle_exhaust(True)
        state["humidifier"] = False
        state["exhaust"] = True
        exhaust_change = True
        humidifier_change = True
        state["everything_ok"] = False

    # ✅ **Confirm adjustments only if changes happened**
    if humidifier_change or dehumidifier_change or exhaust_change:
        print("✅ Conditions adjusted successfully!")
