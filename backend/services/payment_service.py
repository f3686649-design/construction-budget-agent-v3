from __future__ import annotations

import os
import uuid
from typing import Any

import requests
from dotenv import load_dotenv

from backend.services.billing_service import PLANS, set_user_plan

load_dotenv()

YOOKASSA_API_URL = "https://api.yookassa.ru/v3"

MANUAL_PAYMENT_INSTRUCTIONS = (
    "Онлайн-оплата картой пока не подключена. Для активации тарифа запросите счёт: "
    "напишите администратору сервиса, укажите логин и выбранный тариф. "
    "После оплаты счёта администратор активирует подписку вручную."
)


def is_configured() -> bool:
    return bool(os.getenv("YOOKASSA_SHOP_ID")) and bool(os.getenv("YOOKASSA_SECRET_KEY"))


def payment_status() -> dict[str, Any]:
    return {
        "provider": "yookassa",
        "configured": is_configured(),
        "manual_instructions": None if is_configured() else MANUAL_PAYMENT_INSTRUCTIONS,
    }


def create_payment(login: str, plan_code: str, return_url: str | None = None) -> dict[str, Any]:
    """Создаёт платёж в ЮKassa и возвращает ссылку на оплату.

    Без настроенных ключей возвращает manual-режим (оплата по счёту).
    """
    plan = PLANS.get(str(plan_code).strip().lower())
    if plan is None or not plan.get("purchasable"):
        return {
            "status": "error",
            "error": "Этот тариф нельзя оплатить онлайн. Свяжитесь с администратором.",
        }

    if not is_configured():
        return {
            "status": "manual",
            "plan": plan["code"],
            "amount_rub": plan["price_rub"],
            "instructions": MANUAL_PAYMENT_INSTRUCTIONS,
        }

    idempotence_key = uuid.uuid4().hex
    payload = {
        "amount": {"value": f"{plan['price_rub']:.2f}", "currency": "RUB"},
        "capture": True,
        "confirmation": {
            "type": "redirect",
            "return_url": return_url or os.getenv("BILLING_RETURN_URL", "https://example.com/billing"),
        },
        "description": f"Construction Budget Agent — тариф «{plan['name']}», 1 месяц, пользователь {login}",
        "metadata": {"login": login, "plan": plan["code"], "months": 1},
    }
    try:
        response = requests.post(
            f"{YOOKASSA_API_URL}/payments",
            json=payload,
            auth=(os.getenv("YOOKASSA_SHOP_ID", ""), os.getenv("YOOKASSA_SECRET_KEY", "")),
            headers={"Idempotence-Key": idempotence_key},
            timeout=30,
        )
        response.raise_for_status()
        body = response.json()
        return {
            "status": "created",
            "payment_id": body.get("id"),
            "confirmation_url": (body.get("confirmation") or {}).get("confirmation_url"),
            "amount_rub": plan["price_rub"],
            "plan": plan["code"],
        }
    except requests.RequestException as exc:
        detail = str(exc)
        if getattr(exc, "response", None) is not None:
            try:
                detail = f"{exc.response.status_code}: {exc.response.text[:300]}"
            except Exception:  # noqa: BLE001
                pass
        return {"status": "error", "error": f"Ошибка создания платежа: {detail}"}


def fetch_payment(payment_id: str) -> dict[str, Any] | None:
    """Проверка платежа напрямую в ЮKassa — защита от поддельных вебхуков."""
    if not is_configured():
        return None
    try:
        response = requests.get(
            f"{YOOKASSA_API_URL}/payments/{payment_id}",
            auth=(os.getenv("YOOKASSA_SHOP_ID", ""), os.getenv("YOOKASSA_SECRET_KEY", "")),
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None


def handle_webhook(event: dict[str, Any]) -> dict[str, Any]:
    """Обработка вебхука ЮKassa.

    Никогда не доверяем телу вебхука: берём payment_id и перепроверяем платёж
    через API. Активируем подписку только по статусу succeeded из API.
    """
    event_type = str(event.get("event") or "")
    obj = event.get("object") or {}
    payment_id = str(obj.get("id") or "")

    if event_type != "payment.succeeded" or not payment_id:
        return {"status": "ignored", "reason": f"событие {event_type or 'без типа'}"}

    payment = fetch_payment(payment_id)
    if payment is None:
        return {"status": "error", "reason": "не удалось проверить платёж в ЮKassa"}
    if payment.get("status") != "succeeded":
        return {"status": "ignored", "reason": f"статус платежа {payment.get('status')}"}

    metadata = payment.get("metadata") or {}
    login = str(metadata.get("login") or "")
    plan_code = str(metadata.get("plan") or "")
    months = int(metadata.get("months") or 1)
    if not login or not plan_code:
        return {"status": "error", "reason": "в платеже нет metadata login/plan"}

    try:
        result = set_user_plan(login, plan_code, months)
    except ValueError as exc:
        return {"status": "error", "reason": str(exc)}
    return {"status": "activated", **result, "payment_id": payment_id}
