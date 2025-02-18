import sys
import os
import asyncio
import time
from tapo import ApiClient
from tapo.responses import T31XResult
from dotenv import load_dotenv

# Ensure the utils and api modules can be found
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.state import state 
from utils.calculate import calculate_required_humidity

load_dotenv()

# Load credentials
TAPO_USERNAME = os.getenv("TAPO_USERNAME")
TAPO_PASSWORD = os.getenv("TAPO_PASSWORD")
HUB_IP = os.getenv("HUB_IP")
HUMIDIFIER_IP = os.getenv("HUMIDIFIER_IP")
EXHAUST_IP = os.getenv("EXHAUST_IP")
KPA_TOLERANCE = float(os.getenv("KPA_TOLERANCE", 0.1))

async def get_device_info_json():
    """Returns *device info* as json.
    It contains all the properties returned from the Tapo API.
    """
    client = await get_tapo_client()
    device = await client.h100(HUB_IP)
    return await device.get_device_info_json()    

async def air_exchange_cycle(last_air_exchange):
    """
    Runs an air exchange cycle every 30 minutes for 5 minutes.
    Ensures the exhaust fan turns ON for fresh air supply.
    """
    AIR_EXCHANGE_INTERVAL = 30 * 60  # 30 minutes
    AIR_EXCHANGE_DURATION = 5 * 60   # 5 minutes

    current_time = time.time()
    if current_time - last_air_exchange >= AIR_EXCHANGE_INTERVAL:
        print("\n🔄 **Air Exchange Cycle: Venting Air for 5 minutes...**")
        if not state["exhaust"]:  # Only turn ON if it's OFF
            await toggle_exhaust(True)

        await asyncio.sleep(AIR_EXCHANGE_DURATION)

        print("✅ **Air Exchange Complete: Restoring previous state.**")
        await toggle_exhaust(False)  # Turn OFF exhaust after 5 minutes
        return time.time()  # Return updated timestamp

    return last_air_exchange  # No change if air exchange was not needed

async def energy_saving_mode(vpd_leaf, vpd_air, target_vpd_min, target_vpd_max):
    """Turns off humidifier/exhaust if VPD is already within range to save energy."""
    if target_vpd_min <= vpd_leaf <= target_vpd_max and target_vpd_min <= vpd_air <= target_vpd_max:
        if state["humidifier"] or state["exhaust"]:  # Only act if devices are ON
            print("⚡ Energy-Saving Mode: VPD is stable. Turning OFF humidifier & exhaust.")
            await toggle_humidifier(False)
            await toggle_exhaust(False)

async def get_tapo_client():
    """Initialize and return a Tapo API Client."""
    return ApiClient(TAPO_USERNAME, TAPO_PASSWORD)

async def get_device_status():
    """Fetch the device status from the Tapo sensor hub."""
    client = await get_tapo_client()
    device = await client.h100(HUB_IP)
    return await device.get_device_info()

