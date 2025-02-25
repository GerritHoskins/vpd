import joblib
import os
import sys
import time
import requests
import asyncio
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.calculate import calculate_vpd
from utils.logs import log_to_csv
from api.tapo_controller import (
    toggle_exhaust,
    toggle_dehumidifier,
    toggle_humidifier,
    get_sensor_data,
    air_exchange_cycle
)
from model.train_rl_agent import choose_best_action
from api.device_status import get_device_status
from api.state import state
from config.settings import ACTION_MAP, MAX_HUMIDITY_LEVELS, BASE_URL, KPA_TOLERANCE, PROXY_URL, Q_TABLE_PATH
from api.actions import is_override_active


def load_q_table():
    if os.path.exists(Q_TABLE_PATH):
        Q_table = joblib.load(Q_TABLE_PATH)
        print("✅ Q-table loaded successfully.")
        return Q_table
    else:
        print("❌ Error: Q-table file not found.")
        exit()


async def start_anomaly_detection(sensor_data):
    try:
        response = requests.post(f"{PROXY_URL}/detect_anomaly", json=sensor_data)
        response.raise_for_status()
        anomaly_response = response.json()

        if anomaly_response.get('anomaly_detected', False):
            print("🚨 Anomaly detected! Skipping adjustments.")
            return True

    except requests.RequestException as e:
        print(f"❌ Error during anomaly detection request: {e}")
        return True

    return False


async def sync_device_states(action_dict, humidity, max_humidity, air_temp):
    if air_temp > MAX_AIR_TEMP:
        action_dict["exhaust"] = True
        print("🔥 Air temperature above 26°C: Ensuring exhaust is ON.")

    for device, target_state in action_dict.items():
        if device not in ["exhaust", "humidifier", "dehumidifier"]:
            print(f"⚠️ Unknown device '{device}', skipping...")
            continue

        if is_override_active(device):
            print(f"🚫 Skipping {device} due to override")
            continue

        if device == "humidifier" and (state.get("dehumidifier", False) or humidity >= max_humidity):
            print("⚠️ Skipping humidifier ON due to active dehumidifier or humidity within optimal range.")
            continue

        if device == "dehumidifier" and (state.get("humidifier", False) or humidity <= max_humidity - 5):
            print("⚠️ Skipping dehumidifier ON due to active humidifier or humidity within optimal range.")
            continue

        print(f"🔄 Toggling {device} {'ON' if target_state else 'OFF'}")

        if device == "exhaust":
            await toggle_exhaust(target_state)
        elif device == "humidifier":
            await toggle_humidifier(target_state)
        elif device == "dehumidifier":
            await toggle_dehumidifier(target_state)

        state[device] = target_state


def discretize_state(humidity, leaf_temp, air_temp, vpd_air, vpd_leaf):
    return (
        round(humidity / 5) * 5,
        round(leaf_temp, 1),
        round(air_temp, 1),
        round(vpd_air, 1),
        round(vpd_leaf, 1)
    )

async def monitor_vpd(target_vpd_min, target_vpd_max, Q_table):
    last_air_exchange = time.time()

    print(f"✅ Monitoring VPD: {target_vpd_min}-{target_vpd_max} kPa")

    while True:
        air_temp, leaf_temp, humidity = await get_sensor_data()
        vpd_air, vpd_leaf = calculate_vpd(air_temp, leaf_temp, humidity)

        sensor_data = {
            'temperature': air_temp,
            'leaf_temperature': leaf_temp,
            'humidity': humidity,
            'vpd_air': vpd_air,
            'vpd_leaf': vpd_leaf
        }

        if await start_anomaly_detection(sensor_data):
            await asyncio.sleep(5)
            continue

        grow_stage = state.get("grow_stage", "vegetative")
        max_humidity = MAX_HUMIDITY_LEVELS.get(grow_stage, 60)

        state_tuple = discretize_state(humidity, leaf_temp, air_temp, vpd_air, vpd_leaf)
        best_action = choose_best_action(state_tuple, Q_table)
        recommended_action = ACTION_MAP.get(best_action, {})

        await sync_device_states(recommended_action, humidity, max_humidity, air_temp)

        log_to_csv(time.time(), air_temp, leaf_temp, humidity, vpd_air, vpd_leaf,
                   state["exhaust"], state["humidifier"], state["dehumidifier"])

        last_air_exchange = await air_exchange_cycle(last_air_exchange, target_vpd_min, target_vpd_max)

        print("🔄 Waiting 5 seconds...")
        await asyncio.sleep(5)


if __name__ == "__main__":
    state["everything_ok"] = True
    response = requests.get(f"{BASE_URL}/get_vpd_target").json()

    target_vpd_min = float(response.get("target_vpd_min", 1.2))
    target_vpd_max = float(response.get("target_vpd_max", 1.6))

    Q_table = load_q_table()

    asyncio.run(monitor_vpd(target_vpd_min, target_vpd_max, Q_table))
