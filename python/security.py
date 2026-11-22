"""Symmetric encryption for secrets stored in the database (Tapo passwords, TOTP secrets).

The key lives OUTSIDE the database (env SECRET_KEY or a key file next to it), so a copied DB file
or a downloaded backup does not contain usable credentials on its own.
"""
import os
import threading

from cryptography.fernet import Fernet, InvalidToken

ENC_PREFIX = "enc:v1:"
_DEFAULT_DB_PATH = os.getenv("DB_PATH", "/app/data/bms_data.db")
KEY_FILE = os.getenv("SECRET_KEY_FILE", os.path.join(os.path.dirname(_DEFAULT_DB_PATH) or ".", "secret.key"))

_fernet = None
_lock = threading.Lock()


def _load_or_create_key() -> bytes:
    env_key = os.getenv("SECRET_KEY", "").strip()
    if env_key:
        return env_key.encode("utf-8")

    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as f:
            return f.read().strip()

    key = Fernet.generate_key()
    os.makedirs(os.path.dirname(KEY_FILE) or ".", exist_ok=True)
    # O_EXCL: never overwrite an existing key (that would make all stored secrets unreadable).
    fd = os.open(KEY_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(key)
    print(f"🔑 Generated a new encryption key: {KEY_FILE} (keep a copy of it together with DB backups)")
    return key


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        with _lock:
            if _fernet is None:
                _fernet = Fernet(_load_or_create_key())
    return _fernet


def is_encrypted(value) -> bool:
    return isinstance(value, str) and value.startswith(ENC_PREFIX)


def encrypt(value):
    if value is None or value == "" or is_encrypted(value):
        return value
    token = _get_fernet().encrypt(str(value).encode("utf-8")).decode("ascii")
    return ENC_PREFIX + token


def decrypt(value):
    """Returns the plaintext. Legacy (unencrypted) values are returned unchanged."""
    if not is_encrypted(value):
        return value
    try:
        return _get_fernet().decrypt(value[len(ENC_PREFIX):].encode("ascii")).decode("utf-8")
    except InvalidToken:
        print("❌ Cannot decrypt a stored secret: the encryption key has changed or is missing.")
        return None
