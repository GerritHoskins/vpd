import asyncio
from tapo import ApiClient
from tapo.responses import T31XResult
import os
import sys
from dotenv import load_dotenv
from state import state 

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils.calculate import calculate_required_humidity

load_dotenv()

# Load credentials
TAPO_USERNAME = os.getenv("TAPO_USERNAME")
TAPO_PASSWORD = os.getenv("TAPO_PASSWORD")
SENSOR_IP = os.getenv("SENSOR_IP")
HUMIDIFIER_IP = os.getenv("HUMIDIFIER_IP")
EXHAUST_IP = os.getenv("EXHAUST_IP")

async def get_tapo_client():
    """Initialize and return a Tapo API Client."""
    return ApiClient(TAPO_USERNAME, TAPO_PASSWORD)

async def get_device_status():
    """Fetch the device status from the Tapo sensor hub."""
    client = await get_tapo_client()
    device = await client.h100(SENSOR_IP)
    return await device.get_device_info()

async def toggle_humidifier(state_requested):
    """Turn the humidifier ON or OFF based on state (True=ON, False=OFF)."""
    global state  # Use global state dictionary

    if state["humidifier"] == state_requested:
        return {"message": f"Humidifier is already {'ON' if state_requested else 'OFF'}, no action taken."}

    client = await get_tapo_client()
    device = await client.p115(HUMIDIFIER_IP)

    if state_requested:
        await device.on()
        state["humidifier"] = True  # Update state
        return {"message": "Humidifier turned ON"}
    else:
        await device.off()
        state["humidifier"] = False  # Update state
        return {"message": "Humidifier turned OFF"}

async def toggle_exhaust(state_requested):
    """Turn the exhaust fan ON or OFF based on state (True=ON, False=OFF)."""
    global state  # Use global state dictionary

    if state["exhaust"] == state_requested:
        return {"message": f"Exhaust fan is already {'ON' if state_requested else 'OFF'}, no action taken."}

    client = await get_tapo_client()
    device = await client.p100(EXHAUST_IP)

    if state_requested:
        await device.on()
        state["exhaust"] = True  # Update state
        return {"message": "Exhaust fan turned ON"}
    else:
        await device.off()
        state["exhaust"] = False  # Update state
        return {"message": "Exhaust fan turned OFF"}
    
async def get_sensor_data():
    """Fetch temperature & humidity from the Tapo sensor."""
    client = await get_tapo_client()
    hub = await client.h100(SENSOR_IP)
    child_device_list = await hub.get_child_device_list()

    for child in child_device_list:
        if isinstance(child, T31XResult):  # Ensure it's a T31X sensor
            air_temp = round(child.current_temperature or 0, 1)
            leaf_temp = round(max(air_temp - 1.0, 0), 1)  # Estimated leaf temp
            humidity = round(child.current_humidity or 0, 1)

            return air_temp, leaf_temp, humidity
    
    print("⚠️ No valid sensor data found! Using default values (20°C, 18.8°C, 50%).")
    return 20.0, 18.8, 50.0 

async def adjust_conditions(target_vpd, vpd_leaf, vpd_air, humidity, tolerance=0.02):
    """
    Adjust temperature and humidity to achieve the target Leaf VPD within a tolerance range.
    Uses state tracking to avoid unnecessary toggling.
    """
    air_temp, leaf_temp, humidity = await get_sensor_data()
    required_humidity = calculate_required_humidity(target_vpd, air_temp, leaf_temp)

    vpd_min = target_vpd - tolerance
    vpd_max = target_vpd + tolerance
    
    humidity_min = humidity - 0.5
    humidity_max = humidity + 0.5

    print(f"🎯 Adjusting to Target Leaf VPD: {target_vpd} kPa (±{tolerance} kPa)")
    print(f"🔹 Current Air Temp: {air_temp}°C | Leaf Temp: {leaf_temp}°C | Humidity: {humidity}%")
    print(f"🔹 Required Humidity: {required_humidity}%")
    
    if required_humidity < humidity_min:
        print("🌬️ Humidity too high! Making sure humidifier is OFF and exhaust ON...")
        await toggle_humidifier(False)  
        await toggle_exhaust(True)
    elif required_humidity > humidity_max:
        print("🌬️ Humidity too low! Making sure humidifier is ON...") 
        state["humidifier"] = True
        await toggle_humidifier(True)
    
    else:
        print("✅ Humidity is within tolerance range. No adjustments needed.")
        
    if vpd_leaf > vpd_max:
        print("🌬️ VPD too high! Making sure humidifier is ON...")
        await toggle_exhaust(False)
        await toggle_exhaust(True)
    
    elif vpd_leaf < vpd_min:
        print("💦 VPD too low! Turning OFF the humidifier and making sure exhaust is ON...")
        await toggle_humidifier(False)       
        await toggle_humidifier(True)
    
    else:
        print("✅ VPD is within tolerance range. No adjustments needed.")

    print("✅ Conditions adjusted successfully!")