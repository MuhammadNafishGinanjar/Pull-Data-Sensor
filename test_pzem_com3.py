"""Script cepat untuk test baca sensor daya PZEM via COM3."""
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "pzem_python_sdk"))

from pzem_sensor import PZEMSensor

PORT = "COM3"
BAUDRATE = 9600
SLAVE_ID = 1

print(f"Menghubungkan ke PZEM di {PORT} (baudrate={BAUDRATE}, slave_id={SLAVE_ID})...")

try:
    with PZEMSensor(port=PORT, baudrate=BAUDRATE, slave_id=SLAVE_ID, timeout=2.0) as sensor:
        data = sensor.read_measurements()
        print("\n=== Hasil Pembacaan Sensor Daya ===")
        print(f"  Tegangan     : {data['voltage_v']} V")
        print(f"  Arus         : {data['current_a']} A")
        print(f"  Daya Aktif   : {data['active_power_w']} W")
        print(f"  Energi       : {data['energy_wh']} Wh ({data['energy_kwh']:.3f} kWh)")
        print(f"  Frekuensi    : {data['frequency_hz']} Hz")
        print("\nRaw dict:", data)
except Exception as e:
    print(f"\nError: {e}")
    print("Cek: port benar? sensor aktif? RS485 tersambung?")
