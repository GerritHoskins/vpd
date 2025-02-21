import os
import sys
import time
import requests
import asyncio
import json
from dotenv import load_dotenv
import time
from api.state import state

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.calculate import calculate_vpd
from utils.logs import log_to_csv, log_to_json
from api.tapo_controller import get_humidifier_status, get_exhaust_status, get_sensor_data, adjust_conditions, get_dehumidifier_status, air_exchange_cycle

load_dotenv()

BASE_URL = os.getenv('BASE_URL')

DAY_START = int(os.getenv("DAY_START", 16))
NIGHT_START = int(os.getenv("NIGHT_START", 10))
KPA_TOLERANCE = float(os.getenv("KPA_TOLERANCE", 0.1))

async def monitor_vpd(target_vpd_min, target_vpd_max):
    """Continuously monitor VPD and adjust devices."""
    
    # Set initial status of exhaust and humidifier
    humidifier_on = await get_humidifier_status()
    state["humidifier"] = getattr(humidifier_on, "device_on", None)

    exhaust_on = await get_exhaust_status()
    state["exhaust"] = getattr(exhaust_on, "device_on", None)
    
    dehumidifier_on = await get_dehumidifier_status()
    state["dehumidifier"] = getattr(dehumidifier_on, "device_on", None)
    
    
    last_air_exchange = time.time()
    timestamp = time.time()

    # Convert VPD targets to float
    target_vpd_min = float(target_vpd_min)
    target_vpd_max = float(target_vpd_max)

    print(f"✅ Monitoring started with Target VPD: {target_vpd_min} - {target_vpd_max} kPa (±{KPA_TOLERANCE} tolerance)")

    while True:
        air_temp, leaf_temp, humidity = await get_sensor_data()
        vpd_air, vpd_leaf = calculate_vpd(air_temp, leaf_temp, humidity)

        print("\n-------------------- 🌡️ Sensor Readings --------------------")
        print(f"Air Temp: {air_temp}°C | Leaf Temp: {leaf_temp}°C | Humidity: {humidity}%")
        print(f"Air VPD: {vpd_air} kPa | Leaf VPD: {vpd_leaf} kPa")
        print("------------------------------------------------------------")

        if vpd_leaf < target_vpd_min:
            print("🔵 VPD TOO LOW! Adjusting conditions... 💦")
            await adjust_conditions(target_vpd_min, target_vpd_max, vpd_leaf, vpd_air, humidity)

        elif vpd_leaf > target_vpd_max:
            print("🔴 VPD TOO HIGH! Adjusting conditions... 🔥")
            await adjust_conditions(target_vpd_min, target_vpd_max, vpd_leaf, vpd_air, humidity)

        else:
            print("✅ VPD is within range. No adjustment needed.")
            
        log_to_csv(timestamp, air_temp, leaf_temp, humidity, vpd_air, vpd_leaf, state["exhaust"], state["humidifier"], state["dehumidifier"])
        #log_to_json(timestamp, air_temp, leaf_temp, humidity, vpd_air, vpd_leaf, state["exhaust"], state["humidifier"], state["dehumidifier"])

        # Call Air Exchange
        last_air_exchange = await air_exchange_cycle(last_air_exchange, target_vpd_min, target_vpd_max)

        print("🔄 Waiting 5 seconds before next check...\n")
        await asyncio.sleep(5)


if __name__ == "__main__":
    # Fetch target VPD values from API
    response = requests.get(f"{BASE_URL}/get_vpd_target").json()
    
    # Ensure they are floats before passing to `monitor_vpd`
    target_vpd_min = float(response.get("target_vpd_min", 1.2))
    target_vpd_max = float(response.get("target_vpd_max", 1.4))

    asyncio.run(monitor_vpd(target_vpd_min, target_vpd_max))
