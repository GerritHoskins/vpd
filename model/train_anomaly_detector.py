import os
import pandas as pd
import joblib
from sklearn.ensemble import IsolationForest

# ✅ Load dataset
csv_file = "vpd_log.csv"
if not os.path.exists(csv_file):
    print(f"❌ Error: '{csv_file}' not found! Ensure it exists in the root directory.")
    exit()

data = pd.read_csv(csv_file)
print("✅ Dataset loaded successfully!")

# ✅ Rename columns
column_mapping = {
    "Air Temperature (°C)": "temperature",
    "Leaf Temperature (°C)": "leaf_temperature",
    "Humidity (%)": "humidity",
    "Air VPD (kPa)": "vpd_air",
    "Leaf VPD (kPa)": "vpd_leaf",
    "Exhaust": "exhaust",
    "Humidifier": "humidifier",
    "Dehumidifier": "dehumidifier"
}
data.rename(columns=column_mapping, inplace=True)

# ✅ Ensure all required columns exist
features = ["temperature", "leaf_temperature", "humidity", "vpd_air", "vpd_leaf", "exhaust", "humidifier", "dehumidifier"]
data = data[features].fillna(0)  # Fill missing values with 0

# ✅ Convert column names to strings
data.columns = data.columns.astype(str)

# ✅ Train model
anomaly_detector = IsolationForest(contamination=0.05, random_state=42)
anomaly_detector.fit(data)

# ✅ Save model
os.makedirs("model", exist_ok=True)
joblib.dump(anomaly_detector, "model/anomaly_detector.pkl")
print("✅ Anomaly Detection Model saved successfully!")
