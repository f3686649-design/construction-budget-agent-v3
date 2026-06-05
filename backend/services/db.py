from __future__ import annotations

import json
import os
import threading
from datetime import date
from typing import Any

from dotenv import load_dotenv

load_dotenv()

# Хранилище в Postgres включается переменной DATABASE_URL.
# Без неё весь код работает в файловом режиме (локальная разработка, тесты).

_lock = threading.Lock()
_conn = None  # type: ignore[var-annotated]


def db_enabled() -> bool:
    return bool(os.getenv("DATABASE_URL"))


def _connect():  # noqa: ANN202
    import psycopg

    dsn = os.environ["DATABASE_URL"]
    conn = psycopg.connect(dsn, autocommit=True)
    return conn


def _get_conn():  # noqa: ANN202
    global _conn
    if _conn is None or _conn.closed:
        _conn = _connect()
    return _conn


def _execute(query: str, params: tuple = (), fetch: str | None = None):  # noqa: ANN202
    """Выполнение запроса с одним повтором при обрыве соединения."""
    import psycopg

    with _lock:
        for attempt in (1, 2):
            try:
                conn = _get_conn()
                with conn.cursor() as cur:
                    cur.execute(query, params)
                    if fetch == "one":
                        return cur.fetchone()
                    if fetch == "all":
                        return cur.fetchall()
                    return None
            except psycopg.OperationalError:
                global _conn
                try:
                    if _conn is not None:
                        _conn.close()
                except Exception:  # noqa: BLE001
                    pass
                _conn = None
                if attempt == 2:
                    raise
    return None


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    login TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    plan TEXT,
    paid_until DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS usage_counters (
    login TEXT NOT NULL,
    month TEXT NOT NULL,
    scope TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (login, month, scope)
);
CREATE TABLE IF NOT EXISTS projects (
    project_id TEXT PRIMARY KEY,
    username TEXT,
    project_name TEXT,
    metadata JSONB,
    input JSONB,
    result JSONB,
    ai_conclusion JSONB,
    excel_filename TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS files (
    filename TEXT PRIMARY KEY,
    content BYTEA NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


def init_db() -> None:
    """Создаёт схему и админа из APP_ADMIN_* (если пользователей ещё нет)."""
    if not db_enabled():
        return
    _execute(SCHEMA)
    _ensure_admin()


def _ensure_admin() -> None:
    row = _execute("SELECT count(*) FROM users", fetch="one")
    if row and int(row[0]) > 0:
        return
    username = os.getenv("APP_ADMIN_USERNAME")
    password = os.getenv("APP_ADMIN_PASSWORD")
    if not username or not password:
        return
    from backend.auth import hash_password

    role = os.getenv("APP_ADMIN_ROLE", "admin")
    _execute(
        """INSERT INTO users (login, password_hash, role) VALUES (%s, %s, %s)
           ON CONFLICT (login) DO NOTHING""",
        (username.strip(), hash_password(password), role.strip().lower() or "admin"),
    )


# ---------- Пользователи ----------

def fetch_users() -> list[dict[str, Any]]:
    rows = _execute(
        "SELECT login, password_hash, role, plan, paid_until FROM users ORDER BY created_at",
        fetch="all",
    ) or []
    users: list[dict[str, Any]] = []
    for login, password_hash, role, plan, paid_until in rows:
        user: dict[str, Any] = {"login": login, "password_hash": password_hash, "role": role}
        if plan:
            user["plan"] = plan
        if paid_until:
            user["paid_until"] = paid_until.isoformat() if isinstance(paid_until, date) else str(paid_until)
        users.append(user)
    return users


def upsert_user(login: str, password_hash: str, role: str = "user") -> None:
    _execute(
        """INSERT INTO users (login, password_hash, role) VALUES (%s, %s, %s)
           ON CONFLICT (login) DO UPDATE SET password_hash = EXCLUDED.password_hash, role = EXCLUDED.role""",
        (login.strip(), password_hash, role),
    )


def set_plan(login: str, plan: str, paid_until: str) -> bool:
    row = _execute(
        """UPDATE users SET plan = %s, paid_until = %s WHERE lower(login) = lower(%s)
           RETURNING login""",
        (plan, paid_until, login.strip()),
        fetch="one",
    )
    return row is not None


def get_user_plan_row(login: str) -> tuple[str | None, str | None] | None:
    row = _execute(
        "SELECT plan, paid_until FROM users WHERE lower(login) = lower(%s)",
        (login.strip(),),
        fetch="one",
    )
    if row is None:
        return None
    plan, paid_until = row
    return plan, (paid_until.isoformat() if isinstance(paid_until, date) else paid_until)


# ---------- Учёт использования ----------

def get_usage_db(login: str, month: str) -> dict[str, int]:
    rows = _execute(
        "SELECT scope, count FROM usage_counters WHERE lower(login) = lower(%s) AND month = %s",
        (login.strip(), month),
        fetch="all",
    ) or []
    usage = {"generate": 0, "ai": 0}
    for scope, count in rows:
        usage[str(scope)] = int(count)
    return usage


def increment_usage_db(login: str, month: str, scope: str) -> None:
    _execute(
        """INSERT INTO usage_counters (login, month, scope, count) VALUES (lower(%s), %s, %s, 1)
           ON CONFLICT (login, month, scope) DO UPDATE SET count = usage_counters.count + 1""",
        (login.strip(), month, scope),
    )


# ---------- Проекты ----------

def save_project_db(
    *,
    project_id: str,
    username: str | None,
    project_name: str | None,
    metadata: dict[str, Any],
    input_data: dict[str, Any],
    result: dict[str, Any],
    excel_filename: str | None,
) -> None:
    _execute(
        """INSERT INTO projects (project_id, username, project_name, metadata, input, result, excel_filename)
           VALUES (%s, %s, %s, %s, %s, %s, %s)
           ON CONFLICT (project_id) DO UPDATE SET
             metadata = EXCLUDED.metadata, input = EXCLUDED.input,
             result = EXCLUDED.result, excel_filename = EXCLUDED.excel_filename""",
        (
            project_id,
            username,
            project_name,
            json.dumps(metadata, ensure_ascii=False),
            json.dumps(input_data, ensure_ascii=False),
            json.dumps(result, ensure_ascii=False),
            excel_filename,
        ),
    )


def get_project_result_db(project_id: str) -> dict[str, Any] | None:
    row = _execute("SELECT result FROM projects WHERE project_id = %s", (project_id,), fetch="one")
    if row is None:
        return None
    result = row[0]
    return result if isinstance(result, dict) else json.loads(result)


def list_projects_db(limit: int = 100) -> list[dict[str, Any]]:
    rows = _execute(
        "SELECT metadata FROM projects ORDER BY created_at DESC LIMIT %s",
        (limit,),
        fetch="all",
    ) or []
    items: list[dict[str, Any]] = []
    for (metadata,) in rows:
        items.append(metadata if isinstance(metadata, dict) else json.loads(metadata))
    return items


def save_ai_conclusion_db(project_id: str, payload: dict[str, Any]) -> None:
    _execute(
        "UPDATE projects SET ai_conclusion = %s WHERE project_id = %s",
        (json.dumps(payload, ensure_ascii=False), project_id),
    )


def load_ai_conclusion_db(project_id: str) -> dict[str, Any] | None:
    row = _execute("SELECT ai_conclusion FROM projects WHERE project_id = %s", (project_id,), fetch="one")
    if row is None or row[0] is None:
        return None
    payload = row[0]
    return payload if isinstance(payload, dict) else json.loads(payload)


# ---------- Файлы (Excel) ----------

def save_file_db(filename: str, content: bytes) -> None:
    _execute(
        """INSERT INTO files (filename, content) VALUES (%s, %s)
           ON CONFLICT (filename) DO UPDATE SET content = EXCLUDED.content""",
        (filename, content),
    )


def get_file_db(filename: str) -> bytes | None:
    row = _execute("SELECT content FROM files WHERE filename = %s", (filename,), fetch="one")
    if row is None:
        return None
    content = row[0]
    return bytes(content) if content is not None else None
