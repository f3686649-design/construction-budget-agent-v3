from __future__ import annotations

import pytest

from backend.api import rate_limit


@pytest.fixture(autouse=True)
def _clean_limits() -> None:
    rate_limit.reset_rate_limits()
    yield
    rate_limit.reset_rate_limits()


def test_rate_limit_allows_within_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RATE_LIMIT_GENERATE_PER_HOUR", "3")
    results = [rate_limit.check_rate_limit("ivan", "generate") for _ in range(3)]
    assert all(allowed for allowed, _ in results)
    assert results[-1][1] == 0  # остаток исчерпан


def test_rate_limit_blocks_over_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RATE_LIMIT_AI_PER_HOUR", "2")
    assert rate_limit.check_rate_limit("ivan", "ai")[0]
    assert rate_limit.check_rate_limit("ivan", "ai")[0]
    allowed, remaining = rate_limit.check_rate_limit("ivan", "ai")
    assert not allowed
    assert remaining == 0


def test_rate_limit_is_per_user_and_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RATE_LIMIT_AI_PER_HOUR", "1")
    assert rate_limit.check_rate_limit("ivan", "ai")[0]
    assert not rate_limit.check_rate_limit("ivan", "ai")[0]
    # Другой пользователь и другой scope не затронуты.
    assert rate_limit.check_rate_limit("petr", "ai")[0]
    assert rate_limit.check_rate_limit("ivan", "generate")[0]


def test_rate_limit_default_limits() -> None:
    assert rate_limit.get_limit("generate") == 60
    assert rate_limit.get_limit("ai") == 20
    assert rate_limit.get_limit("unknown_scope") == 60


def test_public_api_guard_blocks_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    import backend.main as backend_main
    from fastapi import HTTPException

    monkeypatch.setattr(backend_main, "ALLOW_PUBLIC_GENERATE", False)
    with pytest.raises(HTTPException) as exc_info:
        backend_main._require_public_api()
    assert exc_info.value.status_code == 403

    monkeypatch.setattr(backend_main, "ALLOW_PUBLIC_GENERATE", True)
    backend_main._require_public_api()  # не должно бросить


def test_cors_origins_parsed_from_env() -> None:
    import backend.main as backend_main

    # Дефолт: локальные адреса Vite.
    assert "http://localhost:5173" in backend_main.CORS_ORIGINS
    assert all(origin.strip() == origin for origin in backend_main.CORS_ORIGINS)
