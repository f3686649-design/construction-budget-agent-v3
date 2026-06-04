from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from backend.main import build_financial_model
from backend.models import ProjectInput
from backend.services import llm_service


@pytest.fixture()
def demo_model() -> dict:
    return build_financial_model(
        ProjectInput(
            project_name="Тест ИИ",
            city="Якутск",
            object_type="Жилой комплекс",
            object_class="comfort",
            total_area=12_000,
            sellable_area=9_000,
            floors=9,
            land_area=5_000,
            land_cost=30_000_000,
        )
    )


def test_digest_contains_all_verdicts(demo_model: dict) -> None:
    digest = llm_service.build_project_digest(demo_model)
    assert digest["проект"]["название"] == "Тест ИИ"
    assert digest["экономика"]["бюджет_руб"] > 0
    assert digest["земля"]["вердикт"]
    assert digest["банк_эскроу"]["вердикт"]
    assert digest["техприсоединение"]["вердикт"]
    assert isinstance(digest["риски"], list)
    # Дайджест компактный: не тащим расписания и trace.
    text = json.dumps(digest, ensure_ascii=False)
    assert "schedule" not in text
    assert "trace" not in text
    assert len(text) < 20_000


def test_unavailable_without_api_key(demo_model: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = llm_service.generate_ai_conclusion(demo_model)
    assert result["status"] == "unavailable"
    assert result["conclusion"] is None
    assert "OPENAI_API_KEY" in result["error"]
    assert llm_service.ai_status()["configured"] is False


def test_generate_conclusion_with_mocked_api(demo_model: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    fake_response = MagicMock()
    fake_response.raise_for_status.return_value = None
    fake_response.json.return_value = {
        "model": "gpt-4o-mini",
        "choices": [{"message": {"content": "## Главный вывод\nПроект проходит банк."}}],
        "usage": {"prompt_tokens": 1000, "completion_tokens": 400},
    }
    with patch.object(llm_service.requests, "post", return_value=fake_response) as mocked:
        result = llm_service.generate_ai_conclusion(demo_model)
    assert result["status"] == "ok"
    assert "Главный вывод" in result["conclusion"]
    assert result["tokens"]["completion"] == 400
    # Проверяем, что в API ушли system-промпт и дайджест.
    payload = mocked.call_args.kwargs["json"]
    assert payload["messages"][0]["role"] == "system"
    assert "аналитик" in payload["messages"][0]["content"]
    assert "Тест ИИ" in payload["messages"][1]["content"]


def test_api_error_returns_error_status(demo_model: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    import requests as requests_lib

    with patch.object(
        llm_service.requests, "post", side_effect=requests_lib.ConnectionError("no network")
    ):
        result = llm_service.generate_ai_conclusion(demo_model)
    assert result["status"] == "error"
    assert "OpenAI" in result["error"]


def test_save_and_load_ai_conclusion(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import backend.services.project_storage as storage

    monkeypatch.setattr(storage, "PROJECTS_DIR", tmp_path)
    monkeypatch.setattr(llm_service, "get_project_dir", lambda pid: tmp_path / pid)

    payload = {"status": "ok", "conclusion": "Тестовая записка", "generated_at": "2026-06-04T00:00:00"}
    path = llm_service.save_ai_conclusion("proj1", payload)
    assert path.exists()
    loaded = llm_service.load_ai_conclusion("proj1")
    assert loaded == payload
    assert llm_service.load_ai_conclusion("missing") is None


def test_chat_unavailable_without_api_key(demo_model: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = llm_service.chat_about_project(demo_model, "Почему не проходим банк?")
    assert result["status"] == "unavailable"
    assert result["answer"] is None


def test_chat_rejects_empty_question(demo_model: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    result = llm_service.chat_about_project(demo_model, "   ")
    assert result["status"] == "error"
    assert "Пустой вопрос" in result["error"]


def test_chat_with_mocked_api_includes_digest_history_and_question(
    demo_model: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    fake_response = MagicMock()
    fake_response.raise_for_status.return_value = None
    fake_response.json.return_value = {
        "model": "gpt-4o-mini",
        "choices": [{"message": {"content": "Маржа ниже порога банка."}}],
    }
    history = [
        {"role": "user", "content": "Привет"},
        {"role": "assistant", "content": "Готов отвечать."},
    ]
    with patch.object(llm_service.requests, "post", return_value=fake_response) as mocked:
        result = llm_service.chat_about_project(demo_model, "Почему маржа низкая?", history)
    assert result["status"] == "ok"
    assert "Маржа" in result["answer"]
    messages = mocked.call_args.kwargs["json"]["messages"]
    assert messages[0]["role"] == "system"
    assert "Дайджест" in messages[1]["content"] and "Тест ИИ" in messages[1]["content"]
    # История вошла, последний — вопрос пользователя.
    assert {"role": "user", "content": "Привет"} in messages
    assert messages[-1] == {"role": "user", "content": "Почему маржа низкая?"}


def test_chat_truncates_long_history(demo_model: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    fake_response = MagicMock()
    fake_response.raise_for_status.return_value = None
    fake_response.json.return_value = {
        "model": "m",
        "choices": [{"message": {"content": "ok"}}],
    }
    history = [{"role": "user", "content": f"вопрос {i}"} for i in range(30)]
    with patch.object(llm_service.requests, "post", return_value=fake_response) as mocked:
        llm_service.chat_about_project(demo_model, "финальный вопрос", history)
    messages = mocked.call_args.kwargs["json"]["messages"]
    history_in_payload = [m for m in messages if m["content"].startswith("вопрос ")]
    assert len(history_in_payload) == llm_service.MAX_CHAT_HISTORY
    assert history_in_payload[-1]["content"] == "вопрос 29"
