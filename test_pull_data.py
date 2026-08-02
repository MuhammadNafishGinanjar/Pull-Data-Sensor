"""Coba tarik data dari semua sensor fisik dan print hasilnya.

Berbeda dengan test_*.py di tiap folder akuisisi (yang pakai data mock,
tanpa hardware), script ini menyambung ke sensor asli (PLC, PZEM, WTVB02)
dan hanya print hasil pembacaannya. Tidak menyimpan ke MongoDB maupun
mengirim ke API.
"""

import os
import sys

ROOT_DIR = os.path.dirname(__file__)
sys.path.append(os.path.join(ROOT_DIR, "sensor_temperature"))
sys.path.append(os.path.join(ROOT_DIR, "pzem_python_sdk"))
sys.path.append(os.path.join(ROOT_DIR, "vb02_python_sdk"))

import plc_reader
import pzem_sensor
import sensor_reader


def pull_plc():
    sock = plc_reader.create_socket()
    try:
        temperature = plc_reader.read_temperature(sock)
        pressure = plc_reader.read_pressure(sock)
        print(f"[PLC] temperature = {temperature}")
        print(f"[PLC] pressure    = {pressure}")
    except Exception as e:
        print(f"[PLC] Gagal membaca: {e}")
    finally:
        sock.close()


def pull_pzem():
    pzem = pzem_sensor.create_default_sensor()
    try:
        pzem.connect()
        power = pzem.read_measurements()
        print(f"[PZEM] power = {power}")
    except Exception as e:
        print(f"[PZEM] Gagal membaca: {e}")
    finally:
        pzem.disconnect()


def pull_vibration():
    sensor = sensor_reader.create_default_sensor()
    try:
        sensor.connect()
        data = sensor.get_data()
        print(f"[WTVB02] vibration = {data}")
    except Exception as e:
        print(f"[WTVB02] Gagal membaca: {e}")
    finally:
        sensor.disconnect()


def main():
    pull_plc()
    pull_pzem()
    pull_vibration()


if __name__ == "__main__":
    main()
