"""Minimal RFC 6238 TOTP (SHA1, 6 digits, 30 s) — compatible with Google Authenticator, Aegis, 1Password..."""
import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote

PERIOD = 30
DIGITS = 6
ISSUER = "BMS Monitor"


def generate_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def _code_at(secret: str, step: int) -> str:
    key = base64.b32decode(secret.upper() + "=" * (-len(secret) % 8))
    digest = hmac.new(key, struct.pack(">Q", step), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(value % (10 ** DIGITS)).zfill(DIGITS)


def current_code(secret: str, at: float | None = None) -> str:
    return _code_at(secret, int((at or time.time()) // PERIOD))


def verify(secret: str, code: str, last_used_step: int = 0, window: int = 1, at: float | None = None):
    """Returns the matched time step (store it to prevent replay) or None.

    Accepts ±`window` steps for clock drift, never a step <= last_used_step.
    """
    code = (code or "").strip().replace(" ", "")
    if not secret or not code.isdigit() or len(code) != DIGITS:
        return None
    now_step = int((at or time.time()) // PERIOD)
    for step in range(now_step - window, now_step + window + 1):
        if step <= (last_used_step or 0):
            continue
        if hmac.compare_digest(_code_at(secret, step), code):
            return step
    return None


def provisioning_uri(secret: str, username: str) -> str:
    label = quote(f"{ISSUER}:{username}")
    return (f"otpauth://totp/{label}?secret={secret}&issuer={quote(ISSUER)}"
            f"&algorithm=SHA1&digits={DIGITS}&period={PERIOD}")
