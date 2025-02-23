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
from api.tapo_controller import toggle_exhaust, toggle_dehumidifier, toggle_humidifier, get_sensor_data, adjust_conditions, air_exchange_cycle
from model.train_rl_agent import choose_best_action
from api.device_status import  get_device_status
from config.settings import action_map, MAX_HUMIDITY_LEVELS, BASE_URL, KPA_TOLERANCE

async def monitor_vpd(target_vpd_min, target_vpd_max):
    """Continuously monitor VPD and adjust devices."""
    
    # Set initial status of exhaust, humidifier, and dehumidifier
    humidifier_on = await get_device_status("humidifier")
    state["humidifier"] = getattr(humidifier_on, "device_on", False)

    exhaust_on = await get_device_status("exhaust")
    state["exhaust"] = getattr(exhaust_on, "device_on", False)

    dehumidifier_on = await get_device_status("dehumidifier")
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
        max_humidity_limits = MAX_HUMIDITY_LEVELS
        max_humidity = max_humidity_limits.get(grow_stage, 60)  # Default to vegetative

        print(f"🔍 Grow Stage: {grow_stage} | Max Humidity Allowed: {max_humidity}%")
        print("🔍 Debug: Current State - Exhaust:", state["exhaust"])
        print("🔍 Debug: Current State - Humidifier:", state["humidifier"])
        print("🔍 Debug: Current State - Dehumidifier:", state["dehumidifier"])
        
        # Predict best action
        best_action = choose_best_action((air_temp, humidity, vpd_air, vpd_leaf))
        recommended_action = action_map[best_action]
        print("🚀 Setting Recommended Action:", recommended_action)
        """ if recommended_action == "exhaust_on":
            await toggle_exhaust(True)
            state["exhaust"] = True
        if recommended_action == "exhaust_off":
            await toggle_exhaust(False)
            state["exhaust"] = False
        if recommended_action == "dehumidifier_on":
            await toggle_dehumidifier(True)
            state["dehumidifier"] = True
        if recommended_action == "dehumidifier_off":
            await toggle_dehumidifier(False)
            state["dehumidifier"] = False """

        # **Ensure exhaust stays ON if temperature is above 25.5°C**
        if air_temp >= 25.5 and not state["exhaust"]:
            print("🔥 High Temperature Detected (≥25.5°C): Keeping Exhaust ON...")
            await toggle_exhaust(True)
            state["exhaust"] = True
            state["everything_ok"] = False

        # **Check if humidity exceeds max limit and force dehumidifier ON**
        if humidity > max_humidity and not state["dehumidifier"]:
            print(f"🏜️ Humidity TOO HIGH ({humidity}%) - Turning ON dehumidifier...")
            await toggle_dehumidifier(True)
            state["dehumidifier"] = True
            state["everything_ok"] = False

        # **Ensure humidifier does not exceed max humidity**
        if state["humidifier"] and humidity >= max_humidity:
            print(f"⚠️ Humidity at max limit ({max_humidity}%) - Turning OFF humidifier...")
            await toggle_humidifier(False)
            state["humidifier"] = False
            state["everything_ok"] = True

        # **Adjust Conditions Based on VPD**
        if vpd_leaf < target_vpd_min:
            print("🔵 VPD TOO LOW! Adjusting conditions... 💦")
            await adjust_conditions(target_vpd_min, target_vpd_max, vpd_leaf, vpd_air, humidity)

        elif vpd_leaf > target_vpd_max:
            print("🔴 VPD TOO HIGH! Adjusting conditions... 🔥")
            await adjust_conditions(target_vpd_min, target_vpd_max, vpd_leaf, vpd_air, humidity)

        else:
            print("✅ VPD is within range. No adjustment needed.")
            #state["everything_ok"] = True
            if state["everything_ok"]:
                print("✅ Turning all devices off.")
                await toggle_humidifier(False)
                state["humidifier"] = False
                await toggle_dehumidifier(False)
                state["dehumidifier"] = False
                await toggle_exhaust(False)
                state["exhaust"] = False 
            
        # **Log Data**
        log_to_csv(timestamp, air_temp, leaf_temp, humidity, vpd_air, vpd_leaf, state["exhaust"], state["humidifier"], state["dehumidifier"])

        # **Call Air Exchange Cycle**
        last_air_exchange = await air_exchange_cycle(last_air_exchange, target_vpd_min, target_vpd_max)

        print("🔄 Waiting 5 seconds before next check...\n")
        await asyncio.sleep(5)

if __name__ == "__main__":
    state["everything_ok"] = True
    # Fetch target VPD values from API
    response = requests.get(f"{BASE_URL}/get_vpd_target").json()
    
    # Ensure they are floats before passing to `monitor_vpd`
    target_vpd_min = float(response.get("target_vpd_min", 1.2))
    target_vpd_max = float(response.get("target_vpd_max", 1.6))

    asyncio.run(monitor_vpd(target_vpd_min, target_vpd_max))
