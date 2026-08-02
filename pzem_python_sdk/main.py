from __future__ import annotations

import json
import time
from pathlib import Path

from database import PowerReadingRepository
from pzem_sensor import PZEMSensor


CONFIG_PATH = Path(__file__).with_name("config.json")


def load_config() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as config_file:
        return json.load(config_file)


def print_measurement(machine_name: str, data: dict, document_id: str) -> None:
    alarm_status = "ALARM" if data["alarm"] else "normal"
    print(
        f"[{machine_name}] "
        f"V={data['voltage_v']:.1f} V | "
        f"I={data['current_a']:.3f} A | "
        f"P={data['active_power_w']:.1f} W | "
        f"E={data['energy_kwh']:.3f} kWh | "
        f"f={data['frequency_hz']:.1f} Hz | "
        f"PF={data['power_factor']:.2f} | "
        f"{alarm_status} | MongoDB ID={document_id}"
    )


def main() -> None:
    config = load_config()
    sensor_config = config["sensor"]
    database_config = config["database"]
    poll_interval = float(config.get("poll_interval_seconds", 1.0))
    retry_interval = float(config.get("retry_interval_seconds", 5.0))

    repository = PowerReadingRepository(
        database_name=database_config.get("name", "cmms"),
        collection_name=database_config.get(
            "collection", "power_sensor_reading"
        ),
    )

    sensor = PZEMSensor(
        port=sensor_config["port"],
        baudrate=int(sensor_config.get("baudrate", 9600)),
        slave_id=int(sensor_config.get("slave_id", 1)),
        timeout=float(sensor_config.get("timeout_seconds", 1.0)),
    )

    machine_id = sensor_config["machine_id"]
    machine_name = sensor_config.get("machine_name", machine_id)
    sensor_model = sensor_config.get("model", "PZEM-016")

    print(
        f"Collector {sensor_model} untuk {machine_name} dimulai. "
        "Tekan Ctrl+C untuk berhenti."
    )

    try:
        while True:
            started_at = time.monotonic()
            try:
                sensor.connect()
                measurement = sensor.read_measurements()
                document_id = repository.save(
                    measurement=measurement,
                    machine_id=machine_id,
                    machine_name=machine_name,
                    sensor_model=sensor_model,
                    slave_id=sensor.slave_id,
                )
                print_measurement(machine_name, measurement, document_id)

                elapsed = time.monotonic() - started_at
                time.sleep(max(0.0, poll_interval - elapsed))
            except Exception as error:
                sensor.disconnect()
                print(f"[{machine_name}] Gagal membaca/menyimpan: {error}")
                print(f"Mencoba kembali dalam {retry_interval:.1f} detik...")
                time.sleep(retry_interval)
    except KeyboardInterrupt:
        print("Collector dihentikan.")
    finally:
        sensor.disconnect()
        repository.close()


if __name__ == "__main__":
    main()
