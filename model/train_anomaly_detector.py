import os
import sys
import pandas as pd
import joblib
from sklearn.ensemble import IsolationForest


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config.settings import COLUMN_MAPPING


csv_file = "vpd_log.csv"
if not os.path.exists(csv_file):
    print(f"❌ Error: '{csv_file}' not found! Ensure it exists in the root directory.")
    exit()

data = pd.read_csv(csv_file)
print("✅ Dataset loaded successfully!")

data.rename(columns=COLUMN_MAPPING, inplace=True)

features = ["temperature", "leaf_temperature", "humidity", "vpd_air", "vpd_leaf", "exhaust", "humidifier", "dehumidifier"]
data = data[features].fillna(0)

data.columns = data.columns.astype(str)

anomaly_detector = IsolationForest(contamination=0.05, random_state=42)
anomaly_detector.fit(data)

os.makedirs("model", exist_ok=True)
joblib.dump(anomaly_detector, "model/anomaly_detector.pkl")
print("✅ Anomaly Detection Model saved successfully!")
