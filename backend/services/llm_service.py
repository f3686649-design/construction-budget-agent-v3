from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

from backend.services.project_storage import get_project_dir

load_dotenv()

PROVIDER = "openai"
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_BASE_URL = "https://api.openai.com/v1"
AI_CONCLUSION_FILENAME = "ai_conclusion.json"

SYSTEM_PROMPT = """Ты — независимый финансовый аналитик девелоперских проектов (жилая недвижимость, Россия, 214-ФЗ, эскроу).
Твоя задача — написать аналитическую записку по проекту для инвестора и кредитного комитета банка.

Правила, обязательные к исполнению:
1. Пиши жёстко и честно. Не приукрашивай. Если проект слабый или не проходит критерии — прямо так и пиши.
2. Не смягчай и не оспаривай вердикты расчётного ядра (земля, банк, техприсоединение) — раскрывай их смысл и последствия.
3. Опирайся ТОЛЬКО на числа из переданного дайджеста. Не выдумывай данные. Если данных нет — напиши «нет данных».
4. Все допущения модели называй допущениями.
5. Пиши на русском, деловым языком, без воды. Суммы — в млн ₽ с одним знаком после запятой, где уместно.

Структура записки (markdown, заголовки ##):
1. Главный вывод — 2–4 предложения: входить в проект или нет, пройдёт ли банк, главное ограничение.
2. Экономика проекта — бюджет, выручка, прибыль, маржа, на чём держится результат.
3. Земля — вердикт остаточной оценки и что он означает для сделки.
4. Финансирование и банк — эскроу, LLCR, покрытие, стресс-тесты, вердикт банка.
5. Техприсоединение — затраты, дефицит, сроки.
6. Ключевые риски — 3–5 главных, по убыванию ущерба.
7. Что сделать перед следующим шагом — конкретные действия с числами.

Объём: 350–600 слов."""

CHAT_SYSTEM_PROMPT = """Ты — независимый финансовый аналитик девелоперских проектов (жилая недвижимость, Россия, 214-ФЗ, эскроу).
Ты отвечаешь на вопросы пользователя по конкретному рассчитанному проекту. Дайджест модели передан в первом сообщении.

Правила:
1. Опирайся ТОЛЬКО на числа из дайджеста. Не выдумывай данные. Если в дайджесте нет ответа — прямо скажи, каких данных не хватает.
2. Отвечай жёстко и честно, без приукрашивания. Вердикты расчётного ядра (земля, банк, ТУ) не оспаривай — объясняй их причины и последствия.
3. Можно объяснять методику: остаточный метод оценки земли, эскроу-механику, LLCR, банковские критерии, стресс-тесты.
4. Отвечай кратко и по делу: обычно 50–200 слов, суммы в млн ₽ с одним знаком после запятой. Без воды.
5. Все допущения модели называй допущениями. Пиши на русском.
6. Если вопрос не относится к проекту или девелопменту — вежливо откажись и верни разговор к проекту."""

MAX_CHAT_HISTORY = 10


def is_configured() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def ai_status() -> dict[str, Any]:
    return {
        "provider": PROVIDER,
        "configured": is_configured(),
        "model": os.getenv("OPENAI_MODEL", DEFAULT_MODEL),
        "detail": None if is_configured() else "Не задан OPENAI_API_KEY в .env — ИИ-заключение недоступно.",
    }


