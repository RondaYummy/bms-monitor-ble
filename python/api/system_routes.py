"""Configuration, alerts history and aggregated chart data."""
from datetime import datetime, timedelta
from typing import Optional

import yaml
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

import python.db as db
from python.alert_thresholds import render_message
from python.auth.verify_token import AuthContext, require_admin

router = APIRouter(tags=["System"])

with open('configs/error_codes.yaml', 'r', encoding='utf-8') as file:
    error_codes = yaml.safe_load(file)

PRIVATE_CONFIG_KEYS = ("id", "password", "VAPID_PRIVATE_KEY", "alert_thresholds")

def _public_config(config: dict) -> dict:
    config = {k: v for k, v in config.items() if k not in PRIVATE_CONFIG_KEYS}
    config["public_read"] = bool(config.get("public_read", 1))
    return config

class ConfigUpdateRequest(BaseModel):
    n_hours: Optional[int] = Field(None, ge=1, le=24 * 30)
    auto_power_management_enabled: Optional[int] = Field(None, ge=0, le=1)
    public_read: Optional[bool] = None

@router.get("/configs")
async def get_configs():
    config = db.get_config()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found.")
    
    return _public_config(config)

class ToggleAutoPowerRequest(BaseModel):
    enabled: bool

@router.patch(
    "/auto-power",
    summary="Toggle auto power management",
    dependencies=[Depends(require_admin)]
)
def toggle_auto_power(body: ToggleAutoPowerRequest):
    success = db.toggle_auto_power_management(body.enabled)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update config")

    return {
        "status": "ok",
        "enabled": body.enabled
    }

@router.post("/configs", dependencies=[Depends(require_admin)])
async def update_configs(request: ConfigUpdateRequest):
    updated_config = db.update_config_fields(
        n_hours=request.n_hours,
        auto_power_management_enabled=request.auto_power_management_enabled,
        public_read=None if request.public_read is None else int(request.public_read),
    )
    if not updated_config:
        raise HTTPException(status_code=500, detail="Error updating config.")
    # Never return the password hash / VAPID private key (the old code did).
    return {"message": "Configuration updated successfully", "config": _public_config(updated_config)}

class DeleteAlertRequest(BaseModel):
    id: int
@router.post("/error-alerts")
async def delete_error_alert(request: DeleteAlertRequest, ctx: AuthContext = Depends(require_admin)):
    try:
        db.delete_alert_by_id(alert_id=request.id)
        return {"message": f"Alert with ID {request.id} has been deleted successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting alert: {str(e)}")

@router.delete("/error-alerts/all", dependencies=[Depends(require_admin)])
async def delete_all_error_alerts():
    try:
        db.delete_all_alerts()
        return {"message": "All alerts have been deleted successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting all alerts: {str(e)}")
        
@router.get("/error-alerts")
async def get_error_alerts():
    data = db.fetch_all_notifications()  # already sorted newest → oldest in SQL
    if not data:
        return JSONResponse(content={"message": "No error alerts available yet."}, status_code=404)

    enriched_data = []
    for alert_id, device_address, error_code, device_name, timestamp, stored_message in data:
        try:
            code_info = error_codes.get(int(error_code), {})
        except (TypeError, ValueError):
            code_info = {}
        # New alerts store the message rendered with the thresholds valid at that moment.
        message = stored_message or render_message(code_info.get('message', 'Message not found'))
        enriched_data.append({
            "id": alert_id,
            "device_address": device_address,
            "error_code": error_code,
            "device_name": device_name,
            "timestamp": str(timestamp),
            "message": message,
            "level": code_info.get('level', 'Level not found'),
        })
    return enriched_data

@router.get("/aggregated-data")
async def get_aggregated_data(
    days: int = Query(1, ge=0, le=366, description="Number of days to fetch data for"),
    from_date: Optional[str] = Query(None, alias="from", description="Start date in format YYYY/MM/DD"),
    to_date: Optional[str] = Query(None, alias="to", description="End date in format YYYY/MM/DD")
):
    if from_date and to_date:
        try:
            from_dt = datetime.strptime(from_date, "%Y/%m/%d") # YYYY/MM/DD
            to_dt = datetime.strptime(to_date, "%Y/%m/%d") + timedelta(hours=23, minutes=59, seconds=59)
        except ValueError as e:
            return JSONResponse(content={"message": f"Invalid date format: {e}"}, status_code=400)
        if to_dt < from_dt or (to_dt - from_dt).days > 366:
            return JSONResponse(content={"message": "Invalid range (max 366 days)."}, status_code=400)

        aggregated_data = db.fetch_all_data_range(from_dt, to_dt)
    else:
        aggregated_data = db.fetch_all_data(days=days)
    
    if not aggregated_data:
        return JSONResponse(content={"message": "No aggregated data available yet."}, status_code=404)
    return aggregated_data
