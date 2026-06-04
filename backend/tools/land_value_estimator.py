from __future__ import annotations

from typing import Any

from backend.tools.norms import round_money
from backend.tools.price_estimator import TARGET_MARGIN

SAFETY_THRESHOLD = 0.10

VERDICT_LEVELS = {
    "feasible": "ok",
    "borderline": "warning",
    "infeasible": "critical",
    "infeasible_target_margin": "critical",
    "infeasible_any_price": "critical",
    "infeasible_no_revenue": "critical",
    "infeasible_at_market_price": "critical",
    "reference_only": "info",
}


def evaluate_land_value(
    *,
    revenue: float,
    total_budget: float,
    land_cost: float,
    total_interest: float,
    land_area: float = 0.0,
    market_revenue: float | None = None,
    profit_after_interest: float | None = None,
    margin_after_interest: float | None = None,
    target_margin: float = TARGET_MARGIN,
    safety_threshold: float = SAFETY_THRESHOLD,
) -> dict[str, Any]:
    """Остаточный метод оценки земли.

    Максимально обоснованная цена земли — та, при которой проект сохраняет
    целевую маржу после процентов. Проценты считаются пропорциональными
    бюджету (линейное допущение): k = total_interest / total_budget.

    profit_after_interest(L) = revenue - (1 + k) * (costs_without_land + L)
    Из условия profit >= target_margin * revenue:
    max_land_price = revenue * (1 - target_margin) / (1 + k) - costs_without_land
    """
    revenue = float(revenue or 0)
    total_budget = float(total_budget or 0)
    land_cost = float(land_cost or 0)
    total_interest = float(total_interest or 0)
    land_area = float(land_area or 0)

    costs_without_land = total_budget - land_cost
    interest_ratio = (total_interest / total_budget) if total_budget > 0 else 0.0
    interest_factor = 1.0 + interest_ratio

    max_land_price = revenue * (1.0 - target_margin) / interest_factor - costs_without_land
    break_even_land_price = revenue / interest_factor - costs_without_land

    max_land_price_at_market = None
    if market_revenue is not None and market_revenue > 0:
        max_land_price_at_market = market_revenue * (1.0 - target_margin) / interest_factor - costs_without_land

    verdict_code, verdict = _resolve_verdict(
        revenue=revenue,
        land_cost=land_cost,
        max_land_price=max_land_price,
        break_even_land_price=break_even_land_price,
        target_margin=target_margin,
        safety_threshold=safety_threshold,
    )

    # Жёсткая проверка: если расчётная выручка опирается на цену продажи выше рыночной,
    # вердикт по земле должен выдерживать и рыночную цену.
    if (
        verdict_code in ("feasible", "borderline", "reference_only")
        and max_land_price_at_market is not None
        and market_revenue is not None
        and market_revenue < revenue
    ):
        if land_cost > 0 and land_cost > max_land_price_at_market:
            verdict_code = "infeasible_at_market_price"
            verdict = (
                "Покупка участка экономически нецелесообразна при рыночной цене продажи: "
                f"расчёт сходится только при выручке {_fmt(revenue)} ₽, тогда как рыночная выручка — {_fmt(market_revenue)} ₽. "
                f"Максимально обоснованная цена земли при рыночной цене: {_fmt(max(max_land_price_at_market, 0))} ₽, "
                f"запрошено {_fmt(land_cost)} ₽."
            )
        elif land_cost <= 0:
            verdict += (
                f" При рыночной цене продажи максимально обоснованная цена земли ниже: "
                f"{_fmt(max(max_land_price_at_market, 0))} ₽."
            )

    safety_reserve = None
    if land_cost > 0 and max_land_price > 0:
        safety_reserve = round((max_land_price - land_cost) / max_land_price, 4)

    result: dict[str, Any] = {
        "verdict": verdict,
        "verdict_code": verdict_code,
        "verdict_level": VERDICT_LEVELS[verdict_code],
        "max_land_price": round_money(max_land_price),
        "max_land_price_at_market_price": round_money(max_land_price_at_market) if max_land_price_at_market is not None else None,
        "break_even_land_price": round_money(break_even_land_price),
        "asking_land_price": round_money(land_cost) if land_cost > 0 else None,
        "safety_reserve": safety_reserve,
        "max_land_price_per_land_m2": round_money(max_land_price / land_area) if land_area > 0 else None,
        "land_share_of_budget": round(land_cost / total_budget, 4) if total_budget > 0 else None,
        "land_share_of_revenue": round(land_cost / revenue, 4) if revenue > 0 else None,
        "costs_without_land": round_money(costs_without_land),
        "interest_ratio": round(interest_ratio, 4),
        "target_margin": target_margin,
        "safety_threshold": safety_threshold,
        "profit_after_interest": round_money(profit_after_interest) if profit_after_interest is not None else None,
        "margin_after_interest": round(margin_after_interest, 4) if margin_after_interest is not None else None,
        "method": "Остаточный метод (residual land value)",
        "assumption_records": [
            {
                "field": "land_target_margin",
                "value": target_margin,
                "reason": "Целевая маржа девелопера после процентов для остаточной оценки земли.",
                "source": "developer_assumption",
            },
            {
                "field": "land_interest_ratio",
                "value": round(interest_ratio, 4),
                "reason": "Проценты по кредиту приняты пропорциональными бюджету проекта (линейное допущение).",
                "source": "developer_assumption",
            },
            {
                "field": "land_safety_threshold",
                "value": safety_threshold,
                "reason": "Минимальный запас прочности между ценой участка и максимально обоснованной ценой.",
                "source": "developer_assumption",
            },
        ],
        "trace": [
            {
                "step": "evaluate_land_value",
                "inputs": {
                    "revenue": round_money(revenue),
                    "market_revenue": round_money(market_revenue) if market_revenue is not None else None,
                    "total_budget": round_money(total_budget),
                    "land_cost": round_money(land_cost),
                    "total_interest": round_money(total_interest),
                    "target_margin": target_margin,
                },
                "formula": (
                    "max_land_price = revenue * (1 - target_margin) / (1 + interest_ratio) - costs_without_land; "
                    "break_even_land_price = revenue / (1 + interest_ratio) - costs_without_land"
                ),
                "output": {
                    "max_land_price": round_money(max_land_price),
                    "break_even_land_price": round_money(break_even_land_price),
                    "interest_ratio": round(interest_ratio, 4),
                    "verdict_code": verdict_code,
                    "verdict": verdict,
                },
            }
        ],
    }
    return result


