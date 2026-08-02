import struct
import unittest
from unittest.mock import MagicMock

import plc_reader


class PlcReaderTest(unittest.TestCase):
    def test_build_fins_header_layout(self):
        header = plc_reader.build_fins_header(b"\x01\x01", sid=0x01)

        self.assertEqual(header[:4], b"\x80\x00\x02\x00")
        self.assertEqual(header[4], plc_reader.PLC_NODE)
        self.assertEqual(header[9], 0x01)
        self.assertEqual(header[10:], b"\x01\x01")

    def test_read_temperature_decodes_word_swapped_float(self):
        expected_temp = 36.75
        raw = struct.pack('>f', expected_temp)
        word0, word1 = struct.unpack('!HH', raw)
        data_bytes = struct.pack('!HH', word1, word0)  # PLC menyimpan word ter-swap
        response = bytes(12) + b'\x00\x00' + data_bytes

        sock = MagicMock()
        sock.recvfrom.side_effect = [OSError("no data"), (response, ("plc", 9600))]

        temperature = plc_reader.read_temperature(sock)
        print(f"[test_read_temperature_decodes_word_swapped_float] temperature = {temperature}")

        self.assertAlmostEqual(temperature, expected_temp, places=2)

    def test_read_temperature_returns_none_on_error_end_code(self):
        response = bytes(12) + b'\x01\x02' + bytes(4)
        sock = MagicMock()
        sock.recvfrom.side_effect = [OSError("no data"), (response, ("plc", 9600))]

        temperature = plc_reader.read_temperature(sock)
        print(f"[test_read_temperature_returns_none_on_error_end_code] temperature = {temperature}")

        self.assertIsNone(temperature)

    def test_read_pressure_decodes_word_swapped_float(self):
        expected_pressure = 5.42
        raw = struct.pack('>f', expected_pressure)
        word0, word1 = struct.unpack('!HH', raw)
        data_bytes = struct.pack('!HH', word1, word0)  # PLC menyimpan word ter-swap
        response = bytes(12) + b'\x00\x00' + data_bytes

        sock = MagicMock()
        sock.recvfrom.side_effect = [OSError("no data"), (response, ("plc", 9600))]

        pressure = plc_reader.read_pressure(sock)
        print(f"[test_read_pressure_decodes_word_swapped_float] pressure = {pressure}")

        self.assertAlmostEqual(pressure, expected_pressure, places=2)

    def test_temperature_and_pressure_use_different_registers(self):
        self.assertNotEqual(plc_reader.REGISTER_ADDRESS, plc_reader.PRESSURE_REGISTER_ADDRESS)


if __name__ == "__main__":
    unittest.main()
