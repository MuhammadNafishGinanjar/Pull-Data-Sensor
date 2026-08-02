"""Update status mesin (running/idle) ke CMMS lewat PATCH /api/assets/<asset_id>/status.

Sinyal ambil dari bit PLC yang sama dengan sensor suhu/tekanan:
    Induksi running: W67.00 ON  | idle: W67.00 OFF
    Forging running: W67.01 ON  | idle: W67.01 OFF

Endpoint status pakai ObjectId Mongo (bukan machine_id), jadi machine_id
di-resolve ke asset_id sekali lewat GET /api/assets lalu di-cache.
"""

import os
import socket
import sys
import time

import requests

ROOT_DIR = os.path.dirname(__file__)
sys.path.append(os.path.join(ROOT_DIR, "sensor_temperature"))

import plc_reader

# =======================================================
# KONFIGURASI API STATUS MESIN
# =======================================================
# Production: satu domain lewat nginx (sama dengan API sensor-data).
# Untuk dev lokal ganti ke "http://localhost:5000/api".
STATUS_API_BASE_URL = "https://cmms-polmanbandung.site/api"

# Isi dengan JWT hasil login kalau endpoint ini sudah diproteksi di masa depan.
STATUS_API_TOKEN = None

INDUCTION_MACHINE_ID = "IND-001"
FORGING_MACHINE_ID = "FRG-002"

# Sinyal running/idle (W-Memory, Level Bit)
INDUCTION_STATUS_WORD = 67
INDUCTION_STATUS_BIT = 0

FORGING_STATUS_WORD = 67
FORGING_STATUS_BIT = 1

RUNNING = "running"
IDLE = "idle"

_asset_id_cache = {}


def _headers():
    headers = {"Content-Type": "application/json"}
    if STATUS_API_TOKEN:
        headers["Authorization"] = f"Bearer {STATUS_API_TOKEN}"
    return headers


def resolve_asset_id(machine_id):
    if machine_id in _asset_id_cache:
        return _asset_id_cache[machine_id]

    response = requests.get(f"{STATUS_API_BASE_URL}/assets", headers=_headers(), timeout=5)
    response.raise_for_status()
    for asset in response.json():
        if asset["machine_id"] == machine_id:
            _asset_id_cache[machine_id] = asset["id"]
            return asset["id"]
    raise ValueError(f"Machine {machine_id} tidak ditemukan di /api/assets")


def resolve_asset_id_with_retry(machine_id, retry_interval=5.0):
    while True:
        try:
            return resolve_asset_id(machine_id)
        except Exception as e:
            print(f"[Status] Gagal resolve asset_id untuk {machine_id}: {e}. Coba lagi dalam {retry_interval:.0f}s...")
            time.sleep(retry_interval)


def update_status(asset_id, status):
    response = requests.patch(
        f"{STATUS_API_BASE_URL}/assets/{asset_id}/status",
        json={"status": status},
        headers=_headers(),
        timeout=5,
    )
    response.raise_for_status()
    return response.json()


def read_status_bit(sock, word_address, bit_address):
    bits = plc_reader.read_bit(sock, plc_reader.MEM_BIT_W, word_address, bit_address)
    if bits is None:
        return None
    return RUNNING if bits[0] else IDLE


def run_status_monitor():
    """Pantau bit running/idle tiap siklus, PATCH ke API hanya saat statusnya berubah."""
    sock = plc_reader.create_socket()
    last_status = {}
    try:
        induction_asset_id = resolve_asset_id_with_retry(INDUCTION_MACHINE_ID)
        forging_asset_id = resolve_asset_id_with_retry(FORGING_MACHINE_ID)

        while True:
            try:
                induction_status = read_status_bit(sock, INDUCTION_STATUS_WORD, INDUCTION_STATUS_BIT)
                if induction_status is not None and last_status.get(INDUCTION_MACHINE_ID) != induction_status:
                    result = update_status(induction_asset_id, induction_status)
                    print(f"[Induksi] {result['message']}")
                    last_status[INDUCTION_MACHINE_ID] = induction_status

                forging_status = read_status_bit(sock, FORGING_STATUS_WORD, FORGING_STATUS_BIT)
                if forging_status is not None and last_status.get(FORGING_MACHINE_ID) != forging_status:
                    result = update_status(forging_asset_id, forging_status)
                    print(f"[Forging] {result['message']}")
                    last_status[FORGING_MACHINE_ID] = forging_status
            except socket.timeout:
                print("[Status][TIMEOUT] Tidak ada balasan dari PLC, mencoba lagi...")
            except Exception as e:
                print(f"[Status] Error: {e}")
            time.sleep(1)
    finally:
        sock.close()


if __name__ == "__main__":
    run_status_monitor()
