"""Kolektor data sensor Mesin Bor (DRL-001).

Sensor:
  - ADM-4280-C  (/dev/ttyUSB0) → temp_c
  - PZEM        (/dev/ttyUSB2) → current_a, active_power_w
  - WTVB02      (/dev/ttyUSB1) → vx, vy, vz

Jalankan file ini sendiri (jangan bersamaan dengan main.py —
port serial akan konflik).
"""

import os
import sys
import time
from datetime import datetime, timezone

import requests
from pymongo import MongoClient

ROOT_DIR = os.path.dirname(__file__)
sys.path.append(os.path.join(ROOT_DIR, "adm4280_python_sdk"))
sys.path.append(os.path.join(ROOT_DIR, "pzem_python_sdk"))
sys.path.append(os.path.join(ROOT_DIR, "vb02_python_sdk"))

import adm4280_sensor
import pzem_sensor
import sensor_reader

# =======================================================
# KONFIGURASI MONGODB & API
# =======================================================
MONGO_URI = os.environ["mongodb+srv://ginanjarnafish_db_user:7MdrOsyavxTn88cl@cluster0.sijeilt.mongodb.net/cmms_db?appName=Cluster0"]
DB_NAME   = os.environ.get("MONGO_DB_NAME", "cmms")
API_URL   = os.environ["https://computerize-maintenance-management-system-production.up.railway.app/api/ml/sensor-data"]

MACHINE_ID     = "DRL-001"
API_MACHINE_ID = "DRL-001"
COLLECTION     = "drl_machine_reading"

client = MongoClient(MONGO_URI)
db     = client[DB_NAME]


def send_to_api(readings: dict) -> None:
    payload = {"machine_id": API_MACHINE_ID, **readings}
    try:
        response = requests.post(API_URL, json=payload, timeout=5)
        response.raise_for_status()
        print(f"[API] Terkirim ({API_MACHINE_ID}): {response.status_code}")
    except requests.RequestException as e:
        print(f"[API] Gagal kirim: {e}")


def save_to_db(readings: dict) -> None:
    document = {
        "machine_id": MACHINE_ID,
        "timestamp": datetime.now(timezone.utc),
        **readings,
    }
    try:
        db[COLLECTION].insert_one(document)
        print(f"[DB] Disimpan ({MACHINE_ID}): {readings}")
    except Exception as e:
        print(f"[DB] Gagal simpan: {e}")


def main():
    temp  = adm4280_sensor.create_default_sensor()
    pzem  = pzem_sensor.create_default_sensor()
    vibr  = sensor_reader.create_default_sensor()

    temp.connect()
    vibr.connect()

    print(f"Mesin Bor ({MACHINE_ID}) — mulai membaca sensor. Ctrl+C untuk berhenti.\n")

    try:
        while True:
            readings = {}

            # Suhu
            try:
                t = temp.read_temperature()
                if t is not None:
                    readings["temp_c"] = round(t, 2)
                else:
                    print("[ADM4280] Gagal membaca suhu")
            except Exception as e:
                print(f"[ADM4280] Error: {e}")

            # Daya
            try:
                pzem.connect()
                power = pzem.read_measurements()
                readings["current_a"]      = power["current_a"]
                readings["active_power_w"] = power["active_power_w"]
            except Exception as e:
                print(f"[PZEM] Gagal membaca daya: {e}")
            finally:
                pzem.disconnect()

            # Getaran
            try:
                data = vibr.get_data()
                readings["vx"] = data["velocity"]["x"]
                readings["vy"] = data["velocity"]["y"]
                readings["vz"] = data["velocity"]["z"]
            except Exception as e:
                print(f"[WTVB02] Gagal membaca getaran: {e}")

            if readings:
                save_to_db(readings)
                send_to_api(readings)
            else:
                print("[Bor] Tidak ada data, skip.")

            time.sleep(1)

    except KeyboardInterrupt:
        print("\nDihentikan oleh pengguna.")
    finally:
        temp.disconnect()
        vibr.disconnect()
        client.close()
        print("Selesai.")


if __name__ == "__main__":
    main()
