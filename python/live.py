"""Server-Sent Events: one connection per client instead of polling 4 endpoints every 2 seconds.

A single snapshot loop (only while somebody listens) builds each topic once per second and pushes it
to all subscribers only when it changed. Producers can also publish one-off events (e.g. alerts).
"""
import asyncio
import json
import time

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

import python.db as db
from python.auth.verify_token import consume_stream_ticket, is_public_read_enabled, optional_session
from python.data_store import data_store

router = APIRouter(tags=["Live"])

SNAPSHOT_INTERVAL_SECONDS = 1.0
HEARTBEAT_SECONDS = 15
MAX_SUBSCRIBERS = 50
QUEUE_SIZE = 100


def _encode(event: str, payload: str) -> str:
    return f"event: {event}\ndata: {payload}\n\n"


class LiveHub:
    def __init__(self):
        self.subscribers: set[asyncio.Queue] = set()
        self.last: dict[str, str] = {}
        self.closed = False
        self._task: asyncio.Task | None = None

    def subscribe(self) -> asyncio.Queue:
        if len(self.subscribers) >= MAX_SUBSCRIBERS:
            raise HTTPException(status_code=503, detail="Too many live connections")
        queue: asyncio.Queue = asyncio.Queue(maxsize=QUEUE_SIZE)
        for event, payload in self.last.items():  # newcomers get the current state immediately
            queue.put_nowait(_encode(event, payload))
        self.subscribers.add(queue)
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._snapshot_loop())
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        self.subscribers.discard(queue)

    def _broadcast(self, message: str):
        for queue in list(self.subscribers):
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                # A client that can't keep up is dropped; its EventSource reconnects and resyncs.
                self.subscribers.discard(queue)
                while not queue.empty():
                    queue.get_nowait()
                queue.put_nowait(None)  # tells the stream generator to close

    def publish(self, event: str, data) -> None:
        """One-off event (not stored as state)."""
        if self.subscribers:
            self._broadcast(_encode(event, json.dumps(data, default=str)))

    def update_topic(self, event: str, data) -> None:
        payload = json.dumps(data, default=str, sort_keys=True)
        if self.last.get(event) != payload:
            self.last[event] = payload
            self._broadcast(_encode(event, payload))

    async def _snapshot_loop(self):
        while self.subscribers and not self.closed:
            try:
                for event, data in (await build_snapshot()).items():
                    self.update_topic(event, data)
            except Exception as e:
                print(f"⚠️ Live snapshot error: {e}")
            await asyncio.sleep(SNAPSHOT_INTERVAL_SECONDS)
        self.last.clear()  # nobody listens: next subscriber triggers a fresh snapshot


hub = LiveHub()


async def build_snapshot() -> dict:
    # Same payloads as the REST endpoints, so the frontend stores can consume them unchanged.
    from python.tapo.manage_device_power import power_system_status
    from python.tapo.tapo_routes import get_top_priority_devices

    cell_info, deye, tapo_top, power = await asyncio.gather(
        data_store.get_cell_info(),
        asyncio.to_thread(db.get_all_deye_devices),
        asyncio.to_thread(get_top_priority_devices),
        asyncio.to_thread(power_system_status),
    )
    # duration_s changes every tick; the UI derives it from off_since, so drop it to avoid useless pushes.
    for device in power.get("devices", []):
        device.pop("duration_s", None)
    return {"cell_info": cell_info, "deye": deye, "tapo_top": tapo_top.get("top_devices", []), "power": power}


@router.get("/stream")
async def stream(request: Request, ticket: str | None = None):
    if not is_public_read_enabled():
        session = await optional_session(request)
        if session is None and not consume_stream_ticket(ticket):
            raise HTTPException(status_code=401, detail="Login required")

    queue = hub.subscribe()

    async def events():
        try:
            yield "retry: 5000\n\n"
            last_beat = time.monotonic()
            while not hub.closed:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    message = ""
                if message is None:  # dropped as too slow
                    break
                if message:
                    yield message
                if time.monotonic() - last_beat >= HEARTBEAT_SECONDS:
                    last_beat = time.monotonic()
                    yield ": ping\n\n"  # keeps proxies from closing the idle connection
                if await request.is_disconnected():
                    break
        finally:
            hub.unsubscribe(queue)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )
