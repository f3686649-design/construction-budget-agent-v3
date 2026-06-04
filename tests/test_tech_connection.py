from __future__ import annotations

import pytest

from backend.main import build_financial_model
from backend.models import ProjectInput
from backend.tools.norms import TECH_CONNECTION_DEFAULTS
from backend.tools.tech_connection_estimator import estimate_tech_connection


def _data(**overrides) -> dict:
    base = {
        "total_area": 12_000.0,
        "sellable_area": 9_360.0,
        "construction_months": 18,
        "gas_only_cooking": True,
        "object_class": "comfort",
        "external_networks_included": True,
        "apartments_count": None,
        "tp_total_cost_override": None,
    }
    base.update(overrides)
    return base


def _budget(allocation: float = 50_000_000.0, total: float = 1_000_000_000.0) -> dict:
    return {"external_networks": allocation, "total_budget": total}


def test_loads_calculated_from_normatives() -> None:
    result = estimate_tech_connection(_data(apartments_count=200), _budget())
    norms = TECH_CONNECTION_DEFAULTS
    loads = result["loads"]
    # Электро: 200 кв × 1.5 кВт (газ) × 1.15 = 345 кВт.
    assert loads["power_kw"] == pytest.approx(200 * norms["power_kw_per_flat_gas"] * norms["power_common_area_factor"], abs=0.1)
    # Вода: 200 × 2.5 чел × 0.25 м³ = 125 м³/сут.
    assert loads["water_m3_day"] == pytest.approx(125.0, abs=0.01)
    assert loads["sewer_m3_day"] == loads["water_m3_day"]
    # Тепло: 12000 м² × 80 Вт / 1163000 = 0.8254 Гкал/ч.
    assert loads["heat_gcal_h"] == pytest.approx(12_000 * 80 / 1_163_000, abs=0.001)
    # Газ есть (газовые плиты).
    assert loads["gas_m3_h"] == pytest.approx(200 * norms["gas_m3h_per_flat"], abs=0.01)
    assert len(result["items"]) == 5


def test_electric_stoves_increase_power_and_remove_gas() -> None:
    gas = estimate_tech_connection(_data(apartments_count=200, gas_only_cooking=True), _budget())
    electric = estimate_tech_connection(_data(apartments_count=200, gas_only_cooking=False), _budget())
    assert electric["loads"]["power_kw"] > gas["loads"]["power_kw"]
    assert electric["loads"]["gas_m3_h"] == 0
    assert len(electric["items"]) == 4  # без газа


def test_apartments_estimated_when_not_given() -> None:
    result = estimate_tech_connection(_data(), _budget())
    # 9360 м² / 48 м² (comfort) = 195 квартир.
    assert result["apartments"] == 195
    assert any(a["field"] == "apartments_count" for a in result["assumption_records"])


def test_critical_when_networks_not_in_budget() -> None:
    result = estimate_tech_connection(
        _data(external_networks_included=False),
        _budget(allocation=0.0),
    )
    assert result["verdict_code"] == "critical"
    assert "не учтено в бюджете" in result["verdict"]
    assert result["deficit"] == result["total_cost"]


def test_critical_when_deficit_large() -> None:
    result = estimate_tech_connection(_data(apartments_count=200), _budget(allocation=5_000_000, total=300_000_000))
    assert result["deficit"] > 0
    assert result["verdict_code"] == "critical"
    assert "занижен" in result["verdict"] or "превышает" in result["verdict"]


def test_ok_when_allocation_covers_cost() -> None:
    result = estimate_tech_connection(_data(apartments_count=200), _budget(allocation=120_000_000))
    assert result["verdict_code"] == "ok"
    assert result["deficit"] == 0
    assert "покрывается" in result["verdict"]


def test_schedule_warning_when_construction_too_short() -> None:
    result = estimate_tech_connection(
        _data(apartments_count=200, construction_months=12),
        _budget(allocation=120_000_000),
    )
    # Вода/канализация/тепло — 18 мес > 12 мес стройки.
    assert result["schedule_issues"]
    assert result["verdict_code"] in ("warning", "critical")
    assert "под угрозой" in result["verdict"] or "заявки" in result["verdict"]


def test_override_total_cost_used() -> None:
    result = estimate_tech_connection(
        _data(apartments_count=200, tp_total_cost_override=33_000_000),
        _budget(allocation=120_000_000),
    )
    assert result["total_cost"] == 33_000_000
    assert "Ввод пользователя" in result["cost_source"]


def test_build_financial_model_includes_tech_connection() -> None:
    model = build_financial_model(
        ProjectInput(
            project_name="Тест ТУ",
            city="Якутск",
            object_type="Жилой комплекс",
            object_class="comfort",
            total_area=12_000,
            sellable_area=9_000,
            floors=9,
            land_area=5_000,
            land_cost=30_000_000,
            apartments_count=190,
        )
    )
    tech = model["tech_connection"]
    assert tech["verdict_code"] in ("ok", "warning", "critical")
    assert tech["apartments"] == 190
    assert tech["total_cost"] > 0
    assert any(step.get("step") == "estimate_tech_connection" for step in model["trace"])
    if tech["verdict_level"] == "critical":
        assert any(risk.get("code") == "tech_connection_deficit" for risk in model["risks"])
    elif tech["verdict_level"] == "warning":
        assert any(risk.get("code") == "tech_connection_warning" for risk in model["risks"])
