from __future__ import annotations

import json
import os
import threading
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from backend.auth import USERS_FILE, load_users

STORAGE_DIR = Path(__file__).resolve().parents[1] / "storage" / "usage"
_usage_lock = threading.Lock()
_users_lock = threading.Lock()

# Тарифные планы. Квоты — в месяц на пользователя.
PLANS: dict[str, dict[str, Any]] = {
    "trial": {
        "code": "trial",
        "name": "Триал",
        "price_rub": 0,
        "generate_quota": 1,
        "ai_quota": 2,
        "description": "Бесплатно: 1 расчёт и 2 ИИ-вызова в месяц — чтобы попробовать.",
        "purchasable": False,
    },
    "start": {
        "code": "start",
        "name": "Старт",
        "price_rub": 15_000,
        "generate_quota": 30,
        "ai_quota": 30,
        "description": "Частный девелопер: 30 расчётов и 30 ИИ-вызовов в месяц, Excel-выгрузка.",
        "purchasable": True,
    },
    "team": {
        "code": "team",
        "name": "Команда",
        "price_rub": 29_900,
        "generate_quota": 300,
        "ai_quota": 200,
        "description": "Девелоперская компания: 300 расчётов и 200 ИИ-вызовов в месяц, история проектов.",
        "purchasable": True,
    },
    "corporate": {
        "code": "corporate",
        "name": "Корпоративный",
        "price_rub": 150_000,
        "generate_quota": 100_000,
        "ai_quota": 5_000,
        "description": "Банк/фонд: практически безлимит, свои пороги критериев, white label — по договору.",
        "purchasable": False,
    },
}

DEFAULT_PLAN = "trial"


def get_plan(code: str | None) -> dict[str, Any]:
    return PLANS.get(str(code or "").strip().lower(), PLANS[DEFAULT_PLAN])


def _find_user(login: str) -> dict[str, Any] | None:
    normalized = login.strip().lower()
    for user in load_users(USERS_FILE):
        if str(user.get("login") or "").strip().lower() == normalized:
            return user
    return None


def subscription_info(login: str) -> dict[str, Any]:
    """Текущий план пользователя с учётом срока оплаты.

    Платный план активен до paid_until включительно; после — деградация до trial-квот.
    """
    user = _find_user(login) or {}
    plan_code = str(user.get("plan") or DEFAULT_PLAN).strip().lower()
    paid_until_raw = str(user.get("paid_until") or "").strip()
    paid_until: date | None = None
    if paid_until_raw:
        try:
            paid_until = date.fromisoformat(paid_until_raw[:10])
        except ValueError:
            paid_until = None

    plan = get_plan(plan_code)
    active = True
    effective_plan = plan
    # Администратор сервиса работает без ограничений тарифа.
    if str(user.get("role") or "").strip().lower() == "admin":
        corporate = PLANS["corporate"]
        return {
            "login": user.get("login") or login,
            "plan": "corporate",
            "plan_name": f"{corporate['name']} (админ)",
            "paid_until": None,
            "active": True,
            "effective_plan": "corporate",
            "generate_quota": corporate["generate_quota"],
            "ai_quota": corporate["ai_quota"],
        }
    if plan["code"] != DEFAULT_PLAN:
        if paid_until is None or paid_until < date.today():
            active = False
            effective_plan = PLANS[DEFAULT_PLAN]

    return {
        "login": user.get("login") or login,
        "plan": plan["code"],
        "plan_name": plan["name"],
        "paid_until": paid_until.isoformat() if paid_until else None,
        "active": active,
        "effective_plan": effective_plan["code"],
        "generate_quota": effective_plan["generate_quota"],
        "ai_quota": effective_plan["ai_quota"],
    }


