from __future__ import annotations

from datetime import date
from typing import Any

from backend.tools.norms import round_money
from backend.tools.rate_catalog import RATE_CATALOG


START_DATE = date(2026, 1, 1)
ABOVE_GROUND_NORMATIVE_RATE = 23_120
ABOVE_GROUND_PILE_NO_UNDERGROUND_RATE = 19_500
ENVELOPE_NORMATIVE_RATE = 11_560
ENVELOPE_ECONOMY_COMFORT_RATE = 8_500
EARTHWORKS_PILE_NO_UNDERGROUND_RATE = 800
EARTHWORKS_UNDERGROUND_RATE = 3_000
EARTHWORKS_BASE_RATE = 1_800
DESIGN_RATE = 1_500
DESIGN_CAP_AREA = 12_000
DESIGN_CAP_AMOUNT = 10_000_000


def generate_detailed_budget(data: dict[str, Any], budget: dict[str, Any], economics: dict[str, Any] | None = None) -> dict[str, Any]:
    economics = economics or {}
    grouped = _catalog_by_source()
    cmr_core_total = _calculate_cmr_core_total(data)
    source_totals = {
        "land": float(budget.get("land") or data.get("land_cost") or 0),
        "cmr": cmr_core_total,
        "external_networks": cmr_core_total * float(data.get("external_networks") or 0)
        if bool(data.get("external_networks_included"))
        else 0.0,
        "landscaping": cmr_core_total * float(data.get("landscaping") or 0),
        "design": float(data.get("design_cost_amount") or budget.get("design") or 0),
        "technical_customer": cmr_core_total * float(data.get("technical_customer") or 0),
        "general_contractor": cmr_core_total * float(data.get("general_contractor") or 0),
        "marketing": 0.0,
        "reserve": cmr_core_total * float(data.get("reserve") or 0),
        "revenue": float(economics.get("revenue") or 0),
    }
    items: list[dict[str, Any]] = []

    for source, entries in grouped.items():
        for entry in entries:
            amount = _amount_for_entry(entry, source_totals, data, budget, economics)
            row = _build_row(_effective_entry(entry, data), amount, data, budget, economics)
            items.append(row)

    items.sort(key=lambda row: _sort_code(str(row["Код"])))
    total_budget = round_money(sum(row["Сумма"] for row in items))
    chapter_totals = _chapter_totals(items)
    split_totals = {
        "materials": round_money(sum(row["Материалы, ₽"] for row in items)),
        "works": round_money(sum(row["Работы, ₽"] for row in items)),
        "machinery": round_money(sum(row["Механизмы, ₽"] for row in items)),
        "overheads": round_money(sum(row["Накладные, ₽"] for row in items)),
    }
    budget_adjustments = _budget_adjustments(items, data)
    return {
        "items": items,
        "chapter_totals": chapter_totals,
        "split_totals": split_totals,
        "budget_adjustments": budget_adjustments,
        "total_budget": total_budget,
        "trace": [
            {
                "step": "generate_detailed_budget",
                "inputs": {"base_budget_total": budget["total_budget"], "items_count": len(items)},
                "formula": "Detailed line items are calculated directly from rates and amounts; no residual redistribution to old total_budget.",
                "output": {
                    "total_budget": total_budget,
                    "chapter_totals": chapter_totals,
                    "split_totals": split_totals,
                    "budget_adjustments": budget_adjustments,
                    "base_budget_total": budget["total_budget"],
                },
            }
        ],
    }


def apply_detailed_budget_to_budget(data: dict[str, Any], budget: dict[str, Any], detailed_budget: dict[str, Any]) -> dict[str, Any]:
    totals = _source_totals_from_items(detailed_budget["items"])
    total_area = float(data.get("total_area") or 0)
    total_budget = round_money(float(detailed_budget["total_budget"]))
    updated = dict(budget)
    updated["base_total_budget"] = budget.get("total_budget")
    updated.update(
        {
            "land": round_money(totals.get("land", 0)),
            "cmr": round_money(totals.get("cmr", 0)),
            "external_networks": round_money(totals.get("external_networks", 0)),
            "landscaping": round_money(totals.get("landscaping", 0)),
            "design": round_money(totals.get("design", 0)),
            "technical_customer": round_money(totals.get("technical_customer", 0)),
            "general_contractor": round_money(totals.get("general_contractor", 0)),
            "reserve": round_money(totals.get("reserve", 0)),
            "total_budget": total_budget,
            "cost_per_total_m2": round_money(total_budget / total_area if total_area else 0),
            "construction_price_per_m2": round_money(totals.get("cmr", 0) / total_area if total_area else 0),
            "budget_source": "Детальный бюджет по статьям",
        }
    )
    updated["items"] = _summary_budget_items_from_detail(updated)

    engineering_total = _engineering_total(detailed_budget["items"])
    pile_item = _item_by_code(detailed_budget["items"], "2.3")
    underground_item = _item_by_code(detailed_budget["items"], "2.4")
    data["pile_foundation_amount"] = round_money(float(pile_item.get("Сумма") or 0))
    data["pile_foundation_rate"] = round_money(float(pile_item.get("Ставка") or 0))
    data["underground_part_amount"] = round_money(float(underground_item.get("Сумма") or 0))
    data["engineering_systems_amount"] = engineering_total
    data["engineering_systems_share_of_cmr"] = round(engineering_total / float(updated["cmr"]), 4) if updated["cmr"] else 0.0
    data["adjusted_total_budget"] = total_budget
    return updated


