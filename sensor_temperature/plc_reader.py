import socket
import struct

# =======================================================
# KONFIGURASI FINS OMRON CP2E
# =======================================================
PLC_IP = '192.168.1.3'
PLC_PORT = 9600
PLC_NODE = 2
MEM_D = 0x82
MEM_BIT_W = 0x31                 # W-Memory (Level Bit)
REGISTER_ADDRESS = 872           # Suhu (Mesin Induksi)
PRESSURE_REGISTER_ADDRESS = 646  # Tekanan (Mesin Forging)


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


def build_fins_header(fin_cmd, sid=0x01):
    header = struct.pack('!BBBBBBBBBB', 0x80, 0x00, 0x02, 0x00, PLC_NODE, 0x00, 0x00, PC_NODE, 0x00, sid)
    return header + fin_cmd


def _request_memory(sock, mem_area_code, address, bit_address, count):
    cmd_code = struct.pack('!BB', 0x01, 0x01)
    addr_bytes = struct.pack('!B', mem_area_code) + struct.pack('!HB', address, bit_address)
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
            return resp[14:]
        else:
            raw_hex = ' '.join([f"{b:02X}" for b in resp])
            print(f"PLC mengembalikan Error Code: 0x{end_code_1:02X} 0x{end_code_2:02X}")
            print(f"Full RAW Response: {raw_hex}")
    return None


def read_memory(sock, mem_area_code, address, count=1):
    data_bytes = _request_memory(sock, mem_area_code, address, 0x00, count)
    if data_bytes is None or len(data_bytes) < count * 2:
        return None
    words = []
    for i in range(0, len(data_bytes), 2):
        if i + 1 < len(data_bytes):
            words.append(struct.unpack('!H', data_bytes[i:i + 2])[0])
    return words


def read_bit(sock, mem_area_bit_code, word_address, bit_address, count=1):
    """Baca status ON/OFF (Level Bit), misal untuk sinyal running/idle mesin."""
    data_bytes = _request_memory(sock, mem_area_bit_code, word_address, bit_address, count)
    if data_bytes is None or len(data_bytes) < count:
        return None
    return [byte_val == 1 for byte_val in data_bytes[:count]]


def read_float_register(sock, address):
    data_d = read_memory(sock, MEM_D, address, count=2)
    if data_d and len(data_d) == 2:
        raw_bytes = struct.pack('!HH', data_d[1], data_d[0])
        return struct.unpack('>f', raw_bytes)[0]
    return None


def read_temperature(sock):
    return read_float_register(sock, REGISTER_ADDRESS)


def read_pressure(sock):
    return read_float_register(sock, PRESSURE_REGISTER_ADDRESS)


def create_socket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(3.0)
    return sock