async def smooth_transition(from_device, to_device, duration=10):
    """Gradual transition between exhaust and humidifier for smoother humidity adjustments."""
    print(f"⚙️ **Starting smooth transition: {from_device} → {to_device}** (Duration: {duration}s)")
    await asyncio.sleep(duration // 2)  # Halfway delay before switching fully
    if from_device == "humidifier":
        await toggle_humidifier(False)
        await asyncio.sleep(duration // 2)  # Allow overlap before turning exhaust on
        await toggle_exhaust(True)
    else:
        await toggle_exhaust(False)
        await asyncio.sleep(duration // 2)  # Allow overlap before turning humidifier on
        await toggle_humidifier(True)
    print(f"✅ **Transition complete: {to_device} is now active.**")

async def toggle_humidifier(state_requested):
    """Turn the humidifier ON or OFF based on state (True=ON, False=OFF)."""
    if state["humidifier"] == state_requested:
        print(f"ℹ️ Humidifier already {'ON' if state_requested else 'OFF'}. No action taken.")
        return {"message": f"Humidifier is already {'ON' if state_requested else 'OFF'}"}

    print(f"🔄 Changing humidifier state to {'ON' if state_requested else 'OFF'}...")

    client = await get_tapo_client()
    device = await client.p115(HUMIDIFIER_IP)

    try:
        if state_requested:
            await device.on()
            state["humidifier"] = True
            print("✅ Humidifier turned ON")
        else:
            await device.off()
            state["humidifier"] = False
            print("✅ Humidifier turned OFF")

    except Exception as e:
        print(f"❌ Error: Failed to toggle humidifier - {str(e)}")

async def toggle_exhaust(state_requested):
    """Turn the exhaust fan ON or OFF based on state (True=ON, False=OFF)."""
    
    if state["exhaust"] == state_requested:
        print(f"ℹ️ Exhaust already {'ON' if state_requested else 'OFF'}. No action taken.")
        return

    client = await get_tapo_client()
    device = await client.p100(EXHAUST_IP)

    try:
        if state_requested:
            print("🔄 Changing exhaust state to ON...")
            await device.on()
            state["exhaust"] = True  # ✅ Force state sync
            print("✅ Exhaust turned ON")
        else:
            print("🔄 Changing exhaust state to OFF...")
            await device.off()
            state["exhaust"] = False  # ✅ Force state sync
            print("✅ Exhaust turned OFF")
    except Exception as e:
        print(f"⚠️ Failed to change exhaust state: {str(e)}")
    
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
                    leaf_temp = round(max(air_temp - 1.0, 0), 1)  # Estimate leaf temperature
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
    """Gradually adjust humidifier and exhaust for smooth transitions."""
    
    air_temp, leaf_temp, humidity = await get_sensor_data()
    target_vpd = (target_vpd_min + target_vpd_max) / 2  # Fix for correct target VPD
    required_humidity = calculate_required_humidity(target_vpd, air_temp, leaf_temp)

    # ✅ Correct the min/max VPD calculation
    vpd_min = target_vpd_min - tolerance
    vpd_max = target_vpd_max + tolerance

    print("\n🔍 Debug: Current State - Exhaust:", state["exhaust"], "Humidifier:", state["humidifier"])
    print(f"🔍 Debug: Corrected VPD Min: {vpd_min} | VPD Max: {vpd_max} | Required Humidity: {required_humidity}%")

    humidifier_change = False
    exhaust_change = False

    # **Ensure exhaust is OFF if humidity is too low**
    if humidity < required_humidity and state["exhaust"]:
        print("❗ Humidity too low! Turning OFF exhaust to prevent excess drying...")
        await toggle_exhaust(False)
        state["exhaust"] = False  # Ensure state sync
        exhaust_change = True

    # **Adjust humidifier and exhaust based on required humidity**
    if required_humidity > humidity and not state["humidifier"]:
        print("💦 Gradual Transition: Increasing humidity - Turning ON humidifier...")
        await toggle_humidifier(True)
        humidifier_change = True

    elif required_humidity < humidity and state["humidifier"]:
        print("🌬️ Gradual Transition: Reducing humidity - Turning OFF humidifier...")
        await toggle_humidifier(False)
        humidifier_change = True

    # **Adjust based on VPD levels**
    if vpd_leaf > vpd_max and state["exhaust"]:
        print("🔥 VPD TOO HIGH: Turning OFF exhaust and ON humidifier...")
        await toggle_exhaust(False)
        await toggle_humidifier(True)
        exhaust_change = True
        humidifier_change = True

    elif vpd_leaf < vpd_min and not state["exhaust"]:
        print("💦 VPD TOO LOW: Turning ON exhaust and OFF humidifier...")
        await toggle_humidifier(False)
        await toggle_exhaust(True)
        exhaust_change = True
        humidifier_change = True

    # ✅ **Confirm adjustments only if changes happened**
    if humidifier_change or exhaust_change:
        print("✅ Conditions adjusted successfully!")