from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.services.export_service import download_url_for
from backend.tools.norms import round_money


PROJECTS_DIR = Path(__file__).resolve().parent / "storage" / "projects"


def save_project_metadata(
    *,
    model: dict[str, Any],
    excel_path: Path,
    username: str,
    projects_dir: Path = PROJECTS_DIR,
) -> dict[str, Any]:
    projects_dir.mkdir(parents=True, exist_ok=True)
    project_id = uuid.uuid4().hex
    project_dir = projects_dir / project_id
    project_dir.mkdir(parents=True, exist_ok=True)

    target_excel_path = project_dir / excel_path.name
    if excel_path.exists() and excel_path.resolve() != target_excel_path.resolve():
        shutil.copy2(excel_path, target_excel_path)
    elif excel_path.exists():
        target_excel_path = excel_path

    economics = model["economics"]
    metadata = {
        "project_id": project_id,
        "calculated_at": datetime.now().isoformat(timespec="seconds"),
        "user": username,
        "project_name": model["input"].get("project_name"),
        "city": model["input"].get("city"),
        "total_budget": round_money(model["budget"].get("total_budget") or 0),
        "revenue": round_money(economics.get("revenue") or 0),
        "profit": round_money(economics.get("profit_after_interest") or 0),
        "margin": round(float(economics.get("margin_after_interest") or 0), 4),
        "minimum_dscr": model["dscr"].get("minimum_dscr_after_sales_start"),
        "excel_filename": target_excel_path.name,
        "excel_path": str(target_excel_path),
        "download_url": download_url_for(target_excel_path.name),
    }
    result = {
        **model,
        "project_id": project_id,
        "excel_filename": target_excel_path.name,
        "download_url": download_url_for(target_excel_path.name),
    }
    with (project_dir / "input.json").open("w", encoding="utf-8") as handle:
        json.dump(model.get("input", {}), handle, ensure_ascii=False, indent=2, default=str)
    with (project_dir / "result.json").open("w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2, default=str)
    with (project_dir / "metadata.json").open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, ensure_ascii=False, indent=2)
    return metadata


def load_project_history(projects_dir: Path = PROJECTS_DIR) -> list[dict[str, Any]]:
    if not projects_dir.exists():
        return []
    rows: list[dict[str, Any]] = []
    for metadata_path in projects_dir.glob("*/metadata.json"):
        try:
            with metadata_path.open("r", encoding="utf-8") as handle:
                rows.append(json.load(handle))
        except (OSError, json.JSONDecodeError):
            continue
    return sorted(rows, key=lambda row: str(row.get("calculated_at") or ""), reverse=True)


def metadata_path_for_project(project_id: str, projects_dir: Path = PROJECTS_DIR) -> Path:
    return projects_dir / project_id / "metadata.json"
