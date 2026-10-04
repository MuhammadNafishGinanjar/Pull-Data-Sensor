"""
Test script: baca suhu dari ADM-4280-C, kirim ke API Railway.
Jalankan: python test_temperature_api.py
"""

import os
import sys
import time
from datetime import datetime, timezone

import requests
from pymongo import MongoClient

ROOT_DIR = os.path.dirname(__file__)
sys.path.append(os.path.join(ROOT_DIR, "adm4280_python_sdk"))

import adm4280_sensor

# =======================================================
# KONFIGURASI
# =======================================================
MONGO_URI   = "mongodb+srv://ginanjarnafish_db_user:7MdrOsyavxTn88cl@cluster0.sijeilt.mongodb.net/cmms_db?appName=Cluster0"
DB_NAME     = "cmms"
API_URL     = "https://computerize-maintenance-management-system-production.up.railway.app/api/ml/sensor-data"

MACHINE_ID      = "MCH-003"
API_MACHINE_ID  = "IND-001"
COLLECTION_NAME = "induction_machine_reading"

INTERVAL = 2  # detik antar pembacaan


def send_to_api(payload: dict) -> None:
    try:
        response = requests.post(API_URL, json=payload, timeout=5)
        response.raise_for_status()
        print(f"[API] Terkirim: {response.status_code}")
    except requests.RequestException as e:
        print(f"[API] Gagal kirim: {e}")


def main():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]

    sensor = adm4280_sensor.create_default_sensor()

    print(f"Menghubungkan ke sensor suhu ({adm4280_sensor.ADM4280_PORT})...")
    try:
        sensor.connect()
        print("Terhubung. Membaca suhu dan mengirim ke API. Tekan Ctrl+C untuk berhenti.\n")

        while True:
            temp = sensor.read_temperature()

            if temp is not None:
                readings = {"temp": round(temp, 2)}
                document = {
                    "machine_id": MACHINE_ID,
                    "timestamp": datetime.now(timezone.utc),
                    **readings,
                }
                collection.insert_one(document)
                print(f"[{MACHINE_ID}] Suhu: {temp:.2f} °C → disimpan & dikirim")

                payload = {"machine_id": API_MACHINE_ID, **readings}
                send_to_api(payload)
            else:
                print("[Sensor] Gagal membaca suhu, mencoba lagi...")

            time.sleep(INTERVAL)

    except KeyboardInterrupt:
        print("\nDihentikan oleh pengguna.")
    finally:
        sensor.disconnect()
        client.close()
        print("Selesai.")


if __name__ == "__main__":
    main()
