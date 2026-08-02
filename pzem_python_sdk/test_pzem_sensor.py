import unittest

from pzem_sensor import build_read_request, crc16_modbus, decode_measurement_registers


class PZEMParserTest(unittest.TestCase):
    def test_datasheet_measurement_example(self):
        registers = [
            0x0898,
            0x03E8,
            0x0000,
            0x0898,
            0x0000,
            0x0000,
            0x0000,
            0x01F4,
            0x0064,
            0x0000,
        ]

        data = decode_measurement_registers(registers)
        print(f"[test_datasheet_measurement_example] data = {data}")

        self.assertEqual(data["voltage_v"], 220.0)
        self.assertEqual(data["current_a"], 1.0)
        self.assertEqual(data["active_power_w"], 220.0)
        self.assertEqual(data["energy_wh"], 0)
        self.assertEqual(data["frequency_hz"], 50.0)
        self.assertEqual(data["power_factor"], 1.0)
        self.assertFalse(data["alarm"])

    def test_read_request_uses_function_04_and_valid_crc(self):
        request = build_read_request(slave_id=1, start_address=0, quantity=10)
        print(f"[test_read_request_uses_function_04_and_valid_crc] request = {request.hex().upper()}")

        self.assertEqual(request, bytes.fromhex("01 04 00 00 00 0A 70 0D"))
        self.assertEqual(int.from_bytes(request[-2:], "little"), crc16_modbus(request[:-2]))


if __name__ == "__main__":
    unittest.main()
