import asyncio
import re
import secrets
import sqlite3
import time
from collections import defaultdict, deque
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

import python.db as db
from python.auth import totp
from python.auth.verify_token import (
    ROLE_ADMIN,
    AuthContext,
    issue_stream_ticket,
    require_admin,
    verify_token,
)
from python.pwd import hash_password, verify_password

router = APIRouter(tags=["Auth & users"])

MIN_PASSWORD_LENGTH = 8
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")
# Verifying against a dummy hash for unknown users keeps the response time identical (no user enumeration).
_DUMMY_HASH = hash_password(secrets.token_urlsafe(16))

# ---------- Brute-force protection ----------
LOGIN_WINDOW_SECONDS = 15 * 60
LOGIN_MAX_FAILURES_PER_CLIENT = 5
LOGIN_MAX_FAILURES_GLOBAL = 30
_login_failures: dict = defaultdict(deque)


def _client_key(request: Request) -> str:
    # nginx sets X-Real-IP; the backend port itself is bound to localhost only (see docker-compose.yml).
    return request.headers.get("x-real-ip") or (request.client.host if request.client else "unknown")


def _recent_failures(key: str, now: float) -> deque:
    attempts = _login_failures[key]
    while attempts and now - attempts[0] > LOGIN_WINDOW_SECONDS:
        attempts.popleft()
    return attempts


def _check_login_allowed(client: str):
    now = time.monotonic()
    if (len(_recent_failures(client, now)) >= LOGIN_MAX_FAILURES_PER_CLIENT
            or len(_recent_failures("*", now)) >= LOGIN_MAX_FAILURES_GLOBAL):
        raise HTTPException(status_code=429, detail="Too many failed login attempts. Try again later.")


def _register_login_failure(client: str):
    now = time.monotonic()
    _recent_failures(client, now).append(now)
    _recent_failures("*", now).append(now)


async def _run(func, *args):
    return await asyncio.get_running_loop().run_in_executor(None, func, *args)


def _validate_username(value: str) -> str:
    value = value.strip()
    if not USERNAME_RE.match(value):
        raise ValueError("Username: 3-32 chars, letters, digits, '_', '.', '-'")
    return value


# ---------- Models ----------
class LoginRequest(BaseModel):
    username: str = Field("admin", max_length=64)
    password: str = Field(..., max_length=256)
    otp: Optional[str] = Field(None, max_length=10)


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., max_length=256)
    new_password: str = Field(..., min_length=MIN_PASSWORD_LENGTH, max_length=256)


class CreateUserRequest(BaseModel):
    username: str
    password: str = Field(..., min_length=MIN_PASSWORD_LENGTH, max_length=256)
    role: Literal["admin", "viewer"] = "viewer"

    @field_validator("username")
    @classmethod
    def check_username(cls, value: str) -> str:
        return _validate_username(value)


class UpdateUserRequest(BaseModel):
    role: Optional[Literal["admin", "viewer"]] = None
    password: Optional[str] = Field(None, min_length=MIN_PASSWORD_LENGTH, max_length=256)
    disable_2fa: Optional[bool] = None


class OtpRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=10)


class Disable2faRequest(BaseModel):
    password: str = Field(..., max_length=256)
    code: str = Field(..., min_length=6, max_length=10)


def _public_user(user: dict) -> dict:
    return {
        "id": user["id"],
        "username": user["username"],
        "role": user["role"],
        "totp_enabled": bool(user.get("totp_enabled")),
        "created_at": user.get("created_at"),
    }


# ---------- Login / logout ----------
@router.post("/login")
async def login(body: LoginRequest, request: Request):
    client = _client_key(request)
    _check_login_allowed(client)

    user = await _run(db.get_user_by_username, body.username or "admin")
    password_ok = await _run(verify_password, body.password, user["password_hash"] if user else _DUMMY_HASH)
    if not user or not password_ok:
        _register_login_failure(client)
        await asyncio.sleep(1)  # slow down online guessing
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if user["totp_enabled"]:
        if not body.otp:
            # Second step: the UI asks for the 6-digit code and repeats the request.
            return {"otp_required": True}
        step = totp.verify(user["totp_secret"], body.otp, user.get("totp_last_step") or 0)
        if step is None:
            _register_login_failure(client)
            await asyncio.sleep(1)
            raise HTTPException(status_code=401, detail="Invalid 2FA code")
        await _run(lambda: db.update_user(user["id"], totp_last_step=step))  # prevents code replay

    _login_failures.pop(client, None)
    token = secrets.token_urlsafe(32)
    await _run(db.add_token_to_db, token, user["id"])
    return {"access_token": token, "username": user["username"], "role": user["role"]}


@router.post("/logout")
async def logout(ctx: AuthContext = Depends(verify_token)):
    await _run(db.remove_token_from_db, ctx.token)
    return {"logout": True}


@router.get("/auth/me")
async def me(ctx: AuthContext = Depends(verify_token)):
    user = await _run(db.get_user_by_id, ctx.user_id)
    return _public_user(user)


