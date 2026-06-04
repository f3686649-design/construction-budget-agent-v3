from __future__ import annotations

import pytest

from backend.main import build_financial_model
from backend.models import ProjectInput
from backend.tools.land_value_estimator import evaluate_land_value


def test_feasible_when_land_is_cheap() -> None:
    result = evaluate_land_value(
        revenue=1_000_000_000,
        total_budget=700_000_000,
        land_cost=50_000_000,
        total_interest=70_000_000,
        land_area=10_000,
    )
    assert result["verdict_code"] == "feasible"
    assert result["verdict_level"] == "ok"
    assert result["max_land_price"] > result["asking_land_price"]
    assert result["safety_reserve"] is not None and result["safety_reserve"] >= 0.10
    assert "целесообразна" in result["verdict"]
    assert "нецелесообразна" not in result["verdict"]


def test_infeasible_when_land_is_overpriced() -> None:
    result = evaluate_land_value(
        revenue=1_000_000_000,
        total_budget=950_000_000,
        land_cost=300_000_000,
        total_interest=95_000_000,
        land_area=10_000,
    )
    assert result["verdict_code"] == "infeasible"
    assert result["verdict_level"] == "critical"
    assert "покупка участка экономически нецелесообразна" in result["verdict"].lower()
    assert result["max_land_price"] < result["asking_land_price"]


def test_reference_only_without_land_price() -> None:
    result = evaluate_land_value(
        revenue=1_000_000_000,
        total_budget=700_000_000,
        land_cost=0,
        total_interest=70_000_000,
    )
    assert result["verdict_code"] == "reference_only"
    assert result["verdict_level"] == "info"
    assert result["asking_land_price"] is None
    assert result["max_land_price"] > 0


def test_infeasible_at_any_price_when_costs_exceed_revenue() -> None:
    result = evaluate_land_value(
        revenue=500_000_000,
        total_budget=600_000_000,
        land_cost=10_000_000,
        total_interest=60_000_000,
    )
    assert result["verdict_code"] == "infeasible_any_price"
    assert result["verdict_level"] == "critical"
    assert "при любой цене" in result["verdict"]


def test_borderline_when_reserve_below_threshold() -> None:
    # Без процентов: max = 1 млрд * 0.85 - 800 млн = 50 млн; цена 48 млн -> запас 4% < 10%.
    result = evaluate_land_value(
        revenue=1_000_000_000,
        total_budget=848_000_000,
        land_cost=48_000_000,
        total_interest=0,
    )
    assert result["max_land_price"] == 50_000_000
    assert result["verdict_code"] == "borderline"
    assert result["verdict_level"] == "warning"
    assert "на грани" in result["verdict"]


def test_infeasible_at_market_price_when_calc_price_above_market() -> None:
    # Без процентов: max = 1000*0.85 - 700 = 150 млн, но при рыночной выручке 900 млн max = 65 млн.
    # Цена 100 млн проходит по расчётной выручке, но НЕ проходит по рыночной -> жёсткий вердикт.
    result = evaluate_land_value(
        revenue=1_000_000_000,
        total_budget=800_000_000,
        land_cost=100_000_000,
        total_interest=0,
        market_revenue=900_000_000,
    )
    assert result["verdict_code"] == "infeasible_at_market_price"
    assert result["verdict_level"] == "critical"
    assert result["max_land_price_at_market_price"] == 65_000_000
    assert "нецелесообразна при рыночной цене" in result["verdict"]


def test_market_check_not_triggered_when_land_fits_market_revenue() -> None:
    result = evaluate_land_value(
        revenue=1_000_000_000,
        total_budget=750_000_000,
        land_cost=50_000_000,
        total_interest=0,
        market_revenue=900_000_000,
    )
    # max_at_market = 900*0.85 - 700 = 65 млн > 50 млн -> остаётся feasible.
    assert result["verdict_code"] == "feasible"


def test_residual_formula_consistency() -> None:
    revenue = 1_000_000_000.0
    total_budget = 700_000_000.0
    land_cost = 50_000_000.0
    total_interest = 70_000_000.0
    result = evaluate_land_value(
        revenue=revenue,
        total_budget=total_budget,
        land_cost=land_cost,
        total_interest=total_interest,
    )
    k = total_interest / total_budget
    expected_max = revenue * (1 - 0.15) / (1 + k) - (total_budget - land_cost)
    assert result["max_land_price"] == pytest.approx(expected_max, abs=1)
    # Проверка смысла: при цене земли = max_land_price маржа после процентов = 15%.
    profit = revenue - (1 + k) * ((total_budget - land_cost) + expected_max)
    assert profit / revenue == pytest.approx(0.15, abs=0.0001)


def test_build_financial_model_includes_land_valuation() -> None:
    project_input = ProjectInput(
        project_name="Тест земля",
        city="Якутск",
        object_type="Жилой комплекс",
        object_class="comfort",
        total_area=12_000,
        sellable_area=9_000,
        floors=9,
        land_area=5_000,
        land_cost=30_000_000,
    )
    model = build_financial_model(project_input)
    land = model["land_valuation"]
    assert land["verdict_code"] in (
        "feasible",
        "borderline",
        "infeasible",
        "infeasible_target_margin",
        "infeasible_any_price",
    )
    assert "verdict" in land and land["verdict"]
    assert "max_land_price" in land
    assert any(step.get("step") == "evaluate_land_value" for step in model["trace"])
    assert any(item.get("field") == "land_target_margin" for item in model["assumptions"])
    if land["verdict_level"] == "critical":
        assert any(risk.get("code") == "land_price_infeasible" for risk in model["risks"])
