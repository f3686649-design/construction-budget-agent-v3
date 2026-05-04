from __future__ import annotations

from typing import Any

from backend.models import ProjectInput
from backend.services.export_service import create_excel_file, download_url_for
from backend.services.project_storage import (
    build_project_metadata,
    create_project_id,
    prepare_project_dir,
    save_project_files,
)


def generate_project(project_input: ProjectInput, username: str = "api") -> dict[str, Any]:
    # Local import keeps the service layer from creating an import cycle with backend.main.
    from backend.main import build_financial_model

    project_id = create_project_id()
    project_dir = prepare_project_dir(project_id)
    model = build_financial_model(project_input)
    excel_path = create_excel_file(model, project_dir)
    model["output_filename"] = excel_path.name

    response = build_frontend_response(
        project_id=project_id,
        model=model,
        excel_filename=excel_path.name,
    )
    metadata = build_project_metadata(
        project_id=project_id,
        model=model,
        excel_path=excel_path,
        username=username,
    )
    metadata = save_project_files(
        project_id=project_id,
        input_data=project_input.model_dump(mode="json", exclude_none=True),
        result={**response, "input": model.get("input"), "metadata": metadata},
        metadata=metadata,
        excel_path=excel_path,
    )
    return {**response, "metadata": metadata}


def build_frontend_response(
    *,
    project_id: str,
    model: dict[str, Any],
    excel_filename: str,
) -> dict[str, Any]:
    economics = model.get("economics", {})
    credit = model.get("credit", {})
    dscr = model.get("dscr", {})
    summary = {
        "project_name": model.get("input", {}).get("project_name"),
        "city": model.get("input", {}).get("city"),
        "total_budget": model.get("budget", {}).get("total_budget", 0),
        "revenue": economics.get("revenue", 0),
        "profit": economics.get("profit_after_interest", economics.get("profit", 0)),
        "margin": economics.get("margin_after_interest", economics.get("margin", 0)),
        "minimum_dscr": dscr.get("minimum_dscr_after_sales_start"),
        "total_equity_required": economics.get("total_equity_required", 0),
        "max_credit_balance": credit.get("max_balance", 0),
    }
    return {
        "project_id": project_id,
        "summary": summary,
        "tep": model.get("tep", {}),
        "budget": model.get("budget", {}),
        "detailed_budget": model.get("detailed_budget", {}),
        "gpr": model.get("gpr", []),
        "sales": model.get("sales_plan", []),
        "credit": credit,
        "cashflow": model.get("cashflow", []),
        "dscr": dscr,
        "economics": economics,
        "risks": model.get("risks", []),
        "scenarios": model.get("scenarios", []),
        "optimization": model.get("optimization", {}),
        "improvement_plan": model.get("improvement_plan", {}),
        "excel_filename": excel_filename,
        "download_url": download_url_for(excel_filename),
    }
