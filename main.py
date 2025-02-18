import os
import sys
import time
import asyncio
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.calculate import calculate_vpd
from utils.print_vpd_status import print_vpd_status
from utils.logs import log_to_csv, log_to_json
from utils.config import get_target_vpd
from api.tapo_controller import get_sensor_data, adjust_conditions, energy_saving_mode, air_exchange_cycle

load_dotenv()

DAY_START = int(os.getenv("DAY_START", 16))
NIGHT_START = int(os.getenv("NIGHT_START", 10))
KPA_TOLERANCE = float(os.getenv("KPA_TOLERANCE", 0.1))

async def monitor_vpd(target_vpd_min, target_vpd_max):
    """Continuously monitor VPD and adjust devices."""
    last_air_exchange = time.time()

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

        # Call Air Exchange
        last_air_exchange = await air_exchange_cycle(last_air_exchange)

        print("🔄 Waiting 5 seconds before next check...\n")
        await asyncio.sleep(5)


if __name__ == "__main__":
    target_vpd_min, target_vpd_max = get_target_vpd() 
    asyncio.run(monitor_vpd(target_vpd_min, target_vpd_max))