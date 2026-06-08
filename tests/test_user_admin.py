from __future__ import annotations

import json
from pathlib import Path

import pytest

import backend.auth as auth
from backend.auth import authenticate_user, create_user_record
from backend.services import billing_service, user_admin


@pytest.fixture()
def users_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "users.json"
    payload = {"users": [{**create_user_record("admin", "secret123", "admin")}]}
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(billing_service, "USERS_FILE", path)
    monkeypatch.setattr(auth, "USERS_FILE", path)
    return path


def test_create_user_with_plan(users_file: Path) -> None:
    result = user_admin.create_user("ivan", "secret123", "user", "start", 1)
    assert result["login"] == "ivan"
    assert result["role"] == "user"
    assert result["plan"] == "start"
    assert result["active"] is True
    assert result["paid_until"]
    # Пользователь реально создан и может войти.
    assert authenticate_user("ivan", "secret123", users_file) is not None


def test_create_user_default_trial(users_file: Path) -> None:
    result = user_admin.create_user("petr", "secret123")
    assert result["plan"] == "trial"
    assert authenticate_user("petr", "secret123", users_file) is not None


def test_list_users_hides_password_hash(users_file: Path) -> None:
    user_admin.create_user("ivan", "secret123", "user", "team", 1)
    listed = user_admin.list_all_users()
    logins = {u["login"] for u in listed}
    assert {"admin", "ivan"} <= logins
    for user in listed:
        assert "password_hash" not in user


def test_duplicate_login_rejected_case_insensitive(users_file: Path) -> None:
    user_admin.create_user("ivan", "secret123")
    with pytest.raises(ValueError):
        user_admin.create_user("IVAN", "secret123")
    with pytest.raises(ValueError):
        user_admin.create_user("admin", "secret123")


def test_short_password_rejected(users_file: Path) -> None:
    with pytest.raises(ValueError):
        user_admin.create_user("zoe", "123")
    # Несуществующий — не создан.
    assert authenticate_user("zoe", "123", users_file) is None


def test_invalid_role_rejected(users_file: Path) -> None:
    with pytest.raises(ValueError):
        user_admin.create_user("zoe", "secret123", "superuser")


def test_empty_login_rejected(users_file: Path) -> None:
    with pytest.raises(ValueError):
        user_admin.create_user("   ", "secret123")


def test_block_prevents_login_and_unblock_restores(users_file: Path) -> None:
    user_admin.create_user("ivan", "secret123")
    assert authenticate_user("ivan", "secret123", users_file) is not None
    user_admin.set_blocked("ivan", True)
    assert authenticate_user("ivan", "secret123", users_file) is None
    assert auth.is_user_blocked("ivan") is True
    user_admin.set_blocked("ivan", False)
    assert authenticate_user("ivan", "secret123", users_file) is not None
    assert auth.is_user_blocked("ivan") is False


def test_blocked_flag_in_list(users_file: Path) -> None:
    user_admin.create_user("ivan", "secret123")
    user_admin.set_blocked("ivan", True)
    listed = {u["login"]: u for u in user_admin.list_all_users()}
    assert listed["ivan"]["blocked"] is True


def test_delete_user_removes_account(users_file: Path) -> None:
    user_admin.create_user("ivan", "secret123")
    user_admin.delete_user("ivan")
    assert authenticate_user("ivan", "secret123", users_file) is None
    assert "ivan" not in {u["login"] for u in user_admin.list_all_users()}


def test_cannot_block_or_delete_admin(users_file: Path) -> None:
    with pytest.raises(ValueError):
        user_admin.set_blocked("admin", True)
    with pytest.raises(ValueError):
        user_admin.delete_user("admin")


def test_block_delete_unknown_user_rejected(users_file: Path) -> None:
    with pytest.raises(ValueError):
        user_admin.set_blocked("ghost", True)
    with pytest.raises(ValueError):
        user_admin.delete_user("ghost")
