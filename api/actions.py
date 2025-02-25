import time
from api.state import state
from config.settings import DEVICE_MAP, OVERRIDE_DURATION
from api.tapo_client import get_tapo_client

async def toggle_device(device_name, state_requested):
    """Turn any Tapo device ON or OFF dynamically while respecting manual overrides."""
    
    if device_name not in DEVICE_MAP:
        raise ValueError(f"❌ Invalid device name: {device_name}")

    device_ip = DEVICE_MAP[device_name]["ip"]
    device_type = DEVICE_MAP[device_name]["type"]

    client = await get_tapo_client()
    device = await getattr(client, device_type)(device_ip)

    try:
        if state_requested:
            print(f"🔄 Turning ON {device_name}... (Override Active)")
            await device.on()
            state[device_name] = True
        else:
            print(f"🔄 Turning OFF {device_name}... (Override Active)")
            await device.off()
            state[device_name] = False

        # ✅ Store the manual override timestamp
        state["overrides"][device_name] = {"state": state_requested, "timestamp": time.time()}

    except Exception as e:
        print(f"⚠️ Failed to toggle {device_name}: {str(e)}")


def is_override_active(device_name):
    """Check if an override is still active."""
    if device_name in state["overrides"]:
        override_time = state["overrides"][device_name]["timestamp"]
        if time.time() - override_time < OVERRIDE_DURATION:
            return True  # Override is still active
        else:
            del state["overrides"][device_name]  # Remove expired override
    return False


async def toggle_humidifier(state_requested):
    """Turn the humidifier ON or OFF while respecting manual override."""
    if is_override_active("humidifier"):
        print("🚫 Skipping humidifier adjustment due to manual override")
        return
    await toggle_device("humidifier", state_requested)


async def toggle_exhaust(state_requested):
    """Turn the exhaust ON or OFF while respecting manual override."""
    if is_override_active("exhaust"):
        print("🚫 Skipping exhaust adjustment due to manual override")
        return
    await toggle_device("exhaust", state_requested)


async def toggle_dehumidifier(state_requested):
    """Turn the dehumidifier ON or OFF while respecting manual override."""
    if is_override_active("dehumidifier"):
        print("🚫 Skipping dehumidifier adjustment due to manual override")
        return
    await toggle_device("dehumidifier", state_requested)
