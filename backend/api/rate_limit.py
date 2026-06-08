from __future__ import annotations

import os
import threading
import time
from collections import defaultdict, deque

# Простой in-memory rate limiter для тяжёлых операций (расчёт модели, LLM).
# Для одного инстанса достаточно; при горизонтальном масштабировании заменить на Redis.

_WINDOW_SECONDS = 3600.0
_lock = threading.Lock()
_events: dict[tuple[str, str], deque[float]] = defaultdict(deque)

DEFAULT_LIMITS = {
    "generate": 60,  # расчётов модели в час на пользователя
    "ai": 20,        # ИИ-заключений в час на пользователя (LLM стоит денег)
    "register": 10,  # регистраций в час с одного IP (защита от спама)
}


def get_limit(scope: str) -> int:
    env_key = f"RATE_LIMIT_{scope.upper()}_PER_HOUR"
    raw = os.getenv(env_key)
    if raw:
        try:
            return max(1, int(raw))
        except ValueError:
            pass
    return DEFAULT_LIMITS.get(scope, 60)


def check_rate_limit(user: str, scope: str) -> tuple[bool, int]:
    """Возвращает (разрешено, осталось_запросов). Регистрирует событие, если разрешено."""
    limit = get_limit(scope)
    now = time.monotonic()
    key = (user, scope)
    with _lock:
        events = _events[key]
        while events and now - events[0] > _WINDOW_SECONDS:
            events.popleft()
        if len(events) >= limit:
            return False, 0
        events.append(now)
        return True, limit - len(events)


def reset_rate_limits() -> None:
    """Для тестов."""
    with _lock:
        _events.clear()
