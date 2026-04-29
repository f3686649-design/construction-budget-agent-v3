from __future__ import annotations

import math

from backend.tools.norms import round_area, round_money


def _sales_weights(months: int) -> list[float]:
    raw: list[float] = []
    for index in range(1, months + 1):
        x = index / months
        middle_peak = math.sin(math.pi * x) ** 1.4
        tail = 0.25 + 0.75 * (1 - abs(x - 0.55))
        raw.append(max(0.02, middle_peak * tail))
    total = sum(raw)
    return [value / total for value in raw]


def generate_sales_plan(
    sellable_area: float,
    sale_price_per_m2: float,
    sales_months: int,
    start_month: int = 3,
) -> list[dict[str, float]]:
    months = max(1, int(sales_months))
    weights = _sales_weights(months)
    rows: list[dict[str, float]] = []
    sold_area_total = 0.0
    revenue_total = 0.0

    for index, weight in enumerate(weights, start=1):
        area = sellable_area * weight
        if index == months:
            area = sellable_area - sold_area_total
        revenue = area * sale_price_per_m2
        sold_area_total += area
        revenue_total += revenue
        rows.append(
            {
                "month": start_month + index - 1,
                "weight": round(weight, 6),
                "sold_area": round_area(area),
                "revenue": round_money(revenue),
                "accumulated_sold_area": round_area(sold_area_total),
                "accumulated_revenue": round_money(revenue_total),
            }
        )

    revenue_drift = round_money(sellable_area * sale_price_per_m2 - sum(row["revenue"] for row in rows))
    if rows and abs(revenue_drift) >= 0.01:
        rows[-1]["revenue"] = round_money(rows[-1]["revenue"] + revenue_drift)
        rows[-1]["accumulated_revenue"] = round_money(sellable_area * sale_price_per_m2)

    return rows
