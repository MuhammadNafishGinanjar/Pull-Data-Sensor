import socket
import struct
import time
import os
from datetime import datetime, timezone
from pymongo import MongoClient
import requests

# =======================================================
# KONFIGURASI FINS OMRON CP2E
# =======================================================
PLC_IP = '192.168.1.3'
PLC_PORT = 9600
PLC_NODE = 2
MEM_D = 0x82
REGISTER_ADDRESS = 872

MACHINE_ID = "MCH-003"

def get_local_ip_node(default_node=101):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((PLC_IP, PLC_PORT))
        local_ip = s.getsockname()[0]
        s.close()
        return int(local_ip.split('.')[-1])
    except Exception:
        return default_node

PC_NODE = get_local_ip_node(101)

# =======================================================
# KONFIGURASI MONGODB
# =======================================================
MONGO_URI = "mongodb+srv://naufalreswara7_db_user:admin123@cluster0.q0cqtdj.mongodb.net/?appName=Cluster0"
DB_NAME = "cmms"
COLLECTION_NAME = "temperature_sensor_reading"

API_URL = "https://cmms-polmanbandung.site/api/ml/sensor-data"
API_MACHINE_ID = "IND-001"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

# =======================================================
def build_fins_header(fin_cmd, sid=0x01):
    header = struct.pack('!BBBBBBBBBB', 0x80, 0x00, 0x02, 0x00, PLC_NODE, 0x00, 0x00, PC_NODE, 0x00, sid)
    return header + fin_cmd

def read_memory(sock, mem_area_code, address, count=1):
    cmd_code = struct.pack('!BB', 0x01, 0x01)
    addr_bytes = struct.pack('!B', mem_area_code) + struct.pack('!HB', address, 0x00)
    count_bytes = struct.pack('!H', count)
    req_data = cmd_code + addr_bytes + count_bytes
    packet = build_fins_header(req_data)

    old_timeout = sock.gettimeout()
    sock.settimeout(0.0)
    try:
        while True:
            sock.recvfrom(1024)
    except Exception:
        pass
    finally:
        sock.settimeout(old_timeout)

    sock.sendto(packet, (PLC_IP, PLC_PORT))
    resp, addr = sock.recvfrom(1024)

    if len(resp) >= 14:
        end_code_1, end_code_2 = resp[12], resp[13]
        if end_code_1 == 0x00 and end_code_2 == 0x00:
            data_bytes = resp[14:]
            if len(data_bytes) < count * 2:
                return None
            words = []
            for i in range(0, len(data_bytes), 2):
                if i + 1 < len(data_bytes):
                    value = struct.unpack('!H', data_bytes[i:i+2])[0]
                    words.append(value)
            return words
        else:
            raw_hex = ' '.join([f"{b:02X}" for b in resp])
            print(f"PLC mengembalikan Error Code: 0x{end_code_1:02X} 0x{end_code_2:02X}")
            print(f"Full RAW Response: {raw_hex}")
    return None

def read_temperature(sock):
    data_d = read_memory(sock, MEM_D, REGISTER_ADDRESS, count=2)
    if data_d and len(data_d) == 2:
        raw_bytes = struct.pack('!HH', data_d[1], data_d[0])
        temperature = struct.unpack('>f', raw_bytes)[0]
        return temperature
    return None

def save_to_mongo(temperature):
    document = {
        "machine_id": MACHINE_ID,
        "timestamp": datetime.now(timezone.utc),
        "temp": round(temperature, 2)
    }
    collection.insert_one(document)
    print(f"[{MACHINE_ID}] Saved: {document}")

    payload = {k: v for k, v in document.items() if k not in ("_id", "timestamp")}
    payload["machine_id"] = API_MACHINE_ID
    send_to_api(payload)

def send_to_api(payload):
    try:
        response = requests.post(API_URL, json=payload, timeout=5)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"[API] Failed to send sensor data: {e}")

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(3.0)
    try:
        while True:
            try:
                temperature = read_temperature(sock)
                if temperature is not None:
                    save_to_mongo(temperature)
                else:
                    print("Gagal membaca suhu, mencoba lagi...")
            except socket.timeout:
                print("[TIMEOUT] Tidak ada balasan dari PLC, mencoba lagi...")
            except Exception as e:
                print(f"Error saat membaca/menyimpan: {e}")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nDihentikan oleh pengguna.")
    finally:
        sock.close()
        client.close()
        print("Selesai.")

if __name__ == '__main__':
    main()