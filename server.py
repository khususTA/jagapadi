import socket
import threading
import os
import struct
import time
import hashlib
import base64
import signal
import sys
import select
import json
from datetime import datetime

from deteksi import jalankan_deteksi
from aes_enkripsi import encrypt_AES_CTR
from utils.logger import tulis_log_txt, tulis_log_csv

# Konstanta
SERVER_IP = '0.0.0.0'
SERVER_PORT = 12345
BUFFER_SIZE = 4096
PASSWORD_HASH = hashlib.sha256(b"jagapadi2024").hexdigest()

# Folder
FOLDER_ORIGINAL = "original_images"
FOLDER_HASIL = "hasil_identifikasi"
FOLDER_CLIPPER = "clipper_file"
FOLDER_LOG = "logs"

os.makedirs(FOLDER_ORIGINAL, exist_ok=True)
os.makedirs(FOLDER_HASIL, exist_ok=True)
os.makedirs(FOLDER_CLIPPER, exist_ok=True)
os.makedirs(FOLDER_LOG, exist_ok=True)

# Global variables untuk shutdown
server_socket = None
shutdown_flag = False
active_threads = []

def shutdown_server():
    """Fungsi untuk shutdown server secara manual"""
    global shutdown_flag, server_socket
    print("\n[!] Memulai shutdown server...")
    shutdown_flag = True
    
    if server_socket:
        try:
            server_socket.close()
            print("[!] Server socket ditutup")
        except:
            pass
    
    # Tunggu semua thread client selesai
    print("[!] Menunggu koneksi client selesai...")
    for thread in active_threads:
        if thread.is_alive():
            thread.join(timeout=5)
    
    print("[!] Server berhasil shutdown")

def signal_handler(signum, frame):
    """Handler untuk menangani sinyal shutdown (Ctrl+C)"""
    print("\n[!] Menerima sinyal shutdown...")
    shutdown_server()
    sys.exit(0)

def monitor_terminal_input():
    """Thread untuk memantau input terminal"""
    global shutdown_flag
    print("[+] Thread monitor terminal dimulai")
    print("[+] Ketik 'shutdown' atau 'exit' untuk menghentikan server")
    
    while not shutdown_flag:
        try:
            # Gunakan select untuk non-blocking input di Linux/Mac
            if sys.platform != 'win32':
                if select.select([sys.stdin], [], [], 0.5)[0]:
                    command = sys.stdin.readline().strip().lower()
                    if command in ['shutdown', 'exit', 'quit', 'stop']:
                        print(f"[!] Perintah '{command}' diterima")
                        shutdown_server()
                        break
            else:
                # Untuk Windows, gunakan pendekatan yang berbeda
                import msvcrt
                if msvcrt.kbhit():
                    command = input().strip().lower()
                    if command in ['shutdown', 'exit', 'quit', 'stop']:
                        print(f"[!] Perintah '{command}' diterima")
                        shutdown_server()
                        break
                time.sleep(0.5)
        except:
            # Jika ada error dalam membaca input, lanjutkan
            time.sleep(0.5)
            continue

def receive_client_timing_data(conn):
    """
    Menerima data timing dekripsi dari client
    
    Returns:
        dict: data timing dari client atau None jika gagal
    """
    try:
        # Set timeout singkat untuk timing data
        conn.settimeout(2.0)
        
        # Baca header TIMING
        header = conn.recv(6)  # "TIMING"
        if header != b'TIMING':
            return None
        
        # Baca panjang data JSON
        json_len = struct.unpack('>I', conn.recv(4))[0]
        
        # Baca data JSON
        json_data = conn.recv(json_len).decode('utf-8')
        timing_data = json.loads(json_data)
        
        # Kirim acknowledgment
        conn.sendall(b'ACK')
        
        return timing_data
        
    except (socket.timeout, json.JSONDecodeError, struct.error):
        return None
    except Exception as e:
        print(f"[!] Error menerima timing data: {e}")
        return None

