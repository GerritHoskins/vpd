import json
import os

LOG_JSON_FILE = "vpd_log.json"

def log_to_json(timestamp, air_temp, leaf_temp, humidity, vpd_air, vpd_leaf):
    """Logs the sensor data to a JSON file with UTF-8 encoding to prevent character issues."""
    log_entry = {
        "Timestamp": timestamp,
        "Air Temperature (°C)": air_temp,
        "Leaf Temperature (°C)": leaf_temp,
        "Humidity (%)": humidity,
        "Air VPD (kPa)": vpd_air,
        "Leaf VPD (kPa)": vpd_leaf
    }

    # Load existing JSON data
    if os.path.exists(LOG_JSON_FILE):
        with open(LOG_JSON_FILE, "r", encoding="utf-8") as file:
            try:
                data = json.load(file)
            except json.JSONDecodeError:
                data = []
    else:
        data = []

    # Append new entry and save
    data.append(log_entry)

    with open(LOG_JSON_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)