def generate_work_schedule(
    data: dict[str, Any],
    budget: dict[str, Any],
    detailed_budget: dict[str, Any],
) -> dict[str, Any]:
    months = max(1, int(data.get("construction_months") or 1))
    item_amounts = {row["Статья"]: float(row["Сумма"]) for row in detailed_budget["items"]}
    chapter_totals = {str(row["Глава"]): float(row["Сумма"]) for row in detailed_budget["chapter_totals"]}
    stages_config = [
        ("Подготовительный период", 0.01, 0.10, _sum_items(item_amounts, "Подготовительный период")),
        ("Земляные работы", 0.08, 0.10, _sum_items(item_amounts, "Земляные работы")),
        (
            "Фундамент / сваи / котлован",
            0.12,
            0.15,
            _sum_items(
                item_amounts,
                "Фундаментная плита / свайное основание / ограждение котлована",
                "Свайное основание / ростверк",
            ),
        ),
        ("Подземная часть", 0.18, 0.15, _sum_items(item_amounts, "Устройство несущих конструкций подземной части")),
        ("Надземная часть", 0.25, 0.45, _sum_items(item_amounts, "Устройство несущих конструкций надземной части")),
        (
            "Фасады / кровля / проемы",
            0.50,
            0.30,
            _sum_items(
                item_amounts,
                "Ограждающие конструкции / внутренние стены / кровля",
                "Наружная отделка / заполнение проемов",
            ),
        ),
        (
            "Инженерные системы",
            0.45,
            0.40,
            _sum_items(
                item_amounts,
                "Вертикальный транспорт",
                "Сантехнические системы",
                "Отопление / ИТП / узел учета",
                "Электроснабжение",
                "Слаботочные системы",
                "Вентиляция / дымоудаление",
            ),
        ),
        (
            "Отделка МОП / техпомещений",
            0.60,
            0.30,
            _sum_items(item_amounts, "Внутренняя отделка МОП и техпомещений", "Отделка реализуемых площадей"),
        ),
        ("Наружные сети", 0.65, 0.20, _sum_items(item_amounts, "Наружные сети")),
        ("Благоустройство", 0.80, 0.15, _sum_items(item_amounts, "Благоустройство")),
        (
            "Заказчик / проектирование / резервы",
            0.01,
            1.00,
            chapter_totals.get("1", 0.0) + chapter_totals.get("3", 0.0),
        ),
    ]
    stages: list[dict[str, Any]] = []
    month_totals = [0.0 for _ in range(months)]
    for name, start_fraction, duration_fraction, amount in stages_config:
        start_month, duration, end_month = _stage_timing(months, start_fraction, duration_fraction)
        monthly = [0.0 for _ in range(months)]
        if amount > 0:
            active_months = range(start_month, end_month + 1)
            per_month = amount / duration
            allocated = 0.0
            for index, month in enumerate(active_months, start=1):
                value = per_month if index < duration else amount - allocated
                monthly[month - 1] = round_money(value)
                month_totals[month - 1] += value
                allocated += value
        stages.append(
            {
                "Этап": name,
                "Начало, мес.": start_month,
                "Длительность, мес.": duration,
                "Окончание, мес.": end_month,
                "Стоимость": round_money(amount),
                "monthly_amounts": monthly,
            }
        )

    total_budget = float(budget["total_budget"])
    rounded_month_totals = [round_money(value) for value in month_totals]
    drift = round_money(total_budget - sum(rounded_month_totals))
    if rounded_month_totals and abs(drift) >= 0.01:
        rounded_month_totals[-1] = round_money(rounded_month_totals[-1] + drift)
    cumulative = []
    running = 0.0
    for value in rounded_month_totals:
        running = round_money(running + value)
        cumulative.append(running)
    readiness = [round(value / total_budget if total_budget else 0, 4) for value in cumulative]
    peak_capex = max(rounded_month_totals) if rounded_month_totals else 0
    peak_month = rounded_month_totals.index(peak_capex) + 1 if rounded_month_totals else 0
    main_work_end_month = max((stage["Окончание, мес."] for stage in stages if stage["Стоимость"] > 0), default=months)
    summary = {
        "construction_months": months,
        "peak_capex_month": peak_month,
        "peak_capex": round_money(peak_capex),
        "average_monthly_capex": round_money(total_budget / months if months else 0),
        "main_work_end_month": main_work_end_month,
        "start_date": START_DATE,
        "end_date": _add_months(START_DATE, months - 1),
        "is_short_schedule": months < 12,
    }
    return {
        "stages": stages,
        "month_totals": rounded_month_totals,
        "cumulative_capex": cumulative,
        "readiness": readiness,
        "summary": summary,
        "trace": [
            {
                "step": "generate_work_schedule",
                "inputs": {"construction_months": months, "total_budget": total_budget},
                "formula": "Detailed budget items mapped to ModDEV-like construction stages and spread across active months.",
                "output": {"peak_month": peak_month, "main_work_end_month": main_work_end_month},
            }
        ],
    }


