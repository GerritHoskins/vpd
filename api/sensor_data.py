import sys
import os
# Ensure the utils module is found
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
from tapo import ApiClient
from tapo.responses import T31XResult

load_dotenv()

tapo_username = os.getenv("TAPO_USERNAME")
tapo_password = os.getenv("TAPO_PASSWORD")

sensor_ip = os.getenv("SENSOR_IP")  # IP of Tapo sensor hub (H100)
humidifier_ip = os.getenv("HUMIDIFIER_IP")

# Convert day and night start times to integers (default: 16 for day, 10 for night)
DAY_START = int(os.getenv("DAY_START", 16))  # Ensure it's an integer
NIGHT_START = int(os.getenv("NIGHT_START", 10))  # Ensure it's an integer

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
            leaf_temp = round(max(air_temp - 1.0, 0), 1)  # Estimated leaf temp
            humidity = round(child.current_humidity or 0, 1)

            return air_temp, leaf_temp, humidity

    print("⚠️ No valid sensor data found! Using default values (20°C, 18.8°C, 50%).")
    return 20.0, 18.8, 50.0  # Default values to prevent errors
