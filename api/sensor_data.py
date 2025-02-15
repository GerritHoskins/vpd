import sys
import os
import asyncio
import datetime

# Ensure the utils module is found
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
from tapo import ApiClient
from tapo.requests import AlarmRingtone, AlarmVolume, AlarmDuration
from tapo.responses import T31XResult
from utils.calculate_vpd import calculate_vpd
from utils.check_vpd_alert import check_vpd_alert
from utils.print_vpd_status import print_vpd_status
from utils.log_to_csv import log_to_csv
from utils.log_to_json import log_to_json

load_dotenv()

tapo_username = os.getenv("TAPO_USERNAME")
tapo_password = os.getenv("TAPO_PASSWORD")

sensor_ip = os.getenv("SENSOR_IP")  # IP of Tapo sensor hub (H100)
humidifier_ip = os.getenv("HUMIDIFIER_IP")

# Define VPD thresholds
VPD_DAY_MIN = float(os.getenv("VPD_DAY_MIN", 0.8))  
VPD_DAY_MAX = float(os.getenv("VPD_DAY_MAX", 1.5))  

#VPD_DAY_TARGET = float(os.getenv("VPD_NIGHT_TARGET", 1.2)) 
#VPD_DAY_RANGE = float(os.getenv("VPD_NIGHT_RANGE", 0.2)) 
#VPD_DAY_MIN = VPD_DAY_TARGET - VPD_DAY_RANGE
#VPD_DAY_MAX = VPD_DAY_TARGET + VPD_DAY_RANGE

VPD_NIGHT_TARGET = float(os.getenv("VPD_NIGHT_TARGET", 1.25))  
VPD_NIGHT_RANGE = float(os.getenv("VPD_NIGHT_RANGE", 0.2)) 
VPD_NIGHT_MIN = VPD_NIGHT_TARGET - VPD_NIGHT_RANGE
VPD_NIGHT_MAX = VPD_NIGHT_TARGET + VPD_NIGHT_RANGE

HUMIDITY_OVERRIDE_THRESHOLD = os.getenv("HUMIDITY_OVERRIDE_THRESHOLD", "40").strip()

# Ensure the value is a valid integer
try:
    HUMIDITY_OVERRIDE_THRESHOLD = int(HUMIDITY_OVERRIDE_THRESHOLD)
except ValueError:
    print(f"⚠️ Warning: Invalid HUMIDITY_OVERRIDE_THRESHOLD='{HUMIDITY_OVERRIDE_THRESHOLD}', using default (40).")
    HUMIDITY_OVERRIDE_THRESHOLD = 40  # Default value if parsing fails

# Convert day and night start times to integers (default: 16 for day, 10 for night)
DAY_START = int(os.getenv("DAY_START", 16))  # Ensure it's an integer
NIGHT_START = int(os.getenv("NIGHT_START", 10))  # Ensure it's an integer

def is_daytime():
    """Check if it's daytime based on the 24-hour schedule."""
    current_hour = datetime.datetime.now().hour
    return current_hour >= DAY_START or current_hour < NIGHT_START  # 16:00-10:00 = Daytime, 10:00-16:00 = Nighttime

async def get_sensor_data():
    """
    Fetch temperature and humidity from Tapo sensor.
    Ensures no NoneType values are returned.
    Returns: (air_temperature, leaf_temperature, humidity)
    """

    client = ApiClient(tapo_username, tapo_password)
    hub = await client.h100(sensor_ip)

    child_device_list = await hub.get_child_device_list()
    for child in child_device_list:
        if isinstance(child, T31XResult):  # Ensure it's a T31X sensor
            air_temp = round(child.current_temperature or 0, 1)
            leaf_temp = round(max(air_temp - 1.2, 0), 1)  # Estimated leaf temp
            humidity = round(child.current_humidity or 0, 1)

            return air_temp, leaf_temp, humidity

    print("⚠️ No valid sensor data found! Using default values (20°C, 18.8°C, 50%).")
    return 20.0, 18.8, 50.0  # Default values to prevent errors

