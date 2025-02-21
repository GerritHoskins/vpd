import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
import joblib

# Load dataset
try:
    data = pd.read_csv("vpd_log.csv")
    print("✅ Dataset loaded successfully!")
except FileNotFoundError:
    print("❌ Error: vpd_log.csv not found!")
    exit()

data.rename(columns={
    "Air Temperature (°C)": "temperature",
    "Leaf Temperature (°C)": "leaf_temperature",
    "Humidity (%)": "humidity",
    "Air VPD (kPa)": "vpd_air",
    "Leaf VPD (kPa)": "vpd_leaf",
    "Exhaust": "exhaust",
    "Humidifier": "humidifier",
    "Dehumidifier": "dehumidifier"
}, inplace=True)

# Ensure all required columns exist (Fill missing columns with defaults)
features = ['temperature', 'leaf_temperature', 'humidity', 'vpd_air', 'vpd_leaf', 'exhaust', 'humidifier', 'dehumidifier']
X = data[features]

# Train Isolation Forest Model
anomaly_detector = IsolationForest(contamination=0.05, random_state=42)
anomaly_detector.fit(X)

# Save the model
joblib.dump(anomaly_detector, "model/anomaly_detector.pkl")
print("✅ Anomaly Detection Model saved successfully!")
