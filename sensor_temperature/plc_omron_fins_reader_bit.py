import socket
import struct

# =======================================================
# KONFIGURASI FINS OMRON
# =======================================================
PLC_IP = '192.168.1.3'
PLC_PORT = 9600

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

# -------------------------------------------------------------
# ! PENTING: KODE AREA MEMORI UNTUK BIT (BERBEDA DENGAN WORD) !
# -------------------------------------------------------------
MEM_BIT_D   = 0x02  # D-Memory (Level Bit) 
MEM_BIT_CIO = 0x30  # CIO Area (Level Bit) 
MEM_BIT_W   = 0x31  # W-Memory (Level Bit)
MEM_BIT_H   = 0x32  # H-Memory (Level Bit)

def build_fins_header(fin_cmd, sid=0x01):
    header = struct.pack('!BBBBBBBBBB', 0x80, 0x00, 0x02, 0x00, PLC_NODE, 0x00, 0x00, PC_NODE, 0x00, sid)
    return header + fin_cmd

def read_memory_bit(sock, mem_area_bit_code, word_address, bit_address, count=1):
    """
    Fungsi khusus untuk MEMBACA memori PLC secara satuan saklar/Mikro (Bit Level).
    parameter 'count' adalah berapa banyak bit secara berjejer yang ingin dibaca/diintip.
    """
    # 01 01 adalah Memory Area Read (Membaca)
    cmd_code = struct.pack('!BB', 0x01, 0x01) 
    
    # Area = 1 Byte, Word Address = 2 Byte, Bit Address = 1 Byte
    addr_bytes = struct.pack('!B', mem_area_bit_code) + struct.pack('!HB', word_address, bit_address)
    
    # Berapa banyak jumlah bit yang dibaca skaligus (Default: 1)
    count_bytes = struct.pack('!H', count) 
    
    # Susun, Pengepackan, lalu Kirimkan pesan 
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

    sock.sendto(packet, (PLC_IP, PLC_PORT))
    resp, _ = sock.recvfrom(1024)
    
    # Menerima Respon
    if len(resp) >= 14:
        end_code_1, end_code_2 = resp[12], resp[13]
        if end_code_1 == 0x00 and end_code_2 == 0x00:
            # PLC Merespon Sukses!
            # Pada standart mesin FINS, jika meminta Bit, maka setiap status alat 
            # akan dikirim memakai amplop 1 byte berturut-turut.
            # \x00 artinya OFF. \x01 artinya ON.
            data_bytes = resp[14:]
            
            # Kita bongkar satu-satu menjadi list (True / False)
            hasil_bits = []
            for byte_satuan in data_bytes:
                if byte_satuan == 1:
                    hasil_bits.append(True)
                else:    
                    hasil_bits.append(False)
                    
            return hasil_bits
        else:
            print(f"Error FINS dari PLC (Status Code): 0x{end_code_1:02X} 0x{end_code_2:02X}")
    return None

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(3.0)
    
    print("=== PROGRAM PEMBACA STATUS SAKLAR FISIK / RELAY (FINS BIT READ) ===")
    
    try:
        # ===============================================
        # TARGET KITA: Membaca status nyala/matinya saklar di H2.07
        # ===============================================
        tipe_memori = MEM_BIT_W
        blok_word = 1     
        lokasi_bit = 5    
        
        print(f"\n[Proses] Menanyakan status listrik/sinyal dari saklar {blok_word}.{lokasi_bit:02d} ...")
        
        # Mengeksekusi penarikan saklar dari memori PLC (count = 1 artinya mengecek 1 saklar saja)
        status_kumpulan_bit = read_memory_bit(sock, tipe_memori, blok_word, lokasi_bit, count=1)
        
        if status_kumpulan_bit is not None:
            # Output function kita adalah Array/List (karena siapa tahu Anda mengisi Count = 10 saklar sekaligus).
            # Karena count kita 1, maka hasil pasti berada tepat di urutan array pertama, yaitu [0].
            status_akhir = status_kumpulan_bit[0] 
            
            if status_akhir == True:
                print(f">>> \033[92mTERDETEKSI ON\033[0m: Aliran Listrik dari Relay sedang [MENYALA]")
            else:
                print(f">>> \033[93mTERDETEKSI OFF\033[0m: Aliran Listrik dari Relay sedang [MATI / TERPUTUS]")
        else:
            print(">>> \033[91mGAGAL MENERIMA DATA SAKLAR.\033[0m")
            
    except socket.timeout:
        print("[TIMEOUT] Pastikan PLC siap menerima dan koneksinya aktif.")
    except Exception as e:
        print(f"Terjadi error Python: {e}")
    finally:
        sock.close()

if __name__ == '__main__':
    main()
