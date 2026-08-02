import time
import serial

PORT = "COM4"
BAUD = 9600
ADDR = 0x50


def crc16_modbus(data):
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc & 0xFFFF


def build_read_request(device_addr, reg_addr, reg_count):
    data = [device_addr, 0x03, (reg_addr >> 8) & 0xFF, reg_addr & 0xFF,
            (reg_count >> 8) & 0xFF, reg_count & 0xFF]
    crc = crc16_modbus(data)
    data.extend([crc & 0xFF, crc >> 8])  # CRC dikirim LOW dulu baru HIGH!
    return bytes(data)


def main():
    ser = serial.Serial(PORT, BAUD, timeout=1)
    print("Port berhasil terbuka")

    ser.reset_input_buffer()
    ser.reset_output_buffer()

    req = build_read_request(ADDR, 0x0034, 0x0003)  # baca 3 register (AX,AY,AZ) seperti contoh manual
    print(f"Mengirim: {req.hex().upper()}")
    ser.write(req)
    ser.flush()

    time.sleep(0.2)
    response = ser.read(20)
    print(f"Respons ({len(response)} byte): {response.hex().upper()}")

    ser.close()


if __name__ == "__main__":
    main()