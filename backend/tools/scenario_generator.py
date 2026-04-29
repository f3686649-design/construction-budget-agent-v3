from __future__ import annotations

import math
from copy import deepcopy
from typing import Any

from backend.tools.budget_generator import generate_budget
from backend.tools.cashflow_model import build_operations, generate_cashflow
from backend.tools.credit_model import generate_credit_schedule
from backend.tools.dscr_model import calculate_dscr
from backend.tools.gpr_generator import generate_gpr
from backend.tools.norms import round_money
from backend.tools.sales_plan_generator import generate_sales_plan


def generate_scenarios(base_data: dict[str, Any]) -> list[dict[str, Any]]:
    scenarios = [
        ("base", "Базовый", _base_data(base_data)),
        ("optimistic", "Оптимистичный", _optimistic_data(base_data)),
        ("stress", "Стресс", _stress_data(base_data)),
    ]
    return [_calculate_scenario(code, name, data) for code, name, data in scenarios]


def _base_data(base_data: dict[str, Any]) -> dict[str, Any]:
    return deepcopy(base_data)


def _optimistic_data(base_data: dict[str, Any]) -> dict[str, Any]:
    data = deepcopy(base_data)
    data["sale_price_per_m2"] = float(data["sale_price_per_m2"]) * 1.07
    data["sales_months"] = max(1, int(round(float(data["sales_months"]) * 0.90)))
    return data


def _stress_data(base_data: dict[str, Any]) -> dict[str, Any]:
    data = deepcopy(base_data)
    data["sale_price_per_m2"] = float(data["sale_price_per_m2"]) * 0.90
    data["sales_months"] = max(1, int(math.ceil(float(data["sales_months"]) * 1.20)))
    if data.get("gp_contract_price_per_m2"):
        data["gp_contract_price_per_m2"] = float(data["gp_contract_price_per_m2"]) * 1.07
    elif data.get("construction_cost_per_m2"):
        data["construction_cost_per_m2"] = float(data["construction_cost_per_m2"]) * 1.07
    else:
        data["_estimated_cost_multiplier"] = 1.07
    data["credit_rate"] = float(data["credit_rate"]) + 0.02
    return data


def _calculate_scenario(code: str, name: str, data: dict[str, Any]) -> dict[str, Any]:
    budget = generate_budget(data)
    budget.pop("trace", None)
    gpr = generate_gpr(
        total_budget=float(budget["total_budget"]),
        land_cost=float(budget["land"]),
        construction_months=int(data["construction_months"]),
    )
    sales_plan = generate_sales_plan(
        sellable_area=float(data["sellable_area"]),
        sale_price_per_m2=float(data["sale_price_per_m2"]),
        sales_months=int(data["sales_months"]),
    )
    operations = build_operations(gpr, sales_plan)
    credit = generate_credit_schedule(
        operations=operations,
        credit_share=float(data["credit_share"]),
        annual_rate=float(data["credit_rate"]),
        total_budget=float(budget["total_budget"]),
    )
    cashflow = generate_cashflow(operations, credit["schedule"])
    dscr = calculate_dscr(cashflow)

    revenue = float(data["sellable_area"]) * float(data["sale_price_per_m2"])
    profit_before_interest = revenue - float(budget["total_budget"])
    profit_after_interest = profit_before_interest - float(credit["total_interest"])
    margin_after_interest = profit_after_interest / revenue if revenue else 0.0
    total_equity_required = max((float(row["cumulative_equity_required"]) for row in cashflow), default=0.0)
    minimum_dscr = dscr["minimum_dscr_after_sales_start"]

    margin_assessment, margin_color = _margin_assessment(margin_after_interest)
    dscr_assessment, dscr_color = _dscr_assessment(minimum_dscr)
    return {
        "scenario": code,
        "scenario_name": name,
        "sale_price_per_m2": round_money(data["sale_price_per_m2"]),
        "sales_months": int(data["sales_months"]),
        "gp_contract_price_per_m2": (
            round_money(data["gp_contract_price_per_m2"]) if data.get("gp_contract_price_per_m2") else None
        ),
        "construction_cost_per_m2": budget["construction_price_per_m2"],
        "credit_rate": round(float(data["credit_rate"]), 4),
        "revenue": round_money(revenue),
        "total_budget": budget["total_budget"],
        "profit_before_interest": round_money(profit_before_interest),
        "profit_after_interest": round_money(profit_after_interest),
        "margin_after_interest": round(margin_after_interest, 4),
        "max_credit_balance": credit["max_balance"],
        "total_equity_required": round_money(total_equity_required),
        "minimum_dscr_after_sales_start": minimum_dscr,
        "months_below_1_2": dscr["months_below_1_2"],
        "margin_assessment": margin_assessment,
        "margin_color": margin_color,
        "dscr_assessment": dscr_assessment,
        "dscr_color": dscr_color,
    }


def _margin_assessment(margin: float) -> tuple[str, str]:
    if margin < 0.08:
        return "плохо", "red"
    if margin <= 0.15:
        return "средне", "yellow"
    return "хорошо", "green"


def _dscr_assessment(minimum_dscr: float | None) -> tuple[str, str]:
    if minimum_dscr is None:
        return "нет данных", "gray"
    if minimum_dscr < 1.2:
        return "риск", "red"
    return "норма", "green"