async def toggle_humidifier(vpd_air, vpd_leaf, humidity, daytime):
    """
    Turn the humidifier ON/OFF based on VPD and time of day.
    If humidity < 40%, force humidifier ON.
    """

    client = ApiClient(tapo_username, tapo_password)
    humidifier = await client.p100(humidifier_ip)

    if humidity < HUMIDITY_OVERRIDE_THRESHOLD:
        print("⚠️ Humidity too low (<40%)! Forcing humidifier ON.")
        await humidifier.on()
        return  # Skip normal VPD-based logic if override is active

    if daytime:
        if vpd_air > VPD_DAY_MAX or vpd_leaf > VPD_DAY_MAX:
            print("🌞 Daytime: VPD too high! Turning ON the humidifier...")
            await humidifier.on()
        elif vpd_air < VPD_DAY_MIN or vpd_leaf < VPD_DAY_MIN:
            print("🌞 Daytime: VPD too low! Turning OFF the humidifier...")
            await humidifier.off()
    else:
        if vpd_air > VPD_NIGHT_MAX or vpd_leaf > VPD_NIGHT_MAX:
            print("🌙 Nighttime: VPD too high! Turning ON the humidifier...")
            await humidifier.on()
        elif vpd_air < VPD_NIGHT_MIN or vpd_leaf < VPD_NIGHT_MIN:
            print("🌙 Nighttime: VPD too low! Turning OFF the humidifier...")
            await humidifier.off()

async def toggle_exhaust(vpd_air, vpd_leaf, humidity, daytime):
    """
    Turn the exhaust fan ON/OFF based on VPD and time of day.
    If humidity < 40%, force exhaust fan OFF (prevents excess drying).
    """
    tapo_username = os.getenv("TAPO_USERNAME")
    tapo_password = os.getenv("TAPO_PASSWORD")
    exhaust_ip = os.getenv("EXHAUST_IP")

    client = ApiClient(tapo_username, tapo_password)
    exhaust_fan = await client.p100(exhaust_ip)

    if humidity < HUMIDITY_OVERRIDE_THRESHOLD:
        print("⚠️ Humidity too low (<40%)! Forcing exhaust fan OFF.")
        await exhaust_fan.off()
        return  # Skip normal VPD-based logic if override is active

    if daytime:
        if vpd_air > VPD_DAY_MAX or vpd_leaf > VPD_DAY_MAX:
            print("🌞 Daytime: VPD too high! Turning ON the exhaust fan...")
            await exhaust_fan.on()
        elif vpd_air < VPD_DAY_MIN or vpd_leaf < VPD_DAY_MIN:
            print("🌞 Daytime: VPD too low! Turning OFF the exhaust fan...")
            await exhaust_fan.off()
    else:
        if vpd_air > VPD_NIGHT_MAX or vpd_leaf > VPD_NIGHT_MAX:
            print("🌙 Nighttime: VPD too high! Turning ON the exhaust fan...")
            await exhaust_fan.on()
        elif vpd_air < VPD_NIGHT_MIN or vpd_leaf < VPD_NIGHT_MIN:
            print("🌙 Nighttime: VPD too low! Turning OFF the exhaust fan...")
            await exhaust_fan.off()

async def monitor_vpd():
    """
    Continuously monitor VPD and adjust humidifier/exhaust reactively.
    """
    while True:
        daytime = is_daytime()  # Check if it's day or night
        air_temp, leaf_temp, humidity = await get_sensor_data()
        
        # Calculate both Air VPD & Leaf VPD
        vpd_air, vpd_leaf = calculate_vpd(air_temp, leaf_temp, humidity)

        # Print status
        print(f"Air temperature: {air_temp}C")
        print(f"Leaf temperature: {leaf_temp}C")
        print(f"Humidity: {humidity}%")
        print(f"Air VPD: {vpd_air} kPa")
        print_vpd_status(vpd_air, vpd_leaf)
        
         # Get timestamp
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Log data
        log_to_csv(timestamp, air_temp, leaf_temp, humidity, vpd_air, vpd_leaf)
        log_to_json(timestamp, air_temp, leaf_temp, humidity, vpd_air, vpd_leaf)       

        # Adjust devices based on BOTH Air & Leaf VPD and time of day
        await toggle_humidifier(vpd_air, vpd_leaf, humidity, daytime)
        await toggle_exhaust(vpd_air, vpd_leaf, humidity, daytime)

        print("🔄 Waiting 30 seconds before next check...")
        await asyncio.sleep(30)  # Check every 10 seconds

if __name__ == "__main__":
    asyncio.run(monitor_vpd())
