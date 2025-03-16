import os
import sys
from flask import Flask, request, jsonify, request, Response
import requests
import joblib
import asyncio
import pandas as pd
import numpy as np
import asyncio

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.tapo_controller import get_device_info_json, get_sensor_data, get_device_info
from api.device_status import get_device_status
from api.actions import toggle_dehumidifier, toggle_exhaust, toggle_humidifier
from api.state import state  
from api.models import models, load_models
from utils.calculate import calculate_vpd
from flask_cors import CORS
from config.settings import ACTION_MAP, ANOMALY_MODEL_PATH, Q_TABLE_PATH, EXHAUST_MODEL_PATH, HUMIDIFIER_MODEL_PATH, DEHUMIDIFIER_MODEL_PATH, WS_URL, DEVICE_MAP, MAX_HUMIDITY_LEVELS, VPD_TARGET, VPD_MODES, FASTAPI_URL, PROXY_URL, KPA_TOLERANCE, LEAF_TEMP_OFFSET

app = Flask(__name__)
CORS(app, supports_credentials=True)

Q_table = None
models = {
    "exhaust_model": None,
    "humidifier_model": None,
    "dehumidifier_model": None
}
anomaly_detector = None

@app.route('/config-settings', methods=['GET'])
async def config_settings():
    """Fetch config settings."""
    try:
        return jsonify({
            "KPA_TOLERANCE": KPA_TOLERANCE, 
            "LEAF_TEMP_OFFSET": LEAF_TEMP_OFFSET,
            "VPD_TARGET": VPD_TARGET,
            "VPD_MODES": VPD_MODES,
            "ACTION_MAP": ACTION_MAP,
            "MAX_HUMIDITY_LEVELS": MAX_HUMIDITY_LEVELS,
            "DEVICE_MAP": DEVICE_MAP,
            "WS_URL": WS_URL
        })
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500
    

@app.route('/adjust_conditions', methods=["OPTIONS", "POST"])
def adjust_conditions():
    """Automatically adjust devices based on ML predictions."""

    # Handle OPTIONS request (CORS preflight)
    if request.method == 'OPTIONS':
        response = jsonify({})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
        return response, 204

    # Handle POST request
    sensor_data = request.get_json()
    print(f"🔍 Received sensor data: {sensor_data}")

    return jsonify({"message": "Conditions adjusted", "data": sensor_data}), 200


""" @app.route('/adjust_conditions', methods=["OPTIONS", "POST"])
def adjust_conditions():

    # Handle OPTIONS request
    if request.method == 'OPTIONS':
        response = jsonify({})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
        return response, 204

    # Handle POST request
    try:
        # Get JSON data and ensure required fields exist
        sensor_data = request.get_json()
        print(f"🔍 Received sensor data: {sensor_data}")  # Debugging log

        # Ensure all required fields exist, provide defaults if missing
        formatted_sensor_data = {
            "temperature": sensor_data.get("temperature", 22.5),  # Default: 22.5
            "humidity": sensor_data.get("humidity", 60),          # Default: 60%
            "leaf_temperature": sensor_data.get("leaf_temperature", 20)  # Default: 20°C
        }

        print(f"📤 Sending to ML API: {formatted_sensor_data}")  # Debugging log

        # Send request to ML prediction service
        prediction_response = requests.post(f"{PROXY_URL}/predict", json=formatted_sensor_data)
        prediction_response.raise_for_status()  # Raise error if response is not 200

        prediction = prediction_response.json()
        print(f"✅ ML Prediction Response: {prediction}")  # Debugging log

        toggle_exhaust(prediction.get("exhaust", False))
        toggle_humidifier(prediction.get("humidifier", False))
        toggle_dehumidifier(prediction.get("dehumidifier", False))

        return jsonify({
            "message": "Conditions adjusted successfully",
            "state": prediction
        }), 200

    except requests.exceptions.RequestException as req_err:
        print(f"❌ Prediction API error: {req_err}")
        return jsonify({"error": f"Failed to adjust conditions: {str(req_err)}"}), 500

    except Exception as e:
        print(f"⚠️ Unexpected error: {e}")
        return jsonify({"error": f"Failed to adjust conditions: {str(e)}"}), 500
 """


