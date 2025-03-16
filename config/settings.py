import os
from dotenv import load_dotenv

load_dotenv()

TAPO_USERNAME = 
TAPO_PASSWORD =
HUB_IP = 
HUMIDIFIER_IP = 
EXHAUST_IP = 
DEHUMIDIFIER_IP =

FASTAPI_URL = 
PROXY_URL = 
WS_URL =
BASE_URL =

CONTROL_INTERVAL = 30

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

MAX_HUMIDITY_LEVELS = {"propagation": 70, "vegetative": 60, "flowering": 50}
MIN_HUMIDITY_LEVELS = {"propagation": 65, "vegetative": 55, "flowering": 40}
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

COLUMN_MAPPING = {
    "Air Temperature (°C)": "temperature",
    "Leaf Temperature (°C)": "leaf_temperature",
    "Humidity (%)": "humidity",
    "Air VPD (kPa)": "vpd_air",
    "Leaf VPD (kPa)": "vpd_leaf",
    "Exhaust": "exhaust",
    "Humidifier": "humidifier",
    "Dehumidifier": "dehumidifier"
}

MODEL_DIR = os.path.join(os.path.dirname(__file__), "../model")
Q_TABLE_PATH = os.path.join(MODEL_DIR, "q_learning.pkl")
EXHAUST_MODEL_PATH = os.path.join(MODEL_DIR, "exhaust_model.pkl")
HUMIDIFIER_MODEL_PATH = os.path.join(MODEL_DIR, "humidifier_model.pkl")
DEHUMIDIFIER_MODEL_PATH = os.path.join(MODEL_DIR, "dehumidifier_model.pkl")
ANOMALY_MODEL_PATH = os.path.join(MODEL_DIR, "anomaly_detector.pkl")


CSV_FILE = os.path.join(os.path.dirname(__file__), "../vpd_log.csv")
