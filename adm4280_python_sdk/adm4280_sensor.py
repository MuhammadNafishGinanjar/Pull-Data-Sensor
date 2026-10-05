from __future__ import annotations

import minimalmodbus


# =======================================================
# KONFIGURASI MODBUS RTU ADM-4280-C
# =======================================================
ADM4280_PORT         = "/dev/ttyUSB1"
ADM4280_SLAVE_ID     = 1
ADM4280_BAUDRATE     = 9600
ADM4280_TIMEOUT      = 1.0

# Rentang sensor (4-20 mA = 0-600 °C)
TEMP_MIN             = 0.0
TEMP_MAX             = 600.0

# Offset 4 mA pada sinyal raw (register 0, function code 4)
RAW_ZERO_OFFSET      = 3500.0
RAW_SPAN             = 32767.0 - RAW_ZERO_OFFSET


class ADM4280Sensor:
    def __init__(
        self,
        port: str = ADM4280_PORT,
        slave_id: int = ADM4280_SLAVE_ID,
        baudrate: int = ADM4280_BAUDRATE,
        timeout: float = ADM4280_TIMEOUT,
    ) -> None:
        self.port = port
        self.slave_id = slave_id
        self.baudrate = baudrate
        self.timeout = timeout
        self._instrument: minimalmodbus.Instrument | None = None

    def connect(self) -> None:
        if self._instrument is not None:
            return

        instrument = minimalmodbus.Instrument(self.port, self.slave_id)
        instrument.serial.baudrate = self.baudrate
        instrument.serial.bytesize = 8
        instrument.serial.parity = minimalmodbus.serial.PARITY_NONE
        instrument.serial.stopbits = 1
        instrument.serial.timeout = self.timeout
        instrument.mode = minimalmodbus.MODE_RTU
        self._instrument = instrument

    def disconnect(self) -> None:
        if self._instrument is not None:
            try:
                self._instrument.serial.close()
            except Exception:
                pass
            self._instrument = None

    def read_temperature(self) -> float | None:
        if self._instrument is None:
            raise RuntimeError("Sensor belum terhubung. Panggil connect() terlebih dahulu.")

        try:
            raw_value = self._instrument.read_register(
                registeraddress=0,
                number_of_decimals=0,
                functioncode=4,
                signed=False,
            )
            adjusted_raw = max(0.0, raw_value - RAW_ZERO_OFFSET)
            temperature = (adjusted_raw / RAW_SPAN) * (TEMP_MAX - TEMP_MIN) + TEMP_MIN
            return temperature
        except Exception as e:
            print(f"[ADM4280] Gagal membaca suhu: {e}")
            return None

    def __enter__(self) -> "ADM4280Sensor":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.disconnect()


def create_default_sensor() -> ADM4280Sensor:
    return ADM4280Sensor(
        port=ADM4280_PORT,
        slave_id=ADM4280_SLAVE_ID,
        baudrate=ADM4280_BAUDRATE,
        timeout=ADM4280_TIMEOUT,
    )


if __name__ == "__main__":
    import time

    sensor = create_default_sensor()
    sensor.connect()
    print(f"Menghubungkan ke Sensor Suhu ({ADM4280_PORT})...")
    print("Membaca suhu ruangan/objek (0-600°C). Tekan Ctrl+C untuk keluar.\n")

    try:
        while True:
            temp = sensor.read_temperature()
            if temp is not None:
                print(f"Suhu: {temp:5.1f} °C")
            time.sleep(2)
    except KeyboardInterrupt:
        print("\nProgram dihentikan oleh pengguna.")
    finally:
        sensor.disconnect()