def generate_ai_conclusion(model: dict[str, Any]) -> dict[str, Any]:
    """Формирует ИИ-заключение по рассчитанной модели через OpenAI API."""
    if not is_configured():
        return {
            "status": "unavailable",
            "conclusion": None,
            "provider": PROVIDER,
            "model": None,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "error": "Не задан OPENAI_API_KEY в .env — ИИ-заключение недоступно.",
        }

    digest = build_project_digest(model)
    model_name = os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
    base_url = os.getenv("OPENAI_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", "90"))

    payload = {
        "model": model_name,
        "temperature": 0.2,
        "max_tokens": 2000,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Дайджест рассчитанной финансовой модели проекта (JSON):\n"
                    + json.dumps(digest, ensure_ascii=False)
                    + "\n\nНапиши аналитическую записку по правилам."
                ),
            },
        ],
    }
    try:
        response = requests.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        body = response.json()
        text = body["choices"][0]["message"]["content"].strip()
        usage = body.get("usage", {})
        return {
            "status": "ok",
            "conclusion": text,
            "provider": PROVIDER,
            "model": body.get("model", model_name),
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "tokens": {
                "prompt": usage.get("prompt_tokens"),
                "completion": usage.get("completion_tokens"),
            },
            "error": None,
        }
    except requests.RequestException as exc:
        detail = str(exc)
        if getattr(exc, "response", None) is not None:
            try:
                detail = f"{exc.response.status_code}: {exc.response.text[:300]}"
            except Exception:  # noqa: BLE001
                pass
        return {
            "status": "error",
            "conclusion": None,
            "provider": PROVIDER,
            "model": model_name,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "error": f"Ошибка обращения к OpenAI API: {detail}",
        }
    except (KeyError, IndexError, ValueError) as exc:
        return {
            "status": "error",
            "conclusion": None,
            "provider": PROVIDER,
            "model": model_name,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "error": f"Неожиданный ответ OpenAI API: {exc}",
        }


