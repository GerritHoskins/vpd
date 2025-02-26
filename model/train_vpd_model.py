import os
import sys
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import joblib

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config.settings import COLUMN_MAPPING

try:
    data = pd.read_csv("vpd_log.csv")
    print("✅ Dataset loaded successfully!")
except FileNotFoundError:
    print("❌ Error: vpd_log.csv not found!")
    exit()

data.rename(columns=COLUMN_MAPPING, inplace=True)

expected_columns = [
    "temperature", "leaf_temperature", "humidity",
    "vpd_air", "vpd_leaf", "exhaust", "humidifier", "dehumidifier"
]

for col in expected_columns:
    if col not in data.columns:
        print(f"⚠️ Warning: Missing column '{col}', filling with default values.")
        if col in ["exhaust", "humidifier", "dehumidifier"]:
            data[col] = False  
        else:
            data[col] = np.nan 
            
data["exhaust"] = data["exhaust"].astype(bool)
data["humidifier"] = data["humidifier"].astype(bool)
data["dehumidifier"] = data["dehumidifier"].astype(bool)

print("✅ Dataset processed with all expected columns.")

X = data[["temperature", "leaf_temperature", "humidity", "vpd_air", "vpd_leaf"]]
y_exhaust = data["exhaust"].astype(int)
y_humidifier = data["humidifier"].astype(int)
y_dehumidifier = data["dehumidifier"].astype(int)

X_train, X_test, y_train_ex, y_test_ex = train_test_split(X, y_exhaust, test_size=0.2, random_state=42)
y_train_hum, y_test_hum = train_test_split(y_humidifier, test_size=0.2, random_state=42)
y_train_deh, y_test_deh = train_test_split(y_dehumidifier, test_size=0.2, random_state=42)

exhaust_model = RandomForestClassifier(n_estimators=100, random_state=42)
humidifier_model = RandomForestClassifier(n_estimators=100, random_state=42)
dehumidifier_model = RandomForestClassifier(n_estimators=100, random_state=42)

exhaust_model.fit(X_train, y_train_ex)
humidifier_model.fit(X_train, y_train_hum)
dehumidifier_model.fit(X_train, y_train_deh)

y_pred_ex = exhaust_model.predict(X_test)
y_pred_hum = humidifier_model.predict(X_test)
y_pred_deh = dehumidifier_model.predict(X_test)

print("📊 Model Accuracy Scores:")
print("   ✅ Exhaust Model Accuracy:", accuracy_score(y_test_ex, y_pred_ex))
print("   ✅ Humidifier Model Accuracy:", accuracy_score(y_test_hum, y_pred_hum))
print("   ✅ Dehumidifier Model Accuracy:", accuracy_score(y_test_deh, y_pred_deh))

model_dir = "model"
os.makedirs(model_dir, exist_ok=True)

joblib.dump(exhaust_model, os.path.join(model_dir, "exhaust_model.pkl"))
joblib.dump(humidifier_model, os.path.join(model_dir, "humidifier_model.pkl"))
joblib.dump(dehumidifier_model, os.path.join(model_dir, "dehumidifier_model.pkl"))

print("✅ Models saved successfully!")