def generate_supply_plan(
    data: dict[str, Any],
    detailed_budget: dict[str, Any],
    work_schedule: dict[str, Any],
) -> list[dict[str, Any]]:
    months = int(work_schedule["summary"]["construction_months"])
    total_area = float(data.get("total_area") or 0)
    city = str(data.get("city") or "").lower().replace("ё", "е")
    item_amounts = {row["Статья"]: float(row["Сумма"]) for row in detailed_budget["items"]}
    facade_total = _sum_items(
        item_amounts,
        "Ограждающие конструкции / внутренние стены / кровля",
        "Наружная отделка / заполнение проемов",
    )
    engineering_total = _sum_items(
        item_amounts,
        "Вертикальный транспорт",
        "Сантехнические системы",
        "Отопление / ИТП / узел учета",
        "Электроснабжение",
        "Слаботочные системы",
        "Вентиляция / дымоудаление",
    )
    structural_stage_names = {"Фундамент / сваи / котлован", "Подземная часть", "Надземная часть"}
    facade_stage = _stage_by_name(work_schedule, "Фасады / кровля / проемы")
    engineering_stage = _stage_by_name(work_schedule, "Инженерные системы")
    structural_month_amounts = [0.0 for _ in range(months)]
    for stage in work_schedule["stages"]:
        if stage["Этап"] in structural_stage_names:
            for index, value in enumerate(stage["monthly_amounts"]):
                structural_month_amounts[index] += float(value or 0)
    structural_total = sum(structural_month_amounts)
    total_concrete = total_area * 0.42
    total_rebar = total_area * 0.055
    rows: list[dict[str, Any]] = []
    for month in range(1, months + 1):
        need_date = _add_months(START_DATE, month - 1)
        structural_share = structural_month_amounts[month - 1] / structural_total if structural_total else 0
        facade_value = _stage_month_value(facade_stage, month, facade_total)
        engineering_value = _stage_month_value(engineering_stage, month, engineering_total)
        comment = "Проверить срок логистики по региону" if "якут" in city else ""
        rows.append(
            {
                "Месяц": month,
                "Дата потребности": need_date,
                "Бетон, м3": round(total_concrete * structural_share, 2),
                "Арматура, т": round(total_rebar * structural_share, 2),
                "Фасадные материалы, ₽": round_money(facade_value),
                "Инженерное оборудование, ₽": round_money(engineering_value),
                "Дата заказа бетона": _add_months(need_date, -1),
                "Дата заказа арматуры": _add_months(need_date, -2),
                "Дата заказа фасада": _add_months(need_date, -2),
                "Комментарий": comment,
            }
        )
    return rows


def _catalog_by_source() -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for entry in RATE_CATALOG:
        grouped.setdefault(str(entry["источник"]), []).append(entry)
    return grouped


def _allocate(total: float, shares: list[float]) -> list[float]:
    if not shares:
        return []
    normalized_total = sum(shares)
    if normalized_total <= 0:
        shares = [1 / len(shares) for _ in shares]
        normalized_total = 1
    allocated: list[float] = []
    accumulated = 0.0
    for index, share in enumerate(shares, start=1):
        if index == len(shares):
            amount = round_money(total - accumulated)
        else:
            amount = round_money(total * share / normalized_total)
            accumulated += amount
        allocated.append(amount)
    return allocated


