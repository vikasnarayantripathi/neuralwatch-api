# app/crypto.py
import os
import urllib.parse
from cryptography.fernet import Fernet, InvalidToken

_raw_key = os.environ.get("ENCRYPTION_KEY", "")

if _raw_key:
    _fernet = Fernet(_raw_key.encode())
else:
    # Dev fallback — never used in production
    _fernet = Fernet(Fernet.generate_key())


def encrypt(plaintext: str) -> str:
    """Encrypt a string. Returns ciphertext."""
    if not plaintext:
        return ""
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    """Decrypt a ciphertext string. Returns plaintext."""
    if not ciphertext:
        return ""
    try:
        return _fernet.decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        raise ValueError("Decryption failed — wrong key or corrupted data")


def build_rtsp_url(
    ip: str,
    port: int,
    username: str,
    password: str,
    path: str
) -> str:
    """Assemble a full RTSP URL from parts."""
    user = urllib.parse.quote(username, safe="")
    pwd  = urllib.parse.quote(password, safe="")
    return f"rtsp://{user}:{pwd}@{ip}:{port}{path}"


def mask_rtsp_url(rtsp_url: str) -> str:
    """Replace password in RTSP URL with *** for safe logging."""
    import re
    return re.sub(r"(rtsp?://[^:]+:)[^@]+(@)", r"\1***\2", rtsp_url)
