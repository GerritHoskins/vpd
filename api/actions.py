from api.state import state
from config.settings import DEVICE_MAP
from api.tapo_client import get_tapo_client

async def toggle_device(device_name, state_requested):
    """Turn any Tapo device ON or OFF dynamically."""
    
    if device_name not in DEVICE_MAP:
        raise ValueError(f"❌ Invalid device name: {device_name}")

    device_ip = DEVICE_MAP[device_name]["ip"]
    device_type = DEVICE_MAP[device_name]["type"]

    client = await get_tapo_client()
    device = await getattr(client, device_type)(device_ip)

    try:
        if state_requested:
            print(f"🔄 Turning ON {device_name}...")
            await device.on()
            state[device_name] = True
        else:
            print(f"🔄 Turning OFF {device_name}...")
            await device.off()
            state[device_name] = False
    except Exception as e:
        print(f"⚠️ Failed to toggle {device_name}: {str(e)}")


async def toggle_humidifier(state_requested):
    """Turn the humidifier ON or OFF."""
    await toggle_device("humidifier", state_requested)

async def toggle_exhaust(state_requested):
    """Turn the exhaust ON or OFF."""
    await toggle_device("exhaust", state_requested)

async def toggle_dehumidifier(state_requested):
    """Turn the dehumidifier ON or OFF."""
    await toggle_device("dehumidifier", state_requested)
