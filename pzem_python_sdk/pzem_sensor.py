from __future__ import annotations

import struct
from typing import Any

import serial


class PZEMError(Exception):
    """Kesalahan komunikasi atau respons dari sensor PZEM."""


def crc16_modbus(data: bytes) -> int:
    """Hitung CRC-16 Modbus. Pada frame, low byte dikirim lebih dahulu."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc & 0xFFFF


def build_read_request(slave_id: int, start_address: int = 0, quantity: int = 10) -> bytes:
    if not 1 <= slave_id <= 247:
        raise ValueError("slave_id harus berada pada rentang 1-247")

    payload = struct.pack(">BBHH", slave_id, 0x04, start_address, quantity)
    crc = crc16_modbus(payload)
    return payload + struct.pack("<H", crc)


def decode_measurement_registers(registers: list[int]) -> dict[str, Any]:
    """Ubah 8 input register PZEM-014/016 (voltage..frequency) menjadi nilai engineering."""
    if len(registers) != 8:
        raise ValueError(f"Diperlukan 8 register, diterima {len(registers)}")

    current_raw = registers[1] | (registers[2] << 16)
    power_raw = registers[3] | (registers[4] << 16)
    energy_raw = registers[5] | (registers[6] << 16)

    return {
        "voltage_v": registers[0] / 10.0,
        "current_a": current_raw / 1000.0,
        "active_power_w": power_raw / 10.0,
        "energy_wh": energy_raw,
        "energy_kwh": energy_raw / 1000.0,
        "frequency_hz": registers[7] / 10.0,
    }


class PZEMSensor:
    REGISTER_COUNT = 8

    def __init__(
        self,
        port: str,
        baudrate: int = 9600,
        slave_id: int = 1,
        timeout: float = 1.0,
    ) -> None:
        self.port = port
        self.baudrate = baudrate
        self.slave_id = slave_id
        self.timeout = timeout
        self.serial_port: serial.Serial | None = None

    def connect(self) -> None:
        if self.serial_port and self.serial_port.is_open:
            return

        self.serial_port = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=self.timeout,
            write_timeout=self.timeout,
        )

    def disconnect(self) -> None:
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()

    def _read_exactly(self, size: int) -> bytes:
        if not self.serial_port:
            raise PZEMError("Port serial belum dibuka")

        result = bytearray()
        while len(result) < size:
            chunk = self.serial_port.read(size - len(result))
            if not chunk:
                raise PZEMError(
                    f"Timeout: menunggu {size} byte, hanya menerima {len(result)} byte"
                )
            result.extend(chunk)
        return bytes(result)

    def _read_response(self) -> bytes:
        header = self._read_exactly(3)
        address, function_code, third_byte = header

        if address != self.slave_id:
            raise PZEMError(
                f"Slave ID respons {address}, seharusnya {self.slave_id}"
            )

        if function_code == (0x04 | 0x80):
            frame = header + self._read_exactly(2)
            self._validate_crc(frame)
            raise PZEMError(f"Modbus exception code 0x{third_byte:02X}")

        if function_code != 0x04:
            raise PZEMError(f"Function code respons tidak sesuai: 0x{function_code:02X}")

        byte_count = third_byte
        expected_bytes = self.REGISTER_COUNT * 2
        if byte_count != expected_bytes:
            raise PZEMError(
                f"Byte count respons {byte_count}, seharusnya {expected_bytes}"
            )

        frame = header + self._read_exactly(byte_count + 2)
        self._validate_crc(frame)
        return frame

    @staticmethod
    def _validate_crc(frame: bytes) -> None:
        if len(frame) < 4:
            raise PZEMError("Frame Modbus terlalu pendek")

        received_crc = int.from_bytes(frame[-2:], byteorder="little")
        calculated_crc = crc16_modbus(frame[:-2])
        if received_crc != calculated_crc:
            raise PZEMError(
                f"CRC salah: diterima 0x{received_crc:04X}, "
                f"hasil hitung 0x{calculated_crc:04X}"
            )

    def read_measurements(self) -> dict[str, Any]:
        if not self.serial_port or not self.serial_port.is_open:
            raise PZEMError("Port serial belum dibuka")

        request = build_read_request(
            slave_id=self.slave_id,
            start_address=0,
            quantity=self.REGISTER_COUNT,
        )

        self.serial_port.reset_input_buffer()
        self.serial_port.write(request)
        self.serial_port.flush()

        frame = self._read_response()
        registers = list(struct.unpack(f">{self.REGISTER_COUNT}H", frame[3:-2]))
        return decode_measurement_registers(registers)

    def __enter__(self) -> "PZEMSensor":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.disconnect()


# =======================================================
# KONFIGURASI KONEKSI DEFAULT
# =======================================================
PZEM_PORT = "USB1"
PZEM_BAUDRATE = 9600
PZEM_SLAVE_ID = 1
PZEM_TIMEOUT = 1.0


def create_default_sensor() -> "PZEMSensor":
    return PZEMSensor(
        port=PZEM_PORT,
        baudrate=PZEM_BAUDRATE,
        slave_id=PZEM_SLAVE_ID,
        timeout=PZEM_TIMEOUT,
    )
