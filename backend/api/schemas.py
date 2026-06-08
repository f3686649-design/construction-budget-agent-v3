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


class LoginRequest(BaseModel):
    login: str
    password: str


class RegisterRequest(BaseModel):
    login: str
    email: str = ""
    password: str


class AuthUser(BaseModel):
    login: str
    role: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUser


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
    max_land_price: float | None = None
    land_verdict: str | None = None
    land_verdict_level: str | None = None
    llcr: float | None = None
    escrow_coverage_at_delivery: float | None = None
    bank_verdict: str | None = None
    bank_verdict_code: str | None = None
    bank_verdict_level: str | None = None
    tech_connection_cost: float | None = None
    tech_connection_deficit: float | None = None
    tech_connection_verdict: str | None = None
    tech_connection_verdict_level: str | None = None


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
    land_valuation: dict[str, Any] = Field(default_factory=dict)
    escrow_financing: dict[str, Any] = Field(default_factory=dict)
    bank_approval: dict[str, Any] = Field(default_factory=dict)
    tech_connection: dict[str, Any] = Field(default_factory=dict)
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


class AiChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=4000)


class AiChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    history: list[AiChatMessage] = Field(default_factory=list, max_length=20)


class ErrorResponse(BaseModel):
    detail: str = Field(..., examples=["Не удалось выполнить расчёт проекта."])