def handle_client(conn, addr):
    global active_threads
    client_ip = addr[0]
    waktu_connect = datetime.now()
    log_data = {
        'ip': client_ip,
        'connect_time': waktu_connect,
        'file_logs': []
    }

    print(f"[+] Koneksi dari {client_ip}")
    try:
        # Autentikasi
        header = conn.recv(4)
        if header != b'AUTH':
            conn.close()
            return

        panjang_pw = struct.unpack('>I', conn.recv(4))[0]
        password_hash = conn.recv(panjang_pw).decode()
        if password_hash != PASSWORD_HASH:
            conn.sendall(b'AUTH_NO\x00')
            conn.close()
            return
        conn.sendall(b'AUTH_OK\x00')

        while not shutdown_flag:  # Cek shutdown flag
            # Set timeout untuk recv agar tidak blocking selamanya
            conn.settimeout(1.0)
            try:
                header_data = conn.recv(8)
            except socket.timeout:
                continue  # Coba lagi jika timeout
            except:
                break  # Koneksi terputus
            
            if not header_data:
                break

            # === TIMING: Mulai menerima data ===
            waktu_mulai_terima = time.time()
            
            filename_len, data_len = struct.unpack('>II', header_data)
            filename = conn.recv(filename_len).decode()
            
            file_data = b''
            while len(file_data) < data_len and not shutdown_flag:
                try:
                    chunk = conn.recv(min(BUFFER_SIZE, data_len - len(file_data)))
                    if not chunk:
                        break
                    file_data += chunk
                except socket.timeout:
                    continue
                except:
                    break

            # === TIMING: Selesai menerima data ===
            waktu_selesai_terima = time.time()
            waktu_terima = waktu_selesai_terima - waktu_mulai_terima

            if shutdown_flag:
                break

            # Simpan file asli
            waktu_file = time.time()
            nama_file_simpan = f"{int(waktu_file)}_{filename}"
            path_asli = os.path.join(FOLDER_ORIGINAL, nama_file_simpan)
            with open(path_asli, "wb") as f:
                f.write(file_data)
            ukuran_asli_kb = len(file_data) / 1024

            # === TIMING: Mulai deteksi YOLO ===
            start_deteksi = time.time()
            path_hasil, labels, rata_conf = jalankan_deteksi(path_asli, nama_file_simpan)
            waktu_deteksi = time.time() - start_deteksi

            # === TIMING: Mulai enkripsi ===
            with open(path_hasil, "rb") as f:
                data_hasil = f.read()
            start_enkripsi = time.time()
            encrypted_data, nonce = encrypt_AES_CTR(data_hasil)
            waktu_enkripsi = time.time() - start_enkripsi

            full_data = nonce + encrypted_data
            clipper = base64.b64encode(full_data).decode()
            with open(os.path.join(FOLDER_CLIPPER, nama_file_simpan + ".clip"), "w") as f:
                f.write(clipper)

            # === TIMING: Mulai mengirim data ===
            waktu_mulai_kirim = time.time()
            
            try:
                conn.sendall(struct.pack('>I', len(full_data)))
                conn.sendall(full_data)
            except:
                break  # Koneksi terputus

            # === TIMING: Selesai mengirim data ===
            waktu_selesai_kirim = time.time()
            waktu_kirim = waktu_selesai_kirim - waktu_mulai_kirim

            # === TERIMA DATA TIMING DEKRIPSI DARI CLIENT ===
            client_timing = receive_client_timing_data(conn)

            # Hitung kecepatan transfer
            kecepatan_terima = ukuran_asli_kb / waktu_terima if waktu_terima > 0 else 0
            kecepatan_kirim = (len(full_data) / 1024) / waktu_kirim if waktu_kirim > 0 else 0

            # Logging per file dengan data komunikasi lengkap + timing client
            file_log_entry = {
                'filename': filename,
                'labels': labels,
                'size_ori': ukuran_asli_kb,
                'size_enc': len(full_data) / 1024,
                'waktu_terima': round(waktu_terima, 4),
                'waktu_deteksi': round(waktu_deteksi, 4),
                'waktu_enkripsi': round(waktu_enkripsi, 4),
                'waktu_kirim': round(waktu_kirim, 4),
                'kecepatan_terima': round(kecepatan_terima, 1),
                'kecepatan_kirim': round(kecepatan_kirim, 1),
                'confidence': rata_conf
            }

            # Tambahkan data timing dari client jika tersedia
            if client_timing:
                file_log_entry.update({
                    'waktu_dekripsi_client': client_timing.get('waktu_dekripsi_client', 0),
                    'ukuran_hasil_client_kb': client_timing.get('ukuran_hasil_kb', 0),
                    'waktu_simpan_client': client_timing.get('waktu_simpan_client', 0)
                })
                
                print(f"[📊] {filename} - Server: Terima {waktu_terima:.3f}s, Deteksi {waktu_deteksi:.3f}s, Enkripsi {waktu_enkripsi:.4f}s, Kirim {waktu_kirim:.3f}s | Client: Dekripsi {client_timing.get('waktu_dekripsi_client', 0):.4f}s, Simpan {client_timing.get('waktu_simpan_client', 0):.4f}s")
            else:
                # Data default jika client timing tidak tersedia
                file_log_entry.update({
                    'waktu_dekripsi_client': 0,
                    'ukuran_hasil_client_kb': 0,
                    'waktu_simpan_client': 0
                })
                
                print(f"[📊] {filename} - Terima: {waktu_terima:.3f}s, Deteksi: {waktu_deteksi:.3f}s, Enkripsi: {waktu_enkripsi:.4f}s, Kirim: {waktu_kirim:.3f}s [Client timing: N/A]")

            log_data['file_logs'].append(file_log_entry)

    except Exception as e:
        if not shutdown_flag:  # Jangan print error saat shutdown
            print(f"[!] Error dengan {client_ip}: {e}")
    finally:
        waktu_disc = datetime.now()
        durasi = (waktu_disc - waktu_connect).total_seconds()
        
        # Tulis log lengkap
        if log_data['file_logs']:  # Hanya tulis log jika ada aktivitas
            tulis_log_txt(log_data, waktu_disc, durasi)
            tulis_log_csv(log_data)
            print(f"[📝] Log session disimpan untuk {client_ip} - {len(log_data['file_logs'])} file")
        
        conn.close()
        print(f"[-] Koneksi ditutup: {client_ip} (durasi: {durasi:.1f}s)")
        
        # Hapus thread dari daftar active threads
        current_thread = threading.current_thread()
        if current_thread in active_threads:
            active_threads.remove(current_thread)

