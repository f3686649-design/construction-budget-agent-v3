from __future__ import annotations

from typing import Any

from backend.tools.cost_estimator import estimate_construction_cost
from backend.tools.norms import round_money


def generate_budget(data: dict[str, Any]) -> dict[str, Any]:
    total_area = float(data["total_area"])
    land_cost = float(data["land_cost"])
    gp_price = float(data.get("gp_contract_price_per_m2") or 0)
    manual_construction_price = float(data.get("construction_cost_per_m2") or 0)
    cost_estimation = estimate_construction_cost(data)
    estimated_price = float(cost_estimation["estimated_cmr_cost_per_m2"])
    estimated_multiplier = float(data.get("_estimated_cost_multiplier") or 1)

    if gp_price > 0:
        construction_price = gp_price
        cmr_source = "Ручная цена генподряда"
    elif manual_construction_price > 0:
        construction_price = manual_construction_price
        cmr_source = "Ручная стоимость строительства"
    else:
        construction_price = _round_to_step(estimated_price * estimated_multiplier, 500)
        cmr_source = "Расчётная себестоимость агента"
    cmr = total_area * construction_price

    design = float(data.get("design_cost_amount") or cmr * float(data["design"]))
    technical_customer = cmr * float(data["technical_customer"])
    general_contractor = cmr * float(data["general_contractor"])
    external_networks = cmr * float(data["external_networks"]) if data["external_networks_included"] else 0.0
    landscaping = cmr * float(data["landscaping"])
    reserve = cmr * float(data["reserve"])
    total_budget = sum(
        (
            land_cost,
            cmr,
            design,
            technical_customer,
            general_contractor,
            external_networks,
            landscaping,
            reserve,
        )
    )

    items = [
        {"name": "Земля", "amount": round_money(land_cost), "formula": "Стоимость земли", "source": "Ввод пользователя или допущение"},
        {
            "name": "СМР",
            "amount": round_money(cmr),
            "formula": (
                "Общая площадь × цена генподряда за м²"
                if cmr_source == "Ручная цена генподряда"
                else "Общая площадь × стоимость строительства за м²"
            ),
            "source": cmr_source,
        },
        {
            "name": "Проектирование",
            "amount": round_money(design),
            "formula": (
                "Ручная сумма проектирования"
                if float(data.get("design_cost_override") or 0) > 0
                else "Общая площадь × 1 500 ₽/м², с ограничением до 10 млн ₽ для объектов до 10 000 м²"
            ),
            "source": "Ввод пользователя" if float(data.get("design_cost_override") or 0) > 0 else "Норматив модели",
        },
        {"name": "Технический заказчик", "amount": round_money(technical_customer), "formula": "СМР × 2.5%", "source": "Норматив модели"},
        {"name": "Генподряд", "amount": round_money(general_contractor), "formula": "СМР × 3%", "source": "Норматив модели"},
        {"name": "Наружные сети", "amount": round_money(external_networks), "formula": "СМР × 7% или 0", "source": "Норматив модели"},
        {"name": "Благоустройство", "amount": round_money(landscaping), "formula": "СМР × 2.5%", "source": "Норматив модели"},
        {"name": "Резерв", "amount": round_money(reserve), "formula": "СМР × 5%", "source": "Норматив модели"},
    ]
    budget = {
        "items": items,
        "land": round_money(land_cost),
        "cmr": round_money(cmr),
        "design": round_money(design),
        "technical_customer": round_money(technical_customer),
        "general_contractor": round_money(general_contractor),
        "external_networks": round_money(external_networks),
        "landscaping": round_money(landscaping),
        "reserve": round_money(reserve),
        "total_budget": round_money(total_budget),
        "cost_per_total_m2": round_money(total_budget / total_area if total_area else 0),
        "construction_price_per_m2": round_money(construction_price),
        "estimated_cmr_cost_per_m2": round_money(cost_estimation["estimated_cmr_cost_per_m2"]),
        "cmr_cost_source": cmr_source,
        "cmr_source": cmr_source,
        "cost_estimation_components": cost_estimation["cost_components"],
        "cost_estimation_coefficients": cost_estimation["coefficients"],
        "cost_estimation_assumptions": cost_estimation["assumptions"],
        "cost_estimation_warnings": cost_estimation["warnings"],
        "trace": [
            *cost_estimation["trace"],
            {
                "step": "generate_budget",
                "inputs": {
                    "total_area": total_area,
                    "land_cost": land_cost,
                    "construction_price_per_m2": construction_price,
                    "cmr_cost_source": cmr_source,
                    "external_networks_included": data["external_networks_included"],
                },
                "formula": "land + CMR + design + technical_customer + general_contractor + networks + landscaping + reserve",
                "output": {
                    "total_budget": round_money(total_budget),
                    "construction_price_per_m2": round_money(construction_price),
                    "cmr_cost_source": cmr_source,
                    "items": items,
                },
            }
        ],
    }
    return budget


def _round_to_step(value: float, step: int) -> float:
    return float(round(value / step) * step)
