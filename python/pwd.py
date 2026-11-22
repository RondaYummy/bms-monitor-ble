from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError

ph = PasswordHasher()

def hash_password(plain_password: str) -> str:
    return ph.hash(plain_password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not plain_password or not hashed_password:
        return False
    try:
        return ph.verify(hashed_password, plain_password)
    except (VerificationError, InvalidHashError):
        # Covers mismatch and corrupted/empty hashes (previously raised -> HTTP 500).
        return False
