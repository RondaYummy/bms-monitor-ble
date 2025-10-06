import base64
import json
from datetime import datetime, timedelta, timezone

from cryptography.hazmat.primitives import serialization
from fastapi import APIRouter, HTTPException
from pywebpush import WebPushException, webpush

import python.db as db

SEND_ALLOWED_AFTER: datetime = datetime.now(timezone.utc) + timedelta(minutes=2)

router = APIRouter()

VAPID_CLAIMS = {
    "sub": "mailto:halevych.dev@gmail.com"
}


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

@router.post("/save-subscription")
def save_subscription(subscription: dict):
    print("🔍 Incoming subscription:", subscription)
    if "endpoint" not in subscription or "keys" not in subscription:
        raise HTTPException(status_code=400, detail="Invalid subscription format")

    existing_subscription = db.get_subscription_by_endpoint(subscription["endpoint"])
    if existing_subscription:
        # print("⚠️ Subscription already exists.")
        return {"message": "Subscription already exists"}

    db.add_subscription(subscription)
    # print("✅ Subscription saved successfully.")
    return {"message": "Subscription saved"}

async def send_push_alerts(device_name: str, alert, config):
    if datetime.now(timezone.utc) < SEND_ALLOWED_AFTER:
        print(f"⏰ Затримка: Push-повідомлення про тривогу '{device_name}' пригнічено (сервер нещодавно запустився).")
        return

    message = f"🚨 {device_name}: {alert['message']} (код: {alert['id']})"
    payload = json.dumps({"title": "🔋 Увага!", "body": message})
    subscriptions = db.get_all_subscriptions()

    vapid_private_key_pem = config["VAPID_PRIVATE_KEY"]
    private_key_der = convert_pem_to_der(vapid_private_key_pem)
    private_key_base64 = convert_der_to_base64(private_key_der)

    for sub in subscriptions:
        try:
            webpush(
                subscription_info=sub,
                data=payload,
                vapid_private_key=private_key_base64,
                vapid_claims=VAPID_CLAIMS
            )
        except WebPushException as e:
            if "410 Gone" in str(e):
                db.remove_old_subscription(sub["endpoint"])
            else:
                print(f"Push Notification Error: {str(e)}")

async def send_push_startup(config):
    payload = json.dumps({"title": "📣 Reboot!", "body": "The server has been successfully launched and is starting to work..."})
    subscriptions = db.get_all_subscriptions()
    vapid_private_key_pem = config["VAPID_PRIVATE_KEY"]
    private_key_der = convert_pem_to_der(vapid_private_key_pem)
    private_key_base64 = convert_der_to_base64(private_key_der)

    for sub in subscriptions:
        try:
            webpush(
                subscription_info=sub,
                data=payload,
                vapid_private_key=private_key_base64,
                vapid_claims=VAPID_CLAIMS
            )
        except WebPushException as e:
            if "410 Gone" in str(e):
                db.remove_old_subscription(sub["endpoint"])
            else:
                print(f"Push Notification Error: {str(e)}")
