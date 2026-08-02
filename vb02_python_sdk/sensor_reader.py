import json
import time
from pathlib import Path

import device_model

CONFIG_PATH = Path(__file__).with_name("config.json")


def load_config():
    with CONFIG_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def create_default_sensor():
    config = load_config()
    sensor_config = config["sensors"][0]
    return VibrationSensor(
        port=sensor_config["port"],
        baudrate=sensor_config["baudrate"],
        address=sensor_config["address"],
    )


class VibrationSensor:
    def __init__(self, port="/dev/ttyUSB0", baudrate=9600, address=0x50):
        self.device = device_model.DeviceModel(
            "WTVB02",
            port,
            baudrate,
            address
        )

    def connect(self):
        self.device.openDevice()
        self.device.startLoopRead()
        time.sleep(0.5)

    def disconnect(self):
        self.device.stopLoopRead()
        self.device.closeDevice()

    def get_data(self):

        return {

            "velocity": {
                "x": self.device.get("58"),
                "y": self.device.get("59"),
                "z": self.device.get("60")
            },

            "displacement": {
                "x": self.device.get("65"),
                "y": self.device.get("66"),
                "z": self.device.get("67")
            },

            "frequency": {
                "x": self.device.get("68"),
                "y": self.device.get("69"),
                "z": self.device.get("70")
            }
        }
        


if __name__ == "__main__":

    sensor = VibrationSensor()

    try:
        sensor.connect()

        while True:
            data = sensor.get_data()

            print(data)

            time.sleep(0.2)

    except KeyboardInterrupt:
        sensor.disconnect()
        print("Stopped.")