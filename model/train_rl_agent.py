import os
import sys
import numpy as np
import pandas as pd
import joblib
from collections import defaultdict

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config.settings import action_map

# ✅ Ensure the 'model' directory exists
MODEL_DIR = os.path.join(os.path.dirname(__file__), "../model")
os.makedirs(MODEL_DIR, exist_ok=True)

# ✅ Load dataset
CSV_FILE = os.path.join(os.path.dirname(__file__), "../vpd_log.csv")
if not os.path.exists(CSV_FILE):
    print(f"❌ Error: '{CSV_FILE}' not found! Please ensure it exists in the root directory.")
    exit()

data = pd.read_csv(CSV_FILE)
print("✅ Dataset loaded successfully!")

# ✅ Rename columns to expected format
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

# ✅ Ensure all required columns exist (Fill missing with 0)
required_columns = list(column_mapping.values())
missing_cols = [col for col in required_columns if col not in data.columns]

if missing_cols:
    print(f"⚠️ Warning: Missing columns {missing_cols}, filling with default values.")
    for col in missing_cols:
        data[col] = 0  # Default to 0

# ✅ Initialize Q-table (state-action rewards) with proper tuple-based keys
# ✅ Ensure states are stored as tuples of floats in Q-table
Q_table = defaultdict(lambda: np.zeros(len(action_map), dtype=np.float32))

# ✅ Hyperparameters
alpha = 0.1  # Learning rate
gamma = 0.9  # Discount factor
epsilon = 0.1  # Exploration rate

for _, row in data.iterrows():
    state = (
        float(row["temperature"]),
        float(row["humidity"]),
        float(row["vpd_air"]),
        float(row["vpd_leaf"])
    )

    action = np.random.choice(list(range(len(action_map))))  # ✅ Ensure action is an integer
    reward = -abs(row["vpd_leaf"] - 1.4)  # Reward closer to 1.4 kPa

    # ✅ Convert state to tuple of floats before using in Q_table
    state = tuple(map(float, state))
    
    # ✅ Fix IndexError by using int(action) as index
    best_next_action = np.argmax(Q_table[state])
    Q_table[state][int(action)] += alpha * (reward + gamma * np.max(Q_table[state]) - Q_table[state][int(action)])

# ✅ Save Q-table
Q_table_dict = {tuple(map(float, key)): value for key, value in Q_table.items()}  # Ensure keys are tuples
q_table_path = os.path.join(MODEL_DIR, "q_learning.pkl")
joblib.dump(Q_table_dict, q_table_path)

print(f"✅ Reinforcement Learning Model saved successfully at {q_table_path}!")

def choose_best_action(state):
    """Selects the best action for a given sensor state using Q-learning."""
    state = tuple(map(float, state))  # Ensure proper format
    if state in Q_table:
        return int(np.argmax(Q_table[state]))  # ✅ Ensure action is returned as an integer
    else:
        print("⚠️ Warning: Unseen state, taking random action")
        return np.random.choice(len(action_map))  # If unknown, pick random action
