from flask import Flask, request, jsonify
import asyncio
from tapo_controller import get_device_status, toggle_humidifier, toggle_exhaust, get_sensor_data, get_device_info_json
from state import state  # Import global state
from flask_cors import CORS  # Import CORS

app = Flask(__name__)
CORS(app, supports_credentials=True)

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
@app.route('/device_info_json', methods=['GET'])
def device_info_json():
    """Flask route to fetch Tapo device info."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    response = loop.run_until_complete(get_device_info_json())  # Correct async function call
    
    if isinstance(response, dict):  # Ensure response is a dict
        return jsonify(response)  # Return as JSON without .to_dict()
    else:
        return jsonify(response.to_dict())  # Keep for compatibility in case it's another object

# Flask API Route to Check Current State
@app.route('/device_state', methods=['GET'])
def get_device_state():
    return jsonify(state)  # Return the current state of all devices

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
