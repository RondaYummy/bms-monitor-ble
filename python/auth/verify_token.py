import asyncio
import secrets
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

import python.db as db

auth_scheme = HTTPBearer()
optional_auth_scheme = HTTPBearer(auto_error=False)

global_executor: ThreadPoolExecutor | None = None

_one_day = 24 * 60 * 60
TOKEN_LIFETIME_SECONDS = _one_day * 30

ROLE_ADMIN = "admin"
ROLE_VIEWER = "viewer"
ROLES = (ROLE_ADMIN, ROLE_VIEWER)


@dataclass(frozen=True)
class AuthContext:
    token: str
    user_id: int
    username: str
    role: str

    @property
    def is_admin(self) -> bool:
        return self.role == ROLE_ADMIN


def initialize_auth_dependencies(executor_instance: ThreadPoolExecutor):
    global global_executor
    global_executor = executor_instance
    print("Executor for token verification initialized.")


async def session_for_token(token: str) -> AuthContext | None:
    if not token:
        return None
    loop = asyncio.get_running_loop()
    session = await loop.run_in_executor(global_executor, db.get_session, token, TOKEN_LIFETIME_SECONDS)
    if not session:
        return None
    return AuthContext(token=token, user_id=session["user_id"], username=session["username"], role=session["role"])


async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(auth_scheme)) -> AuthContext:
    """Any logged-in user (admin or viewer)."""
    if global_executor is None:
        raise RuntimeError("Executor was not initialized. Call initialize_auth_dependencies in main.py.")

    ctx = await session_for_token(credentials.credentials)
    if ctx is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return ctx


async def require_admin(ctx: AuthContext = Depends(verify_token)) -> AuthContext:
    """Every endpoint that changes something (devices, settings, users) requires the admin role."""
    if not ctx.is_admin:
        raise HTTPException(status_code=403, detail="Admin role required")
    return ctx


def is_public_read_enabled() -> bool:
    config = db.get_config() or {}
    return bool(config.get("public_read", 1))


async def optional_session(request: Request) -> AuthContext | None:
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return await session_for_token(token.strip())


# ---------- One-time tickets for EventSource (it cannot send an Authorization header) ----------
STREAM_TICKET_TTL_SECONDS = 60
_stream_tickets: dict[str, tuple[float, int]] = {}


def issue_stream_ticket(ctx: AuthContext) -> str:
    now = time.monotonic()
    for key, (expires, _) in list(_stream_tickets.items()):
        if expires < now:
            _stream_tickets.pop(key, None)
    ticket = secrets.token_urlsafe(32)
    _stream_tickets[ticket] = (now + STREAM_TICKET_TTL_SECONDS, ctx.user_id)
    return ticket


def consume_stream_ticket(ticket: str | None) -> bool:
    if not ticket:
        return False
    entry = _stream_tickets.pop(ticket, None)  # single use: never valid twice, never logged in URLs for long
    return bool(entry and entry[0] >= time.monotonic())