@app.route("/vpd", methods=["GET"])
def get_vpd_data():
    """Fetch latest VPD data from FastAPI."""
    try:
        response = requests.get(f"{FASTAPI_URL}/ws/vpd", stream=True)
        return Response(response.iter_content(), content_type=response.headers['Content-Type'])
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500
    
    
@app.route('/device_status', methods=['GET'])
def device_status():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    device_info = loop.run_until_complete(get_device_status("sensor_hub"))
    return jsonify(device_info.to_dict())


@app.route('/sensor_data', methods=['GET'])
def sensor_data():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    response = loop.run_until_complete(get_sensor_data())
    return jsonify(response)


@app.route('/humidifier/<state_requested>', methods=['POST'])
def humidifier_control(state_requested):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    if state_requested.lower() == "on":
        state["override_humidifier"] = True
        response = loop.run_until_complete(toggle_humidifier(True))
    elif state_requested.lower() == "off":
        state["override_humidifier"] = False
        response = loop.run_until_complete(toggle_humidifier(False))
    else:
        return jsonify({"error": "Invalid state. Use 'on' or 'off'."}), 400

    return jsonify(response)


@app.route('/dehumidifier/<state_requested>', methods=['POST'])
def dehumidifier_control(state_requested):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    if state_requested.lower() == "on":
        state["override_dehumidifier"] = True
        response = loop.run_until_complete(toggle_dehumidifier(True))
    elif state_requested.lower() == "off":
        state["override_dehumidifier"] = False
        response = loop.run_until_complete(toggle_dehumidifier(False))
    else:
        return jsonify({"error": "Invalid state. Use 'on' or 'off'."}), 400

    return jsonify(response)


@app.route('/exhaust/<state_requested>', methods=['POST'])
def exhaust_control(state_requested):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    if state_requested.lower() == "on":
        state["override"] = True
        response = loop.run_until_complete(toggle_exhaust(True))
    elif state_requested.lower() == "off":
        state["override_exhaust"] = False
        response = loop.run_until_complete(toggle_exhaust(False))
    else:
        return jsonify({"error": "Invalid state. Use 'on' or 'off'."}), 400

    return jsonify(response)


@app.route('/exhaust_info_json', methods=['GET'])
def exhaust_info_json():
    """Flask route to fetch Tapo device info."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    response = loop.run_until_complete(get_device_info_json("exhaust")) 
    
    if isinstance(response, dict):  
        return jsonify(response) 
    else:
        return jsonify(response.to_dict()) 
    


@app.route('/humidifier_info_json', methods=['GET'])
def humidifier_info_json():
    """Flask route to fetch Tapo device info."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    response = loop.run_until_complete(get_device_info_json("humidifier"))  
    
    if isinstance(response, dict):  
        return jsonify(response)  
    else:
        return jsonify(response.to_dict()) 
    

