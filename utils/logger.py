import os
import csv
from datetime import datetime

def tulis_log_txt(log_data, waktu_disc, durasi):
    """
    Menulis log session dalam format TXT yang mudah dibaca
    
    Args:
        log_data: dict berisi data client dan file logs
        waktu_disc: datetime waktu disconnect
        durasi: float durasi koneksi dalam detik
    """
    # Format nama file log berdasarkan waktu connect
    connect_time_str = log_data['connect_time'].strftime("%Y%m%d_%H%M%S")
    log_filename = f"session_{connect_time_str}.txt"
    log_path = os.path.join("logs", log_filename)
    
    # Hitung statistik session
    jumlah_file = len(log_data['file_logs'])
    jumlah_deteksi = sum(1 for file_log in log_data['file_logs'] if file_log['labels'])
    
    # Hitung rata-rata confidence (hanya file yang ada deteksi)
    confidence_values = [file_log['confidence'] for file_log in log_data['file_logs'] if file_log['confidence'] > 0]
    rata_conf = sum(confidence_values) / len(confidence_values) if confidence_values else 0.0
    
    # Hitung statistik timing dekripsi client
    client_decrypt_times = [file_log.get('waktu_dekripsi_client', 0) for file_log in log_data['file_logs'] if file_log.get('waktu_dekripsi_client', 0) > 0]
    rata_decrypt_client = sum(client_decrypt_times) / len(client_decrypt_times) if client_decrypt_times else 0.0
    total_decrypt_client = sum(client_decrypt_times)
    
    # Hitung statistik timing simpan client
    client_save_times = [file_log.get('waktu_simpan_client', 0) for file_log in log_data['file_logs'] if file_log.get('waktu_simpan_client', 0) > 0]
    rata_save_client = sum(client_save_times) / len(client_save_times) if client_save_times else 0.0
    total_save_client = sum(client_save_times)
    
    with open(log_path, 'w', encoding='utf-8') as f:
        # Header session
        f.write("=" * 80 + "\n")
        f.write(f"IP Client             : {log_data['ip']}\n")
        f.write(f"Connected             : {log_data['connect_time'].strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Disconnected          : {waktu_disc.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total Waktu Session   : {durasi:.2f} detik\n")
        f.write(f"Jumlah File           : {jumlah_file}\n")
        f.write(f"Jumlah Deteksi        : {jumlah_deteksi}\n")
        f.write(f"Rata-rata Confidence  : {rata_conf:.3f}\n")
        f.write("=" * 80 + "\n")
        
        # Statistik Timing Client (jika ada data)
        if client_decrypt_times or client_save_times:
            f.write("STATISTIK TIMING CLIENT:\n")
            f.write("-" * 50 + "\n")
            if client_decrypt_times:
                f.write(f"Rata-rata Dekripsi Client : {rata_decrypt_client:.4f} detik\n")
                f.write(f"Total Dekripsi Client     : {total_decrypt_client:.4f} detik\n")
            if client_save_times:
                f.write(f"Rata-rata Simpan Client   : {rata_save_client:.4f} detik\n")
                f.write(f"Total Simpan Client       : {total_save_client:.4f} detik\n")
            f.write("-" * 50 + "\n")
        
        # Detail transfer file
        if jumlah_file > 0:
            f.write("DETAIL TRANSFER FILE:\n")
            f.write("-" * 250 + "\n")
            
            # Header tabel dengan kolom tambahan untuk client timing
            header = f"{'Nama File':<25} | {'Label Deteksi':<20} | {'Uk. Asli (KB)':>12} | {'Uk. Enkripsi (KB)':>15} | {'W. Terima (s)':>12} | {'W. Deteksi (s)':>13} | {'W. Enkripsi (s)':>14} | {'W. Kirim (s)':>12} | {'Kec. Masuk (KB/s)':>16} | {'Kec. Keluar (KB/s)':>17} | {'W. Dekripsi Client (s)':>20} | {'W. Simpan Client (s)':>18}"
            f.write(header + "\n")
            f.write("-" * 250 + "\n")
            
            # Data setiap file
            for file_log in log_data['file_logs']:
                # Potong nama file jika terlalu panjang
                filename = file_log['filename']
                if len(filename) > 23:
                    filename = filename[:20] + "..."
                
                # Format label (gabung dengan koma jika multiple)
                labels_str = ", ".join(file_log['labels']) if file_log['labels'] else ""
                if len(labels_str) > 18:
                    labels_str = labels_str[:15] + "..."
                
                # Format angka dengan presisi yang sesuai
                size_ori = f"{file_log['size_ori']:.2f}"
                size_enc = f"{file_log['size_enc']:.2f}"
                waktu_terima = f"{file_log.get('waktu_terima', 0):.4f}"
                waktu_det = f"{file_log['waktu_deteksi']:.4f}"
                waktu_enc = f"{file_log['waktu_enkripsi']:.4f}"
                waktu_kirim = f"{file_log.get('waktu_kirim', 0):.4f}"
                kec_masuk = f"{file_log.get('kecepatan_terima', 0):.1f}"
                kec_keluar = f"{file_log.get('kecepatan_kirim', 0):.1f}"
                
                # Format timing client
                waktu_dekripsi_client = f"{file_log.get('waktu_dekripsi_client', 0):.4f}"
                waktu_simpan_client = f"{file_log.get('waktu_simpan_client', 0):.4f}"
                
                # Tulis baris data
                row = f"{filename:<25} | {labels_str:<20} | {size_ori:>12} | {size_enc:>15} | {waktu_terima:>12} | {waktu_det:>13} | {waktu_enc:>14} | {waktu_kirim:>12} | {kec_masuk:>16} | {kec_keluar:>17} | {waktu_dekripsi_client:>20} | {waktu_simpan_client:>18}"
                f.write(row + "\n")
        
        f.write("\n")
        
        # Summary timing jika ada data client
        if client_decrypt_times or client_save_times:
            f.write("SUMMARY TIMING LENGKAP:\n")
            f.write("-" * 60 + "\n")
            
            # Hitung total waktu server
            total_server_detect = sum(file_log['waktu_deteksi'] for file_log in log_data['file_logs'])
            total_server_encrypt = sum(file_log['waktu_enkripsi'] for file_log in log_data['file_logs'])
            total_server_receive = sum(file_log.get('waktu_terima', 0) for file_log in log_data['file_logs'])
            total_server_send = sum(file_log.get('waktu_kirim', 0) for file_log in log_data['file_logs'])
            
            f.write(f"TOTAL SERVER PROCESSING:\n")
            f.write(f"  - Terima data      : {total_server_receive:.4f} detik\n")
            f.write(f"  - Deteksi YOLO     : {total_server_detect:.4f} detik\n")
            f.write(f"  - Enkripsi AES     : {total_server_encrypt:.4f} detik\n")
            f.write(f"  - Kirim hasil      : {total_server_send:.4f} detik\n")
            f.write(f"  - TOTAL SERVER     : {total_server_receive + total_server_detect + total_server_encrypt + total_server_send:.4f} detik\n")
            f.write("\n")
            
            if client_decrypt_times or client_save_times:
                f.write(f"TOTAL CLIENT PROCESSING:\n")
                f.write(f"  - Dekripsi AES     : {total_decrypt_client:.4f} detik\n")
                f.write(f"  - Simpan file      : {total_save_client:.4f} detik\n")
                f.write(f"  - TOTAL CLIENT     : {total_decrypt_client + total_save_client:.4f} detik\n")
                f.write("\n")
                
                f.write(f"TOTAL KESELURUHAN   : {total_server_receive + total_server_detect + total_server_encrypt + total_server_send + total_decrypt_client + total_save_client:.4f} detik\n")
            
            f.write("-" * 60 + "\n")

