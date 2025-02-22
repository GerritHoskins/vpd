from flask import Flask, request, jsonify, request, Response
import requests
import joblib
import asyncio
import pandas as pd
import numpy as np
from tapo_controller import get_device_status, toggle_humidifier, toggle_dehumidifier, get_dehumidifier_info_json, toggle_exhaust, get_sensor_data, get_exhaust_info_json, get_humidifier_info_json
from utils.calculate import calculate_vpd
from state import state  
from flask_cors import CORS
from utils.config import action_map, VPD_TARGET, VPD_MODES

app = Flask(__name__)
CORS(app, supports_credentials=True)

try:
    Q_table = joblib.load("model/q_learning.pkl")
    print("✅ Q-table loaded successfully!")
except FileNotFoundError:
    print("❌ Error: Q-table not found! Reinforcement learning is disabled.")
    Q_table = {}

# **Load trained ML models**
try:
    exhaust_model = joblib.load("model/exhaust_model.pkl")
    humidifier_model = joblib.load("model/humidifier_model.pkl")
    dehumidifier_model = joblib.load("model/dehumidifier_model.pkl")
    anomaly_detector = joblib.load("model/anomaly_detector.pkl")
    print("✅ All models loaded successfully!")
except FileNotFoundError as e:
    print(f"❌ Error loading models: {e}")
    
FASTAPI_URL = "http://127.0.0.1:8001"  # FastAPI server URL

