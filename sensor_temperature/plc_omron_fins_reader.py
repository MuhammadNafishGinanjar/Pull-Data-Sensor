import socket
import struct
import time
from turtle import st

# =======================================================
# KONFIGURASI FINS OMRON CP2E
# =======================================================
PLC_IP = '192.168.1.3'
PLC_PORT = 9600  # Port standar FINS UDP adalah 9600

PLC_NODE = 2

def get_local_ip_node(default_node=103):
    try:
        # Hubungkan socket dummy ke IP PLC untuk mendapatkan IP interface lokal
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((PLC_IP, PLC_PORT))
        local_ip = s.getsockname()[0]
        s.close()
        return int(local_ip.split('.')[-1])
    except Exception:
        return default_node

PC_NODE = get_local_ip_node(101)
# =======================================================

# KODE AREA MEMORI OMRON (Word Level)
MEM_D   = 0x82  # D-Memory
MEM_CIO = 0xB0  # CIO Area (Input/Output/Kontak)
MEM_W   = 0xB1  # W-Memory (Work Area)
MEM_H   = 0xB2  # H-Memory (Holding Relay)

def build_fins_header(fin_cmd, sid=0x01):
    """Membangun 10-byte header khusus spesifikasi FINS Omron"""
    # ICF=0x80, RSV=0x00, GCT=0x02
    # DNA=0x00, DA1=Node PLC, DA2=0x00
    # SNA=0x00, SA1=Node PC,  SA2=0x00
    # SID=Penanda Paket
    header = struct.pack('!BBBBBBBBBB', 0x80, 0x00, 0x02, 0x00, PLC_NODE, 0x00, 0x00, PC_NODE, 0x00, sid)
    return header + fin_cmd

def read_memory(sock, mem_area_code, address, count=1):
    """Fungsi utama untuk membaca area memori terserah kita!"""
    # FINS Command Code untuk "Memory Area Read" adalah 01 01
    cmd_code = struct.pack('!BB', 0x01, 0x01)
    
    # Area = 1 Byte, Address Utama = 2 Byte, Bit Num = 1 Byte (0x00 karena kita baca penuh 1 Word / 16bit)
    addr_bytes = struct.pack('!B', mem_area_code) + struct.pack('!HB', address, 0x00)
    
    # Jumlah word yang dibaca
    count_bytes = struct.pack('!H', count)
    
    # Gabungkan semua menjadi 1 paket lalu tambahkan header
    req_data = cmd_code + addr_bytes + count_bytes
    packet = build_fins_header(req_data)
    
    # Flush socket buffer to discard stale packets
    old_timeout = sock.gettimeout()
    sock.settimeout(0.0)
    try:
        while True:
            sock.recvfrom(1024)
    except Exception:
        pass
    finally:
        sock.settimeout(old_timeout)

    # Kirim paket via UDP
    sock.sendto(packet, (PLC_IP, PLC_PORT))
    
    # Tunggu balasan dari PLC
    resp, addr = sock.recvfrom(1024)
    
    # Cek Balasan
    # Header 10 byte + 2 byte command echoes + 2 byte End Code (Status)
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
            # Mencetak respon mentah untuk kita diagnosa bersama
            raw_hex = ' '.join([f"{b:02X}" for b in resp])
            print(f"PLC mengembalikan Error Code: 0x{end_code_1:02X} 0x{end_code_2:02X}")
            print(f"Full RAW Response (Untuk Diagnosa): {raw_hex}")
    return None

def main():
    # FINS secara baku menggunakan koneksi cepat UDP
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(3.0) 
    
    print("=== MENGUJI KONEKSI FINS OMRON ===\n")
    try:
        # Contoh 1: Membaca D100
        print("1. Meminta data dari memori D872...")
        data_d = read_memory(sock, MEM_D, 872, count=2)
        print(f"-> Raw words D872-D873: {data_d}")
        
        if data_d and len(data_d) == 2:
            raw_bytes_normal = struct.pack('!HH', data_d[0], data_d[1])
            raw_bytes_swapped = struct.pack('!HH', data_d[1], data_d[0])
            
            try:
                val_normal = struct.unpack('>f', raw_bytes_normal)[0]
                print(f"-> Float (normal word order): {val_normal}")
            except:
                pass
            
            try:
                val_swapped = struct.unpack('>f', raw_bytes_swapped)[0]
                print(f"-> Float (swapped word order): {val_swapped}")
            except:
                pass
        
        time.sleep(1)
        
        # Contoh 2: Membaca CIO 0 (Biasa berisi status Relay Input Fisik)
        print("\n2. Meminta status Kontak / Bit (Word) di memori CIO 0...")
        data_cio = read_memory(sock, MEM_CIO, 0)
        if data_cio:
            print(f"-> Nilai mentah CIO 0 (Dalam desimal): {data_cio[0]}")
            # Mengkonversi ke representasi biner (Bit 0.00 hingga 0.15)
            print(f"-> Status Per-Bit (0.15 ... 0.00): {bin(data_cio[0])[2:].zfill(16)}")
        time.sleep(1)
        
        # Contoh 3: Membaca W10 (Work Area)
        print("\n3. Meminta data memori bayangan W10...")
        data_w = read_memory(sock, MEM_W, 10)
        print(f"-> Nilai W10: {data_w}")
        
    except socket.timeout:
        print("\n[TIMEOUT] Tidak ada balasan dari PLC.")
        print("Pastikan Port UDP 9600 dihentikan atau Node Number (PC_NODE / PLC_NODE) pada kode ini sudah sama seperti di IP Address Anda!")
    except Exception as e:
        print(f"Terjadi error: {e}")
    finally:
        sock.close()
        print("\nSelesai.")

if __name__ == '__main__':
    main()
