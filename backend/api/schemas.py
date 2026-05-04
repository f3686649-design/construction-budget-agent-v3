from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from backend.models import ProjectInput


class HealthResponse(BaseModel):
    status: str = "ok"
    app: str = "Construction Budget Agent"
    version: str = "3"


class ProjectRequest(ProjectInput):
    """Project input payload accepted by the React frontend."""


class ProjectSummary(BaseModel):
    project_name: str | None = None
    city: str | None = None
    total_budget: float = 0
    revenue: float = 0
    profit: float = 0
    margin: float = 0
    minimum_dscr: float | None = None
    total_equity_required: float = 0
    max_credit_balance: float = 0


class GenerateModelResponse(BaseModel):
    project_id: str
    summary: dict[str, Any]
    tep: dict[str, Any]
    budget: dict[str, Any]
    detailed_budget: dict[str, Any]
    gpr: list[dict[str, Any]]
    sales: list[dict[str, Any]]
    credit: dict[str, Any]
    cashflow: list[dict[str, Any]]
    dscr: dict[str, Any]
    economics: dict[str, Any]
    risks: list[dict[str, Any]]
    scenarios: list[dict[str, Any]]
    optimization: dict[str, Any]
    improvement_plan: dict[str, Any]
    excel_filename: str
    download_url: str


class ProjectHistoryItem(BaseModel):
    project_id: str
    calculated_at: str
    user: str | None = None
    project_name: str | None = None
    city: str | None = None
    total_budget: float = 0
    revenue: float = 0
    profit: float = 0
    margin: float = 0
    minimum_dscr: float | None = None
    excel_filename: str | None = None
    download_url: str | None = None


class ErrorResponse(BaseModel):
    detail: str = Field(..., examples=["Не удалось выполнить расчёт проекта."])
