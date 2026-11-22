import asyncio
import base64
import json
import os
from functools import lru_cache
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from cryptography.hazmat.primitives import serialization
from fastapi import APIRouter, Body, HTTPException
from pywebpush import WebPushException, webpush

import python.db as db

router = APIRouter()

VAPID_CLAIMS = {
    "sub": os.getenv("VAPID_SUBJECT", "mailto:halevych.dev@gmail.com")
}

# The server POSTs to every stored endpoint, so endpoints must belong to a real push service.
# Otherwise anyone could register e.g. http://192.168.31.1/... and turn the server into an SSRF proxy.
ALLOWED_PUSH_HOST_SUFFIXES = (
    "fcm.googleapis.com",
    "android.googleapis.com",
    "push.services.mozilla.com",
    "notify.windows.com",
    "push.apple.com",
)
MAX_SUBSCRIPTIONS = 50
PUSH_TIMEOUT_SECONDS = 10


def convert_der_to_base64(der_key: bytes) -> str:
    return base64.urlsafe_b64encode(der_key).decode("utf-8").rstrip("=")


def convert_pem_to_der(private_pem: str) -> bytes:
    private_key = serialization.load_pem_private_key(
        private_pem.encode("utf-8"),
        password=None
    )
    return private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )


@lru_cache(maxsize=4)
def _vapid_private_key_base64(private_pem: str) -> str:
    return convert_der_to_base64(convert_pem_to_der(private_pem))


def send_to_subscription(sub: dict, payload: str, private_key_base64: str,
                         ttl: int = 0, urgency: Optional[str] = None) -> bool:
    """Sends one push (blocking). Removes subscriptions the push service reports as gone. Returns success."""
    try:
        webpush(
            subscription_info={"endpoint": sub["endpoint"], "keys": sub["keys"]},
            data=payload,
            vapid_private_key=private_key_base64,
            vapid_claims=dict(VAPID_CLAIMS),
            timeout=PUSH_TIMEOUT_SECONDS,
            ttl=ttl,
            headers={"Urgency": urgency} if urgency else None,
        )
        return True
    except WebPushException as e:
        status = getattr(getattr(e, "response", None), "status_code", None)
        if status in (404, 410) or "410 Gone" in str(e):
            db.remove_old_subscription(sub["endpoint"])
        else:
            print(f"Push Notification Error: {e}")
    except Exception as e:
        print(f"Push Notification Error: {e}")
    return False


def vapid_key_from_config(config: Optional[Dict[str, Any]] = None) -> Optional[str]:
    config = config or db.get_config() or {}
    try:
        return _vapid_private_key_base64(config["VAPID_PRIVATE_KEY"])
    except Exception as e:
        print(f"❌ VAPID Configuration Error: {e}")
        return None


def _send_blocking(payload: str, private_key_base64: str):
    """Runs in a worker thread: pywebpush does synchronous HTTP requests."""
    for sub in db.get_all_subscriptions():
        send_to_subscription(sub, payload, private_key_base64)


async def _send_to_all_subscriptions(payload: str, config: Optional[Dict[str, Any]] = None):
    config = config or db.get_config()
    try:
        private_key_base64 = _vapid_private_key_base64(config["VAPID_PRIVATE_KEY"])
    except Exception as e:
        print(f"❌ VAPID Configuration Error: {e}")
        return
    # Never block the event loop (BLE notifications and the API share it).
    await asyncio.to_thread(_send_blocking, payload, private_key_base64)


async def send_push_notification(title: str, body: str):
    payload = json.dumps({"title": title, "body": body})
    await _send_to_all_subscriptions(payload)


async def send_push_alerts(device_name: str, alert, config):
    message = f"🚨 {device_name}: {alert['message']} (код: {alert['id']})"
    payload = json.dumps({"title": "🔋 Увага!", "body": message})
    await _send_to_all_subscriptions(payload, config)


async def send_push_startup(config):
    payload = json.dumps({"title": "📣 Reboot!", "body": "The server has been successfully launched and is starting to work..."})
    await _send_to_all_subscriptions(payload, config)


def _is_allowed_endpoint(endpoint: str) -> bool:
    try:
        parsed = urlparse(endpoint)
    except ValueError:
        return False
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not host:
        return False
    return any(host == suffix or host.endswith("." + suffix) for suffix in ALLOWED_PUSH_HOST_SUFFIXES)


@router.post("/save-subscription")
def save_subscription(body: dict = Body(...)):
    # The frontend sends {"subscription": PushSubscription}; accept the bare object too.
    subscription = body.get("subscription", body) if isinstance(body, dict) else None
    if not isinstance(subscription, dict):
        raise HTTPException(status_code=400, detail="Invalid subscription format")

    endpoint = subscription.get("endpoint")
    keys = subscription.get("keys") or {}
    if (
        not isinstance(endpoint, str)
        or len(endpoint) > 1024
        or not isinstance(keys, dict)
        or not isinstance(keys.get("p256dh"), str)
        or not isinstance(keys.get("auth"), str)
        or len(keys["p256dh"]) > 256
        or len(keys["auth"]) > 64
    ):
        raise HTTPException(status_code=400, detail="Invalid subscription format")

    if not _is_allowed_endpoint(endpoint):
        raise HTTPException(status_code=400, detail="Unsupported push service endpoint")

    existing_subscription = db.get_subscription_by_endpoint(endpoint)
    if existing_subscription:
        return {"message": "Subscription already exists"}

    if db.count_subscriptions() >= MAX_SUBSCRIPTIONS:
        raise HTTPException(status_code=429, detail="Too many subscriptions")

    db.add_subscription({"endpoint": endpoint, "keys": {"p256dh": keys["p256dh"], "auth": keys["auth"]}})
    return {"message": "Subscription saved"}
