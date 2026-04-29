from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProjectInput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    project_name: str | None = Field(default=None)
    city: str | None = Field(default=None)
    object_type: str | None = Field(default=None)
    object_class: str | None = Field(default=None)
    land_area: float | None = Field(default=None, ge=0)
    land_cost: float | None = Field(default=None, ge=0)
    total_area: float | None = Field(default=None, ge=0)
    sellable_area: float | None = Field(default=None, ge=0)
    floors: int | None = Field(default=None, ge=0)
    sale_price_per_m2: float | None = Field(default=None, ge=0)
    construction_cost_per_m2: float | None = Field(default=None, ge=0)
    gp_contract_price_per_m2: float | None = Field(default=None, ge=0)
    construction_months: int | None = Field(default=None, ge=1)
    sales_months: int | None = Field(default=None, ge=1)
    credit_share: float | None = Field(default=None, ge=0)
    credit_rate: float | None = Field(default=None, ge=0)
    external_networks_included: bool | None = None
    gas_only_cooking: bool | None = None

    @field_validator("credit_share", "credit_rate")
    @classmethod
    def normalize_percent(cls, value: float | None) -> float | None:
        if value is None:
            return None
        return value / 100 if value > 1 else value


class Assumption(BaseModel):
    field: str
    value: Any
    reason: str
    source: str = "developer_assumption"


class TraceStep(BaseModel):
    step: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    formula: str | None = None


class EconomicsMetrics(BaseModel):
    model_config = ConfigDict(extra="ignore")

    revenue: float
    total_budget: float
    sellable_ratio: float
    budget_per_total_m2: float
    budget_per_sellable_m2: float
    revenue_per_total_m2: float
    profit_before_interest: float
    profit_after_interest: float
    margin_before_interest: float
    margin_after_interest: float
    total_interest: float
    max_credit_balance: float
    total_equity_required: float
    minimum_dscr: float | None = None
    minimum_dscr_after_sales_start: float | None = None
    average_dscr_after_sales_start: float | None = None
    months_below_1_2: int = 0
    roi_on_budget: float = 0
    profit: float | None = None
    margin: float | None = None
    sale_price_source: str | None = None
    sale_price_per_m2: float | None = None
    estimated_sale_price_per_m2: float | None = None
    market_price_per_m2: float | None = None
    break_even_price_per_m2: float | None = None
    target_margin_price_per_m2: float | None = None
    recommended_price_per_m2: float | None = None
    price_gap_to_market: float | None = None


class GeneratedModel(BaseModel):
    status: str = "ok"
    input: dict[str, Any]
    assumptions: list[dict[str, Any]]
    tep: dict[str, Any]
    budget: dict[str, Any]
    estimated_cmr_cost_per_m2: float
    cmr_cost_source: str
    cost_estimation_components: dict[str, Any]
    cost_estimation_coefficients: dict[str, Any]
    estimated_sale_price_per_m2: float
    sale_price_source: str
    market_price_per_m2: float
    break_even_price_per_m2: float
    target_margin_price_per_m2: float
    recommended_price_per_m2: float
    price_gap_to_market: float
    price_estimation_components: dict[str, Any]
    price_estimation_coefficients: dict[str, Any]
    price_estimation_warnings: list[str]
    cmr: dict[str, Any]
    gpr: list[dict[str, Any]]
    sales_plan: list[dict[str, Any]]
    credit: dict[str, Any]
    cashflow: list[dict[str, Any]]
    dscr: dict[str, Any]
    economics: EconomicsMetrics
    optimization: dict[str, Any]
    scenarios: list[dict[str, Any]]
    risks: list[dict[str, Any]]
    trace: list[dict[str, Any]]
    output_filename: str | None = None
