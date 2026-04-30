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
    foundation_type: str | None = Field(default=None)
    has_underground_part: bool | None = None
    sellable_finish_level: str | None = Field(default=None)
    above_ground_structures_rate_override: float | None = Field(default=None, ge=0)
    envelope_roof_walls_rate_override: float | None = Field(default=None, ge=0)
    design_cost_override: float | None = Field(default=None, ge=0)
    preparation_cost_override: float | None = Field(default=None, ge=0)
    earthworks_rate_override: float | None = Field(default=None, ge=0)
    sellable_finish_rate_override: float | None = Field(default=None, ge=0)
    pile_foundation_rate_override: float | None = Field(default=None, ge=0)
    pile_foundation_cost_override: float | None = Field(default=None, ge=0)
    pile_count: int | None = Field(default=None, ge=0)
    average_pile_depth: float | None = Field(default=None, ge=0)
    pile_unit_cost: float | None = Field(default=None, ge=0)
    grillage_rate_override: float | None = Field(default=None, ge=0)
    foundation_optimization_mode: str | None = Field(default=None)
    plumbing_rate_override: float | None = Field(default=None, ge=0)
    heating_rate_override: float | None = Field(default=None, ge=0)
    electrical_rate_override: float | None = Field(default=None, ge=0)
    low_voltage_rate_override: float | None = Field(default=None, ge=0)
    ventilation_rate_override: float | None = Field(default=None, ge=0)

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
    preliminary_recommended_price_per_m2: float | None = None
    final_recommended_price_per_m2: float | None = None
    final_target_margin_price_per_m2: float | None = None
    price_iteration_count: int = 0
    actual_total_interest_used_for_price: float | None = None
    price_gap_to_market: float | None = None
    project_revenue: float | None = None
    project_cost: float | None = None
    cmr_total: float | None = None
    chapter_1_total: float | None = None
    chapter_2_total: float | None = None
    chapter_3_total: float | None = None
    margin_rub: float | None = None
    margin_percent: float | None = None
    cost_per_sellable_m2: float | None = None
    average_sale_price_per_m2: float | None = None
    peak_debt: float | None = None
    accrued_interest: float | None = None
    minimum_dscr_for_summary: float | None = None
    equity_share: float | None = None
    ending_debt_balance: float | None = None


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
    preliminary_recommended_price_per_m2: float
    final_recommended_price_per_m2: float
    final_target_margin_price_per_m2: float
    price_iteration_count: int
    actual_total_interest_used_for_price: float
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
    detailed_budget: dict[str, Any]
    work_schedule: dict[str, Any]
    gpr_summary: dict[str, Any]
    supply_plan: list[dict[str, Any]]
    summary_metrics: dict[str, Any]
    optimization: dict[str, Any]
    improvement_plan: dict[str, Any]
    scenarios: list[dict[str, Any]]
    risks: list[dict[str, Any]]
    trace: list[dict[str, Any]]
    output_filename: str | None = None
