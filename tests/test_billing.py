from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from backend.auth import create_user_record
from backend.services import billing_service, payment_service


@pytest.fixture()
def users_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "users.json"
    payload = {
        "users": [
            {**create_user_record("ivan", "secret123", "user")},
            {**create_user_record("admin", "secret123", "admin")},
        ]
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(billing_service, "USERS_FILE", path)
    import backend.auth as auth

    monkeypatch.setattr(auth, "USERS_FILE", path)
    return path


@pytest.fixture(autouse=True)
def usage_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    usage = tmp_path / "usage"
    monkeypatch.setattr(billing_service, "STORAGE_DIR", usage)
    return usage


def test_default_plan_is_trial(users_file: Path) -> None:
    info = billing_service.subscription_info("ivan")
    assert info["plan"] == "trial"
    assert info["active"] is True
    assert info["generate_quota"] == billing_service.PLANS["trial"]["generate_quota"]


def test_quota_enforced_and_usage_recorded(users_file: Path) -> None:
    quota = billing_service.PLANS["trial"]["generate_quota"]
    for _ in range(quota):
        ok, _details = billing_service.check_quota("ivan", "generate")
        assert ok
        billing_service.record_usage("ivan", "generate")
    ok, details = billing_service.check_quota("ivan", "generate")
    assert not ok
    assert details["remaining"] == 0
    assert details["used"] == quota
    # ai-квота независима
    ok_ai, _ = billing_service.check_quota("ivan", "ai")
    assert ok_ai


def test_set_user_plan_activates_and_extends(users_file: Path) -> None:
    result = billing_service.set_user_plan("ivan", "start", months=1)
    assert result["plan"] == "start"
    info = billing_service.subscription_info("ivan")
    assert info["plan"] == "start" and info["active"]
    assert info["generate_quota"] == billing_service.PLANS["start"]["generate_quota"]
    first_until = date.fromisoformat(result["paid_until"])
    # Продление добавляет ещё 30 дней к текущему сроку.
    result2 = billing_service.set_user_plan("ivan", "start", months=1)
    assert date.fromisoformat(result2["paid_until"]) == first_until + timedelta(days=30)


def test_expired_plan_degrades_to_trial(users_file: Path) -> None:
    billing_service.set_user_plan("ivan", "team", months=1)
    payload = json.loads(users_file.read_text(encoding="utf-8"))
    for user in payload["users"]:
        if user["login"] == "ivan":
            user["paid_until"] = (date.today() - timedelta(days=1)).isoformat()
    users_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    info = billing_service.subscription_info("ivan")
    assert info["plan"] == "team"
    assert info["active"] is False
    assert info["effective_plan"] == "trial"
    assert info["generate_quota"] == billing_service.PLANS["trial"]["generate_quota"]


def test_set_unknown_plan_rejected(users_file: Path) -> None:
    with pytest.raises(ValueError):
        billing_service.set_user_plan("ivan", "vip")
    with pytest.raises(ValueError):
        billing_service.set_user_plan("ghost", "start")


def test_create_payment_manual_mode_without_keys(users_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("YOOKASSA_SHOP_ID", raising=False)
    monkeypatch.delenv("YOOKASSA_SECRET_KEY", raising=False)
    result = payment_service.create_payment("ivan", "start")
    assert result["status"] == "manual"
    assert "счёт" in result["instructions"]
    # Некупимый тариф — ошибка.
    bad = payment_service.create_payment("ivan", "corporate")
    assert bad["status"] == "error"


def test_create_payment_with_mocked_yookassa(users_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("YOOKASSA_SHOP_ID", "shop")
    monkeypatch.setenv("YOOKASSA_SECRET_KEY", "key")
    fake = MagicMock()
    fake.raise_for_status.return_value = None
    fake.json.return_value = {
        "id": "pay_1",
        "confirmation": {"confirmation_url": "https://yookassa.ru/pay/1"},
    }
    with patch.object(payment_service.requests, "post", return_value=fake) as mocked:
        result = payment_service.create_payment("ivan", "start", "https://app/billing")
    assert result["status"] == "created"
    assert result["confirmation_url"] == "https://yookassa.ru/pay/1"
    sent = mocked.call_args.kwargs["json"]
    assert sent["metadata"] == {"login": "ivan", "plan": "start", "months": 1}
    assert sent["amount"]["value"] == "15000.00"


def test_webhook_activates_plan_after_api_verification(users_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("YOOKASSA_SHOP_ID", "shop")
    monkeypatch.setenv("YOOKASSA_SECRET_KEY", "key")
    fake = MagicMock()
    fake.raise_for_status.return_value = None
    fake.json.return_value = {
        "id": "pay_1",
        "status": "succeeded",
        "metadata": {"login": "ivan", "plan": "team", "months": 1},
    }
    with patch.object(payment_service.requests, "get", return_value=fake):
        result = payment_service.handle_webhook({"event": "payment.succeeded", "object": {"id": "pay_1"}})
    assert result["status"] == "activated"
    assert billing_service.subscription_info("ivan")["plan"] == "team"


def test_webhook_ignores_unverified_or_foreign_events(users_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("YOOKASSA_SHOP_ID", "shop")
    monkeypatch.setenv("YOOKASSA_SECRET_KEY", "key")
    # Чужое событие
    assert payment_service.handle_webhook({"event": "payment.canceled", "object": {"id": "x"}})["status"] == "ignored"
    # API говорит, что платёж не succeeded — активации нет.
    fake = MagicMock()
    fake.raise_for_status.return_value = None
    fake.json.return_value = {"id": "pay_2", "status": "pending", "metadata": {"login": "ivan", "plan": "team"}}
    with patch.object(payment_service.requests, "get", return_value=fake):
        result = payment_service.handle_webhook({"event": "payment.succeeded", "object": {"id": "pay_2"}})
    assert result["status"] == "ignored"
    assert billing_service.subscription_info("ivan")["plan"] == "trial"


def test_admin_has_unlimited_corporate_plan(users_file: Path) -> None:
    info = billing_service.subscription_info("admin")
    assert info["effective_plan"] == "corporate"
    assert info["active"] is True
    assert info["generate_quota"] == billing_service.PLANS["corporate"]["generate_quota"]
    ok, details = billing_service.check_quota("admin", "generate")
    assert ok and details["quota"] >= 100_000
