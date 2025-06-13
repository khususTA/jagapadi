from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

# KEY statis sepanjang 32 byte (256 bit)
KEY = b'tEaXKE1f8Xe8k3SlVRMGxQAoGIcDAq0C'  # Ganti jika diperlukan

def encrypt_AES_CTR(data: bytes):
    """
    Enkripsi data (gambar) menggunakan AES CTR.
    Mengembalikan: (ciphertext, nonce)
    """
    nonce = get_random_bytes(8)  # 64-bit nonce untuk CTR
    cipher = AES.new(KEY, AES.MODE_CTR, nonce=nonce)
    ciphertext = cipher.encrypt(data)
    return ciphertext, nonce