def chat_about_project(
    model: dict[str, Any],
    question: str,
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Ответ на вопрос по проекту с контекстом рассчитанной модели."""
    if not is_configured():
        return {
            "status": "unavailable",
            "answer": None,
            "provider": PROVIDER,
            "model": None,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "error": "Не задан OPENAI_API_KEY в .env — чат с ИИ недоступен.",
        }

    question = (question or "").strip()
    if not question:
        return {
            "status": "error",
            "answer": None,
            "provider": PROVIDER,
            "model": None,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "error": "Пустой вопрос.",
        }

    digest = build_project_digest(model)
    model_name = os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
    base_url = os.getenv("OPENAI_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", "90"))

    messages: list[dict[str, str]] = [
        {"role": "system", "content": CHAT_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": "Дайджест рассчитанной финансовой модели проекта (JSON):\n"
            + json.dumps(digest, ensure_ascii=False),
        },
        {"role": "assistant", "content": "Дайджест получен. Готов отвечать на вопросы по проекту."},
    ]
    for item in (history or [])[-MAX_CHAT_HISTORY:]:
        role = item.get("role")
        content = str(item.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content[:4000]})
    messages.append({"role": "user", "content": question[:4000]})

    payload = {
        "model": model_name,
        "temperature": 0.3,
        "max_tokens": 1200,
        "messages": messages,
    }
    try:
        response = requests.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        body = response.json()
        text = body["choices"][0]["message"]["content"].strip()
        return {
            "status": "ok",
            "answer": text,
            "provider": PROVIDER,
            "model": body.get("model", model_name),
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "error": None,
        }
    except requests.RequestException as exc:
        detail = str(exc)
        if getattr(exc, "response", None) is not None:
            try:
                detail = f"{exc.response.status_code}: {exc.response.text[:300]}"
            except Exception:  # noqa: BLE001
                pass
        return {
            "status": "error",
            "answer": None,
            "provider": PROVIDER,
            "model": model_name,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "error": f"Ошибка обращения к OpenAI API: {detail}",
        }
    except (KeyError, IndexError, ValueError) as exc:
        return {
            "status": "error",
            "answer": None,
            "provider": PROVIDER,
            "model": model_name,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "error": f"Неожиданный ответ OpenAI API: {exc}",
        }


def build_project_digest(model: dict[str, Any]) -> dict[str, Any]:
    """Компактная выжимка модели для LLM: только то, что нужно для заключения."""

    def block(name: str) -> dict[str, Any]:
        value = model.get(name)
        return value if isinstance(value, dict) else {}

    tep = block("tep")
    economics = block("economics")
    if hasattr(economics, "model_dump"):
        economics = economics.model_dump()
    land = block("land_valuation")
    escrow = block("escrow_financing")
    bank = block("bank_approval")
    tech = block("tech_connection")
    summary = block("summary") or block("summary_metrics")
    input_data = block("input")

    risks = []
    for risk in (model.get("risks") or [])[:7]:
        risks.append(
            {
                "level": risk.get("level"),
                "title": _cut(risk.get("title") or risk.get("message")),
                "description": _cut(risk.get("description")),
            }
        )

    scenarios = []
    for scenario in (model.get("scenarios") or [])[:4]:
        scenarios.append(
            {
                "scenario": scenario.get("scenario") or scenario.get("name"),
                "profit": scenario.get("profit") or scenario.get("profit_after_interest"),
                "margin": scenario.get("margin") or scenario.get("margin_after_interest"),
            }
        )

    failed_criteria = [
        {"name": c.get("name"), "threshold": c.get("threshold"), "actual": c.get("actual"), "severity": c.get("severity")}
        for c in (bank.get("criteria") or [])
        if not c.get("passed")
    ]

    return {
        "проект": {
            "название": input_data.get("project_name") or tep.get("project_name"),
            "город": input_data.get("city") or tep.get("city"),
            "класс": input_data.get("object_class") or tep.get("object_class"),
            "общая_площадь_м2": tep.get("total_area") or input_data.get("total_area"),
            "продаваемая_площадь_м2": tep.get("sellable_area") or input_data.get("sellable_area"),
            "этажность": tep.get("floors") or input_data.get("floors"),
            "срок_стройки_мес": tep.get("construction_months"),
            "срок_продаж_мес": tep.get("sales_months"),
        },
        "экономика": {
            "бюджет_руб": economics.get("total_budget"),
            "выручка_руб": economics.get("revenue"),
            "прибыль_после_процентов_руб": economics.get("profit_after_interest"),
            "маржа_после_процентов": economics.get("margin_after_interest"),
            "цена_продажи_м2": economics.get("sale_price_per_m2"),
            "источник_цены": economics.get("sale_price_source"),
            "рыночная_цена_м2": economics.get("market_price_per_m2"),
            "собственные_средства_руб": economics.get("total_equity_required"),
        },
        "земля": {
            "вердикт": land.get("verdict"),
            "уровень": land.get("verdict_level"),
            "макс_обоснованная_цена_руб": land.get("max_land_price"),
            "цена_в_расчете_руб": land.get("asking_land_price"),
            "запас": land.get("safety_reserve"),
        },
        "банк_эскроу": {
            "вердикт": bank.get("verdict"),
            "уровень": bank.get("verdict_level"),
            "непройденные_критерии": failed_criteria,
            "рекомендации": (bank.get("recommendations") or [])[:5],
            "llcr": escrow.get("llcr"),
            "покрытие_эскроу_на_вводе": escrow.get("escrow_coverage_at_delivery"),
            "пиковый_долг_руб": escrow.get("max_debt"),
            "проценты_руб": escrow.get("total_interest"),
            "собственное_участие": escrow.get("equity_share"),
            "стресс_тесты": bank.get("stress_tests"),
        },
        "техприсоединение": {
            "вердикт": tech.get("verdict"),
            "уровень": tech.get("verdict_level"),
            "плата_итого_руб": tech.get("total_cost"),
            "заложено_в_бюджете_руб": tech.get("budget_allocation"),
            "дефицит_руб": tech.get("deficit"),
            "проблемы_сроков": tech.get("schedule_issues"),
        },
        "риски": risks,
        "сценарии": scenarios,
        "сводка": {
            "минимальный_dscr": summary.get("minimum_dscr") or economics.get("minimum_dscr_after_sales_start"),
            "пик_кредита_руб": summary.get("max_credit_balance") or economics.get("max_credit_balance"),
        },
    }


def save_ai_conclusion(project_id: str, payload: dict[str, Any]) -> Path:
    project_dir = get_project_dir(project_id)
    project_dir.mkdir(parents=True, exist_ok=True)
    path = project_dir / AI_CONCLUSION_FILENAME
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_ai_conclusion(project_id: str) -> dict[str, Any] | None:
    path = get_project_dir(project_id) / AI_CONCLUSION_FILENAME
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _cut(value: Any, limit: int = 220) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if len(text) <= limit else text[: limit - 1] + "…"
