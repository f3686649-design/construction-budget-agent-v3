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

ESCROW_DEFAULTS = {
    # Ставка на часть долга, покрытую остатками на эскроу (проектное финансирование, 214-ФЗ).
    "escrow_covered_rate": 0.045,
    # Месяц ввода = конец строительства; продажи после ввода поступают напрямую.
}

TECH_CONNECTION_DEFAULTS = {
    # Нагрузки (нормативные допущения, помечаются в assumptions)
    "avg_apartment_area_by_class": {  # средняя продаваемая площадь квартиры, м²
        "standard": 42.0,
        "comfort": 48.0,
        "business": 60.0,
        "premium": 75.0,
    },
    "avg_apartment_area_default": 48.0,
    "residents_per_apartment": 2.5,
    "power_kw_per_flat_gas": 1.5,        # расчётная мощность с коэфф. одновременности, газовые плиты
    "power_kw_per_flat_electric": 2.2,   # электроплиты
    "power_common_area_factor": 1.15,    # общедомовые нагрузки (лифты, освещение, ИТП)
    "power_min_kw": 20.0,
    "water_m3_per_resident_day": 0.25,   # 250 л/сут на жителя
    "heat_w_per_m2": 80.0,               # отопление + вентиляция + ГВС, Вт/м² общей площади
    "gas_m3h_per_flat": 0.3,             # с коэфф. одновременности
    # Ставки платы за техприсоединение (региональные тарифы — ДОПУЩЕНИЯ, требуют уточнения по ТУ)
    "rate_power_per_kw": 25_000.0,         # ₽/кВт
    "rate_water_per_m3_day": 200_000.0,    # ₽/(м³/сут)
    "rate_sewer_per_m3_day": 180_000.0,    # ₽/(м³/сут)
    "rate_heat_per_gcal_h": 8_000_000.0,   # ₽/(Гкал/ч)
    "rate_gas_per_m3_h": 1_500.0,          # ₽/(м³/ч)
    "rate_gas_fixed": 150_000.0,           # фиксированная часть за подключение газа
    # Типовые сроки мероприятий по техприсоединению, месяцев от заявки
    "lead_time_months": {
        "power": 12,
        "water": 18,
        "sewer": 18,
        "heat": 18,
        "gas": 12,
    },
    # Пороги вердикта
    "deficit_critical_share_of_budget": 0.01,  # дефицит > 1% бюджета — критично
    "schedule_grace_months": 0,                # запас по срокам
}

BANK_REQUIREMENTS = {
    "min_equity_share": 0.15,        # собственное участие девелопера
    "min_margin": 0.15,              # маржа проекта по эскроу-модели
    "min_llcr": 1.25,                # Loan Life Coverage Ratio
    "min_escrow_coverage": 1.00,     # покрытие долга эскроу на вводе (warning ниже)
    "critical_escrow_coverage": 0.70,  # критично ниже
    "max_credit_share": 0.85,        # максимальная доля кредита (LTC)
    "stress_price_drop": 0.10,       # стресс: снижение цены продажи
    "stress_cost_increase": 0.10,    # стресс: удорожание строительства
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
