"""SSL certificate status shown in the UI.

The expiry date is read from the certificate itself (no more manual "renewed today" records):
  1. SSL_CERT_FILE  — copy of fullchain.pem made by the certbot deploy hook (scripts/ssl/deploy-hook.sh),
                      mounted read-only into the container. Only the public certificate, never the key.
  2. SSL_CHECK_HOST — "domain:port" that is contacted with a real TLS handshake: shows exactly what browsers
                      get (incl. "nginx was not reloaded" and untrusted chains).
  3. Legacy manual record in the ssl_certificates table (old installs), until one of the above is configured.
"""
import asyncio
import os
import socket
import ssl
import time
from datetime import datetime, timedelta, timezone

from cryptography import x509
from cryptography.x509.oid import ExtensionOID, NameOID
from fastapi import APIRouter, Depends

import python.db as db
from python.auth.verify_token import require_admin
from python.push_notifications import send_push_notification

router = APIRouter(tags=["SSL"])

SSL_CERT_FILE = os.getenv("SSL_CERT_FILE", "/ssl/fullchain.pem")
SSL_CHECK_HOST = os.getenv("SSL_CHECK_HOST", "").strip()
CACHE_SECONDS = 60 * 60
# certbot renews 30 days before expiry, so < 20 days left means automatic renewal is failing.
AUTO_WARNING_DAYS = 20
MANUAL_WARNING_DAYS = 30
DANGER_DAYS = 7

_cache: dict = {"at": 0.0, "value": None}


def _utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _cert_details(cert: x509.Certificate) -> dict:
    not_before = _utc(getattr(cert, "not_valid_before_utc", None) or cert.not_valid_before)
    not_after = _utc(getattr(cert, "not_valid_after_utc", None) or cert.not_valid_after)

    def _name(name: x509.Name) -> str:
        parts = name.get_attributes_for_oid(NameOID.COMMON_NAME) or name.get_attributes_for_oid(NameOID.ORGANIZATION_NAME)
        return parts[0].value if parts else name.rfc4514_string()

    try:
        domains = cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME).value.get_values_for_type(x509.DNSName)
    except x509.ExtensionNotFound:
        domains = []
    return {
        "created_at": not_before.isoformat(),
        "expires_at": not_after.isoformat(),
        "days_valid": (not_after - not_before).days,
        "days_left": (not_after - datetime.now(timezone.utc)).days,
        "subject": _name(cert.subject),
        "issuer": _name(cert.issuer),
        "domains": domains,
    }


def _from_file(path: str) -> dict | None:
    if not path or not os.path.isfile(path):
        return None
    with open(path, "rb") as f:
        cert = x509.load_pem_x509_certificate(f.read())  # first certificate = the leaf
    return {"source": "file", **_cert_details(cert)}


def _from_host(target: str) -> dict | None:
    if not target:
        return None
    host, _, port = target.partition(":")
    port = int(port or 443)
    pem = ssl.get_server_certificate((host, port), timeout=10)
    result = {"source": "host", "checked_host": f"{host}:{port}",
              **_cert_details(x509.load_pem_x509_certificate(pem.encode()))}
    # A verified handshake tells whether browsers will trust it (ERR_CERT_AUTHORITY_INVALID etc.).
    try:
        context = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=host):
                pass
        result["trusted"] = True
    except ssl.SSLCertVerificationError as e:
        result.update(trusted=False, trust_error=e.verify_message or str(e))
    return result


def _from_manual_record() -> dict | None:
    record = db.get_latest_ssl_certificate()
    if not record:
        return None
    created = _utc(datetime.fromisoformat(str(record["created_at"]).replace("Z", "+00:00")))
    days = record.get("days") or 90
    expires = created + timedelta(days=days)
    return {"source": "manual", "created_at": created.isoformat(), "expires_at": expires.isoformat(),
            "days_valid": days, "days_left": (expires - datetime.now(timezone.utc)).days}


def read_certificate_status() -> dict:
    errors = []
    details = None
    for loader, arg in ((_from_file, SSL_CERT_FILE), (_from_host, SSL_CHECK_HOST)):
        try:
            details = loader(arg)
        except Exception as e:  # unreadable file, DNS/TLS failure...
            errors.append(f"{loader.__name__[6:]}: {e}")
            details = None
        if details:
            break
    if details is None:
        details = _from_manual_record()

    if details is None:
        return {
            "status": "warning",
            "message": "Немає даних про SSL-сертифікат. Налаштуйте SSL_CERT_FILE або SSL_CHECK_HOST (див. SSL_CERTIFICATE.md).",
            "source": None,
            "errors": errors,
            "certificat": None,
        }

    days_left = details["days_left"]
    warning_days = MANUAL_WARNING_DAYS if details["source"] == "manual" else AUTO_WARNING_DAYS
    status = "ok"
    if days_left <= warning_days:
        status = "warning"
    if days_left <= DANGER_DAYS or details.get("trusted") is False:
        status = "danger"

    if details.get("trusted") is False:
        message = f"Браузери НЕ довіряють сертифікату: {details.get('trust_error')}"
    elif days_left < 0:
        message = "Сертифікат прострочений!"
    else:
        message = f"Сертифікат дійсний ще {days_left} днів."
        if details["source"] != "manual" and days_left <= warning_days:
            message += " Автоматичне поновлення, схоже, не спрацювало — перевірте certbot."

    return {"status": status, "message": message, "source": details["source"], "errors": errors,
            "certificat": details}


async def get_certificate_status(force: bool = False) -> dict:
    if force or _cache["value"] is None or time.monotonic() - _cache["at"] > CACHE_SECONDS:
        _cache["value"] = await asyncio.to_thread(read_certificate_status)
        _cache["at"] = time.monotonic()
    return _cache["value"]


async def ssl_watch_loop():
    """Pushes a notification (at most once a day) when the certificate needs attention."""
    last_notified = None
    while True:
        try:
            status = await get_certificate_status(force=True)
            today = datetime.now().date()
            if status["status"] in ("warning", "danger") and status.get("certificat") and last_notified != today:
                await send_push_notification("🔒 SSL-сертифікат", status["message"])
                last_notified = today
        except Exception as e:
            print(f"❌ SSL watch error: {e}")
        await asyncio.sleep(12 * 60 * 60)


@router.get("/ssl")
async def get_ssl():
    return await get_certificate_status()


@router.post("/ssl/refresh", dependencies=[Depends(require_admin)])
async def refresh_ssl():
    """Re-reads the certificate. For legacy manual setups it also records "renewed now"."""
    current = await get_certificate_status(force=True)
    if current.get("source") in (None, "manual"):
        if not db.refresh_ssl_certificate():
            return {"status": "error", "message": "❌ Не вдалося оновити SSL сертифікат", "certificat": None}
        current = await get_certificate_status(force=True)
    return current
