import json
from pywebpush import webpush, WebPushException
import python.db as db
from fastapi import APIRouter, HTTPException

router = APIRouter()

VAPID_CLAIMS = {
    "sub": "mailto:halevych.dev@gmail.com"
}

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
    for sub in subscriptions:
        try:
            webpush(
                subscription_info=sub,
                data=payload,
                vapid_private_key=config["VAPID_PRIVATE_KEY"],
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
    for sub in subscriptions:
        try:
            webpush(
                subscription_info=sub,
                data=payload,
                vapid_private_key=config["VAPID_PRIVATE_KEY"],
                vapid_claims=VAPID_CLAIMS
            )
        except WebPushException as e:
            if "410 Gone" in str(e):
                db.remove_old_subscription(sub["endpoint"])
            else:
                print(f"Push Notification Error: {str(e)}")
