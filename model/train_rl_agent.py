import numpy as np
import pandas as pd
import joblib
from collections import defaultdict

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


# Convert device actions to numeric values
action_map = {
    "exhaust_on": 0, "exhaust_off": 1,
    "humidifier_on": 2, "humidifier_off": 3,
    "dehumidifier_on": 4, "dehumidifier_off": 5
}

# Initialize Q-table (state-action rewards)
Q_table = defaultdict(lambda: np.zeros(len(action_map)))

# Hyperparameters
alpha = 0.1  # Learning rate
gamma = 0.9  # Discount factor
epsilon = 0.1  # Exploration rate

# Train Q-learning agent
for index, row in data.iterrows():
    state = (row["temperature"], row["humidity"], row["vpd_air"], row["vpd_leaf"])
    action = np.random.choice(list(action_map.values()))  # Random action
    reward = -abs(row["vpd_leaf"] - 1.4)  # Reward closer to 1.2 kPa VPD

    # Q-learning update
    best_next_action = np.argmax(Q_table[state])
    Q_table[state][action] += alpha * (reward + gamma * np.max(Q_table[state]) - Q_table[state][action])

# Save Q-table
joblib.dump(dict(Q_table), "model/q_learning.pkl")
print("✅ Reinforcement Learning Model saved successfully!")

def choose_best_action(state):
    """Selects the best action for a given sensor state using Q-learning."""
    if state in Q_table:
        return np.argmax(Q_table[state])  # Choose action with highest reward
    else:
        return np.random.choice(list(range(6)))  # If unknown, pick random action
