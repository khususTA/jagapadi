#!/usr/bin/env python3
"""
JAGAPADI v2.0 Flask Server untuk Raspberry Pi
Integrated dengan tampilan HTML/CSS/JS yang sudah ada
"""

from flask import Flask, render_template, request, jsonify, send_from_directory, send_file
import socket
import base64
import struct
import hashlib
import os
import json
import time
import threading
from datetime import datetime
from pathlib import Path
from aes_deskripsi import decrypt_AES_CTR

# Konfigurasi
SERVER_HOST = '192.168.1.100'  # Sesuaikan dengan server AI
SERVER_PORT = 12345
AES_KEY = b'tEaXKE1f8Xe8k3SlVRMGxQAoGIcDAq0C'

# Flask setup
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

# Path untuk Raspberry Pi
HOME_DIR = Path.home()
BASE_DIR = HOME_DIR / "jagapadi"
FOLDER_HASIL = BASE_DIR / "hasil_dekripsi"
FOLDER_HISTORY = BASE_DIR / "cache_history"
FOLDER_LOG_CLIENT = BASE_DIR / "client_logs"
UPLOAD_FOLDER = BASE_DIR / "uploads"

# Buat direktori yang diperlukan
for folder in [FOLDER_HASIL, FOLDER_HISTORY, FOLDER_LOG_CLIENT, UPLOAD_FOLDER]:
    folder.mkdir(parents=True, exist_ok=True)

