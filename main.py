import os
import sys
import time
import requests
import asyncio
from dotenv import load_dotenv
import time
from api.state import state

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.calculate import calculate_vpd
from utils.logs import log_to_csv, log_to_json
from api.tapo_controller import get_humidifier_status, toggle_exhaust, toggle_dehumidifier, toggle_humidifier, get_exhaust_status, get_sensor_data, adjust_conditions, get_dehumidifier_status, air_exchange_cycle
from model.train_rl_agent import choose_best_action
from utils.config import action_map

load_dotenv()

BASE_URL = os.getenv('BASE_URL')

DAY_START = int(os.getenv("DAY_START", 16))
NIGHT_START = int(os.getenv("NIGHT_START", 10))
KPA_TOLERANCE = float(os.getenv("KPA_TOLERANCE", 0.1))

async def monitor_vpd(target_vpd_min, target_vpd_max):
    """Continuously monitor VPD and adjust devices."""
    
    # Set initial status of exhaust, humidifier, and dehumidifier
    humidifier_on = await get_humidifier_status()
    state["humidifier"] = getattr(humidifier_on, "device_on", False)

    exhaust_on = await get_exhaust_status()
    state["exhaust"] = getattr(exhaust_on, "device_on", False)

    dehumidifier_on = await get_dehumidifier_status()
    state["dehumidifier"] = getattr(dehumidifier_on, "device_on", False)
    
    last_air_exchange = time.time()
    timestamp = time.time()

    # Convert VPD targets to float
    target_vpd_min = float(target_vpd_min)
    target_vpd_max = float(target_vpd_max)

    print(f"✅ Monitoring started with Target VPD: {target_vpd_min} - {target_vpd_max} kPa (±{KPA_TOLERANCE} tolerance)")

    while True:
        # **Get Sensor Data**
        air_temp, leaf_temp, humidity = await get_sensor_data()
        vpd_air, vpd_leaf = calculate_vpd(air_temp, leaf_temp, humidity)

        print("\n-------------------- 🌡️ Sensor Readings --------------------")
        print(f"Air Temp: {air_temp}°C | Leaf Temp: {leaf_temp}°C | Humidity: {humidity}%")
        print(f"Air VPD: {vpd_air} kPa | Leaf VPD: {vpd_leaf} kPa")
        print("------------------------------------------------------------")

        # **Determine Grow Stage & Max Humidity Limit**
        grow_stage = state.get("grow_stage", "vegetative")  # Default to vegetative
        max_humidity_limits = {"propagation": 70, "vegetative": 55, "flowering": 50}
        max_humidity = max_humidity_limits.get(grow_stage, 55)  # Default to vegetative

        print(f"🔍 Grow Stage: {grow_stage} | Max Humidity Allowed: {max_humidity}%")
        print("🔍 Debug: Current State - Exhaust:", state["exhaust"])
        print("🔍 Debug: Current State - Humidifier:", state["humidifier"])
        print("🔍 Debug: Current State - Dehumidifier:", state["dehumidifier"])
        
        
        # Predict best action
        best_action = choose_best_action((air_temp, humidity, vpd_air, vpd_leaf))
        print("🚀 Recommended Action:", action_map[best_action])


        # **Ensure exhaust stays ON if temperature is above 25.5°C**
        if air_temp >= 25.5 and not state["exhaust"]:
            print("🔥 High Temperature Detected (≥25.5°C): Keeping Exhaust ON...")
            await toggle_exhaust(True)
            state["exhaust"] = True

        # **Check if humidity exceeds max limit and force dehumidifier ON**
        if humidity > max_humidity and not state["dehumidifier"]:
            print(f"🏜️ Humidity TOO HIGH ({humidity}%) - Turning ON dehumidifier...")
            await toggle_dehumidifier(True)
            state["dehumidifier"] = True

        # **Ensure humidifier does not exceed max humidity**
        if state["humidifier"] and humidity >= max_humidity:
            print(f"⚠️ Humidity at max limit ({max_humidity}%) - Turning OFF humidifier...")
            await toggle_humidifier(False)
            state["humidifier"] = False

        # **Adjust Conditions Based on VPD**
        if vpd_leaf < target_vpd_min:
            print("🔵 VPD TOO LOW! Adjusting conditions... 💦")
            await adjust_conditions(target_vpd_min, target_vpd_max, vpd_leaf, vpd_air, humidity)

        elif vpd_leaf > target_vpd_max:
            print("🔴 VPD TOO HIGH! Adjusting conditions... 🔥")
            await adjust_conditions(target_vpd_min, target_vpd_max, vpd_leaf, vpd_air, humidity)

        else:
            print("✅ VPD is within range. No adjustment needed.")

        # **Log Data**
        log_to_csv(timestamp, air_temp, leaf_temp, humidity, vpd_air, vpd_leaf, state["exhaust"], state["humidifier"], state["dehumidifier"])

        # **Call Air Exchange Cycle**
        last_air_exchange = await air_exchange_cycle(last_air_exchange, target_vpd_min, target_vpd_max)

        print("🔄 Waiting 5 seconds before next check...\n")
        await asyncio.sleep(5)

if __name__ == "__main__":
    # Fetch target VPD values from API
    response = requests.get(f"{BASE_URL}/get_vpd_target").json()
    
    # Ensure they are floats before passing to `monitor_vpd`
    target_vpd_min = float(response.get("target_vpd_min", 1.2))
    target_vpd_max = float(response.get("target_vpd_max", 1.6))

    asyncio.run(monitor_vpd(target_vpd_min, target_vpd_max))