def tulis_log_csv(log_data):
    """
    Menulis log ke file CSV untuk analisis data
    
    Args:
        log_data: dict berisi data client dan file logs
    """
    csv_path = os.path.join("logs", "detection_database.csv")
    
    # Cek apakah file CSV sudah ada (untuk header)
    file_exists = os.path.exists(csv_path)
    
    with open(csv_path, 'a', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'timestamp', 'client_ip', 'filename', 'labels', 
            'size_ori_kb', 'size_enc_kb', 'waktu_terima', 'waktu_deteksi', 
            'waktu_enkripsi', 'waktu_kirim', 'kecepatan_terima', 
            'kecepatan_kirim', 'confidence', 'waktu_dekripsi_client',
            'ukuran_hasil_client_kb', 'waktu_simpan_client'
        ]
        
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        # Tulis header jika file baru
        if not file_exists:
            writer.writeheader()
        
        # Tulis data setiap file
        for file_log in log_data['file_logs']:
            writer.writerow({
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'client_ip': log_data['ip'],
                'filename': file_log['filename'],
                'labels': "|".join(file_log['labels']) if file_log['labels'] else "",
                'size_ori_kb': round(file_log['size_ori'], 2),
                'size_enc_kb': round(file_log['size_enc'], 2),
                'waktu_terima': round(file_log.get('waktu_terima', 0), 4),
                'waktu_deteksi': round(file_log['waktu_deteksi'], 4),
                'waktu_enkripsi': round(file_log['waktu_enkripsi'], 4),
                'waktu_kirim': round(file_log.get('waktu_kirim', 0), 4),
                'kecepatan_terima': round(file_log.get('kecepatan_terima', 0), 1),
                'kecepatan_kirim': round(file_log.get('kecepatan_kirim', 0), 1),
                'confidence': round(file_log['confidence'], 3),
                'waktu_dekripsi_client': round(file_log.get('waktu_dekripsi_client', 0), 4),
                'ukuran_hasil_client_kb': round(file_log.get('ukuran_hasil_client_kb', 0), 2),
                'waktu_simpan_client': round(file_log.get('waktu_simpan_client', 0), 4)
            })

