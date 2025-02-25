import os
from dotenv import load_dotenv

load_dotenv()

TAPO_USERNAME = os.getenv("TAPO_USERNAME")
TAPO_PASSWORD = os.getenv("TAPO_PASSWORD")
HUB_IP = os.getenv("HUB_IP")
HUMIDIFIER_IP = os.getenv("HUMIDIFIER_IP")
EXHAUST_IP = os.getenv("EXHAUST_IP")
DEHUMIDIFIER_IP = os.getenv("DEHUMIDIFIER_IP")

FASTAPI_URL = "http://0.0.0.0:8001"
PROXY_URL = "http://127.0.0.1:5000"
WS_URL = "ws://localhost:8000/ws/vpd"
 
BASE_URL = os.getenv('BASE_URL')

KPA_TOLERANCE = float(os.getenv("KPA_TOLERANCE", 0.1))
LEAF_TEMP_OFFSET = 1.3

OVERRIDE_DURATION = 3000 

AIR_EXCHANGE_SETTINGS = {
    "propagation": {"interval": 45 * 60, "duration": 2 * 60},  # Every 45 min, 2 min duration
    "vegetative": {"interval": 30 * 60, "duration": 4 * 60},  # Every 30 min, 4 min duration
    "flowering": {"interval": 20 * 60, "duration": 6 * 60},  # Every 20 min, 6 min duration
}

VPD_TARGET = {"min": None, "max": None}
VPD_MODES = {
    "propagation": (0.4, 0.8),
    "vegetative": (0.8, 1.2),
    "flowering": (1.2, 1.6),
}

MAX_HUMIDITY_LEVELS = {"propagation": 70, "vegetative": 60, "flowering": 55}
MAX_AIR_TEMP = 26.0

DEVICE_MAP = {
    "sensor_hub": {"ip": HUB_IP, "type": "h100"},
    "exhaust": {"ip": EXHAUST_IP, "type": "p100"},
    "humidifier": {"ip": HUMIDIFIER_IP, "type": "p115"},
    "dehumidifier": {"ip": DEHUMIDIFIER_IP, "type": "p115"},
}

ACTION_MAP = {
    0: {"exhaust": True},  1: {"exhaust": False},
    2: {"humidifier": True}, 3: {"humidifier": False},
    4: {"dehumidifier": True}, 5: {"dehumidifier": False}
}

MODEL_DIR = os.path.join(os.path.dirname(__file__), "../model")
Q_TABLE_PATH = os.path.join(MODEL_DIR, "q_learning.pkl")

CSV_FILE = os.path.join(os.path.dirname(__file__), "../vpd_log.csv")
