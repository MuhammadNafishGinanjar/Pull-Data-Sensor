import json
import time
import threading

from sensor_reader import VibrationSensor
from mongodb import save_sensor_data

def run_sensor(sensor_config):
    machine_id = sensor_config["machine_id"]
    machine_name = sensor_config.get("machine_name", machine_id)

    sensor = VibrationSensor(
        port=sensor_config["port"],
        baudrate=sensor_config["baudrate"],
        address=sensor_config["address"]
    )

    try:
        sensor.connect()
        print(f"[{machine_name}] Connected on {sensor_config['port']}")

        while True:
            data = sensor.get_data()
            save_sensor_data(data, machine_id)
            print(f"[{machine_name}] Saved:", data)
            time.sleep(1)

    except Exception as e:
        print(f"[{machine_name}] Error: {e}")

    finally:
        sensor.disconnect()
        print(f"[{machine_name}] Disconnected.")


def main():
    with open("config.json") as f:
        config = json.load(f)

    threads = []
    for sensor_config in config["sensors"]:
        t = threading.Thread(target=run_sensor, args=(sensor_config,), daemon=True)
        t.start()
        threads.append(t)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping all sensors...")


if __name__ == "__main__":
    main()