import os
import sys
import asyncio
import datetime
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.calculate import calculate_vpd
from utils.print_vpd_status import print_vpd_status
from utils.logs import log_to_csv, log_to_json
from utils.config import get_target_vpd
from api.tapo_controller import get_sensor_data, adjust_conditions

load_dotenv()

DAY_START = int(os.getenv("DAY_START", 16))
NIGHT_START = int(os.getenv("NIGHT_START", 10))
TARGET_VPD = get_target_vpd()

def is_daytime():
    """Check if it's daytime based on the 24-hour schedule."""
    current_hour = datetime.datetime.now().hour
    return current_hour >= DAY_START or current_hour < NIGHT_START

async def monitor_vpd():
    """Continuously monitor VPD and adjust humidifier/exhaust reactively."""
    print(f"✅ Monitoring started with Target Leaf VPD: {TARGET_VPD} kPa (±0.02 tolerance)")

    while True:
        air_temp, leaf_temp, humidity = await get_sensor_data()
        vpd_air, vpd_leaf = calculate_vpd(air_temp, leaf_temp, humidity)

        print(f"🌡️ Air: {air_temp}°C | 🌿 Leaf: {leaf_temp}°C | 💧 Humidity: {humidity}%")
        print(f"🌫️ Air VPD: {vpd_air} kPa | Leaf VPD: {vpd_leaf} kPa")
        print_vpd_status(vpd_air, vpd_leaf)

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_to_csv(timestamp, air_temp, leaf_temp, humidity, vpd_air, vpd_leaf)
        log_to_json(timestamp, air_temp, leaf_temp, humidity, vpd_air, vpd_leaf)

        # Adjust conditions dynamically
        await adjust_conditions(TARGET_VPD, vpd_leaf, vpd_air, humidity, tolerance=0.02)

        print("🔄 Waiting 30 seconds before next check...")
        await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(monitor_vpd())
