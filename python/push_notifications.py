import json
from pywebpush import webpush, WebPushException
import python.db as db
from fastapi import APIRouter, HTTPException
from cryptography.hazmat.primitives import serialization
import base64

router = APIRouter()

VAPID_CLAIMS = {
    "sub": "mailto:halevych.dev@gmail.com"
}

def convert_pem_to_der(private_pem: str) -> bytes:
    """Конвертує приватний ключ у форматі PEM у DER"""
    try:
        if isinstance(private_pem, bytes):
            pem_data = private_pem
        else:
            pem_data = private_pem.encode("utf-8")

        private_key = serialization.load_pem_private_key(
            pem_data,
            password=None
        )
        return private_key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
    except Exception as e:
        raise ValueError(f"Помилка конвертації PEM у DER: {e}")

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
    message = f"🚨 {device_name}: {alert['message']} (код: {alert['id']})"
    payload = json.dumps({"title": "🔋 Увага!", "body": message})
    subscriptions = db.get_all_subscriptions()

    vapid_private_key_pem = config["VAPID_PRIVATE_KEY"]
    private_key_pem = vapid_private_key_pem.replace("-----BEGIN PRIVATE KEY-----", "").replace("-----END PRIVATE KEY-----", "").strip()
    private_key_bytes = base64.b64decode(private_key_pem)
    for sub in subscriptions:
        try:
            webpush(
                subscription_info=sub,
                data=payload,
                vapid_private_key=private_key_bytes,
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
    private_key_pem = vapid_private_key_pem.replace("-----BEGIN PRIVATE KEY-----", "").replace("-----END PRIVATE KEY-----", "").strip()
    private_key_bytes = base64.b64decode(private_key_pem)

    for sub in subscriptions:
        try:
            webpush(
                subscription_info=sub,
                data=payload,
                vapid_private_key=private_key_bytes,
                vapid_claims=VAPID_CLAIMS
            )
        except WebPushException as e:
            if "410 Gone" in str(e):
                db.remove_old_subscription(sub["endpoint"])
            else:
                print(f"Push Notification Error: {str(e)}")