def set_user_plan(login: str, plan_code: str, months: int = 1, users_file: Path | None = None) -> dict[str, Any]:
    """Активация/продление плана (вебхук оплаты или админ вручную)."""
    users_file = users_file if users_file is not None else USERS_FILE
    plan = PLANS.get(str(plan_code).strip().lower())
    if plan is None:
        raise ValueError(f"Неизвестный тариф: {plan_code}")
    months = max(1, int(months))

    from backend.services.db import db_enabled, get_user_plan_row, set_plan

    if db_enabled():
        today = date.today()
        current_until: date | None = None
        row = get_user_plan_row(login)
        if row is None:
            raise ValueError(f"Пользователь {login} не найден.")
        current_plan, current_until_raw = row
        if current_until_raw:
            try:
                current_until = date.fromisoformat(str(current_until_raw)[:10])
            except ValueError:
                current_until = None
        base = current_until if (current_until and current_until > today and current_plan == plan["code"]) else today
        new_until = base + timedelta(days=30 * months)
        if not set_plan(login, plan["code"], new_until.isoformat()):
            raise ValueError(f"Пользователь {login} не найден.")
        return {"login": login, "plan": plan["code"], "paid_until": new_until.isoformat(), "months": months}

    with _users_lock:
        if not users_file.exists():
            raise ValueError("users.json не найден.")
        payload = json.loads(users_file.read_text(encoding="utf-8"))
        users = payload.get("users", [])
        normalized = login.strip().lower()
        target = None
        for user in users:
            if str(user.get("login") or "").strip().lower() == normalized:
                target = user
                break
        if target is None:
            raise ValueError(f"Пользователь {login} не найден.")

        today = date.today()
        current_until: date | None = None
        raw = str(target.get("paid_until") or "").strip()
        if raw:
            try:
                current_until = date.fromisoformat(raw[:10])
            except ValueError:
                current_until = None
        # Продление: от текущей даты окончания, если она в будущем и план тот же.
        base = current_until if (current_until and current_until > today and target.get("plan") == plan["code"]) else today
        new_until = base + timedelta(days=30 * months)

        target["plan"] = plan["code"]
        target["paid_until"] = new_until.isoformat()
        users_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"login": target["login"], "plan": plan["code"], "paid_until": new_until.isoformat(), "months": months}


# ---------- Учёт использования ----------

def _usage_file(month_key: str | None = None) -> Path:
    month_key = month_key or datetime.now().strftime("%Y-%m")
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    return STORAGE_DIR / f"usage_{month_key}.json"


def _load_usage(month_key: str | None = None) -> dict[str, dict[str, int]]:
    path = _usage_file(month_key)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def get_usage(login: str, month_key: str | None = None) -> dict[str, int]:
    from backend.services.db import db_enabled, get_usage_db

    month = month_key or datetime.now().strftime("%Y-%m")
    if db_enabled():
        return get_usage_db(login, month)
    usage = _load_usage(month).get(login.strip().lower(), {})
    return {"generate": int(usage.get("generate") or 0), "ai": int(usage.get("ai") or 0)}


def check_quota(login: str, scope: str) -> tuple[bool, dict[str, Any]]:
    """Проверка квоты БЕЗ списания. scope: generate | ai."""
    info = subscription_info(login)
    quota = int(info["generate_quota"] if scope == "generate" else info["ai_quota"])
    used = get_usage(login)[scope]
    details = {
        "scope": scope,
        "used": used,
        "quota": quota,
        "remaining": max(0, quota - used),
        "plan": info["effective_plan"],
        "plan_active": info["active"],
    }
    return used < quota, details


def record_usage(login: str, scope: str) -> None:
    from backend.services.db import db_enabled, increment_usage_db

    if db_enabled():
        increment_usage_db(login, datetime.now().strftime("%Y-%m"), scope)
        return
    key = login.strip().lower()
    with _usage_lock:
        path = _usage_file()
        usage = _load_usage()
        user_usage = usage.setdefault(key, {})
        user_usage[scope] = int(user_usage.get(scope) or 0) + 1
        path.write_text(json.dumps(usage, ensure_ascii=False, indent=2), encoding="utf-8")


def billing_overview(login: str) -> dict[str, Any]:
    info = subscription_info(login)
    usage = get_usage(login)
    return {
        **info,
        "usage": usage,
        "remaining": {
            "generate": max(0, int(info["generate_quota"]) - usage["generate"]),
            "ai": max(0, int(info["ai_quota"]) - usage["ai"]),
        },
        "month": datetime.now().strftime("%Y-%m"),
        "plans": [
            {k: v for k, v in plan.items()}
            for plan in PLANS.values()
        ],
    }