def _amount_for_entry(
    entry: dict[str, Any],
    source_totals: dict[str, float],
    data: dict[str, Any],
    budget: dict[str, Any],
    economics: dict[str, Any],
) -> float:
    code = str(entry["код"])
    source = str(entry["источник"])
    if source == "cmr":
        return _cmr_entry_amount(code, data)
    total = source_totals.get(source, 0.0)
    share = float(entry.get("доля источника") or 1)
    return round_money(total * share)


def _calculate_cmr_core_total(data: dict[str, Any]) -> float:
    return round_money(sum(_cmr_entry_amount(str(entry["код"]), data) for entry in RATE_CATALOG if entry["источник"] == "cmr"))


def _cmr_entry_amount(code: str, data: dict[str, Any]) -> float:
    total_area = float(data.get("total_area") or 0)
    rates = {
        "2.7": 3_500,
        "2.9": 7_000,
        "2.10": 2_500,
        "2.11": _engineering_rate(data, "plumbing_rate_override", 4_200),
        "2.12": _engineering_rate(data, "heating_rate_override", 5_200),
        "2.13": _engineering_rate(data, "electrical_rate_override", 4_600),
        "2.14": _engineering_rate(data, "low_voltage_rate_override", 1_500),
        "2.15": _engineering_rate(data, "ventilation_rate_override", 2_500),
    }
    if code == "2.1":
        amount = _preparation_amount(data)
    elif code == "2.2":
        amount = _earthworks_amount(data)
    elif code == "2.3":
        amount = _foundation_amount(data)
    elif code == "2.4":
        amount = 0.0 if not bool(data.get("has_underground_part")) else round_money(total_area * 12_000)
    elif code == "2.5":
        amount = _above_ground_structures_amount(data)
    elif code == "2.6":
        amount = _envelope_roof_walls_amount(data)
    elif code == "2.8":
        amount = _sellable_finish_amount(data)
    else:
        amount = round_money(total_area * rates.get(code, float(_catalog_rate(code) or 0)))
    if code.startswith("2.") and code != "2.4":
        amount = round_money(amount * _detailed_cost_multiplier(data))
    return amount


