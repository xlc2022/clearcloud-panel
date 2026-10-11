"""Admin password, login sessions, and the request guard."""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, Request

from .store import Store

ADMIN = "admin"
SESSION_COOKIE = "ccf_session"
SESSION_TTL = timedelta(days=30)
MIN_PASSWORD_LENGTH = 10

_SCRYPT = {"n": 2**15, "r": 8, "p": 1, "maxmem": 64 * 1024 * 1024}


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, **_SCRYPT)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, salt_hex, digest_hex = stored.split("$")
    except ValueError:
        return False
    if scheme != "scrypt":
        return False
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), **_SCRYPT)
    return hmac.compare_digest(digest, bytes.fromhex(digest_hex))


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(store: Store, username: str) -> str:
    token = secrets.token_urlsafe(32)
    now = datetime.now(UTC)
    store.db.execute(
        "INSERT INTO sessions (token_hash, username, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (_token_hash(token), username, now.isoformat(), (now + SESSION_TTL).isoformat()),
    )
    return token


def delete_session(store: Store, token: str) -> None:
    store.db.execute("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),))


def session_user(store: Store, token: str | None) -> str | None:
    if not token:
        return None
    row = store.db.execute(
        "SELECT username, expires_at FROM sessions WHERE token_hash = ?", (_token_hash(token),)
    ).fetchone()
    if row is None:
        return None
    if datetime.fromisoformat(row["expires_at"]) < datetime.now(UTC):
        delete_session(store, token)
        return None
    return row["username"]


def current_user(request: Request) -> str | None:
    store: Store = request.app.state.store
    return session_user(store, request.cookies.get(SESSION_COOKIE))


def require_user(request: Request) -> str:
    user = current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in required")
    return user


def set_session_cookie(response, request: Request, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=int(SESSION_TTL.total_seconds()),
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
        path="/",
    )
