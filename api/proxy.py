import os
import sys
from flask import Flask, request, jsonify, request, Response
import requests
import joblib
import asyncio
import pandas as pd
import numpy as np

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.tapo_controller import get_device_info_json, get_sensor_data, get_device_info
from api.device_status import get_device_status
from api.actions import toggle_dehumidifier, toggle_exhaust, toggle_humidifier
from api.state import state  
from api.models import models, load_models
from utils.calculate import calculate_vpd
from flask_cors import CORS
from config.settings import ACTION_MAP, WS_URL, DEVICE_MAP, MAX_HUMIDITY_LEVELS, VPD_TARGET, VPD_MODES, FASTAPI_URL, PROXY_URL, KPA_TOLERANCE, LEAF_TEMP_OFFSET

app = Flask(__name__)
CORS(app, supports_credentials=True)


load_models()

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
    

@app.route('/adjust_conditions', methods=['POST'])
async def adjust_conditions():
    """Automatically adjust devices based on ML predictions."""
    try:
        sensor_data = await get_sensor_data()  
        prediction = requests.post(f"{PROXY_URL}/predict", json=sensor_data).json()

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
    

@app.route("/get_prediction_data", methods=["GET"])
def get_prediction_data():
    """Fetch real-time sensor data and calculate VPD."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        air_temp, leaf_temp, humidity = loop.run_until_complete(get_sensor_data())

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
            sensor_data[feature] = 0 

    return np.array([[
        sensor_data["temperature"], sensor_data["leaf_temperature"],
        sensor_data["humidity"], sensor_data["vpd_air"], sensor_data["vpd_leaf"],
        sensor_data["exhaust"], sensor_data["humidifier"], sensor_data["dehumidifier"]
    ]])

@app.route("/predict_action", methods=["POST"])
def predict_action():
    try:
        data = request.json
        
        input_state = (
            float(data["humidity"]),
            float(data["leaf_temperature"]),
            float(data["temperature"]),
            float(data["vpd_air"]),
            float(data["vpd_leaf"])
        )

        global Q_table
        if "Q_table" not in globals():
            Q_table = joblib.load("../model/q_learning.pkl")
            print("✅ Q-learning table loaded!")

        if input_state not in Q_table:
            print(f"⚠️ Warning: Unseen state {input_state}, taking random action")
            action = np.random.choice(list(range(6)))  
        else:
            action = np.argmax(Q_table[input_state])

        action_name = list(ACTION_MAP.keys())[action]
        return jsonify({"predicted_action": action_name})

    except Exception as e:
        print(f"⚠️ Prediction API error: {e}")
        return jsonify({"error": "Action prediction failed"}), 500


@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.json
       
        required_fields = ["temperature", "leaf_temperature", "humidity", "vpd_air", "vpd_leaf"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

       
        features = np.array([[data["temperature"], data["leaf_temperature"], data["humidity"], data["vpd_air"], data["vpd_leaf"]]])

        if models["exhaust_model"] is None or models["humidifier_model"] is None or models["dehumidifier_model"] is None:
            return jsonify({"error": "One or more ML models are not loaded"}), 500

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
                print(f"⚠️ Missing feature: {col}, filling with 0")
                input_features[col] = 0  

        input_features.columns = input_features.columns.astype(str)

        input_features = input_features[expected_features]
        
        global anomaly_detector
        if "anomaly_detector" not in globals():
            print("⚠️ Loading anomaly detection model...")
            anomaly_detector = joblib.load("../model/anomaly_detector.pkl")

     
        anomaly_score = anomaly_detector.decision_function(input_features)
        is_anomaly = anomaly_score < -0.5  

        print(f"🚀 Anomaly Score: {anomaly_score}, Detected: {bool(is_anomaly)}")

        return jsonify({"anomaly_detected": bool(is_anomaly)})

    except Exception as e:
        print(f"❌ ERROR in Anomaly Detection: {e}")  
        return jsonify({"error": f"Anomaly detection failed: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
