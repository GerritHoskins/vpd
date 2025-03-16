from api.tapo_client import get_tapo_client
from config.settings import DEVICE_MAP

async def get_device_status(device_name):
    """Fetch the status of any Tapo device dynamically."""
    
    if device_name not in DEVICE_MAP:
        raise ValueError(f"❌ Invalid device name: {device_name}")

    device_ip = DEVICE_MAP[device_name]["ip"]
    device_type = DEVICE_MAP[device_name]["type"]

    client = await get_tapo_client()
    device = await getattr(client, device_type)(device_ip)

    return await device.get_device_info()
