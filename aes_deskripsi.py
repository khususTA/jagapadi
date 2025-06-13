from Crypto.Cipher import AES

def decrypt_AES_CTR(ciphertext: bytes, nonce: bytes, key: bytes) -> bytes:
    """
    Melakukan dekripsi menggunakan AES CTR.
    Parameter:
        - ciphertext: data terenkripsi (tanpa nonce)
        - nonce: 8-byte nonce yang dikirim dari server
        - key: 32-byte key (harus sama dengan server)
    Return:
        - plain data (bytes)
    """
    cipher = AES.new(key, AES.MODE_CTR, nonce=nonce)
    plaintext = cipher.decrypt(ciphertext)
    return plaintext
