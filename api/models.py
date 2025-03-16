import joblib

# Global dictionary to store models
models = {}

def load_models():
    """Loads all required machine learning models into the global `models` dictionary."""
    global models  # Ensure we're modifying the global dictionary

    model_files = {
        "Q_table": "../model/q_learning.pkl",
        "exhaust_model": "../model/exhaust_model.pkl",
        "humidifier_model": "../model/humidifier_model.pkl",
        "dehumidifier_model": "../model/dehumidifier_model.pkl",
        "anomaly_detector": "../model/anomaly_detector.pkl",
    }

    for model_name, path in model_files.items():
        try:
            models[model_name] = joblib.load(path)
            print(f"✅ {model_name} loaded successfully!")
        except FileNotFoundError:
            print(f"❌ ERROR: Model {model_name} NOT found at {path}. Check if it exists!")
            models[model_name] = None
        except Exception as e:
            print(f"❌ ERROR loading {model_name}: {str(e)}")
            models[model_name] = None
