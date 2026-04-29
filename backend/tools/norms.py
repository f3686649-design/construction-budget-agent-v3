from __future__ import annotations

DEFAULT_ASSUMPTIONS = {
    "project_name": "Новый девелоперский проект",
    "city": "Не указан",
    "object_type": "Жилой комплекс",
    "object_class": "comfort",
    "land_area": 10_000.0,
    "land_cost": 0.0,
    "total_area": 12_000.0,
    "sellable_area_ratio": 0.78,
    "floors": 9,
    "construction_months": 18,
    "sales_months": 24,
    "credit_share": 0.70,
    "credit_rate": 0.18,
    "reserve": 0.05,
    "design": 0.04,
    "technical_customer": 0.025,
    "general_contractor": 0.03,
    "landscaping": 0.025,
    "external_networks": 0.07,
    "external_networks_included": False,
    "gas_only_cooking": True,
}

CMR_SPLIT = {
    "materials": 0.55,
    "works": 0.30,
    "machinery": 0.05,
    "overheads": 0.05,
    "reserve": 0.05,
}

RISK_THRESHOLDS = {
    "min_dscr": 1.20,
    "low_margin": 0.15,
    "high_credit_share": 0.75,
    "short_construction_months": 12,
    "high_cost_to_sale_ratio": 0.72,
    "minimum_reserve": 0.05,
}


def round_money(value: float) -> float:
    return round(float(value), 2)


def round_area(value: float) -> float:
    return round(float(value), 4)