class JagaPadiClient:
    def __init__(self):
        self.sock = None
        self.connected = False
        self.authenticated = False
        self.lock = threading.Lock()
        self.connection_info = {
            'last_connected': None,
            'connection_attempts': 0,
            'last_error': None
        }

    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def connect_to_server(self, password):
        with self.lock:
            try:
                # Close existing connection if any
                if self.sock:
                    try:
                        self.sock.close()
                    except:
                        pass
                
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.settimeout(30)
                
                connect_start = time.time()
                self.sock.connect((SERVER_HOST, SERVER_PORT))
                connect_time = time.time() - connect_start

                auth_start = time.time()
                password_hash = self.hash_password(password).encode()
                self.sock.sendall(b'AUTH' + struct.pack('>I', len(password_hash)) + password_hash)

                response = self.sock.recv(8)
                auth_time = time.time() - auth_start
                
                if response == b'AUTH_OK\x00':
                    self.connected = True
                    self.authenticated = True
                    self.connection_info['last_connected'] = datetime.now()
                    self.connection_info['connection_attempts'] += 1
                    self.connection_info['last_error'] = None
                    
                    self._log_connection(True, connect_time, auth_time)
                    
                    return True, f"Terhubung ke server (koneksi: {connect_time:.3f}s, auth: {auth_time:.3f}s)"
                else:
                    self.sock.close()
                    self.connection_info['last_error'] = "Password salah"
                    self._log_connection(False, connect_time, auth_time, "Password salah")
                    return False, "Password salah atau server menolak koneksi"
                    
            except Exception as e:
                self.connection_info['last_error'] = str(e)
                self._log_connection(False, 0, 0, str(e))
                return False, f"Gagal koneksi: {e}"

    def send_image(self, filename, image_data):
        if not self.connected or not self.authenticated:
            return False, "Belum terhubung ke server", None

        try:
            # Timing preparation
            prep_start = time.time()
            filename_bytes = filename.encode('utf-8')
            header = struct.pack('>II', len(filename_bytes), len(image_data))
            prep_time = time.time() - prep_start

            # Send data
            send_start = time.time()
            self.sock.sendall(header + filename_bytes + image_data)
            send_time = time.time() - send_start

            # Receive encrypted result
            receive_start = time.time()
            expected_len = struct.unpack('>I', self._receive_exact(4))[0]
            encrypted_data = self._receive_exact(expected_len)
            receive_time = time.time() - receive_start

            # Decrypt
            decrypt_start = time.time()
            nonce = encrypted_data[:8]
            ciphertext = encrypted_data[8:]
            hasil_bytes = decrypt_AES_CTR(ciphertext, nonce, AES_KEY)
            decrypt_time = time.time() - decrypt_start

            # Save result
            save_start = time.time()
            hasil_filename = f"hasil_{filename}"
            path_hasil = FOLDER_HASIL / hasil_filename
            with open(path_hasil, "wb") as f:
                f.write(hasil_bytes)
            save_time = time.time() - save_start

            # Send timing data to server
            timing_data = {
                'filename': filename,
                'waktu_dekripsi_client': round(decrypt_time, 4),
                'ukuran_hasil_kb': len(hasil_bytes) / 1024,
                'waktu_simpan_client': round(save_time, 4)
            }
            
            try:
                timing_json = json.dumps(timing_data).encode('utf-8')
                timing_header = b'TIMING' + struct.pack('>I', len(timing_json))
                self.sock.sendall(timing_header + timing_json)
                
                ack = self.sock.recv(3)
                if ack != b'ACK':
                    print("[!] Server tidak acknowledge timing data")
            except Exception as e:
                print(f"[!] Gagal kirim timing data: {e}")

            # Create result base64 for response
            result_b64 = "data:image/jpeg;base64," + base64.b64encode(hasil_bytes).decode()
            
            # Log timing
            full_timing = {
                'filename': filename,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'ukuran_asli_kb': len(image_data) / 1024,
                'ukuran_hasil_kb': len(hasil_bytes) / 1024,
                'waktu_kirim': round(send_time, 4),
                'waktu_terima': round(receive_time, 4),
                'waktu_dekripsi': round(decrypt_time, 4),
                'waktu_simpan': round(save_time, 4)
            }
            
            self._save_history(filename, str(path_hasil), full_timing)

            status = f"Berhasil - Upload: {send_time:.2f}s, Download: {receive_time:.2f}s, Dekripsi: {decrypt_time:.3f}s"
            
            return True, status, result_b64
            
        except Exception as e:
            return False, f"Gagal proses gambar: {e}", None

    def _receive_exact(self, size):
        buffer = b""
        while len(buffer) < size:
            chunk = self.sock.recv(size - len(buffer))
            if not chunk:
                raise ConnectionError("Koneksi terputus")
            buffer += chunk
        return buffer

    def _log_connection(self, success, connect_time, auth_time, error=None):
        log_data = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'server': f"{SERVER_HOST}:{SERVER_PORT}",
            'waktu_koneksi': round(connect_time, 4),
            'waktu_autentikasi': round(auth_time, 4),
            'status': 'SUCCESS' if success else 'FAILED',
            'error': error
        }
        
        log_file = FOLDER_LOG_CLIENT / f"connection_{datetime.now().strftime('%Y%m%d')}.log"
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{log_data['timestamp']}] KONEKSI {log_data['status']}\n")
            f.write(f"  Server: {log_data['server']}\n")
            f.write(f"  Waktu Koneksi: {log_data['waktu_koneksi']}s\n")
            f.write(f"  Waktu Auth: {log_data['waktu_autentikasi']}s\n")
            if error:
                f.write(f"  Error: {error}\n")
            f.write("-" * 50 + "\n")

    def _save_history(self, filename, path_hasil, timing_data):
        history_file = FOLDER_HISTORY / "history.json"
        
        item = {
            "nama_file": filename,
            "path": path_hasil,
            "waktu": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "timing": timing_data
        }

        if history_file.exists():
            with open(history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = []

        data.append(item)
        
        if len(data) > 50:
            data = data[-50:]
            
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_history(self):
        history_file = FOLDER_HISTORY / "history.json"
        if history_file.exists():
            with open(history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []

    def get_status(self):
        return {
            'connected': self.connected,
            'authenticated': self.authenticated,
            'server': f"{SERVER_HOST}:{SERVER_PORT}",
            'connection_info': self.connection_info
        }

    def disconnect(self):
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
        self.connected = False
        self.authenticated = False
        
        # Log disconnection
        log_file = FOLDER_LOG_CLIENT / f"connection_{datetime.now().strftime('%Y%m%d')}.log"
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] DISCONNECTED\n")
            f.write("-" * 50 + "\n")

# Global client instance
client_app = JagaPadiClient()

# === FLASK ROUTES ===

@app.route('/')
def index():
    """Halaman utama - render template HTML yang sudah ada"""
    return render_template('index.html')

@app.route('/api/status')
def status():
    """API untuk mengecek status koneksi"""
    return jsonify(client_app.get_status())

@app.route('/api/connect', methods=['POST'])
def connect():
    """API untuk menghubungkan ke server AI"""
    data = request.get_json()
    password = data.get('password', '')
    
    if not password:
        return jsonify({
            'success': False,
            'message': 'Password diperlukan'
        })
    
    success, message = client_app.connect_to_server(password)
    return jsonify({
        'success': success,
        'message': message,
        'connected': client_app.connected
    })

@app.route('/api/disconnect', methods=['POST'])
def disconnect():
    """API untuk memutuskan koneksi dari server"""
    client_app.disconnect()
    return jsonify({
        'success': True,
        'message': 'Terputus dari server'
    })

@app.route('/api/upload', methods=['POST'])
def upload():
    """API untuk upload dan proses gambar"""
    if 'file' not in request.files:
        return jsonify({
            'success': False,
            'message': 'Tidak ada file yang dikirim'
        })
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({
            'success': False,
            'message': 'File tidak dipilih'
        })
    
    if not file.content_type.startswith('image/'):
        return jsonify({
            'success': False,
            'message': 'File harus berupa gambar'
        })
    
    try:
        # Read file data
        file_data = file.read()
        filename = file.filename
        
        # Validate file size
        if len(file_data) > 10 * 1024 * 1024:  # 10MB
            return jsonify({
                'success': False,
                'message': 'Ukuran file terlalu besar (maksimal 10MB)'
            })
        
        # Save uploaded file
        upload_path = UPLOAD_FOLDER / filename
        with open(upload_path, 'wb') as f:
            f.write(file_data)
        
        # Send to AI server
        success, message, result_image = client_app.send_image(filename, file_data)
        
        return jsonify({
            'success': success,
            'message': message,
            'result_image': result_image if success else None,
            'filename': filename,
            'size': len(file_data)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error memproses file: {str(e)}'
        })

@app.route('/api/history')
def history():
    """API untuk mendapatkan riwayat deteksi"""
    return jsonify(client_app.get_history())

@app.route('/hasil/<filename>')
def serve_result(filename):
    """Serve file hasil deteksi"""
    try:
        return send_from_directory(FOLDER_HASIL, filename)
    except FileNotFoundError:
        return jsonify({'error': 'File tidak ditemukan'}), 404

@app.route('/uploads/<filename>')
def serve_upload(filename):
    """Serve file upload"""
    try:
        return send_from_directory(UPLOAD_FOLDER, filename)
    except FileNotFoundError:
        return jsonify({'error': 'File tidak ditemukan'}), 404

@app.route('/api/system-info')
def system_info():
    """API untuk informasi sistem"""
    import psutil
    import platform
    
    try:
        info = {
            'platform': platform.platform(),
            'processor': platform.processor(),
            'architecture': platform.architecture()[0],
            'python_version': platform.python_version(),
            'memory': {
                'total': psutil.virtual_memory().total,
                'available': psutil.virtual_memory().available,
                'percent': psutil.virtual_memory().percent
            },
            'disk': {
                'total': psutil.disk_usage('/').total,
                'free': psutil.disk_usage('/').free,
                'percent': psutil.disk_usage('/').percent
            },
            'network': get_local_ip(),
            'folders': {
                'hasil': str(FOLDER_HASIL),
                'history': str(FOLDER_HISTORY),
                'logs': str(FOLDER_LOG_CLIENT),
                'uploads': str(UPLOAD_FOLDER)
            }
        }
        return jsonify(info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs')
def logs():
    """API untuk mendapatkan log terbaru"""
    try:
        log_files = []
        for log_file in FOLDER_LOG_CLIENT.glob("*.log"):
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read().split('\n')[-50:]  # Last 50 lines
            log_files.append({
                'filename': log_file.name,
                'content': '\n'.join(content),
                'size': log_file.stat().st_size,
                'modified': datetime.fromtimestamp(log_file.stat().st_mtime).isoformat()
            })
        
        return jsonify(log_files)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clear-history', methods=['POST'])
def clear_history():
    """API untuk menghapus riwayat"""
    try:
        history_file = FOLDER_HISTORY / "history.json"
        if history_file.exists():
            history_file.unlink()
        
        return jsonify({
            'success': True,
            'message': 'Riwayat berhasil dihapus'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Gagal menghapus riwayat: {str(e)}'
        })

@app.route('/api/export-logs')
def export_logs():
    """API untuk export semua log sebagai ZIP"""
    import zipfile
    import io
    
    try:
        # Create ZIP in memory
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add all log files
            for log_file in FOLDER_LOG_CLIENT.glob("*.log"):
                zip_file.write(log_file, log_file.name)
            
            # Add history file
            history_file = FOLDER_HISTORY / "history.json"
            if history_file.exists():
                zip_file.write(history_file, "history.json")
        
        zip_buffer.seek(0)
        
        return send_file(
            io.BytesIO(zip_buffer.read()),
            as_attachment=True,
            download_name=f'jagapadi_logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip',
            mimetype='application/zip'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# === ERROR HANDLERS ===

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint tidak ditemukan'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Terjadi kesalahan server'}), 500

@app.errorhandler(413)
def too_large(error):
    return jsonify({'error': 'File terlalu besar'}), 413

# === UTILITY FUNCTIONS ===

def get_local_ip():
    """Mendapatkan IP lokal"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except:
        return "127.0.0.1"

def cleanup_old_files():
    """Membersihkan file lama"""
    import time
    current_time = time.time()
    
    # Hapus file upload yang lebih dari 1 hari
    for file_path in UPLOAD_FOLDER.glob("*"):
        if current_time - file_path.stat().st_mtime > 86400:  # 24 hours
            try:
                file_path.unlink()
                print(f"Deleted old upload: {file_path}")
            except:
                pass
    
    # Hapus log yang lebih dari 30 hari
    for log_file in FOLDER_LOG_CLIENT.glob("*.log"):
        if current_time - log_file.stat().st_mtime > 30 * 86400:  # 30 days
            try:
                log_file.unlink()
                print(f"Deleted old log: {log_file}")
            except:
                pass

def start_web_server():
    """Start Flask web server"""
    print("=" * 60)
    print("🌾 JAGAPADI v2.0 Web Server untuk Raspberry Pi")
    print("=" * 60)
    print(f"🌐 Web interface: http://localhost:5000")
    print(f"🌐 Akses dari jaringan: http://{get_local_ip()}:5000")
    print(f"📁 Hasil disimpan di: {FOLDER_HASIL}")
    print(f"🖥️  Target AI server: {SERVER_HOST}:{SERVER_PORT}")
    print(f"📊 History: {FOLDER_HISTORY}")
    print(f"📝 Logs: {FOLDER_LOG_CLIENT}")
    print("=" * 60)
    print("📱 Buka browser dan akses alamat di atas")
    print("🔧 Untuk development, gunakan debug=True")
    print("=" * 60)
    
    # Cleanup old files on startup
    cleanup_old_files()
    
    # Run Flask app
    try:
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=False,  # Set True untuk development
            threaded=True,
            use_reloader=False  # Disable reloader untuk production
        )
    except KeyboardInterrupt:
        print("\n🛑 Server dihentikan oleh user")
        client_app.disconnect()
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        client_app.disconnect()

if __name__ == '__main__':
    start_web_server()