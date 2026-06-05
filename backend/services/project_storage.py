from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.services.export_service import download_url_for
from backend.tools.norms import round_money


PROJECTS_DIR = Path(__file__).resolve().parents[1] / "storage" / "projects"


def create_project_id() -> str:
    return uuid.uuid4().hex


def get_projects_dir(projects_dir: Path = PROJECTS_DIR) -> Path:
    projects_dir.mkdir(parents=True, exist_ok=True)
    return projects_dir


def get_project_dir(project_id: str, projects_dir: Path = PROJECTS_DIR) -> Path:
    if not project_id or any(part in project_id for part in ("..", "/", "\\")):
        raise ValueError("Некорректный идентификатор проекта.")
    return get_projects_dir(projects_dir) / project_id


def prepare_project_dir(project_id: str, projects_dir: Path = PROJECTS_DIR) -> Path:
    project_dir = get_project_dir(project_id, projects_dir)
    project_dir.mkdir(parents=True, exist_ok=True)
    return project_dir


def build_project_metadata(
    *,
    project_id: str,
    model: dict[str, Any],
    excel_path: Path,
    username: str = "api",
) -> dict[str, Any]:
    economics = model.get("economics", {})
    dscr = model.get("dscr", {})
    metadata = {
        "project_id": project_id,
        "calculated_at": datetime.now().isoformat(timespec="seconds"),
        "user": username,
        "project_name": model.get("input", {}).get("project_name"),
        "city": model.get("input", {}).get("city"),
        "total_budget": round_money(model.get("budget", {}).get("total_budget") or 0),
        "revenue": round_money(economics.get("revenue") or 0),
        "profit": round_money(economics.get("profit_after_interest") or economics.get("profit") or 0),
        "margin": round(float(economics.get("margin_after_interest") or economics.get("margin") or 0), 4),
        "minimum_dscr": dscr.get("minimum_dscr_after_sales_start"),
        "excel_filename": excel_path.name,
        "excel_path": str(excel_path),
        "download_url": download_url_for(excel_path.name),
    }
    return metadata


def save_project_files(
    *,
    project_id: str,
    input_data: dict[str, Any],
    result: dict[str, Any],
    metadata: dict[str, Any],
    excel_path: Path,
    projects_dir: Path = PROJECTS_DIR,
) -> dict[str, Any]:
    from backend.services.db import db_enabled, save_file_db, save_project_db

    if db_enabled():
        metadata = {**metadata, "excel_filename": excel_path.name}
        result = {**result, "excel_filename": excel_path.name, "download_url": download_url_for(excel_path.name)}
        if excel_path.exists():
            save_file_db(excel_path.name, excel_path.read_bytes())
        save_project_db(
            project_id=project_id,
            username=str(metadata.get("user") or "") or None,
            project_name=str(metadata.get("project_name") or "") or None,
            metadata=metadata,
            input_data=input_data,
            result=result,
            excel_filename=excel_path.name,
        )
        return metadata

    project_dir = prepare_project_dir(project_id, projects_dir)
    target_excel_path = project_dir / excel_path.name
    if excel_path.exists() and excel_path.resolve() != target_excel_path.resolve():
        shutil.copy2(excel_path, target_excel_path)
    metadata = {**metadata, "excel_path": str(target_excel_path), "excel_filename": target_excel_path.name}
    result = {**result, "excel_filename": target_excel_path.name, "download_url": download_url_for(target_excel_path.name)}

    _write_json(project_dir / "input.json", input_data)
    _write_json(project_dir / "result.json", result)
    _write_json(project_dir / "metadata.json", metadata)
    return metadata


def list_projects(projects_dir: Path = PROJECTS_DIR) -> list[dict[str, Any]]:
    from backend.services.db import db_enabled, list_projects_db

    if db_enabled():
        return list_projects_db()
    if not projects_dir.exists():
        return []
    rows: list[dict[str, Any]] = []
    for metadata_path in projects_dir.glob("*/metadata.json"):
        try:
            rows.append(_read_json(metadata_path))
        except (OSError, json.JSONDecodeError):
            continue
    return sorted(rows, key=lambda row: str(row.get("calculated_at") or ""), reverse=True)


def get_project_result(project_id: str, projects_dir: Path = PROJECTS_DIR) -> dict[str, Any] | None:
    from backend.services.db import db_enabled, get_project_result_db

    if db_enabled():
        return get_project_result_db(project_id)
    result_path = get_project_dir(project_id, projects_dir) / "result.json"
    if not result_path.exists():
        return None
    return _read_json(result_path)


def find_excel_file(filename: str, projects_dir: Path = PROJECTS_DIR) -> Path | None:
    if not filename or any(part in filename for part in ("..", "/", "\\")):
        return None
    if not projects_dir.exists():
        return None
    for project_dir in projects_dir.iterdir():
        candidate = project_dir / filename
        if candidate.is_file():
            return candidate
    return None


def _write_json(path: Path, data: dict[str, Any] | list[Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2, default=str)


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def get_excel_bytes(filename: str, projects_dir: Path = PROJECTS_DIR) -> bytes | None:
    """Содержимое Excel: из БД (db-режим) или с диска (файловый режим)."""
    from backend.services.db import db_enabled, get_file_db

    if db_enabled():
        if not filename or any(part in filename for part in ("..", "/", "\\")):
            return None
        return get_file_db(filename)
    path = find_excel_file(filename, projects_dir)
    return path.read_bytes() if path else None
