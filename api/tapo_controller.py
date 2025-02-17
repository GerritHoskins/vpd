import sys
import os
import asyncio
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

async def get_tapo_client():
    """Initialize and return a Tapo API Client."""
    return ApiClient(TAPO_USERNAME, TAPO_PASSWORD)

async def get_device_status():
    """Fetch the device status from the Tapo sensor hub."""
    client = await get_tapo_client()
    device = await client.h100(HUB_IP)
    return await device.get_device_info()

async def toggle_humidifier(state_requested):
    """Turn the humidifier ON or OFF based on state (True=ON, False=OFF)."""
    if state["humidifier"] == state_requested:
        return {"message": f"Humidifier is already {'ON' if state_requested else 'OFF'}, no action taken."}

    client = await get_tapo_client()
    device = await client.p115(HUMIDIFIER_IP)

    try:
        if state_requested:
            await device.on()
            state["humidifier"] = True
            return {"message": "Humidifier turned ON"}
        else:
            await device.off()
            state["humidifier"] = False
            return {"message": "Humidifier turned OFF"}
    except Exception as e:
        return {"error": f"Failed to change humidifier state: {str(e)}"}

async def toggle_exhaust(state_requested):
    """Turn the exhaust fan ON or OFF based on state (True=ON, False=OFF)."""
    if state["exhaust"] == state_requested:
        return {"message": f"Exhaust fan is already {'ON' if state_requested else 'OFF'}, no action taken."}

    client = await get_tapo_client()
    device = await client.p100(EXHAUST_IP)

    try:
        if state_requested:
            await device.on()
            state["exhaust"] = True  # Update state
            return {"message": "Exhaust fan turned ON"}
        else:
            await device.off()
            state["exhaust"] = False  # Update state
            return {"message": "Exhaust fan turned OFF"}
    except Exception as e:
        return {"error": f"Failed to change exhaust state: {str(e)}"}
    
async def get_sensor_data(retries=3, delay=2):
    """Fetch temperature & humidity from the Tapo sensor with retries."""
    client = await get_tapo_client()

    for attempt in range(retries):
        try:
            hub = await client.h100(HUB_IP)
            child_device_list = await hub.get_child_device_list()

            for child in child_device_list:
                if isinstance(child, T31XResult):
                    air_temp = round(child.current_temperature or 0, 1)
                    leaf_temp = round(max(air_temp - 1.0, 0), 1)
                    humidity = round(child.current_humidity or 0, 1)
                    return air_temp, leaf_temp, humidity

            print("⚠️ No valid sensor data found! Using default values (20°C, 18.8°C, 50%).")
            return 20.0, 18.8, 50.0
        except Exception as e:
            print(f"⚠️ Error fetching sensor data (attempt {attempt+1}/{retries}): {e}")
            await asyncio.sleep(delay)

    return 20.0, 18.8, 50.0  # Default values after failed attempts

async def adjust_conditions(target_vpd, vpd_leaf, vpd_air, humidity, tolerance=0.02):
    """Adjust conditions to maintain target VPD only when necessary."""
    air_temp, leaf_temp, humidity = await get_sensor_data()
    required_humidity = calculate_required_humidity(target_vpd, air_temp, leaf_temp)

    vpd_min = target_vpd - tolerance
    vpd_max = target_vpd + tolerance
    
    humidity_min = humidity - 1.5
    humidity_max = humidity + 1.5

    # Track whether changes are needed
    humidifier_change = False
    exhaust_change = False

    # Check if humidifier/exhaust should change based on humidity
    if required_humidity < humidity_min and state["humidifier"]:
        print("🌬️ Humidity too high! Turning OFF humidifier, ON exhaust...")
        await toggle_humidifier(False)
        await toggle_exhaust(True)
        humidifier_change = True
        exhaust_change = True
    elif required_humidity > humidity_max and not state["humidifier"]:
        print("💦 Humidity too low! Turning ON humidifier...")
        await toggle_humidifier(True)
        humidifier_change = True

    # Check if exhaust should change based on VPD
    if vpd_leaf > vpd_max and state["exhaust"]:
        print("🌬️ VPD too high! Turning OFF exhaust and ON humidifier...")
        await toggle_exhaust(False)
        await toggle_humidifier(True)
        exhaust_change = True
        humidifier_change = True
    elif vpd_leaf < vpd_min and not state["exhaust"]:
        print("💦 VPD too low! Turning OFF humidifier and ON exhaust...")
        await toggle_humidifier(False)
        await toggle_exhaust(True)
        humidifier_change = True
        exhaust_change = True

    # Only print final success message if any change was made
    if humidifier_change or exhaust_change:
        print("✅ Conditions adjusted successfully!")

