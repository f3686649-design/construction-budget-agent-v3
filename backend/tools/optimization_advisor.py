from __future__ import annotations

import math
from typing import Any

from backend.tools.price_estimator import TARGET_MARGIN


def advise_project_optimization(
    data: dict[str, Any],
    budget: dict[str, Any],
    economics: dict[str, Any],
) -> dict[str, Any]:
    sellable_area = float(data.get("sellable_area") or 0)
    total_area = float(data.get("total_area") or 0)
    market_price = float(economics.get("market_price_per_m2") or data.get("market_price_per_m2") or 0)
    recommended_price = float(
        economics.get("recommended_price_per_m2")
        or data.get("recommended_price_per_m2")
        or data.get("sale_price_per_m2")
        or 0
    )
    current_total_budget = float(budget.get("total_budget") or 0)
    total_interest = float(economics.get("total_interest") or 0)
    current_cmr = float(budget.get("cmr") or 0)
    current_cmr_cost_per_m2 = float(budget.get("construction_price_per_m2") or 0)
    land_cost = float(budget.get("land") or data.get("land_cost") or 0)
    target_margin = float(economics.get("target_margin") or TARGET_MARGIN)

    market_revenue = sellable_area * market_price
    target_profit = market_revenue * target_margin
    allowed_total_cost_with_interest = market_revenue - target_profit
    current_total_cost_with_interest = current_total_budget + total_interest
    required_budget_reduction = max(0.0, current_total_cost_with_interest - allowed_total_cost_with_interest)
    required_cmr_cost_per_m2 = _required_cmr_cost_per_m2(
        allowed_total_cost_with_interest=allowed_total_cost_with_interest,
        total_interest=total_interest,
        land_cost=land_cost,
        total_area=total_area,
        data=data,
    )
    required_sellable_area = (
        current_total_cost_with_interest / market_price / (1 - target_margin)
        if market_price and target_margin < 1
        else 0.0
    )
    required_sale_price = (
        current_total_cost_with_interest / sellable_area / (1 - target_margin)
        if sellable_area and target_margin < 1
        else 0.0
    )
    gap_to_market_price = max(0.0, recommended_price - market_price)

    recommendations = _build_recommendations(
        required_budget_reduction=required_budget_reduction,
        current_total_budget=current_total_budget,
        current_cmr=current_cmr,
        current_cmr_cost_per_m2=current_cmr_cost_per_m2,
        required_cmr_cost_per_m2=required_cmr_cost_per_m2,
        sellable_area=sellable_area,
        required_sellable_area=required_sellable_area,
        market_price=market_price,
        gap_to_market_price=gap_to_market_price,
    )

    return {
        "market_revenue": _round_money(market_revenue),
        "target_margin": round(target_margin, 4),
        "target_profit": _round_money(target_profit),
        "allowed_total_cost_with_interest": _round_money(allowed_total_cost_with_interest),
        "current_total_cost_with_interest": _round_money(current_total_cost_with_interest),
        "required_budget_reduction_for_market_price": _round_money(required_budget_reduction),
        "required_budget_reduction_mln_rub": round(required_budget_reduction / 1_000_000, 2),
        "required_cmr_cost_per_m2_for_market_price": _round_to_step(required_cmr_cost_per_m2, 500),
        "required_sellable_area_for_market_price": round(required_sellable_area, 4),
        "required_sale_price_for_target_margin": _ceil_to_step(required_sale_price, 1000),
        "gap_to_market_price": _round_money(gap_to_market_price),
        "most_realistic_option": recommendations["most_realistic_option"],
        "recommendations": recommendations["items"],
        "trace": [
            {
                "step": "advise_project_optimization",
                "inputs": {
                    "sellable_area": sellable_area,
                    "market_price_per_m2": market_price,
                    "recommended_price_per_m2": recommended_price,
                    "current_total_budget": current_total_budget,
                    "total_interest": total_interest,
                    "target_margin": target_margin,
                },
                "formula": "market_revenue = sellable_area * market_price; budget gap = budget + interest - market_revenue * (1 - target_margin)",
                "output": {
                    "required_budget_reduction_for_market_price": _round_money(required_budget_reduction),
                    "required_cmr_cost_per_m2_for_market_price": _round_to_step(required_cmr_cost_per_m2, 500),
                    "required_sellable_area_for_market_price": round(required_sellable_area, 4),
                    "gap_to_market_price": _round_money(gap_to_market_price),
                    "most_realistic_option": recommendations["most_realistic_option"],
                },
            }
        ],
    }