def _resolve_verdict(
    *,
    revenue: float,
    land_cost: float,
    max_land_price: float,
    break_even_land_price: float,
    target_margin: float,
    safety_threshold: float,
) -> tuple[str, str]:
    margin_pct = f"{target_margin * 100:.0f}%"

    if revenue <= 0:
        return (
            "infeasible_no_revenue",
            "Проект не генерирует выручку — покупка участка экономически нецелесообразна.",
        )

    if break_even_land_price <= 0:
        return (
            "infeasible_any_price",
            (
                "Затраты проекта без земли с учётом процентов превышают выручку — "
                "покупка участка экономически нецелесообразна при любой цене. "
                "Сначала нужно снизить себестоимость или поднять цену продажи."
            ),
        )

    if max_land_price <= 0:
        return (
            "infeasible_target_margin",
            (
                f"Целевая маржа {margin_pct} недостижима даже при бесплатной земле — "
                "покупка участка экономически нецелесообразна. "
                f"Проект безубыточен только при цене земли до {_fmt(break_even_land_price)} ₽."
            ),
        )

    if land_cost <= 0:
        return (
            "reference_only",
            (
                "Цена участка не указана — оценка справочная. "
                f"Максимально обоснованная цена при целевой марже {margin_pct}: {_fmt(max_land_price)} ₽, "
                f"безубыточная: {_fmt(break_even_land_price)} ₽."
            ),
        )

    if land_cost > max_land_price:
        excess = land_cost - max_land_price
        excess_pct = excess / max_land_price * 100
        text = (
            f"Покупка участка экономически нецелесообразна: цена {_fmt(land_cost)} ₽ "
            f"превышает максимально обоснованную {_fmt(max_land_price)} ₽ "
            f"на {_fmt(excess)} ₽ ({excess_pct:.0f}%)."
        )
        if land_cost >= break_even_land_price:
            text += " При этой цене проект убыточен с учётом процентов."
        else:
            text += f" Целевая маржа {margin_pct} недостижима."
        return ("infeasible", text)

    reserve = (max_land_price - land_cost) / max_land_price
    if reserve < safety_threshold:
        return (
            "borderline",
            (
                f"Покупка участка на грани целесообразности: запас всего {reserve * 100:.1f}% "
                f"(цена {_fmt(land_cost)} ₽ при пределе {_fmt(max_land_price)} ₽). "
                "Любое удорожание строительства или снижение цены продажи сделает покупку нецелесообразной."
            ),
        )

    return (
        "feasible",
        (
            f"Покупка участка экономически целесообразна: цена {_fmt(land_cost)} ₽ "
            f"ниже максимально обоснованной {_fmt(max_land_price)} ₽, запас {reserve * 100:.1f}%."
        ),
    )


def _fmt(value: float) -> str:
    return f"{value:,.0f}".replace(",", " ")