@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.json

        # ✅ Ensure all expected fields exist
        required_fields = ["temperature", "leaf_temperature", "humidity", "vpd_air", "vpd_leaf"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        # Extract values from request
        features = np.array([[data["temperature"], data["leaf_temperature"], data["humidity"], data["vpd_air"], data["vpd_leaf"]]])

        # Make Predictions
        exhaust_prediction = exhaust_model.predict(features)[0]
        humidifier_prediction = humidifier_model.predict(features)[0]
        dehumidifier_prediction = dehumidifier_model.predict(features)[0]

        return jsonify({
            "exhaust": bool(exhaust_prediction),
            "humidifier": bool(humidifier_prediction),
            "dehumidifier": bool(dehumidifier_prediction),
        })

    except Exception as e:
        print(f"⚠️ Prediction error: {e}")
        return jsonify({"error": "Server error during prediction"}), 500
    

@app.route('/adjust_conditions', methods=['POST'])
async def adjust_conditions():
    """Automatically adjust devices based on ML predictions."""
    try:
        sensor_data = await get_sensor_data()  # Get real-time data from Tapo devices
        prediction = requests.post("http://127.0.0.1:5000/predict", json=sensor_data).json()

        # Toggle devices based on predictions
        await toggle_exhaust(prediction["exhaust"])
        await toggle_humidifier(prediction["humidifier"])
        await toggle_dehumidifier(prediction["dehumidifier"])

        return jsonify({
            "message": "Conditions adjusted successfully",
            "state": prediction
        })
    
    except Exception as e:
        print(f"⚠️ Error adjusting conditions: {e}")
        return jsonify({"error": "Failed to adjust conditions"}), 500
    

@app.route("/vpd", methods=["GET"])
def get_vpd_data():
    """Fetch latest VPD data from FastAPI."""
    try:
        response = requests.get(f"{FASTAPI_URL}/ws/vpd", stream=True)
        return Response(response.iter_content(), content_type=response.headers['Content-Type'])
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500

# Flask API Route to Get Device Status
@app.route('/device_status', methods=['GET'])
def device_status():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    device_info = loop.run_until_complete(get_device_status())
    return jsonify(device_info.to_dict())


# Flask API Route to Get Sensor Data (Temperature & Humidity)
@app.route('/sensor_data', methods=['GET'])
def sensor_data():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    response = loop.run_until_complete(get_sensor_data())
    return jsonify(response)


# Flask API Route to Turn On/Off Humidifier
@app.route('/humidifier/<state_requested>', methods=['POST'])
def humidifier_control(state_requested):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    if state_requested.lower() == "on":
        response = loop.run_until_complete(toggle_humidifier(True))
    elif state_requested.lower() == "off":
        response = loop.run_until_complete(toggle_humidifier(False))
    else:
        return jsonify({"error": "Invalid state. Use 'on' or 'off'."}), 400

    return jsonify(response)


# Flask API Route to Turn On/Off Humidifier
@app.route('/dehumidifier/<state_requested>', methods=['POST'])
def dehumidifier_control(state_requested):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    if state_requested.lower() == "on":
        response = loop.run_until_complete(toggle_dehumidifier(True))
    elif state_requested.lower() == "off":
        response = loop.run_until_complete(toggle_dehumidifier(False))
    else:
        return jsonify({"error": "Invalid state. Use 'on' or 'off'."}), 400

    return jsonify(response)


# Flask API Route to Turn On/Off Exhaust Fan
@app.route('/exhaust/<state_requested>', methods=['POST'])
def exhaust_control(state_requested):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    if state_requested.lower() == "on":
        response = loop.run_until_complete(toggle_exhaust(True))
    elif state_requested.lower() == "off":
        response = loop.run_until_complete(toggle_exhaust(False))
    else:
        return jsonify({"error": "Invalid state. Use 'on' or 'off'."}), 400

    return jsonify(response)


# Flask API Route to Get all the properties returned from the Tapo API as JSON
@app.route('/exhaust_info_json', methods=['GET'])
def exhaust_info_json():
    """Flask route to fetch Tapo device info."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    response = loop.run_until_complete(get_exhaust_info_json())  # Correct async function call
    
    if isinstance(response, dict):  # Ensure response is a dict
        return jsonify(response)  # Return as JSON without .to_dict()
    else:
        return jsonify(response.to_dict())  # Keep for compatibility in case it's another object

# Flask API Route to Get all the properties returned from the Tapo API as JSON
@app.route('/humidifier_info_json', methods=['GET'])
def humidifier_info_json():
    """Flask route to fetch Tapo device info."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    response = loop.run_until_complete(get_humidifier_info_json())  # Correct async function call
    
    if isinstance(response, dict):  # Ensure response is a dict
        return jsonify(response)  # Return as JSON without .to_dict()
    else:
        return jsonify(response.to_dict())  # Keep for compatibility in case it's another object

# Flask API Route to Get all the properties returned from the Tapo API as JSON
@app.route('/dehumidifier_info_json', methods=['GET'])
def dehumidifier_info_json():
    """Flask route to fetch Tapo device info."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    response = loop.run_until_complete(get_dehumidifier_info_json())  # Correct async function call
    
    if isinstance(response, dict):  # Ensure response is a dict
        return jsonify(response)  # Return as JSON without .to_dict()
    else:
        return jsonify(response.to_dict())  # Keep for compatibility in case it's another object

# Flask API Route to Check Current State
@app.route('/device_state', methods=['GET'])
def get_device_state():
    return jsonify(state)  # Return the current state of all devices


@app.route('/set_vpd_target', methods=['POST'])
def set_vpd_target():
    """Set the target VPD based on user selection."""
    data = request.json
    stage = data.get("stage")

    if stage not in VPD_MODES:
        return jsonify({"error": "Invalid stage selection"}), 400

    VPD_TARGET["min"], VPD_TARGET["max"] = VPD_MODES[stage]
    return jsonify({"message": f"VPD set to {VPD_TARGET['min']} - {VPD_TARGET['max']} kPa"})

@app.route("/get_vpd_target", methods=["GET"])
def get_vpd_target():
    """Returns the current VPD target stage."""
    try:
        if not state['grow_stage']:
            return jsonify({"error": "No VPD stage set"}), 400
        return jsonify({"stage": state['grow_stage']})
    except Exception as e:
        print(f"⚠️ Error fetching VPD target: {e}")
        return jsonify({"error": "Server error"}), 500

@app.route("/get_prediction_data", methods=["GET"])
def get_prediction_data():
    """Fetch real-time sensor data and calculate VPD."""
    try:
        # **Run async function in an event loop**
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        air_temp, leaf_temp, humidity = loop.run_until_complete(get_sensor_data())

        # **Calculate VPD**
        vpd_air, vpd_leaf = calculate_vpd(air_temp, leaf_temp, humidity)

        # **Return proper JSON response**
        return jsonify({
            "temperature": air_temp,
            "leaf_temperature": leaf_temp,
            "humidity": humidity,
            "vpd_air": vpd_air,
            "vpd_leaf": vpd_leaf
        })

    except Exception as e:
        print(f"⚠️ Error fetching prediction data: {e}")
        return jsonify({"error": "Server error"}), 500
    

def ensure_feature_format(sensor_data):
    """Ensure the input data has the correct feature format for ML models."""
    required_features = ["temperature", "leaf_temperature", "humidity", "vpd_air", "vpd_leaf", "exhaust", "humidifier", "dehumidifier"]
    
    # Fill missing features with default values (assume devices are off)
    for feature in required_features:
        if feature not in sensor_data:
            sensor_data[feature] = 0  # Assume False/0 if missing

    return np.array([[
        sensor_data["temperature"], sensor_data["leaf_temperature"],
        sensor_data["humidity"], sensor_data["vpd_air"], sensor_data["vpd_leaf"],
        sensor_data["exhaust"], sensor_data["humidifier"], sensor_data["dehumidifier"]
    ]])


@app.route("/predict_action", methods=["POST"])
def predict_action():
    """Predict the best action using Q-learning."""
    try:
        data = request.json
        state = (data["temperature"], data["humidity"], data["vpd_air"], data["vpd_leaf"])
        
        if Q_table:
            action_index = np.argmax(Q_table.get(state, np.zeros(len(action_map))))
            action = action_map[action_index]
        else:
            action = "error_no_q_table"

        return jsonify({"recommended_action": action})

    except Exception as e:
        print(f"⚠️ Prediction Error: {e}")
        return jsonify({"error": "Failed to process data"}), 500


@app.route("/predict", methods=["POST"])
def predict_device_states():
    """Predict device states (on/off) using trained ML models."""
    try:
        sensor_data = request.json
        formatted_data = ensure_feature_format(sensor_data)

        # Predict device states
        exhaust_prediction = exhaust_model.predict(formatted_data)[0]
        humidifier_prediction = humidifier_model.predict(formatted_data)[0]
        dehumidifier_prediction = dehumidifier_model.predict(formatted_data)[0]

        return jsonify({
            "exhaust": bool(exhaust_prediction),
            "humidifier": bool(humidifier_prediction),
            "dehumidifier": bool(dehumidifier_prediction),
        })

    except Exception as e:
        print(f"⚠️ Prediction API Error: {e}")
        return jsonify({"error": "Failed to predict device states"}), 500


@app.route("/detect_anomaly", methods=["POST"])
def detect_anomaly():
    """Detect anomalies in sensor data using Isolation Forest."""
    try:
        sensor_data = request.json
        formatted_data = ensure_feature_format(sensor_data)

        anomaly_score = anomaly_detector.predict(formatted_data)[0]
        is_anomaly = anomaly_score == -1  # Isolation Forest returns -1 for anomalies

        return jsonify({"anomaly_detected": is_anomaly})

    except Exception as e:
        print(f"⚠️ Anomaly Detection Error: {e}")
        return jsonify({"error": "Anomaly detection failed"}), 500
    
    
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
