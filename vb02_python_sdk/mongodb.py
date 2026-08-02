from pymongo import MongoClient
from datetime import datetime
import requests

MONGO_URI = "mongodb+srv://naufalreswara7_db_user:admin123@cluster0.q0cqtdj.mongodb.net/?appName=Cluster0"
API_URL = "https://cmms-polmanbandung.site/api/ml/sensor-data"
API_MACHINE_ID = "FRG-002"

client = MongoClient(MONGO_URI)

db = client["cmms"]
collection = db["vibration_sensor_reading"]

def save_sensor_data(data, machine_id):
    document = {
        "machine_id": machine_id,
        "timestamp": datetime.utcnow(),
        "vx": data["velocity"]["x"],
        "vy": data["velocity"]["y"],
        "vz": data["velocity"]["z"],
        "dx": data["displacement"]["x"],
        "dy": data["displacement"]["y"],
        "dz": data["displacement"]["z"],
        "fx": data["frequency"]["x"],
        "fy": data["frequency"]["y"],
        "fz": data["frequency"]["z"]
    }
    collection.insert_one(document)

    payload = {k: v for k, v in document.items() if k not in ("_id", "timestamp")}
    payload["machine_id"] = API_MACHINE_ID
    send_to_api(payload)

def send_to_api(payload):
    try:
        response = requests.post(API_URL, json=payload, timeout=5)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"[API] Failed to send sensor data: {e}")