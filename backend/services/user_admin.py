from __future__ import annotations

import json
from typing import Any

from backend import auth
from backend.auth import create_user_record, hash_password, load_users
from backend.services import billing_service

MIN_PASSWORD_LENGTH = 6
VALID_ROLES = {"admin", "user"}


def list_all_users() -> list[dict[str, Any]]:
    """Список пользователей без хэшей паролей — для админ-панели."""
    result: list[dict[str, Any]] = []
    for user in load_users(auth.USERS_FILE):
        login = str(user.get("login") or "").strip()
        if not login:
            continue
        info = billing_service.subscription_info(login)
        result.append(
            {
                "login": login,
                "role": str(user.get("role") or "user"),
                "plan": info.get("plan"),
                "plan_name": info.get("plan_name"),
                "paid_until": info.get("paid_until"),
                "active": info.get("active"),
                "blocked": bool(user.get("blocked")),
            }
        )
    return result


def _user_exists(login: str) -> bool:
    normalized = login.strip().lower()
    return any(
        str(u.get("login") or "").strip().lower() == normalized
        for u in load_users(auth.USERS_FILE)
    )


def create_user(
    login: str,
    password: str,
    role: str = "user",
    plan: str | None = None,
    months: int = 1,
) -> dict[str, Any]:
    """Создаёт клиентский аккаунт (Postgres или файл) и опционально включает тариф."""
    login = (login or "").strip()
    if not login:
        raise ValueError("Логин не может быть пустым.")
    if len(password or "") < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Пароль должен быть не короче {MIN_PASSWORD_LENGTH} символов.")
    normalized_role = (role or "user").strip().lower() or "user"
    if normalized_role not in VALID_ROLES:
        raise ValueError("Роль должна быть admin или user.")
    if _user_exists(login):
        raise ValueError(f"Пользователь «{login}» уже существует.")

    from backend.services.db import db_enabled, upsert_user

    if db_enabled():
        upsert_user(login, hash_password(password), normalized_role)
    else:
        users_file = auth.USERS_FILE
        if users_file.exists():
            payload = json.loads(users_file.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                payload = {"users": []}
        else:
            payload = {"users": []}
        payload.setdefault("users", [])
        payload["users"].append(create_user_record(login, password, normalized_role))
        users_file.parent.mkdir(parents=True, exist_ok=True)
        users_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    plan_code = (plan or "").strip().lower()
    if plan_code and plan_code != billing_service.DEFAULT_PLAN:
        # users_file игнорируется в режиме Postgres, в файловом — пишем в тот же файл.
        billing_service.set_user_plan(login, plan_code, months, users_file=auth.USERS_FILE)

    info = billing_service.subscription_info(login)
    return {
        "login": login,
        "role": normalized_role,
        "plan": info.get("plan"),
        "plan_name": info.get("plan_name"),
        "paid_until": info.get("paid_until"),
        "active": info.get("active"),
    }


def _target_user(login: str) -> dict[str, Any]:
    normalized = (login or "").strip().lower()
    if not normalized:
        raise ValueError("Логин не указан.")
    for user in load_users(auth.USERS_FILE):
        if str(user.get("login") or "").strip().lower() == normalized:
            return user
    raise ValueError(f"Пользователь «{login}» не найден.")


def set_blocked(login: str, blocked: bool) -> dict[str, Any]:
    user = _target_user(login)
    if str(user.get("role") or "").strip().lower() == "admin":
        raise ValueError("Администратора нельзя заблокировать.")
    real_login = str(user.get("login"))

    from backend.services.db import db_enabled
    from backend.services.db import set_blocked as set_blocked_db

    if db_enabled():
        set_blocked_db(real_login, blocked)
    else:
        users_file = auth.USERS_FILE
        payload = json.loads(users_file.read_text(encoding="utf-8"))
        for u in payload.get("users", []):
            if str(u.get("login") or "").strip().lower() == real_login.strip().lower():
                u["blocked"] = bool(blocked)
        users_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"login": real_login, "blocked": bool(blocked)}


def delete_user(login: str) -> dict[str, Any]:
    user = _target_user(login)
    if str(user.get("role") or "").strip().lower() == "admin":
        raise ValueError("Администратора нельзя удалить.")
    real_login = str(user.get("login"))

    from backend.services.db import db_enabled, delete_user_db

    if db_enabled():
        delete_user_db(real_login)
    else:
        users_file = auth.USERS_FILE
        payload = json.loads(users_file.read_text(encoding="utf-8"))
        payload["users"] = [
            u for u in payload.get("users", [])
            if str(u.get("login") or "").strip().lower() != real_login.strip().lower()
        ]
        users_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"login": real_login, "deleted": True}
