import os
import sys
import numpy as np
import pandas as pd
import joblib
from collections import defaultdict
from scipy.spatial import KDTree

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config.settings import MODEL_DIR, CSV_FILE, ACTION_MAP, MAX_HUMIDITY_LEVELS, VPD_MODES, COLUMN_MAPPING


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
    
    data.rename(columns=COLUMN_MAPPING, inplace=True)

    required_columns = list(COLUMN_MAPPING.values())
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


def build_state_lookup(Q_table):
    """Build a KDTree for fast nearest-neighbor lookup."""
    if not Q_table:
        return None, []

    known_states = np.array(list(Q_table.keys()))
    tree = KDTree(known_states)
    return tree, known_states


def choose_best_action(state, Q_table, state_tree, known_states, grow_stage, tolerance=1.0):
    """
    Choose the best action given the current state and growth stage.

    - If state exists in Q-table, use the best action.
    - If state is unseen, find the closest known state and use its best action.
    - If no similar states exist, default to a calculated best action.
    """
    state = tuple(map(float, state))

    if state in Q_table:
        sorted_actions = np.argsort(Q_table[state])[::-1]
        best_action = next((a for a in sorted_actions if a in ACTION_MAP), 1)
        return best_action

    if state_tree is not None:
        distance, index = state_tree.query(state)
        if distance < tolerance:
            closest_state = tuple(known_states[index])
            sorted_actions = np.argsort(Q_table[closest_state])[::-1]
            best_action = next((a for a in sorted_actions if a in ACTION_MAP), 1)
            print(f"⚠️ Warning: Unseen state {state}, using closest match {closest_state} with action {best_action}.")
            return best_action

    print(f"⚠️ Warning: Completely new state {state}, estimating best action.")

    humidity, leaf_temp, air_temp, vpd_air, vpd_leaf = state
    max_humidity = MAX_HUMIDITY_LEVELS.get(grow_stage, 60)
    vpd_min, vpd_max = VPD_MODES.get(grow_stage, (0.8, 1.2))

    actions = {}

    if air_temp > 26.0 or vpd_leaf > vpd_max:
        actions["exhaust"] = True  # Turn ON exhaust
        actions["dehumidifier"] = False
    elif vpd_leaf < vpd_min:
        actions["exhaust"] = False  # Turn OFF exhaust

    if humidity > max_humidity:
        actions["humidifier"] = False  # Turn OFF humidifier
        actions["dehumidifier"] = True  # Turn ON dehumidifier
        actions["exhaust"] = True
    elif humidity < max_humidity - 5:  # Allow 5% buffer
        actions["humidifier"] = True  # Turn ON humidifier
        actions["dehumidifier"] = False  # Turn OFF dehumidifier

    for action, state in ACTION_MAP.items():
        if state == actions:
            return action

    return 1  # Default to keeping exhaust OFF


if __name__ == "__main__":
    ensure_directories()
    data = load_dataset(CSV_FILE)
    data = preprocess_data(data)

    Q_table = train_q_learning(data)
    save_model(Q_table, os.path.join(MODEL_DIR, "q_learning.pkl"))

    state_tree, known_states = build_state_lookup(Q_table)
