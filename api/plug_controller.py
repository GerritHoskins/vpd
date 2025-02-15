import os
from dotenv import load_dotenv
from tapo import ApiClient
from tapo.requests import AlarmRingtone, AlarmVolume, AlarmDuration
from tapo.responses import T31XResult

load_dotenv()

tapo_username = os.getenv("TAPO_USERNAME")
tapo_password = os.getenv("TAPO_PASSWORD")

sensor_ip = os.getenv("SENSOR_IP")  # IP of Tapo sensor hub (H100)
humidifier_ip = os.getenv("HUMIDIFIER_IP")
exhaust_ip = os.getenv("EXHAUST_IP")

VPD_DAY_MIN = float(os.getenv("VPD_DAY_MIN", 0.8))  
VPD_DAY_MAX = float(os.getenv("VPD_DAY_MAX", 1.5))  
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
    

client = ApiClient(tapo_username, tapo_password)

async def force_off_humidifier():
    humidifier = await client.p100(humidifier_ip)
    await humidifier.off()

async def force_off_exhaust():
    exhaust = await client.p100(exhaust_ip)
    await exhaust.off()

async def toggle_humidifier(vpd_air, target_vpd, humidity, daytime, tolerance=0.2):
    """
    Turn the humidifier ON/OFF based on user-defined VPD and humidity conditions.
    """
    humidifier = await client.p100(humidifier_ip)
    vpd_min = target_vpd - tolerance
    vpd_max = target_vpd + tolerance

    if humidity < HUMIDITY_OVERRIDE_THRESHOLD:
        print("⚠️ Humidity too low (<40%)! Forcing humidifier ON.")
        await humidifier.on()
        return  # Skip normal VPD-based logic if override is active

    if vpd_air > vpd_max:
        print("🔥 VPD too high! Turning ON the humidifier...")
        await humidifier.on()
    elif vpd_air < vpd_min:
        print("💧 VPD too low! Turning OFF the humidifier...")
        await humidifier.off()


async def toggle_exhaust(vpd_air, target_vpd, humidity, daytime, tolerance=0.2):
    """
    Turn the exhaust fan ON/OFF based on user-defined VPD and humidity conditions.
    """
    exhaust_fan = await client.p100(exhaust_ip)
    vpd_min = target_vpd - tolerance
    vpd_max = target_vpd + tolerance

    if humidity < HUMIDITY_OVERRIDE_THRESHOLD:
        print("⚠️ Humidity too low (<40%)! Forcing exhaust OFF.")
        await exhaust_fan.off()
        return  # Skip normal VPD-based logic if override is active

    if vpd_air > vpd_max:
        print("🌬️ VPD too high! Turning ON the exhaust fan...")
        await exhaust_fan.on()
    elif vpd_air < vpd_min:
        print("💨 VPD too low! Turning OFF the exhaust fan...")
        await exhaust_fan.off()
