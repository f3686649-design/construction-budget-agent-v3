from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
USERS_FILE = ROOT_DIR / "users.json"
HASH_ALGORITHM = "pbkdf2_sha256"
DEFAULT_ITERATIONS = 200_000
TOKEN_TTL_SECONDS = int(os.getenv("AUTH_TOKEN_TTL_SECONDS", "43200"))
AUTH_SECRET = os.getenv("AUTH_SECRET", "construction-budget-agent-v3-local-secret")


def hash_password(password: str, salt: str | None = None, iterations: int = DEFAULT_ITERATIONS) -> str:
    if not password:
        raise ValueError("Пароль не может быть пустым.")
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
    return f"{HASH_ALGORITHM}${iterations}${salt}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations_raw, salt, expected_hash = password_hash.split("$", 3)
        if algorithm != HASH_ALGORITHM:
            return False
        candidate = hash_password(password, salt=salt, iterations=int(iterations_raw)).split("$", 3)[3]
        return hmac.compare_digest(candidate, expected_hash)
    except (ValueError, TypeError):
        return False


def create_user_record(username: str, password: str, role: str = "user") -> dict[str, str]:
    login = username.strip()
    normalized_role = role.strip().lower() or "user"
    if not login:
        raise ValueError("Логин не может быть пустым.")
    if normalized_role not in {"admin", "user"}:
        raise ValueError("Роль пользователя должна быть admin или user.")
    return {
        "login": login,
        "password_hash": hash_password(password),
        "role": normalized_role,
    }


def load_users(users_file: Path | None = None) -> list[dict[str, Any]]:
    # При заданном DATABASE_URL пользователи живут в Postgres.
    from backend.services.db import db_enabled, fetch_users

    if db_enabled():
        return fetch_users()
    if users_file is None:
        users_file = USERS_FILE
    if not users_file.exists():
        return []
    with users_file.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    users = payload.get("users", []) if isinstance(payload, dict) else []
    return [user for user in users if isinstance(user, dict)]


def authenticate_user(login: str, password: str, users_file: Path | None = None) -> dict[str, str] | None:
    normalized_login = login.strip().lower()
    for user in load_users(users_file):
        stored_login = str(user.get("login") or "").strip().lower()
        if stored_login != normalized_login:
            continue
        if user.get("blocked"):
            return None
        password_hash = str(user.get("password_hash") or "")
        if verify_password(password, password_hash):
            return {
                "login": str(user.get("login")),
                "role": str(user.get("role") or "user"),
            }
    return None


def create_access_token(user: dict[str, str], ttl_seconds: int = TOKEN_TTL_SECONDS) -> str:
    payload = {
        "login": user["login"],
        "role": user.get("role") or "user",
        "exp": int(time.time()) + ttl_seconds,
    }
    payload_bytes = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    signature = hmac.new(AUTH_SECRET.encode("utf-8"), payload_bytes, hashlib.sha256).digest()
    return f"{_base64url_encode(payload_bytes)}.{_base64url_encode(signature)}"


def verify_access_token(token: str) -> dict[str, str] | None:
    try:
        payload_raw, signature_raw = token.split(".", 1)
        payload_bytes = _base64url_decode(payload_raw)
        signature = _base64url_decode(signature_raw)
    except (ValueError, TypeError):
        return None

    expected_signature = hmac.new(AUTH_SECRET.encode("utf-8"), payload_bytes, hashlib.sha256).digest()
    if not hmac.compare_digest(signature, expected_signature):
        return None

    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None

    if int(payload.get("exp") or 0) < int(time.time()):
        return None

    login = str(payload.get("login") or "").strip()
    if not login:
        return None
    return {
        "login": login,
        "role": str(payload.get("role") or "user"),
    }


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def is_user_blocked(login: str) -> bool:
    """Заблокирован ли пользователь (вход и доступ запрещены)."""
    from backend.services.db import db_enabled, get_user_blocked

    if db_enabled():
        return bool(get_user_blocked(login))
    normalized = login.strip().lower()
    for user in load_users():
        if str(user.get("login") or "").strip().lower() == normalized:
            return bool(user.get("blocked"))
    return False
