import os
import sys
import numpy as np
import pandas as pd
import joblib
from collections import defaultdict

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config.settings import ACTION_MAP, MODEL_DIR, CSV_FILE


def ensure_directories():
    """Ensure necessary directories exist."""
    os.makedirs(MODEL_DIR, exist_ok=True)


def load_dataset(csv_file):
    """Load and validate dataset from CSV file."""
    if not os.path.exists(csv_file):
        print(f"❌ Error: '{csv_file}' not found! Please ensure it exists.")
        exit()

    data = pd.read_csv(csv_file)
    print("✅ Dataset loaded successfully!")
    return data


def preprocess_data(data):
    """Rename columns and handle missing columns."""
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

    required_columns = list(column_mapping.values())
    missing_cols = [col for col in required_columns if col not in data.columns]

    if missing_cols:
        print(f"⚠️ Warning: Missing columns {missing_cols}, filling with zeros.")
        for col in missing_cols:
            data[col] = 0

    return data


def train_q_learning(data, alpha=0.1, gamma=0.9, epsilon=0.1):
    """Train Q-learning model based on provided data."""
    Q_table = defaultdict(lambda: np.zeros(len(ACTION_MAP), dtype=np.float32))

    for _, row in data.iterrows():
        state = tuple(float(row[col]) for col in ["humidity", "leaf_temperature", "temperature", "vpd_air", "vpd_leaf"])
        action = np.random.choice(len(ACTION_MAP))
        reward = -abs(row["vpd_leaf"] - 1.4)

        best_next_action = np.argmax(Q_table[state])
        Q_table[state][action] += alpha * (reward + gamma * Q_table[state][best_next_action] - Q_table[state][action])

    return Q_table


def save_model(Q_table, path):
    """Save trained Q-table to file."""
    Q_table_dict = {state: actions for state, actions in Q_table.items()}
    joblib.dump(Q_table_dict, path)
    print(f"✅ Reinforcement Learning Model saved successfully at {path}!")


def choose_best_action(state, Q_table):
    """Choose best action given the current state without unseen actions."""
    state = tuple(map(float, state))

    if state in Q_table:
        sorted_actions = np.argsort(Q_table[state])[::-1]
        best_action = next((a for a in sorted_actions if a in ACTION_MAP), 0)
    else:
        print(f"⚠️ Warning: Unseen state {state}, selecting default action 0.")
        best_action = 0

    return best_action


if __name__ == "__main__":
    ensure_directories()
    data = load_dataset(CSV_FILE)
    data = preprocess_data(data)

    Q_table = train_q_learning(data)
    save_model(Q_table, os.path.join(MODEL_DIR, "q_learning.pkl"))
