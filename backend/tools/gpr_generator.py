from __future__ import annotations

import math

from backend.tools.norms import round_money


def _s_curve_weights(months: int) -> list[float]:
    raw: list[float] = []
    for month in range(1, months + 1):
        position = (month - 0.5) / months
        bell = math.sin(math.pi * position) ** 1.7
        ramp = 0.35 + 0.9 * position
        raw.append(max(0.01, bell * ramp))
    total = sum(raw)
    return [value / total for value in raw]


def generate_gpr(total_budget: float, land_cost: float, construction_months: int) -> list[dict[str, float]]:
    months = max(1, int(construction_months))
    weights = _s_curve_weights(months)
    non_land_budget = max(0.0, total_budget - land_cost)
    rows: list[dict[str, float]] = []
    accumulated = 0.0
    accumulated_construction = 0.0

    for index, weight in enumerate(weights, start=1):
        construction_amount = non_land_budget * weight
        if index == months:
            construction_amount = non_land_budget - accumulated_construction
        land_payment = land_cost if index == 1 else 0.0
        amount = construction_amount + land_payment
        accumulated += amount
        accumulated_construction += construction_amount
        rows.append(
            {
                "month": index,
                "weight": round(weight, 6),
                "construction_cost": round_money(construction_amount),
                "land_payment": round_money(land_payment),
                "amount": round_money(amount),
                "accumulated": round_money(accumulated),
            }
        )

    drift = round_money(total_budget - sum(row["amount"] for row in rows))
    if rows and abs(drift) >= 0.01:
        rows[-1]["amount"] = round_money(rows[-1]["amount"] + drift)
        rows[-1]["construction_cost"] = round_money(rows[-1]["construction_cost"] + drift)
        rows[-1]["accumulated"] = round_money(total_budget)

    return rows
