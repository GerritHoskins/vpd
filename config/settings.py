import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

TAPO_USERNAME = os.getenv("TAPO_USERNAME")
TAPO_PASSWORD = os.getenv("TAPO_PASSWORD")
HUB_IP = os.getenv("HUB_IP")
HUMIDIFIER_IP = os.getenv("HUMIDIFIER_IP")
EXHAUST_IP = os.getenv("EXHAUST_IP")
DEHUMIDIFIER_IP = os.getenv("DEHUMIDIFIER_IP")

FASTAPI_URL = "http://0.0.0.0:8001"
PROXY_URL = "http://127.0.0.1:5000"
 
BASE_URL = os.getenv('BASE_URL')

KPA_TOLERANCE = float(os.getenv("KPA_TOLERANCE", 0.1))
LEAF_TEMP_OFFSET = 1.0

# Define air exchange settings for each stage
AIR_EXCHANGE_SETTINGS = {
    "propagation": {"interval": 45 * 60, "duration": 2 * 60},  # Every 45 min, 2 min duration
    "vegetative": {"interval": 30 * 60, "duration": 4 * 60},  # Every 30 min, 4 min duration
    "flowering": {"interval": 20 * 60, "duration": 6 * 60},  # Every 20 min, 6 min duration
}

# Define different VPD target ranges for plant growth stages
VPD_TARGET = {"min": None, "max": None}
VPD_MODES = {
    "propagation": (0.4, 0.8),
    "vegetative": (0.8, 1.2),
    "flowering": (1.2, 1.6),
}
MAX_HUMIDITY_LEVELS = {"propagation": 70, "vegetative": 60, "flowering": 55}

DEVICE_MAP = {
    "sensor_hub": {"ip": HUB_IP, "type": "h100"},
    "exhaust": {"ip": EXHAUST_IP, "type": "p100"},
    "humidifier": {"ip": HUMIDIFIER_IP, "type": "p115"},
    "dehumidifier": {"ip": DEHUMIDIFIER_IP, "type": "p115"},
}

action_map = {
    0: "exhaust_on", 1: "exhaust_off",
    2: "humidifier_on", 3: "humidifier_off",
    4: "dehumidifier_on", 5: "dehumidifier_off"
}