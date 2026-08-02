import os
import socket
import sys
import threading
import time
from datetime import datetime, timezone

import requests
from pymongo import MongoClient

ROOT_DIR = os.path.dirname(__file__)
sys.path.append(os.path.join(ROOT_DIR, "sensor_temperature"))
sys.path.append(os.path.join(ROOT_DIR, "pzem_python_sdk"))
sys.path.append(os.path.join(ROOT_DIR, "vb02_python_sdk"))

import plc_reader
import pzem_sensor
import sensor_reader

# =======================================================
# KONFIGURASI MONGODB & API
# =======================================================
MONGO_URI = "mongodb+srv://naufalreswara7_db_user:admin123@cluster0.q0cqtdj.mongodb.net/?appName=Cluster0"
DB_NAME = "cmms"
API_URL = "https://cmms-polmanbandung.site/api/ml/sensor-data"

INDUCTION_MACHINE_ID = "MCH-003"
INDUCTION_API_MACHINE_ID = "IND-001"
INDUCTION_COLLECTION = "induction_machine_reading"

FORGING_MACHINE_ID = "MCH-002"
FORGING_API_MACHINE_ID = "FRG-002"
FORGING_COLLECTION = "forging_machine_reading"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]


def send_to_api(payload):
    try:
        response = requests.post(API_URL, json=payload, timeout=5)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"[API] Failed to send sensor data: {e}")


def build_batch(api_machine_id, readings):
    """Gabungkan hasil pembacaan beberapa sensor menjadi satu payload/batch."""
    return {"machine_id": api_machine_id, **readings}


def save_and_send(collection, machine_id, api_machine_id, readings):
    document = {
        "machine_id": machine_id,
        "timestamp": datetime.now(timezone.utc),
        **readings,
    }
    collection.insert_one(document)
    print(f"[{machine_id}] Saved: {document}")

    send_to_api(build_batch(api_machine_id, readings))


def run_induction_machine():
    """Baca suhu (PLC) + daya (PZEM), gabungkan, simpan, lalu kirim satu payload."""
    collection = db[INDUCTION_COLLECTION]
    sock = plc_reader.create_socket()
    pzem = pzem_sensor.create_default_sensor()
    try:
        while True:
            try:
                temperature = plc_reader.read_temperature(sock)

                power = None
                try:
                    pzem.connect()
                    power = pzem.read_measurements()
                except Exception as e:
                    print(f"[PZEM] Gagal membaca daya: {e}")
                    pzem.disconnect()

                if temperature is not None and power is not None:
                    readings = {"temp": round(temperature, 2), **power}
                    save_and_send(collection, INDUCTION_MACHINE_ID, INDUCTION_API_MACHINE_ID, readings)
                else:
                    print("[Induksi] Gagal membaca suhu dan/atau daya, mencoba lagi...")
            except socket.timeout:
                print("[Induksi][TIMEOUT] Tidak ada balasan dari PLC, mencoba lagi...")
            except Exception as e:
                print(f"[Induksi] Error saat membaca/menyimpan: {e}")
            time.sleep(1)
    finally:
        sock.close()
        pzem.disconnect()


def run_forging_machine():
    """Baca getaran (WTVB02) + tekanan (PLC), gabungkan, simpan, lalu kirim satu payload."""
    collection = db[FORGING_COLLECTION]
    sensor = sensor_reader.create_default_sensor()
    sock = plc_reader.create_socket()
    try:
        sensor.connect()
        while True:
            try:
                data = sensor.get_data()
                pressure = plc_reader.read_pressure(sock)

                if pressure is not None:
                    readings = {
                        "vx": data["velocity"]["x"],
                        "vy": data["velocity"]["y"],
                        "vz": data["velocity"]["z"],
                        "pressure": round(pressure, 2),
                    }
                    save_and_send(collection, FORGING_MACHINE_ID, FORGING_API_MACHINE_ID, readings)
                else:
                    print("[Forging] Gagal membaca tekanan, mencoba lagi...")
            except socket.timeout:
                print("[Forging][TIMEOUT] Tidak ada balasan dari PLC, mencoba lagi...")
            except Exception as e:
                print(f"[Forging] Error saat membaca/menyimpan: {e}")
            time.sleep(1)
    finally:
        sensor.disconnect()
        sock.close()


def main():
    threads = [
        threading.Thread(target=run_induction_machine, daemon=True),
        threading.Thread(target=run_forging_machine, daemon=True),
    ]
    for t in threads:
        t.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nDihentikan oleh pengguna.")
    finally:
        client.close()
        print("Selesai.")


if __name__ == "__main__":
    main()