def _required_cmr_cost_per_m2(
    *,
    allowed_total_cost_with_interest: float,
    total_interest: float,
    land_cost: float,
    total_area: float,
    data: dict[str, Any],
) -> float:
    if not total_area:
        return 0.0
    cmr_multiplier = 1 + sum(
        (
            float(data.get("design") or 0),
            float(data.get("technical_customer") or 0),
            float(data.get("general_contractor") or 0),
            float(data.get("landscaping") or 0),
            float(data.get("reserve") or 0),
            float(data.get("external_networks") or 0) if data.get("external_networks_included") else 0.0,
        )
    )
    allowed_budget_without_interest = max(0.0, allowed_total_cost_with_interest - total_interest)
    required_cmr_total = max(0.0, (allowed_budget_without_interest - land_cost) / cmr_multiplier)
    return required_cmr_total / total_area


def _build_recommendations(
    *,
    required_budget_reduction: float,
    current_total_budget: float,
    current_cmr: float,
    current_cmr_cost_per_m2: float,
    required_cmr_cost_per_m2: float,
    sellable_area: float,
    required_sellable_area: float,
    market_price: float,
    gap_to_market_price: float,
) -> dict[str, Any]:
    if gap_to_market_price <= 0 and required_budget_reduction <= 0:
        return {
            "most_realistic_option": "Проект проходит по рынку",
            "items": [
                "Проект уже проходит по рыночному ориентиру при целевой марже. Отдельная оптимизация до рынка не требуется."
            ],
        }

    budget_reduction_ratio = required_budget_reduction / current_total_budget if current_total_budget else 0.0
    cmr_reduction = max(0.0, current_cmr_cost_per_m2 - required_cmr_cost_per_m2)
    cmr_reduction_ratio = cmr_reduction / current_cmr_cost_per_m2 if current_cmr_cost_per_m2 else 0.0
    sellable_area_gap = max(0.0, required_sellable_area - sellable_area)
    sellable_area_increase_ratio = sellable_area_gap / sellable_area if sellable_area else 0.0
    price_gap_ratio = gap_to_market_price / market_price if market_price else 0.0

    options = [
        ("Снижать себестоимость", cmr_reduction_ratio),
        ("Увеличивать продаваемую площадь", sellable_area_increase_ratio),
        ("Повышать цену", price_gap_ratio),
    ]
    realistic_option = min((option for option in options if option[1] > 0), key=lambda item: item[1], default=options[0])[0]

    recommendations = [
        f"Чтобы пройти по рыночной цене, нужно снизить совокупный бюджет с процентами примерно на {required_budget_reduction / 1_000_000:,.1f} млн ₽.",
        f"Ориентир по СМР: снизиться с {current_cmr_cost_per_m2:,.0f} до {required_cmr_cost_per_m2:,.0f} ₽/м².",
        f"Альтернатива по продукту: увеличить продаваемую площадь до {required_sellable_area:,.0f} м².",
        f"Альтернатива по цене: продавать по цене для целевой маржи, то есть около {_ceil_to_step((market_price + gap_to_market_price), 1000):,.0f} ₽/м².",
        f"Самый реалистичный первый рычаг по размеру разрыва: {realistic_option.lower()}.",
    ]
    if current_cmr and budget_reduction_ratio > 0.12:
        recommendations.append("Разрыв значительный: одной оптимизации бюджета может быть мало, лучше комбинировать себестоимость, квартирографию и цену.")
    return {"most_realistic_option": realistic_option, "items": recommendations}


def _round_money(value: float) -> float:
    return round(float(value), 2)


def _round_to_step(value: float, step: int) -> float:
    return float(round(float(value) / step) * step)


def _ceil_to_step(value: float, step: int) -> float:
    return float(math.ceil(float(value) / step) * step)
