from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.tools.excel_exporter import export_model_to_excel


def create_excel_file(model: dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    return export_model_to_excel(model, output_dir)


def download_url_for(filename: str) -> str:
    return f"/api/download/{filename}"