def _effective_entry(entry: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    effective = dict(entry)
    code = str(entry["код"])
    foundation_type = _normalize(data.get("foundation_type"))
    has_underground = bool(data.get("has_underground_part"))
    finish_level = _normalize(data.get("sellable_finish_level"))
    object_class = _normalize(data.get("object_class"))
    if code == "2.1":
        effective["нормативная ставка"] = 750
        effective["источник значения"] = "ручная корректировка" if float(data.get("preparation_cost_override") or 0) > 0 else "норматив"
        if float(data.get("preparation_cost_override") or 0) > 0:
            effective["примечание"] = "Ручная сумма подготовительных работ имеет приоритет над нормативом 750 ₽/м²."
    if code == "2.2":
        earthworks_rate = _earthworks_rate(data)
        effective["ставка"] = earthworks_rate
        effective["нормативная ставка"] = EARTHWORKS_UNDERGROUND_RATE if has_underground else EARTHWORKS_BASE_RATE
        effective["источник значения"] = _source_label(
            float(data.get("earthworks_rate_override") or 0) > 0,
            foundation_type == "сваи" and not has_underground,
        )
        if float(data.get("earthworks_rate_override") or 0) > 0:
            effective["примечание"] = "Ручная ставка земляных работ имеет приоритет над нормативом."
        elif foundation_type == "сваи" and not has_underground:
            effective["примечание"] = "Сниженный объём земляных работ: свайный фундамент, подземная часть отсутствует."
    if code == "2.3" and foundation_type == "сваи":
        manual = _foundation_manual_mode(data)
        effective["статья"] = "Свайное основание / ростверк"
        effective["ставка"] = _foundation_rate(data)
        effective["нормативная ставка"] = 6_500
        effective["примечание"] = "Свайный фундамент без подземной части. Котлован, плита и подземный конструктив не предусмотрены."
        effective["источник значения"] = manual or _foundation_source(data)
    if code == "2.4" and not has_underground:
        effective["примечание"] = "Не предусмотрено: подземная часть отсутствует."
        effective["источник значения"] = "технологическая корректировка"
    if code == "2.5":
        manual = float(data.get("above_ground_structures_rate_override") or 0) > 0
        technology_adjusted = foundation_type == "сваи" and not has_underground
        effective["ставка"] = _above_ground_structures_rate(data)
        effective["нормативная ставка"] = ABOVE_GROUND_NORMATIVE_RATE
        effective["источник значения"] = _source_label(manual, technology_adjusted)
        if manual:
            effective["примечание"] = "Ручная ставка надземных несущих конструкций имеет приоритет над нормативом."
        elif technology_adjusted:
            effective["примечание"] = "Скорректировано: типовой надземный конструктив для объекта на сваях без подземной части."
    if code == "2.6":
        manual = float(data.get("envelope_roof_walls_rate_override") or 0) > 0
        technology_adjusted = object_class in {"эконом", "economy", "комфорт", "comfort"}
        effective["ставка"] = _envelope_roof_walls_rate(data)
        effective["нормативная ставка"] = ENVELOPE_NORMATIVE_RATE
        effective["источник значения"] = _source_label(manual, technology_adjusted)
        if manual:
            effective["примечание"] = "Ручная ставка ограждающих конструкций / стен / кровли имеет приоритет над нормативом."
        elif technology_adjusted:
            effective["примечание"] = "Скорректировано: эконом/комфорт класс, без повышенной отделки ограждающих конструкций."
    if code == "2.8":
        effective["ставка"] = _finish_rate(finish_level)
        effective["примечание"] = f"Отделка реализуемых помещений: {data.get('sellable_finish_level') or 'черновая'}."
        effective["источник значения"] = "технологическая корректировка"
    if code in {"2.11", "2.12", "2.13", "2.14", "2.15"}:
        override_by_code = {
            "2.11": ("plumbing_rate_override", 4_200, "Сантехнические системы рассчитаны по оптимизированному нормативу или ручной ставке."),
            "2.12": ("heating_rate_override", 5_200, "Отопление / ИТП / узел учета рассчитаны по оптимизированному нормативу или ручной ставке."),
            "2.13": ("electrical_rate_override", 4_600, "Электроснабжение рассчитано по оптимизированному нормативу или ручной ставке."),
            "2.14": ("low_voltage_rate_override", 1_500, "Слаботочные системы рассчитаны по оптимизированному нормативу или ручной ставке."),
            "2.15": ("ventilation_rate_override", 2_500, "Вентиляция / дымоудаление рассчитаны по оптимизированному нормативу или ручной ставке."),
        }
        override_field, default_rate, note = override_by_code[code]
        manual = float(data.get(override_field) or 0) > 0
        effective["ставка"] = _engineering_rate(data, override_field, default_rate)
        effective["нормативная ставка"] = default_rate
        effective["примечание"] = note
        effective["источник значения"] = "ручная корректировка" if manual else "оптимизированный норматив"
    if code == "3.1":
        effective["нормативная ставка"] = DESIGN_RATE
        if float(data.get("design_cost_override") or 0) > 0:
            effective["источник значения"] = "ручная корректировка"
            effective["примечание"] = "Ручная сумма проектирования имеет приоритет над нормативным расчётом."
        elif float(data.get("total_area") or 0) <= DESIGN_CAP_AREA:
            effective["источник значения"] = "технологическая корректировка"
            effective["примечание"] = "Проектирование ограничено ориентиром 10 млн ₽ для объекта до 12 000 м²."
        else:
            effective["источник значения"] = "норматив"
    return effective


def _preparation_amount(data: dict[str, Any]) -> float:
    override = float(data.get("preparation_cost_override") or 0)
    if override > 0:
        return round_money(override)
    return round_money(float(data.get("total_area") or 0) * 750)


def _earthworks_amount(data: dict[str, Any]) -> float:
    total_area = float(data.get("total_area") or 0)
    return round_money(total_area * _earthworks_rate(data))


def _earthworks_rate(data: dict[str, Any]) -> float:
    override = float(data.get("earthworks_rate_override") or 0)
    if override > 0:
        return override
    if _normalize(data.get("foundation_type")) == "сваи" and not bool(data.get("has_underground_part")):
        return EARTHWORKS_PILE_NO_UNDERGROUND_RATE
    if bool(data.get("has_underground_part")):
        return EARTHWORKS_UNDERGROUND_RATE
    return EARTHWORKS_BASE_RATE


def _above_ground_structures_amount(data: dict[str, Any]) -> float:
    return round_money(float(data.get("total_area") or 0) * _above_ground_structures_rate(data))


def _above_ground_structures_rate(data: dict[str, Any]) -> float:
    override = float(data.get("above_ground_structures_rate_override") or 0)
    if override > 0:
        return override
    if _normalize(data.get("foundation_type")) == "сваи" and not bool(data.get("has_underground_part")):
        return ABOVE_GROUND_PILE_NO_UNDERGROUND_RATE
    return ABOVE_GROUND_NORMATIVE_RATE


def _envelope_roof_walls_amount(data: dict[str, Any]) -> float:
    return round_money(float(data.get("total_area") or 0) * _envelope_roof_walls_rate(data))


def _envelope_roof_walls_rate(data: dict[str, Any]) -> float:
    override = float(data.get("envelope_roof_walls_rate_override") or 0)
    if override > 0:
        return override
    if _normalize(data.get("object_class")) in {"эконом", "economy", "комфорт", "comfort"}:
        return ENVELOPE_ECONOMY_COMFORT_RATE
    return ENVELOPE_NORMATIVE_RATE


def _source_label(is_manual: bool, is_technology_adjusted: bool) -> str:
    if is_manual:
        return "ручная корректировка"
    if is_technology_adjusted:
        return "технологическая корректировка"
    return "норматив"


def _engineering_rate(data: dict[str, Any], override_field: str, default_rate: float) -> float:
    override = float(data.get(override_field) or 0)
    return override if override > 0 else default_rate


def _catalog_rate(code: str) -> float:
    entry = next((item for item in RATE_CATALOG if str(item["код"]) == code), None)
    return float(entry.get("ставка") or 0) if entry else 0.0


def _detailed_cost_multiplier(data: dict[str, Any]) -> float:
    return float(data.get("_detailed_cost_multiplier") or data.get("_estimated_cost_multiplier") or 1)


def _foundation_amount(data: dict[str, Any]) -> float:
    total_area = float(data.get("total_area") or 0)
    foundation_type = _normalize(data.get("foundation_type"))
    if foundation_type == "сваи" and not bool(data.get("has_underground_part")):
        cost_override = float(data.get("pile_foundation_cost_override") or 0)
        if cost_override > 0:
            return round_money(cost_override)
        pile_count = float(data.get("pile_count") or 0)
        pile_unit_cost = float(data.get("pile_unit_cost") or 0)
        if pile_count > 0 and pile_unit_cost > 0:
            return round_money(pile_count * pile_unit_cost + total_area * float(data.get("grillage_rate_override") or 0))
        return round_money(total_area * _foundation_rate(data))
    rates = {
        "сваи": 9_000,
        "плита": 8_500,
        "лента": 5_000,
        "подземнаячасть": 12_000,
    }
    return round_money(total_area * rates.get(foundation_type, 9_000))


def _foundation_rate(data: dict[str, Any]) -> float:
    total_area = float(data.get("total_area") or 0)
    cost_override = float(data.get("pile_foundation_cost_override") or 0)
    if cost_override > 0:
        return round_money(cost_override / total_area) if total_area else 0.0
    pile_count = float(data.get("pile_count") or 0)
    pile_unit_cost = float(data.get("pile_unit_cost") or 0)
    if pile_count > 0 and pile_unit_cost > 0:
        amount = pile_count * pile_unit_cost + total_area * float(data.get("grillage_rate_override") or 0)
        return round_money(amount / total_area) if total_area else 0.0
    rate_override = float(data.get("pile_foundation_rate_override") or 0)
    if rate_override > 0:
        return rate_override
    mode = _normalize(data.get("foundation_optimization_mode"))
    return 6_500 if mode == "нормативный" else 5_500


def _foundation_source(data: dict[str, Any]) -> str:
    if float(data.get("pile_foundation_cost_override") or 0) > 0:
        return "Ручная сумма свайного основания"
    if float(data.get("pile_count") or 0) > 0 and float(data.get("pile_unit_cost") or 0) > 0:
        return "Расчёт по количеству свай"
    if float(data.get("pile_foundation_rate_override") or 0) > 0:
        return "Ручная ставка свайного основания"
    mode = _normalize(data.get("foundation_optimization_mode"))
    return "Норматив свайного основания" if mode == "нормативный" else "Оптимизированный норматив свайного основания"


def _foundation_manual_mode(data: dict[str, Any]) -> str | None:
    source = _foundation_source(data)
    return source if source.startswith(("Ручная", "Расчёт")) else None


def _sellable_finish_amount(data: dict[str, Any]) -> float:
    sellable_area = float(data.get("sellable_area") or 0)
    return round_money(sellable_area * _finish_rate(_normalize(data.get("sellable_finish_level"))))


def _finish_rate(finish_level: str) -> float:
    rates = {
        "безотделки": 0,
        "черновая": 2_500,
        "whitebox": 10_000,
        "чистовая": 22_000,
    }
    return float(rates.get(finish_level, 2_500))


def _build_row(
    entry: dict[str, Any],
    amount: float,
    data: dict[str, Any],
    budget: dict[str, Any],
    economics: dict[str, Any],
) -> dict[str, Any]:
    base_value = _base_value(str(entry["база"]), data, budget, economics)
    coefficient = float(entry.get("коэффициент") or 1)
    rate = round_money(amount / base_value / coefficient) if base_value and coefficient else 0.0
    normative_rate = float(entry.get("нормативная ставка") or entry.get("ставка") or 0)
    normative_amount = round_money(base_value * normative_rate * coefficient) if base_value and normative_rate else 0.0
    row = {
        "Глава": entry["глава"],
        "Код": entry["код"],
        "Статья": entry["статья"],
        "Источник бюджета": entry.get("источник"),
        "База": round_money(base_value),
        "Ед.": entry["единица"],
        "Ставка": rate,
        "Коэфф.": coefficient,
        "Сумма": round_money(amount),
        "Нормативная ставка": round_money(normative_rate),
        "Нормативная сумма": normative_amount,
        "Разница к нормативу": round_money(amount - normative_amount) if normative_amount else 0.0,
        "Источник значения": entry.get("источник значения", "норматив"),
        "Примечание": entry["примечание"],
        "Материалы, %": round(float(entry["доля материалов"]) * 100, 2),
        "Работы, %": round(float(entry["доля работ"]) * 100, 2),
        "Механизмы, %": round(float(entry["доля механизмов"]) * 100, 2),
        "Накладные, %": round(float(entry["доля накладных"]) * 100, 2),
    }
    _apply_split_amounts(row)
    return row


def _apply_split_amounts(row: dict[str, Any]) -> None:
    amount = float(row["Сумма"])
    materials = round_money(amount * float(row["Материалы, %"]) / 100)
    works = round_money(amount * float(row["Работы, %"]) / 100)
    machinery = round_money(amount * float(row["Механизмы, %"]) / 100)
    overheads = round_money(amount - materials - works - machinery)
    row["Материалы, ₽"] = materials
    row["Работы, ₽"] = works
    row["Механизмы, ₽"] = machinery
    row["Накладные, ₽"] = overheads


def _base_value(base: str, data: dict[str, Any], budget: dict[str, Any], economics: dict[str, Any]) -> float:
    if base == "land_area":
        return float(data.get("land_area") or 0)
    if base == "sellable_area":
        return float(data.get("sellable_area") or 0)
    if base == "cmr":
        return _calculate_cmr_core_total(data) or float(budget.get("cmr") or 0)
    if base == "revenue":
        return float(economics.get("revenue") or 0)
    return float(data.get("total_area") or 0)


def _chapter_totals(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    titles = {
        "1": "ИТОГО ГЛАВА 1",
        "2": "ИТОГО ГЛАВА 2",
        "3": "ИТОГО ГЛАВА 3",
    }
    totals = []
    for chapter in ("1", "2", "3"):
        totals.append(
            {
                "Глава": chapter,
                "Статья": titles[chapter],
                "Сумма": round_money(sum(row["Сумма"] for row in items if str(row["Глава"]) == chapter)),
            }
        )
    return totals


def _budget_adjustments(items: list[dict[str, Any]], data: dict[str, Any]) -> list[dict[str, Any]]:
    item_by_name = {row["Статья"]: row for row in items}

    def pick(*names: str) -> dict[str, Any]:
        for name in names:
            if name in item_by_name:
                return item_by_name[name]
        return {"Статья": names[0], "Сумма": 0, "Ставка": 0, "Примечание": ""}

    engineering_rows = [
        pick("Сантехнические системы"),
        pick("Отопление / ИТП / узел учета"),
        pick("Электроснабжение"),
        pick("Слаботочные системы"),
        pick("Вентиляция / дымоудаление"),
    ]
    engineering_total = round_money(sum(float(row.get("Сумма") or 0) for row in engineering_rows))
    cmr_total = round_money(sum(float(row["Сумма"]) for row in items if row.get("Источник бюджета") == "cmr"))
    engineering_share = round(engineering_total / cmr_total, 4) if cmr_total else 0.0

    rows = [
        {
            "Статья": "Режим расчёта свай",
            "Сумма": data.get("foundation_optimization_mode"),
            "Ставка": "",
            "Нормативная сумма": "",
            "Разница к нормативу": "",
            "Источник значения": _foundation_source(data),
            "Примечание": "Используется для статьи «Свайное основание / ростверк».",
        },
        pick("Свайное основание / ростверк", "Фундаментная плита / свайное основание / ограждение котлована"),
        pick("Земляные работы"),
        pick("Устройство несущих конструкций подземной части"),
        pick("Устройство несущих конструкций надземной части"),
        pick("Ограждающие конструкции / внутренние стены / кровля"),
        *engineering_rows,
        {
            "Статья": "Итог инженерных систем",
            "Сумма": engineering_total,
            "Ставка": "",
            "Нормативная сумма": "",
            "Разница к нормативу": "",
            "Источник значения": "расчёт",
            "Примечание": "Сумма статей 2.11–2.15.",
        },
        {
            "Статья": "Доля инженерных систем в СМР",
            "Сумма": engineering_share,
            "Ставка": "",
            "Нормативная сумма": "",
            "Разница к нормативу": "",
            "Источник значения": "расчёт",
            "Примечание": "Итог инженерных систем / СМР.",
        },
        pick("Проектирование"),
        pick("Подготовительный период"),
        pick("Отделка реализуемых площадей"),
    ]
    return [
        {
            "Статья": row["Статья"],
            "Сумма": row["Сумма"],
            "Ставка": row["Ставка"],
            "Нормативная сумма": row.get("Нормативная сумма", 0),
            "Разница к нормативу": row.get("Разница к нормативу", 0),
            "Источник значения": row.get("Источник значения", "норматив"),
            "Комментарий": row["Примечание"],
        }
        for row in rows
    ]


def _sort_code(code: str) -> tuple[int, ...]:
    return tuple(int(part) for part in code.split(".") if part.isdigit())


def _sum_items(item_amounts: dict[str, float], *names: str) -> float:
    return sum(item_amounts.get(name, 0.0) for name in names)


def _source_totals_from_items(items: list[dict[str, Any]]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for row in items:
        source = str(row.get("Источник бюджета") or "")
        totals[source] = totals.get(source, 0.0) + float(row.get("Сумма") or 0)
    return {key: round_money(value) for key, value in totals.items()}


def _summary_budget_items_from_detail(budget: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"name": "Земля", "amount": budget["land"], "formula": "Детальный бюджет, глава 1", "source": "Детальный бюджет"},
        {"name": "СМР", "amount": budget["cmr"], "formula": "Сумма детальных статей 2.1–2.15", "source": "Детальный бюджет"},
        {"name": "Проектирование", "amount": budget["design"], "formula": "Детальная статья 3.1", "source": "Детальный бюджет"},
        {"name": "Технический заказчик", "amount": budget["technical_customer"], "formula": "СМР × 2.5%", "source": "Детальный бюджет"},
        {"name": "Генподряд", "amount": budget["general_contractor"], "formula": "СМР × 3%", "source": "Детальный бюджет"},
        {"name": "Наружные сети", "amount": budget["external_networks"], "formula": "СМР × 7% или 0", "source": "Детальный бюджет"},
        {"name": "Благоустройство", "amount": budget["landscaping"], "formula": "СМР × 2.5%", "source": "Детальный бюджет"},
        {"name": "Резерв", "amount": budget["reserve"], "formula": "СМР × 5%", "source": "Детальный бюджет"},
    ]


def _engineering_total(items: list[dict[str, Any]]) -> float:
    return round_money(
        sum(float(row.get("Сумма") or 0) for row in items if str(row.get("Код")) in {"2.11", "2.12", "2.13", "2.14", "2.15"})
    )


def _item_by_code(items: list[dict[str, Any]], code: str) -> dict[str, Any]:
    return next((row for row in items if str(row.get("Код")) == code), {})


def _normalize(value: Any) -> str:
    return str(value or "").lower().replace("ё", "е").replace(" ", "").replace("-", "")


def _stage_timing(months: int, start_fraction: float, duration_fraction: float) -> tuple[int, int, int]:
    start = min(months, max(1, round(months * start_fraction)))
    duration = max(1, round(months * duration_fraction))
    if start + duration - 1 > months:
        duration = max(1, months - start + 1)
    end = min(months, start + duration - 1)
    return start, duration, end


def _stage_by_name(work_schedule: dict[str, Any], name: str) -> dict[str, Any] | None:
    return next((stage for stage in work_schedule["stages"] if stage["Этап"] == name), None)


def _stage_month_value(stage: dict[str, Any] | None, month: int, total: float) -> float:
    if not stage or total <= 0:
        return 0.0
    monthly = stage["monthly_amounts"]
    stage_sum = sum(float(value or 0) for value in monthly)
    if stage_sum <= 0:
        return 0.0
    return total * float(monthly[month - 1] or 0) / stage_sum


def _add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, 28)
    return date(year, month, day)
