"""BMS Monitor backend: FastAPI app wiring (routers, middleware, background loops).

Domain logic lives in `python/`:
  ble/        JK-BMS over Bluetooth (protocol, connection manager, frame parsing, API)
  api/        configuration, alerts history, chart data, SSL status
  auth/       users, roles, 2FA, sessions
  tapo/ deye/ smart plugs and the inverter
"""
import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import python.db as db
from python.alert_thresholds import router as alert_thresholds_router
from python.analytics import router as analytics_router
from python.api.energy_routes import router as energy_router
from python.api.ssl_routes import router as ssl_router, ssl_watch_loop
from python.api.system_routes import router as system_router
from python.auth.auth_routes import router as auth_router
from python.auth.verify_token import initialize_auth_dependencies, is_public_read_enabled, session_for_token
from python.auto_power import auto_power_manager_loop
from python.ble.manager import ble_main
from python.ble.routes import router as ble_router
from python.cell_history import router as cell_history_router
from python.solar_forecast import router as solar_router, solar_forecast_loop
from python.deye.deye_routes import router as deye_router
from python.deye.read_deye import run_deye_loop
from python.energy import accumulator as energy_accumulator
from python.live import hub as live_hub, router as live_router
from python.maintenance import maintenance_loop, router as maintenance_router
from python.push_notifications import router as alerts_router
from python.push_notifications import send_push_startup
from python.pwd import verify_password
from python.tapo.find_tapo import router as tapo_find_router
from python.tapo.manage_device_power import manage_tapo_power
from python.tapo.manage_device_power import router as power_manage_router
from python.tapo.schedule import router as tapo_schedule_router, run_tapo_schedule_loop
from python.tapo.tapo_routes import router as tapo_router
from python.tapo.tapo_service import check_all_tapo_devices
from python.tasks import background_tasks, run_forever, spawn

LEGACY_DEFAULT_PASSWORD = "123456"

executor = ThreadPoolExecutor()
initialize_auth_dependencies(executor)


async def periodic_tapo_status():
    while True:
        try:
            await check_all_tapo_devices()
        except Exception as e:
            print(f"❌ Tapo status checker error: {e}")
        await asyncio.sleep(5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, db.create_table)
    await loop.run_in_executor(None, db.set_all_devices_disconnected)
    await loop.run_in_executor(None, db.cleanup_ssl_certificates)

    loops = [
        spawn(run_forever("ble_main", ble_main)),
        spawn(run_forever("process_devices", db.process_devices)),
        spawn(run_forever("deye_loop", run_deye_loop)),
        spawn(run_forever("manage_tapo_power", manage_tapo_power)),
        spawn(run_forever("auto_power_manager", auto_power_manager_loop)),
        spawn(run_forever("tapo_status", periodic_tapo_status)),
        spawn(run_forever("tapo_schedule", run_tapo_schedule_loop)),
        spawn(run_forever("maintenance", maintenance_loop)),
        spawn(run_forever("ssl_watch", ssl_watch_loop)),
        spawn(run_forever("solar_forecast", solar_forecast_loop)),
    ]

    admin = await loop.run_in_executor(None, db.get_user_by_username, "admin")
    if admin and await loop.run_in_executor(executor, verify_password, LEGACY_DEFAULT_PASSWORD, admin["password_hash"]):
        print("⚠️⚠️⚠️ SECURITY WARNING: the admin password is still the default '123456'. Change it in Settings! ⚠️⚠️⚠️")
    config = db.get_config()
    if config:
        spawn(send_push_startup(config))

    yield

    # Shutdown: let SSE streams finish, then stop the background loops cleanly.
    live_hub.closed = True
    try:
        await asyncio.to_thread(energy_accumulator.flush)  # keep the last minute of kWh accounting
    except Exception as e:
        print(f"⚠️ Energy flush on shutdown failed: {e}")
    for task in loops + list(background_tasks):
        task.cancel()
    await asyncio.gather(*loops, return_exceptions=True)


app = FastAPI(lifespan=lifespan)

for router in (
    auth_router,
    tapo_schedule_router,  # before tapo_router: /tapo/rules must not hit /tapo/{...}
    tapo_router,
    alerts_router,
    tapo_find_router,
    deye_router,
    power_manage_router,
    alert_thresholds_router,
    analytics_router,
    maintenance_router,
    live_router,
    ble_router,
    system_router,
    ssl_router,
    energy_router,
    cell_history_router,
    solar_router,
):
    app.include_router(router, prefix="/api")

# Endpoints that must work without a session even when public read access is disabled.
ALWAYS_PUBLIC_PATHS = {"/api/login", "/api/configs", "/api/stream"}


@app.middleware("http")
async def read_access_guard(request: Request, call_next):
    """With `public_read` disabled every data endpoint requires a session (viewer or admin).

    Mutating endpoints are protected individually with `require_admin`.
    """
    path = request.url.path
    guarded = (request.method == "GET" and path.startswith("/api/") and path not in ALWAYS_PUBLIC_PATHS) \
        or path == "/api/save-subscription"
    if guarded and not is_public_read_enabled():
        header = request.headers.get("authorization", "")
        scheme, _, token = header.partition(" ")
        if scheme.lower() != "bearer" or not await session_for_token(token.strip()):
            return JSONResponse(status_code=401, content={"detail": "Login required"})
    return await call_next(request)


# The frontend is served by nginx which proxies /api on the same origin, so CORS is only needed
# for development setups (e.g. `quasar dev` on :8080). Configure with CORS_ORIGINS="http://a,http://b".
_cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
if _cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )


def start_services():
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    start_services()
