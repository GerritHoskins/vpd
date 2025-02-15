import csv
import os

LOG_CSV_FILE = "vpd_log.csv"

def log_to_csv(timestamp, air_temp, leaf_temp, humidity, vpd_air, vpd_leaf):
    """Logs the sensor data to a CSV file with UTF-8 encoding to prevent character issues."""
    file_exists = os.path.isfile(LOG_CSV_FILE)

    with open(LOG_CSV_FILE, mode='a', newline='', encoding="utf-8") as file:
        writer = csv.writer(file)

        # Write headers only if the file is new
        if not file_exists:
            writer.writerow(["Timestamp", "Air Temperature (°C)", "Leaf Temperature (°C)", "Humidity (%)", "Air VPD (kPa)", "Leaf VPD (kPa)"])

        writer.writerow([timestamp, air_temp, leaf_temp, humidity, vpd_air, vpd_leaf])
