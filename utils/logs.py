import csv
import json
import os

LOG_CSV_FILE = "vpd_log.csv"
LOG_JSON_FILE = "vpd_log.json"

def log_to_csv(timestamp, air_temp, leaf_temp, humidity, vpd_air, vpd_leaf, exhaust_state, humidifier_state, dehumidifier_state):
    """Logs the sensor data to a CSV file with UTF-8 encoding to prevent character issues."""
    file_exists = os.path.isfile(LOG_CSV_FILE)

    with open(LOG_CSV_FILE, mode='a', newline='', encoding="utf-8") as file:
        writer = csv.writer(file)

        # Write headers only if the file is new
        if not file_exists:
            writer.writerow(["Timestamp", "Air Temperature (°C)", "Leaf Temperature (°C)", "Humidity (%)", "Air VPD (kPa)", "Leaf VPD (kPa)", "Exhaust", "Humidifier", "Dehumidifier"])

        writer.writerow([timestamp, air_temp, leaf_temp, humidity, vpd_air, vpd_leaf, exhaust_state, humidifier_state, dehumidifier_state])


def log_to_json(timestamp, air_temp, leaf_temp, humidity, vpd_air, vpd_leaf, exhaust_state, humidifier_state, dehumidifier_state):
    """Logs the sensor data to a JSON file with UTF-8 encoding to prevent character issues."""
    log_entry = {
        "Timestamp": timestamp,
        "Air Temperature (°C)": air_temp,
        "Leaf Temperature (°C)": leaf_temp,
        "Humidity (%)": humidity,
        "Air VPD (kPa)": vpd_air,
        "Leaf VPD (kPa)": vpd_leaf,
        "Exhaust": exhaust_state,
        "Humidifier": humidifier_state, 
        "Dehumidifier": dehumidifier_state
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
