from __future__ import annotations

from typing import Any

from backend.tools.norms import TECH_CONNECTION_DEFAULTS, round_money

RESOURCE_NAMES = {
    "power": "Электроснабжение",
    "water": "Водоснабжение",
    "sewer": "Водоотведение",
    "heat": "Теплоснабжение",
    "gas": "Газоснабжение",
}

VERDICT_LEVELS = {
    "ok": "ok",
    "warning": "warning",
    "critical": "critical",
}


def estimate_tech_connection(
    data: dict[str, Any],
    budget: dict[str, Any],
) -> dict[str, Any]:
    """Модуль технического присоединения (ТУ).

    Считает нагрузки по нормативам от параметров проекта, оценивает плату за
    техприсоединение по региональным ставкам (допущения — требуют уточнения по
    фактическим ТУ), сверяет с заложенной в бюджете статьёй «Наружные сети» и
    проверяет, вписываются ли типовые сроки мероприятий ТП в срок стройки.
    Бюджет не подгоняется: дефицит показывается прямо.
    """
    norms = TECH_CONNECTION_DEFAULTS
    assumptions: list[dict[str, Any]] = []

    total_area = float(data.get("total_area") or 0)
    sellable_area = float(data.get("sellable_area") or 0)
    construction_months = int(data.get("construction_months") or 0)
    gas_cooking = bool(data.get("gas_only_cooking"))
    object_class = str(data.get("object_class") or "").lower()

    # Количество квартир: ввод пользователя или оценка по средней площади класса.
    apartments_input = data.get("apartments_count")
    avg_area = norms["avg_apartment_area_by_class"].get(
        object_class, norms["avg_apartment_area_default"]
    )
    if apartments_input:
        apartments = int(apartments_input)
        apartments_source = "Ввод пользователя"
    else:
        apartments = max(1, round(sellable_area / avg_area)) if sellable_area else 1
        apartments_source = f"Оценка: продаваемая площадь / {avg_area} м²"
        assumptions.append(
            {
                "field": "apartments_count",
                "value": apartments,
                "reason": f"Количество квартир оценено по средней площади {avg_area} м² для класса «{object_class or 'comfort'}».",
                "source": "developer_assumption",
            }
        )

    residents = apartments * norms["residents_per_apartment"]

    # Нагрузки.
    power_per_flat = (
        norms["power_kw_per_flat_gas"] if gas_cooking else norms["power_kw_per_flat_electric"]
    )
    power_kw = max(
        norms["power_min_kw"],
        apartments * power_per_flat * norms["power_common_area_factor"],
    )
    water_m3_day = residents * norms["water_m3_per_resident_day"]
    sewer_m3_day = water_m3_day
    heat_gcal_h = total_area * norms["heat_w_per_m2"] / 1_163_000.0
    gas_m3_h = apartments * norms["gas_m3h_per_flat"] if gas_cooking else 0.0

    # Стоимость по ресурсам.
    items: list[dict[str, Any]] = []
    lead_times = norms["lead_time_months"]

    def add_item(code: str, load: float, unit: str, rate: float, cost: float, basis: str) -> None:
        lead = int(lead_times.get(code, 12))
        deadline_ok = construction_months >= lead if construction_months else False
        items.append(
            {
                "code": code,
                "resource": RESOURCE_NAMES[code],
                "load": round(load, 3),
                "unit": unit,
                "rate": round_money(rate),
                "cost": round_money(cost),
                "basis": basis,
                "lead_time_months": lead,
                "deadline_ok": deadline_ok,
            }
        )

    add_item(
        "power",
        power_kw,
        "кВт",
        norms["rate_power_per_kw"],
        power_kw * norms["rate_power_per_kw"],
        f"{apartments} кв. × {power_per_flat} кВт × {norms['power_common_area_factor']} (МОП)",
    )
    add_item(
        "water",
        water_m3_day,
        "м³/сут",
        norms["rate_water_per_m3_day"],
        water_m3_day * norms["rate_water_per_m3_day"],
        f"{residents:.0f} жителей × {norms['water_m3_per_resident_day'] * 1000:.0f} л/сут",
    )
    add_item(
        "sewer",
        sewer_m3_day,
        "м³/сут",
        norms["rate_sewer_per_m3_day"],
        sewer_m3_day * norms["rate_sewer_per_m3_day"],
        "Водоотведение = водопотребление",
    )
    add_item(
        "heat",
        heat_gcal_h,
        "Гкал/ч",
        norms["rate_heat_per_gcal_h"],
        heat_gcal_h * norms["rate_heat_per_gcal_h"],
        f"{total_area:.0f} м² × {norms['heat_w_per_m2']:.0f} Вт/м²",
    )
    if gas_cooking:
        add_item(
            "gas",
            gas_m3_h,
            "м³/ч",
            norms["rate_gas_per_m3_h"],
            norms["rate_gas_fixed"] + gas_m3_h * norms["rate_gas_per_m3_h"],
            f"{apartments} кв. × {norms['gas_m3h_per_flat']} м³/ч + фикс {norms['rate_gas_fixed']:.0f} ₽",
        )

    calculated_cost = sum(float(item["cost"]) for item in items)

    # Override: девелопер знает фактическую плату по ТУ.
    override = data.get("tp_total_cost_override")
    if override and float(override) > 0:
        total_cost = float(override)
        cost_source = "Ввод пользователя (фактические ТУ)"
    else:
        total_cost = calculated_cost
        cost_source = "Расчёт по нормативным ставкам (требует уточнения по фактическим ТУ)"
        assumptions.append(
            {
                "field": "tp_total_cost",
                "value": round_money(total_cost),
                "reason": "Плата за техприсоединение рассчитана по усреднённым региональным ставкам — обязательно уточнить по фактическим ТУ ресурсоснабжающих организаций.",
                "source": "developer_assumption",
            }
        )

    # Сверка с бюджетом: статья «Наружные сети».
    budget_allocation = float(budget.get("external_networks") or 0)
    total_budget = float(budget.get("total_budget") or 0)
    deficit = max(0.0, total_cost - budget_allocation)
    networks_included = bool(data.get("external_networks_included"))

    # Сроки.
    schedule_issues = [item for item in items if not item["deadline_ok"]]
    max_lead = max((item["lead_time_months"] for item in items), default=0)

    # Вердикт.
    deficit_share = deficit / total_budget if total_budget else 0.0
    if not networks_included or budget_allocation <= 0:
        verdict_code = "critical"
        verdict = (
            f"Техприсоединение не учтено в бюджете: статья «Наружные сети» пуста, "
            f"а расчётная плата за ТП — {_fmt(total_cost)} ₽. Эти затраты неизбежны для МКД."
        )
    elif deficit > 0 and deficit_share > norms["deficit_critical_share_of_budget"]:
        verdict_code = "critical"
        verdict = (
            f"Плата за техприсоединение {_fmt(total_cost)} ₽ превышает заложенную статью "
            f"«Наружные сети» {_fmt(budget_allocation)} ₽ на {_fmt(deficit)} ₽ "
            f"({deficit_share:.1%} бюджета). Бюджет занижен."
        )
    elif deficit > 0:
        verdict_code = "warning"
        verdict = (
            f"Плата за ТП {_fmt(total_cost)} ₽ немного превышает статью «Наружные сети» "
            f"{_fmt(budget_allocation)} ₽ (дефицит {_fmt(deficit)} ₽). Запаса на прокладку сетей нет."
        )
    else:
        share_of_allocation = total_cost / budget_allocation if budget_allocation else 0.0
        verdict_code = "ok"
        verdict = (
            f"Плата за ТП {_fmt(total_cost)} ₽ покрывается статьёй «Наружные сети» "
            f"({share_of_allocation:.0%} от {_fmt(budget_allocation)} ₽); "
            f"на прокладку сетей остаётся {_fmt(budget_allocation - total_cost)} ₽."
        )

    if schedule_issues:
        names = ", ".join(f"{item['resource']} ({item['lead_time_months']} мес)" for item in schedule_issues)
        verdict += (
            f" Сроки мероприятий ТП превышают срок стройки {construction_months} мес: {names} — "
            "заявки на ТУ нужно подавать до старта стройки, иначе ввод под угрозой."
        )
        if verdict_code == "ok":
            verdict_code = "warning"

    return {
        "verdict": verdict,
        "verdict_code": verdict_code,
        "verdict_level": VERDICT_LEVELS[verdict_code],
        "items": items,
        "apartments": apartments,
        "apartments_source": apartments_source,
        "residents": round(residents, 1),
        "loads": {
            "power_kw": round(power_kw, 1),
            "water_m3_day": round(water_m3_day, 2),
            "sewer_m3_day": round(sewer_m3_day, 2),
            "heat_gcal_h": round(heat_gcal_h, 4),
            "gas_m3_h": round(gas_m3_h, 2),
        },
        "calculated_cost": round_money(calculated_cost),
        "total_cost": round_money(total_cost),
        "cost_source": cost_source,
        "budget_allocation": round_money(budget_allocation),
        "networks_included_in_budget": networks_included,
        "deficit": round_money(deficit),
        "deficit_share_of_budget": round(deficit_share, 4),
        "max_lead_time_months": max_lead,
        "construction_months": construction_months,
        "schedule_issues": [item["code"] for item in schedule_issues],
        "assumption_records": assumptions,
        "trace": [
            {
                "step": "estimate_tech_connection",
                "inputs": {
                    "apartments": apartments,
                    "total_area": total_area,
                    "gas_only_cooking": gas_cooking,
                    "construction_months": construction_months,
                    "budget_allocation": round_money(budget_allocation),
                },
                "formula": (
                    "Нагрузки по нормативам (кВт/кв, л/сут/чел, Вт/м²) × региональные ставки платы за ТП; "
                    "сверка с статьёй «Наружные сети»; сроки мероприятий vs срок стройки."
                ),
                "output": {
                    "total_cost": round_money(total_cost),
                    "deficit": round_money(deficit),
                    "verdict_code": verdict_code,
                    "loads": {
                        "power_kw": round(power_kw, 1),
                        "water_m3_day": round(water_m3_day, 2),
                        "heat_gcal_h": round(heat_gcal_h, 4),
                        "gas_m3_h": round(gas_m3_h, 2),
                    },
                },
            }
        ],
    }


def _fmt(value: float) -> str:
    return f"{value:,.0f}".replace(",", " ")
