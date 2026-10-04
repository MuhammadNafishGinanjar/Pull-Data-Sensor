"""Coba tarik data dari semua sensor fisik, print hasilnya, dan kirim ke API Railway.

Berbeda dengan test_*.py di tiap folder akuisisi (yang pakai data mock,
tanpa hardware), script ini menyambung ke sensor asli (ADM-4280-C, PZEM, WTVB02, PLC)
dan print hasil pembacaannya. Menyimpan ke MongoDB dan mengirim ke API Railway.
"""

import os
import sys
from datetime import datetime, timezone

import requests
from pymongo import MongoClient

ROOT_DIR = os.path.dirname(__file__)
sys.path.append(os.path.join(ROOT_DIR, "adm4280_python_sdk"))
sys.path.append(os.path.join(ROOT_DIR, "pzem_python_sdk"))
sys.path.append(os.path.join(ROOT_DIR, "vb02_python_sdk"))
sys.path.append(os.path.join(ROOT_DIR, "sensor_temperature"))

import adm4280_sensor
import plc_reader
import pzem_sensor
import sensor_reader

# =======================================================
# KONFIGURASI
# =======================================================
MONGO_URI = "mongodb+srv://ginanjarnafish_db_user:7MdrOsyavxTn88cl@cluster0.sijeilt.mongodb.net/cmms_db?appName=Cluster0"
DB_NAME   = "cmms"
API_URL   = "https://computerize-maintenance-management-system-production.up.railway.app/api/ml/sensor-data"

INDUCTION_MACHINE_ID     = "MCH-003"
INDUCTION_API_MACHINE_ID = "IND-001"
INDUCTION_COLLECTION     = "induction_machine_reading"

FORGING_MACHINE_ID       = "MCH-002"
FORGING_API_MACHINE_ID   = "FRG-002"
FORGING_COLLECTION       = "forging_machine_reading"


def send_to_api(machine_id: str, readings: dict) -> None:
    payload = {"machine_id": machine_id, **readings}
    try:
        response = requests.post(API_URL, json=payload, timeout=5)
        response.raise_for_status()
        print(f"[API] Terkirim ({machine_id}): {response.status_code}")
    except requests.RequestException as e:
        print(f"[API] Gagal kirim ({machine_id}): {e}")


def save_to_db(collection, machine_id: str, readings: dict) -> None:
    document = {
        "machine_id": machine_id,
        "timestamp": datetime.now(timezone.utc),
        **readings,
    }
    collection.insert_one(document)
    print(f"[DB] Disimpan ({machine_id}): {readings}")


def pull_induction(db):
    """Baca suhu (ADM-4280-C) + daya (PZEM), simpan & kirim."""
    collection = db[INDUCTION_COLLECTION]
    readings = {}

    # Suhu
    sensor = adm4280_sensor.create_default_sensor()
    try:
        sensor.connect()
        temp = sensor.read_temperature()
        if temp is not None:
            readings["temp"] = round(temp, 2)
            print(f"[ADM4280] temperature = {temp:.2f} °C")
        else:
            print("[ADM4280] Gagal membaca suhu")
    except Exception as e:
        print(f"[ADM4280] Gagal membaca: {e}")
    finally:
        sensor.disconnect()

    # Daya
    pzem = pzem_sensor.create_default_sensor()
    try:
        pzem.connect()
        power = pzem.read_measurements()
        readings.update(power)
        print(f"[PZEM] power = {power}")
    except Exception as e:
        print(f"[PZEM] Gagal membaca: {e}")
    finally:
        pzem.disconnect()

    if readings:
        save_to_db(collection, INDUCTION_MACHINE_ID, readings)
        send_to_api(INDUCTION_API_MACHINE_ID, readings)
    else:
        print("[Induksi] Tidak ada data, skip kirim.")


def pull_forging(db):
    """Baca getaran (WTVB02) + tekanan (PLC), simpan & kirim."""
    collection = db[FORGING_COLLECTION]
    readings = {}

    # Getaran
    vibration_sensor = sensor_reader.create_default_sensor()
    try:
        vibration_sensor.connect()
        data = vibration_sensor.get_data()
        readings.update({
            "vx": data["velocity"]["x"],
            "vy": data["velocity"]["y"],
            "vz": data["velocity"]["z"],
        })
        print(f"[WTVB02] vibration = {data}")
    except Exception as e:
        print(f"[WTVB02] Gagal membaca: {e}")
    finally:
        vibration_sensor.disconnect()

    # Tekanan
    sock = plc_reader.create_socket()
    try:
        pressure = plc_reader.read_pressure(sock)
        readings["pressure"] = round(pressure, 2) if pressure is not None else None
        print(f"[PLC] pressure = {pressure}")
    except Exception as e:
        print(f"[PLC] Gagal membaca: {e}")
    finally:
        sock.close()

    if readings:
        save_to_db(collection, FORGING_MACHINE_ID, readings)
        send_to_api(FORGING_API_MACHINE_ID, readings)
    else:
        print("[Forging] Tidak ada data, skip kirim.")


def main():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    try:
        print("=== Induksi ===")
        pull_induction(db)
        print("\n=== Forging ===")
        pull_forging(db)
    finally:
        client.close()


if __name__ == "__main__":
    main()
