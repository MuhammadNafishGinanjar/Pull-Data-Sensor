import unittest
from unittest.mock import MagicMock, patch

import sensor_reader


class VibrationSensorTest(unittest.TestCase):
    @patch("sensor_reader.device_model.DeviceModel")
    def test_get_data_maps_vrms_registers_to_velocity(self, mock_device_model_cls):
        mock_device = MagicMock()
        mock_device.get.side_effect = lambda key: {
            "VRMS_80": 1.1, "VRMS_92": 1.2, "VRMS_104": 1.3,
        }[key]
        mock_device_model_cls.return_value = mock_device

        sensor = sensor_reader.VibrationSensor(port="COM4", baudrate=9600, address=0x50)
        data = sensor.get_data()
        print(f"[test_get_data_maps_vrms_registers_to_velocity] data = {data}")

        self.assertEqual(data, {"velocity": {"x": 1.1, "y": 1.2, "z": 1.3}})

    @patch("sensor_reader.device_model.DeviceModel")
    def test_create_default_sensor_reads_config(self, mock_device_model_cls):
        sensor_reader.create_default_sensor()

        config = sensor_reader.load_config()["sensors"][0]
        print(f"[test_create_default_sensor_reads_config] config = {config}")
        mock_device_model_cls.assert_called_once_with(
            "WTVB02", config["port"], config["baudrate"], config["address"]
        )


if __name__ == "__main__":
    unittest.main()