@router.post("/stream/ticket")
async def stream_ticket(ctx: AuthContext = Depends(verify_token)):
    """Short-lived single-use ticket for /api/stream when public read access is disabled."""
    return {"ticket": issue_stream_ticket(ctx)}


@router.post("/change-password")
async def change_password(body: ChangePasswordRequest, ctx: AuthContext = Depends(verify_token)):
    user = await _run(db.get_user_by_id, ctx.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # 400, not 401/403: the frontend treats those as "session expired" and logs the user out.
    if not await _run(verify_password, body.old_password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Old password is incorrect.")

    new_hash = await _run(hash_password, body.new_password)
    await _run(lambda: db.update_user(ctx.user_id, password_hash=new_hash))
    # Log out every other session of this user.
    await _run(lambda: db.remove_all_tokens_except(ctx.token, ctx.user_id))
    return {"message": "Password changed successfully."}


# ---------- 2FA (TOTP) ----------
@router.post("/auth/2fa/setup")
async def setup_2fa(ctx: AuthContext = Depends(verify_token)):
    user = await _run(db.get_user_by_id, ctx.user_id)
    if user["totp_enabled"]:
        raise HTTPException(status_code=400, detail="2FA is already enabled")
    secret = totp.generate_secret()
    # Stored (encrypted) as pending; it only becomes active after a correct code in /enable.
    await _run(lambda: db.update_user(ctx.user_id, totp_secret=secret, totp_enabled=0, totp_last_step=0))
    return {"secret": secret, "otpauth_uri": totp.provisioning_uri(secret, user["username"])}


@router.post("/auth/2fa/enable")
async def enable_2fa(body: OtpRequest, ctx: AuthContext = Depends(verify_token)):
    user = await _run(db.get_user_by_id, ctx.user_id)
    if user["totp_enabled"]:
        raise HTTPException(status_code=400, detail="2FA is already enabled")
    if not user.get("totp_secret"):
        raise HTTPException(status_code=400, detail="Run 2FA setup first")
    step = totp.verify(user["totp_secret"], body.code, 0)
    if step is None:
        raise HTTPException(status_code=400, detail="Invalid 2FA code")
    await _run(lambda: db.update_user(ctx.user_id, totp_enabled=1, totp_last_step=step))
    # Other sessions were created without the second factor.
    await _run(lambda: db.remove_all_tokens_except(ctx.token, ctx.user_id))
    return {"totp_enabled": True}


@router.post("/auth/2fa/disable")
async def disable_2fa(body: Disable2faRequest, ctx: AuthContext = Depends(verify_token)):
    user = await _run(db.get_user_by_id, ctx.user_id)
    if not user["totp_enabled"]:
        return {"totp_enabled": False}
    if not await _run(verify_password, body.password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Password is incorrect.")
    if totp.verify(user["totp_secret"], body.code, user.get("totp_last_step") or 0) is None:
        raise HTTPException(status_code=400, detail="Invalid 2FA code")
    await _run(lambda: db.update_user(ctx.user_id, totp_enabled=0, totp_secret=None, totp_last_step=0))
    return {"totp_enabled": False}


# ---------- User management (admin) ----------
@router.get("/users")
async def list_users(ctx: AuthContext = Depends(require_admin)):
    return [_public_user(u) for u in await _run(db.list_users)]


@router.post("/users")
async def create_user(body: CreateUserRequest, ctx: AuthContext = Depends(require_admin)):
    password_hash = await _run(hash_password, body.password)
    try:
        user = await _run(db.create_user, body.username, password_hash, body.role)
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="User already exists")
    print(f"👤 User '{user['username']}' ({user['role']}) created by {ctx.username}")
    return _public_user(user)


@router.patch("/users/{user_id}")
async def update_user(user_id: int, body: UpdateUserRequest, ctx: AuthContext = Depends(require_admin)):
    user = await _run(db.get_user_by_id, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    fields = {}
    if body.role and body.role != user["role"]:
        if user["role"] == ROLE_ADMIN and await _run(db.count_admins) <= 1:
            raise HTTPException(status_code=400, detail="Cannot demote the last admin")
        fields["role"] = body.role
    if body.password:
        fields["password_hash"] = await _run(hash_password, body.password)
    if body.disable_2fa:
        fields.update(totp_enabled=0, totp_secret=None, totp_last_step=0)

    updated = await _run(lambda: db.update_user(user_id, **fields))
    if fields:
        # Role/password changes must not leave old sessions with old permissions.
        keep = ctx.token if user_id == ctx.user_id else None
        await _run(lambda: db.remove_all_tokens_except(keep, user_id))
    return _public_user(updated)


@router.delete("/users/{user_id}")
async def delete_user(user_id: int, ctx: AuthContext = Depends(require_admin)):
    if user_id == ctx.user_id:
        raise HTTPException(status_code=400, detail="You cannot delete yourself")
    user = await _run(db.get_user_by_id, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user["role"] == ROLE_ADMIN and await _run(db.count_admins) <= 1:
        raise HTTPException(status_code=400, detail="Cannot delete the last admin")
    await _run(db.delete_user, user_id)
    return {"deleted": True}