def buat_log_summary_harian():
    """
    Membuat summary log harian dari semua session
    """
    today = datetime.now().strftime("%Y%m%d")
    summary_path = os.path.join("logs", f"daily_summary_{today}.txt")
    
    # Scan semua file log hari ini
    log_files = []
    for filename in os.listdir("logs"):
        if filename.startswith("session_") and filename.startswith(f"session_{today}"):
            log_files.append(filename)
    
    if not log_files:
        return
    
    # Hitung statistik harian
    total_sessions = len(log_files)
    total_files = 0
    total_detections = 0
    unique_ips = set()
    total_client_decrypt_time = 0
    total_client_save_time = 0
    client_processes = 0
    
    # Baca CSV untuk statistik detail
    csv_path = os.path.join("logs", "detection_database.csv")
    if os.path.exists(csv_path):
        with open(csv_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['timestamp'].startswith(today.replace('', '-')):
                    total_files += 1
                    if row['labels']:
                        total_detections += 1
                    unique_ips.add(row['client_ip'])
                    
                    # Statistik client timing
                    if row.get('waktu_dekripsi_client') and float(row['waktu_dekripsi_client']) > 0:
                        total_client_decrypt_time += float(row['waktu_dekripsi_client'])
                        client_processes += 1
                    if row.get('waktu_simpan_client') and float(row['waktu_simpan_client']) > 0:
                        total_client_save_time += float(row['waktu_simpan_client'])
    
    # Tulis summary
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write(f"DAILY SUMMARY - {today}\n")
        f.write("=" * 60 + "\n")
        f.write(f"Total Sessions     : {total_sessions}\n")
        f.write(f"Unique IPs         : {len(unique_ips)}\n")
        f.write(f"Total Files        : {total_files}\n")
        f.write(f"Total Detections   : {total_detections}\n")
        f.write(f"Detection Rate     : {(total_detections/total_files*100):.1f}%\n" if total_files > 0 else "Detection Rate     : 0.0%\n")
        f.write("-" * 60 + "\n")
        
        # Statistik Client Processing
        if client_processes > 0:
            avg_client_decrypt = total_client_decrypt_time / client_processes
            avg_client_save = total_client_save_time / client_processes
            f.write("CLIENT PROCESSING STATISTICS:\n")
            f.write(f"Files with Client Data : {client_processes}\n")
            f.write(f"Total Client Decrypt   : {total_client_decrypt_time:.4f} detik\n")
            f.write(f"Total Client Save      : {total_client_save_time:.4f} detik\n")
            f.write(f"Avg Client Decrypt     : {avg_client_decrypt:.4f} detik\n")
            f.write(f"Avg Client Save        : {avg_client_save:.4f} detik\n")
            f.write("-" * 60 + "\n")
        
        f.write("=" * 60 + "\n")

def cleanup_old_logs(days_to_keep=30):
    """
    Membersihkan log lama (opsional)
    
    Args:
        days_to_keep: int jumlah hari log yang disimpan
    """
    import time
    
    current_time = time.time()
    cutoff_time = current_time - (days_to_keep * 24 * 60 * 60)
    
    log_dir = "logs"
    for filename in os.listdir(log_dir):
        if filename.startswith("session_"):
            file_path = os.path.join(log_dir, filename)
            if os.path.getmtime(file_path) < cutoff_time:
                os.remove(file_path)
                print(f"[LOG] Cleaned up old log: {filename}")

# Fungsi utility untuk membaca log
def baca_statistik_hari_ini():
    """
    Membaca statistik hari ini dari CSV
    
    Returns:
        dict: statistik hari ini
    """
    today = datetime.now().strftime("%Y-%m-%d")
    csv_path = os.path.join("logs", "detection_database.csv")
    
    stats = {
        'total_files': 0,
        'total_detections': 0,
        'avg_confidence': 0.0,
        'avg_detection_time': 0.0,
        'unique_ips': set(),
        'avg_client_decrypt_time': 0.0,
        'avg_client_save_time': 0.0,
        'total_client_decrypt_time': 0.0,
        'total_client_save_time': 0.0,
        'files_with_client_data': 0
    }
    
    if not os.path.exists(csv_path):
        return stats
    
    confidence_values = []
    detection_times = []
    client_decrypt_times = []
    client_save_times = []
    
    with open(csv_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row['timestamp'].startswith(today):
                stats['total_files'] += 1
                stats['unique_ips'].add(row['client_ip'])
                
                if row['labels']:
                    stats['total_detections'] += 1
                    if float(row['confidence']) > 0:
                        confidence_values.append(float(row['confidence']))
                
                detection_times.append(float(row['waktu_deteksi']))
                
                # Statistik client
                if row.get('waktu_dekripsi_client') and float(row['waktu_dekripsi_client']) > 0:
                    client_decrypt_times.append(float(row['waktu_dekripsi_client']))
                    stats['files_with_client_data'] += 1
                
                if row.get('waktu_simpan_client') and float(row['waktu_simpan_client']) > 0:
                    client_save_times.append(float(row['waktu_simpan_client']))
    
    # Hitung rata-rata
    if confidence_values:
        stats['avg_confidence'] = sum(confidence_values) / len(confidence_values)
    
    if detection_times:
        stats['avg_detection_time'] = sum(detection_times) / len(detection_times)
    
    if client_decrypt_times:
        stats['avg_client_decrypt_time'] = sum(client_decrypt_times) / len(client_decrypt_times)
        stats['total_client_decrypt_time'] = sum(client_decrypt_times)
    
    if client_save_times:
        stats['avg_client_save_time'] = sum(client_save_times) / len(client_save_times)
        stats['total_client_save_time'] = sum(client_save_times)
    
    stats['unique_ips'] = len(stats['unique_ips'])
    
    return stats

def baca_analisis_performa_client():
    """
    Membaca dan menganalisis performa client dari log
    
    Returns:
        dict: analisis performa client
    """
    today = datetime.now().strftime("%Y-%m-%d")
    csv_path = os.path.join("logs", "detection_database.csv")
    
    client_stats = {}
    
    if not os.path.exists(csv_path):
        return client_stats
    
    with open(csv_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row['timestamp'].startswith(today):
                client_ip = row['client_ip']
                
                if client_ip not in client_stats:
                    client_stats[client_ip] = {
                        'total_files': 0,
                        'total_detections': 0,
                        'decrypt_times': [],
                        'save_times': [],
                        'confidence_values': []
                    }
                
                client_stats[client_ip]['total_files'] += 1
                
                if row['labels']:
                    client_stats[client_ip]['total_detections'] += 1
                    if float(row['confidence']) > 0:
                        client_stats[client_ip]['confidence_values'].append(float(row['confidence']))
                
                if row.get('waktu_dekripsi_client') and float(row['waktu_dekripsi_client']) > 0:
                    client_stats[client_ip]['decrypt_times'].append(float(row['waktu_dekripsi_client']))
                
                if row.get('waktu_simpan_client') and float(row['waktu_simpan_client']) > 0:
                    client_stats[client_ip]['save_times'].append(float(row['waktu_simpan_client']))
    
    # Hitung statistik per client
    for client_ip in client_stats:
        stats = client_stats[client_ip]
        
        stats['avg_decrypt_time'] = sum(stats['decrypt_times']) / len(stats['decrypt_times']) if stats['decrypt_times'] else 0
        stats['avg_save_time'] = sum(stats['save_times']) / len(stats['save_times']) if stats['save_times'] else 0
        stats['avg_confidence'] = sum(stats['confidence_values']) / len(stats['confidence_values']) if stats['confidence_values'] else 0
        stats['detection_rate'] = (stats['total_detections'] / stats['total_files'] * 100) if stats['total_files'] > 0 else 0
        
        # Bersihkan list yang tidak diperlukan untuk output
        del stats['decrypt_times']
        del stats['save_times']
        del stats['confidence_values']
    
    return client_stats