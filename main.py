import sys
import os
import asyncio
import datetime

# Ensure the utils module is found
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
from utils.calculate import calculate_vpd, calculate_required_humidity
from utils.print_vpd_status import print_vpd_status
from utils.log_to_csv import log_to_csv
from utils.log_to_json import log_to_json
from api.sensor_data import get_sensor_data
from api.plug_controller import toggle_exhaust, toggle_humidifier, force_off_humidifier, force_off_exhaust

load_dotenv()

tapo_username = os.getenv("TAPO_USERNAME")
tapo_password = os.getenv("TAPO_PASSWORD")

sensor_ip = os.getenv("SENSOR_IP")  # IP of Tapo sensor hub (H100)
humidifier_ip = os.getenv("HUMIDIFIER_IP")


# Convert day and night start times to integers (default: 16 for day, 10 for night)
DAY_START = int(os.getenv("DAY_START", 16))  # Ensure it's an integer
NIGHT_START = int(os.getenv("NIGHT_START", 10))  # Ensure it's an integer

def is_daytime():
    """Check if it's daytime based on the 24-hour schedule."""
    current_hour = datetime.datetime.now().hour
    return current_hour >= DAY_START or current_hour < NIGHT_START  # 16:00-10:00 = Daytime, 10:00-16:00 = Nighttime

def get_target_vpd():
    """Prompt the user for a target Leaf VPD value and validate input."""
    while True:
        try:
            target_vpd = float(input("🎯 Enter your target Leaf VPD (kPa): "))
            if 0.0 < target_vpd < 3.0:  # Ensuring a realistic VPD range
                return target_vpd
            else:
                print("❌ Please enter a value between 0.1 and 3.0 kPa.")
        except ValueError:
            print("❌ Invalid input! Please enter a numeric value.")

async def adjust_conditions(target_vpd, vpd_air, tolerance=0.2):
    """
    Adjust temperature and humidity to achieve the target Leaf VPD within a tolerance range.
    """
    air_temp, leaf_temp, humidity = await get_sensor_data()
    required_humidity = calculate_required_humidity(target_vpd, air_temp, leaf_temp)

    print(f"🎯 Adjusting to Target Leaf VPD: {target_vpd} kPa (±{tolerance} kPa)")
    print(f"🔹 Current Air Temp: {air_temp}°C | Leaf Temp: {leaf_temp}°C | Humidity: {humidity}%")
    print(f"🔹 Required Humidity: {required_humidity}%")

    vpd_min = target_vpd - tolerance
    vpd_max = target_vpd + tolerance

    # Adjust humidifier/exhaust based on required humidity and tolerance range
    if required_humidity > humidity and vpd_air > vpd_max:
        print("💦 Increasing humidity to reach target VPD...")
        await toggle_humidifier(air_temp, target_vpd, humidity, is_daytime(), tolerance)
        await force_off_exhaust()
    elif required_humidity < humidity and vpd_air < vpd_min:
        print("🌬️ Decreasing humidity to reach target VPD...")
        await toggle_exhaust(air_temp, target_vpd, humidity, is_daytime(), tolerance)
        await force_off_humidifier()

    print("✅ Conditions adjusted successfully!")

async def monitor_vpd():
    """
    Continuously monitor VPD and adjust humidifier/exhaust reactively.
    """
    # Ask for target Leaf VPD when the program starts
    target_vpd = get_target_vpd()
    print(f"✅ Monitoring started with Target Leaf VPD: {target_vpd} kPa (±0.2 tolerance)")

    while True:
        daytime = is_daytime()
        air_temp, leaf_temp, humidity = await get_sensor_data()

        # Calculate both Air VPD & Leaf VPD
        vpd_air, vpd_leaf = calculate_vpd(air_temp, leaf_temp, humidity)

        # Print status
        print(f"🌡️ Air temperature: {air_temp}°C")
        print(f"🌿 Leaf temperature: {leaf_temp}°C")
        print(f"💧 Humidity: {humidity}%")
        print(f"🌫️ Air VPD: {vpd_air} kPa | Leaf VPD: {vpd_leaf} kPa")
        print_vpd_status(vpd_air, vpd_leaf)

        # Log data
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_to_csv(timestamp, air_temp, leaf_temp, humidity, vpd_air, vpd_leaf)
        log_to_json(timestamp, air_temp, leaf_temp, humidity, vpd_air, vpd_leaf)

        # Adjust conditions dynamically based on user input with ±0.2 tolerance
        await adjust_conditions(target_vpd, vpd_air, tolerance=0.2)

        # Adjust devices based on user-defined VPD target with ±0.2 tolerance
        await toggle_humidifier(vpd_air, target_vpd, humidity, daytime, tolerance=0.2)
        await toggle_exhaust(vpd_air, target_vpd, humidity, daytime, tolerance=0.2)

        print("🔄 Waiting 30 seconds before next check...")
        await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(monitor_vpd())
