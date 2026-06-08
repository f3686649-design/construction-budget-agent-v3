from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import backend.auth as auth
from backend.api import rate_limit
from backend.main import app
from backend.services import billing_service


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    users = tmp_path / "users.json"
    users.write_text(json.dumps({"users": []}, ensure_ascii=False), encoding="utf-8")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("ALLOW_SELF_REGISTRATION", "true")
    monkeypatch.setattr(auth, "USERS_FILE", users)
    monkeypatch.setattr(billing_service, "USERS_FILE", users)
    rate_limit.reset_rate_limits()
    return TestClient(app)


def test_register_creates_account_and_logs_in(client: TestClient) -> None:
    r = client.post("/api/auth/register", json={"login": "newbie", "password": "secret123"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["access_token"]
    assert data["user"]["login"] == "newbie"
    assert data["user"]["role"] == "user"
    # Тем же логином/паролем можно войти.
    r2 = client.post("/api/auth/login", json={"login": "newbie", "password": "secret123"})
    assert r2.status_code == 200


def test_register_new_user_gets_trial(client: TestClient) -> None:
    client.post("/api/auth/register", json={"login": "newbie", "password": "secret123"})
    login = client.post("/api/auth/login", json={"login": "newbie", "password": "secret123"})
    token = login.json()["access_token"]
    billing = client.get("/api/billing", headers={"Authorization": f"Bearer {token}"})
    assert billing.status_code == 200
    assert billing.json()["plan"] == "trial"


def test_register_duplicate_rejected(client: TestClient) -> None:
    client.post("/api/auth/register", json={"login": "newbie", "password": "secret123"})
    r = client.post("/api/auth/register", json={"login": "NEWBIE", "password": "secret123"})
    assert r.status_code == 400


def test_register_short_password_rejected(client: TestClient) -> None:
    r = client.post("/api/auth/register", json={"login": "newbie", "password": "12345"})
    assert r.status_code == 400


def test_register_disabled_by_flag(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALLOW_SELF_REGISTRATION", "false")
    r = client.post("/api/auth/register", json={"login": "newbie", "password": "secret123"})
    assert r.status_code == 403


def test_register_rate_limited(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RATE_LIMIT_REGISTER_PER_HOUR", "2")
    assert client.post("/api/auth/register", json={"login": "a", "password": "secret123"}).status_code == 200
    assert client.post("/api/auth/register", json={"login": "b", "password": "secret123"}).status_code == 200
    # Третья регистрация с того же IP — блок.
    assert client.post("/api/auth/register", json={"login": "c", "password": "secret123"}).status_code == 429


def test_email_verification_full_flow(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from backend import auth
    from backend.services import email_service

    sent: dict = {}
    monkeypatch.setattr(email_service, "email_enabled", lambda: True)
    monkeypatch.setattr(email_service, "send_verification_email", lambda to, token: sent.update(to=to))

    r = client.post("/api/auth/register", json={"login": "newbie", "email": "a@b.ru", "password": "secret123"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "verification_sent"
    assert sent.get("to") == "a@b.ru"

    # Вход заблокирован до подтверждения.
    r2 = client.post("/api/auth/login", json={"login": "newbie", "password": "secret123"})
    assert r2.status_code == 403

    token = auth.create_email_token("newbie")
    v = client.get(f"/api/auth/verify?token={token}", follow_redirects=False)
    assert v.status_code == 303
    assert "verified=1" in v.headers["location"]

    r3 = client.post("/api/auth/login", json={"login": "newbie", "password": "secret123"})
    assert r3.status_code == 200


def test_register_rejects_bad_email_when_verification_on(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.services import email_service

    monkeypatch.setattr(email_service, "email_enabled", lambda: True)
    monkeypatch.setattr(email_service, "send_verification_email", lambda to, token: None)
    r = client.post("/api/auth/register", json={"login": "x", "email": "not-an-email", "password": "secret123"})
    assert r.status_code == 400


def test_verify_invalid_token_redirects(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    v = client.get("/api/auth/verify?token=garbage", follow_redirects=False)
    assert v.status_code == 303
    assert "verify=invalid" in v.headers["location"]


def test_resend_verification(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.services import email_service

    calls: list = []
    monkeypatch.setattr(email_service, "email_enabled", lambda: True)
    monkeypatch.setattr(email_service, "send_verification_email", lambda to, token: calls.append(to))
    client.post("/api/auth/register", json={"login": "newbie", "email": "a@b.ru", "password": "secret123"})
    r = client.post("/api/auth/resend-verification", json={"login": "newbie"})
    assert r.status_code == 200 and r.json()["status"] == "ok"
    assert calls
