from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
USERS_FILE = ROOT_DIR / "users.json"
HASH_ALGORITHM = "pbkdf2_sha256"
DEFAULT_ITERATIONS = 200_000


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


def load_users(users_file: Path = USERS_FILE) -> list[dict[str, Any]]:
    if not users_file.exists():
        return []
    with users_file.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    users = payload.get("users", []) if isinstance(payload, dict) else []
    return [user for user in users if isinstance(user, dict)]


def authenticate_user(login: str, password: str, users_file: Path = USERS_FILE) -> dict[str, str] | None:
    normalized_login = login.strip().lower()
    for user in load_users(users_file):
        stored_login = str(user.get("login") or "").strip().lower()
        if stored_login != normalized_login:
            continue
        password_hash = str(user.get("password_hash") or "")
        if verify_password(password, password_hash):
            return {
                "login": str(user.get("login")),
                "role": str(user.get("role") or "user"),
            }
    return None
