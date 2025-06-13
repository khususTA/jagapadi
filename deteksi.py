import os
from ultralytics import YOLO
from PIL import Image
import numpy as np

MODEL_PATH = "model_hama.pt"
HASIL_FOLDER = "hasil_identifikasi/"

# Inisialisasi model saat file diimpor
model = YOLO(MODEL_PATH)

def jalankan_deteksi(path_input, nama_file):
    """
    Jalankan deteksi YOLO pada file gambar.
    Simpan hasil ke folder hasil_identifikasi.
    Kembalikan: (path_output, list_label, rata_rata_confidence)
    """
    # Jalankan deteksi
    results = model(path_input)
    result = results[0]

    # Ekstrak label dan confidence
    labels = []
    confidences = []
    for box in result.boxes:
        cls = int(box.cls[0])
        conf = float(box.conf[0])
        label = model.names[cls]
        labels.append(label)
        confidences.append(conf)

    # Hitung rata-rata confidence
    rata_conf = round(sum(confidences) / len(confidences), 3) if confidences else 0.0

    # Simpan hasil ke file
    nama_output = f"hasil_{nama_file}"
    path_output = os.path.join(HASIL_FOLDER, nama_output)
    result.save(filename=path_output)

    return path_output, labels, rata_conf
