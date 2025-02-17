import os
import sys
from dotenv import load_dotenv
from tapo import ApiClient

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from api.state import state

load_dotenv()

tapo_username = os.getenv("TAPO_USERNAME")
tapo_password = os.getenv("TAPO_PASSWORD")

hub_ip = os.getenv("HUB_IP")  # IP of Tapo hub hub (H100)
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

async def force_on_humidifier():
    humidifier = await client.p115(humidifier_ip)
    state["humidifier"] = True
    await humidifier.on()

async def force_off_humidifier():
    humidifier = await client.p115(humidifier_ip)
    state["humidifier"] = False
    await humidifier.off()

async def force_off_exhaust():
    exhaust = await client.p100(exhaust_ip)
    state["exhaust"] = False
    await exhaust.off()
    
async def force_on_exhaust():
    exhaust = await client.p100(exhaust_ip)
    state["exhaust"] = True
    await exhaust.on()

async def toggle_humidifier(target_vpd, vpd_leaf, vpd_air, humidity, daytime, tolerance=0.02):
    """
    Turn the humidifier ON/OFF based on user-defined VPD and humidity conditions.
    Prevents redundant toggling.
    """
    vpd_min = target_vpd - tolerance
    vpd_max = target_vpd + tolerance

    if humidity < HUMIDITY_OVERRIDE_THRESHOLD:
        if not state["humidifier"]:
            print("⚠️ Humidity too low (<40%)! Forcing humidifier ON.")
            await force_on_humidifier()
        return

    if vpd_leaf < vpd_min:
        if not state["humidifier"]:
            print("💦 VPD too low! Turning ON the humidifier...")
            await force_on_humidifier()
    elif vpd_leaf > vpd_max:
        if state["humidifier"]:
            print("🌬️ VPD too high! Turning OFF the humidifier...")
            await force_off_humidifier()

async def toggle_exhaust(target_vpd, vpd_leaf, vpd_air, humidity, daytime, tolerance=0.02):
    """
    Turn the exhaust fan ON/OFF based on user-defined VPD and humidity conditions.
    Prevents redundant toggling.
    """
    vpd_min = target_vpd - tolerance
    vpd_max = target_vpd + tolerance

    if humidity < HUMIDITY_OVERRIDE_THRESHOLD:
        if state["exhaust"]:
            print("⚠️ Humidity too low (<40%)! Forcing exhaust OFF.")
            await force_off_exhaust()
        return

    if vpd_leaf > vpd_max:
        if not state["exhaust"]:
            print("🌬️ VPD too high! Turning ON the exhaust fan...")
            await force_on_exhaust()
    elif vpd_leaf < vpd_min:
        if state["exhaust"]:
            print("💨 VPD too low! Turning OFF the exhaust fan...")
            await force_off_exhaust()