@app.route('/dehumidifier_info_json', methods=['GET'])
def dehumidifier_info_json():
    """Flask route to fetch Tapo device info."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    response = loop.run_until_complete(get_device_info_json("dehumidifier")) 
    
    if isinstance(response, dict):  
        return jsonify(response) 
    else:
        return jsonify(response.to_dict()) 
    

@app.route('/device_state', methods=['GET'])
def get_device_state():
    return jsonify(state)  


@app.route('/set_vpd_target', methods=['POST'])
def set_vpd_target():
    """Set the target VPD based on user selection."""
    data = request.json
    print(data)
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
 
 
def load_models():
    """Load all required models into memory."""
    global Q_table, models, anomaly_detector

    if Q_table is None:
        Q_table = joblib.load(Q_TABLE_PATH)
        print("✅ Q-learning table loaded!")

    if models["exhaust_model"] is None:
        models["exhaust_model"] = joblib.load(EXHAUST_MODEL_PATH)
        models["humidifier_model"] = joblib.load(HUMIDIFIER_MODEL_PATH)
        models["dehumidifier_model"] = joblib.load(DEHUMIDIFIER_MODEL_PATH)
        print("✅ ML models loaded!")

    if anomaly_detector is None:
        anomaly_detector = joblib.load(ANOMALY_MODEL_PATH)
        print("✅ Anomaly detection model loaded!")


@app.route("/get_prediction_data", methods=["GET"])
def get_prediction_data():
    """Fetch real-time sensor data and calculate VPD."""
    try:
        data = asyncio.run(get_sensor_data())  # 🔹 Fix: Use asyncio.run() instead of new loop
        air_temp, leaf_temp, humidity = data

        vpd_air, vpd_leaf = calculate_vpd(air_temp, leaf_temp, humidity)

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

    for feature in required_features:
        if feature not in sensor_data:
            sensor_data[feature] = False if feature in ["exhaust", "humidifier", "dehumidifier"] else 0  # 🔹 Fix: Use False for binary features

    return np.array([[sensor_data[f] for f in required_features]])


@app.route("/predict_action", methods=["POST"])
def predict_action():
    try:
        load_models()  
        data = request.json

        input_state = (
            float(data["humidity"]),
            float(data["leaf_temperature"]),
            float(data["temperature"]),
            float(data["vpd_air"]),
            float(data["vpd_leaf"])
        )

        if input_state not in Q_table:
            print(f"⚠️ Warning: Unseen state {input_state}, taking random action")
            action = np.random.choice(list(ACTION_MAP.keys()))
        else:
            action = np.argmax(Q_table[input_state])

        action_name = ACTION_MAP[action] if action in ACTION_MAP else "unknown_action"  
        return jsonify({"predicted_action": action_name})

    except Exception as e:
        print(f"⚠️ Prediction API error: {e}")
        return jsonify({"error": "Action prediction failed"}), 500


@app.route("/predict", methods=["POST"])
def predict():
    try:
        load_models()  

        data = request.json
        required_fields = ["temperature", "leaf_temperature", "humidity", "vpd_air", "vpd_leaf"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        features = np.array([[data[f] for f in required_fields]])

        exhaust_prediction = models["exhaust_model"].predict(features)[0]
        humidifier_prediction = models["humidifier_model"].predict(features)[0]
        dehumidifier_prediction = models["dehumidifier_model"].predict(features)[0]

        return jsonify({
            "exhaust": bool(exhaust_prediction),
            "humidifier": bool(humidifier_prediction),
            "dehumidifier": bool(dehumidifier_prediction),
        })

    except Exception as e:
        print(f"⚠️ Prediction error: {e}")
        return jsonify({"error": "Server error during prediction"}), 500


@app.route("/detect_anomaly", methods=["POST"])
def detect_anomaly():
    try:
        load_models()  

        data = request.json
        if not isinstance(data, dict):
            if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                print("⚠️ Warning: Received a list, extracting first item...")
                data = data[0]
            else:
                print("❌ Error: Expected JSON dictionary but received something else.")
                return jsonify({"error": "Invalid input format. Expected a JSON dictionary."}), 400

        print(f"✅ Processed data for anomaly detection: {data}")

        input_features = pd.DataFrame([data])
        expected_features = ["temperature", "leaf_temperature", "humidity", "vpd_air", "vpd_leaf", "exhaust", "humidifier", "dehumidifier"]

        for col in expected_features:
            if col not in input_features.columns:
                print(f"⚠️ Missing feature: {col}, filling with False/0")
                input_features[col] = False if col in ["exhaust", "humidifier", "dehumidifier"] else 0

        input_features = input_features[expected_features]

        anomaly_score = anomaly_detector.decision_function(input_features)
        is_anomaly = anomaly_score[0] < -0.5 
        
        print(f"🚀 Anomaly Score: {anomaly_score}, Detected: {bool(is_anomaly)}")
        return jsonify({"anomaly_detected": bool(is_anomaly)})

    except Exception as e:
        print(f"❌ ERROR in Anomaly Detection: {e}")
        return jsonify({"error": "Anomaly detection failed"}), 500


if __name__ == "__main__":
    load_models() 
    app.run(host="0.0.0.0", port=5000, debug=True)
