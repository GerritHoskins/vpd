import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import joblib

# Load dataset (Ensure the file exists)
try:
    data = pd.read_csv("vpd_log.csv")
    print("✅ Dataset loaded successfully!")
except FileNotFoundError:
    print("❌ Error: vpd_log.csv not found!")
    exit()

# Rename CSV columns to match expected feature names
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
expected_columns = ['temperature', 'leaf_temperature', 'humidity', 'vpd_air', 'vpd_leaf', 'exhaust', 'humidifier', 'dehumidifier']

for col in expected_columns:
    if col not in data.columns:
        print(f"⚠️ Warning: Missing column '{col}', filling with default values.")
        data[col] = False if col in ['exhaust', 'humidifier', 'dehumidifier'] else np.nan

# Convert device state columns to boolean values
data['exhaust'] = data['exhaust'].astype(bool)
data['humidifier'] = data['humidifier'].astype(bool)
data['dehumidifier'] = data['dehumidifier'].astype(bool)

print("✅ Dataset processed with all expected columns.")

# Define features (inputs) and labels (outputs)
X = data[['temperature', 'leaf_temperature', 'humidity', 'vpd_air', 'vpd_leaf']]
y_exhaust = data['exhaust'].astype(int)  # Convert boolean to 0/1 for ML training
y_humidifier = data['humidifier'].astype(int)
y_dehumidifier = data['dehumidifier'].astype(int)

# Split dataset into training and testing
X_train, X_test, y_train_ex, y_test_ex = train_test_split(X, y_exhaust, test_size=0.2, random_state=42)
X_train, X_test, y_train_hum, y_test_hum = train_test_split(X, y_humidifier, test_size=0.2, random_state=42)
X_train, X_test, y_train_deh, y_test_deh = train_test_split(X, y_dehumidifier, test_size=0.2, random_state=42)

# Train Random Forest models
exhaust_model = RandomForestClassifier(n_estimators=100, random_state=42)
humidifier_model = RandomForestClassifier(n_estimators=100, random_state=42)
dehumidifier_model = RandomForestClassifier(n_estimators=100, random_state=42)

exhaust_model.fit(X_train, y_train_ex)
humidifier_model.fit(X_train, y_train_hum)
dehumidifier_model.fit(X_train, y_train_deh)

# Evaluate models
y_pred_ex = exhaust_model.predict(X_test)
y_pred_hum = humidifier_model.predict(X_test)
y_pred_deh = dehumidifier_model.predict(X_test)

print("📊 Model Accuracy Scores:")
print("   ✅ Exhaust Model Accuracy:", accuracy_score(y_test_ex, y_pred_ex))
print("   ✅ Humidifier Model Accuracy:", accuracy_score(y_test_hum, y_pred_hum))
print("   ✅ Dehumidifier Model Accuracy:", accuracy_score(y_test_deh, y_pred_deh))

# Save trained models
joblib.dump(exhaust_model, "model/exhaust_model.pkl")
joblib.dump(humidifier_model, "model/humidifier_model.pkl")
joblib.dump(dehumidifier_model, "model/dehumidifier_model.pkl")

print("✅ Models saved successfully!")