def start_server():
    global server_socket, active_threads
    
    # Setup signal handler untuk Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Set socket option untuk reuse address
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((SERVER_IP, SERVER_PORT))
    server_socket.listen(5)
    
    print("=" * 70)
    print("🌾 PESTDETECT SERVER v2.1 - Enhanced with Client Decryption Timing")
    print("=" * 70)
    print(f"[+] Server aktif di {SERVER_IP}:{SERVER_PORT}")
    print(f"[+] Folder log: {FOLDER_LOG}")
    print(f"[+] Password: jagapadi2024")
    print("[+] FITUR BARU: Pencatatan waktu dekripsi dari client")
    print("[+] Tekan Ctrl+C untuk shutdown server")
    print("[+] Atau ketik 'shutdown', 'exit', 'quit', atau 'stop'")
    print("=" * 70)
    
    # Start thread untuk monitor input terminal
    terminal_thread = threading.Thread(target=monitor_terminal_input, daemon=True)
    terminal_thread.start()

    try:
        while not shutdown_flag:
            try:
                # Set timeout untuk accept agar tidak blocking selamanya
                server_socket.settimeout(1.0)
                conn, addr = server_socket.accept()
                
                if shutdown_flag:
                    conn.close()
                    break
                
                thread = threading.Thread(target=handle_client, args=(conn, addr))
                active_threads.append(thread)
                thread.start()
                
                # Bersihkan thread yang sudah selesai
                active_threads = [t for t in active_threads if t.is_alive()]
                
            except socket.timeout:
                continue  # Timeout normal, coba lagi
            except OSError:
                if shutdown_flag:
                    break  # Socket ditutup saat shutdown
                raise
                
    except Exception as e:
        if not shutdown_flag:
            print(f"[!] Error server: {e}")
    finally:
        if server_socket:
            server_socket.close()
        print("[!] Server dihentikan")
        sys.exit(0)

if __name__ == '__main__':
    start_server()