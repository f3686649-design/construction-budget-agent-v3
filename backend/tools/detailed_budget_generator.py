from __future__ import annotations

from datetime import date
from typing import Any

from backend.tools.norms import round_money
from backend.tools.rate_catalog import RATE_CATALOG


START_DATE = date(2026, 1, 1)


def generate_detailed_budget(data: dict[str, Any], budget: dict[str, Any], economics: dict[str, Any] | None = None) -> dict[str, Any]:
    economics = economics or {}
    bucket_totals = {
        "land": float(budget.get("land") or 0),
        "cmr": float(budget.get("cmr") or 0),
        "external_networks": float(budget.get("external_networks") or 0),
        "landscaping": float(budget.get("landscaping") or 0),
        "design": float(budget.get("design") or 0),
        "technical_customer": float(budget.get("technical_customer") or 0),
        "general_contractor": float(budget.get("general_contractor") or 0),
        "marketing": 0.0,
        "reserve": float(budget.get("reserve") or 0),
        "revenue": float(economics.get("revenue") or 0),
    }
    grouped = _catalog_by_source()
    remaining_by_source: dict[str, float] = {}
    items: list[dict[str, Any]] = []

    for source, entries in grouped.items():
        total = bucket_totals.get(source, 0.0)
        amounts = _allocate(total, [float(entry.get("доля источника") or 0) for entry in entries])
        remaining_by_source[source] = total
        for entry, amount in zip(entries, amounts, strict=True):
            remaining_by_source[source] -= amount
            row = _build_row(entry, amount, data, budget, economics)
            items.append(row)

    items.sort(key=lambda row: _sort_code(str(row["Код"])))
    total_budget = round_money(sum(row["Сумма"] for row in items))
    drift = round_money(float(budget["total_budget"]) - total_budget)
    if items and abs(drift) >= 0.01:
        items[-1]["Сумма"] = round_money(items[-1]["Сумма"] + drift)
        _apply_split_amounts(items[-1])
        total_budget = round_money(sum(row["Сумма"] for row in items))

    chapter_totals = _chapter_totals(items)
    split_totals = {
        "materials": round_money(sum(row["Материалы, ₽"] for row in items)),
        "works": round_money(sum(row["Работы, ₽"] for row in items)),
        "machinery": round_money(sum(row["Механизмы, ₽"] for row in items)),
        "overheads": round_money(sum(row["Накладные, ₽"] for row in items)),
    }
    return {
        "items": items,
        "chapter_totals": chapter_totals,
        "split_totals": split_totals,
        "total_budget": total_budget,
        "trace": [
            {
                "step": "generate_detailed_budget",
                "inputs": {"budget_total": budget["total_budget"], "items_count": len(items)},
                "formula": "Agent budget buckets distributed into ModDEV-like detailed cost structure.",
                "output": {
                    "total_budget": total_budget,
                    "chapter_totals": chapter_totals,
                    "split_totals": split_totals,
                    "drift": drift,
                },
            }
        ],
    }


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
        ("Фундамент / сваи / котлован", 0.12, 0.15, _sum_items(item_amounts, "Фундаментная плита / свайное основание / ограждение котлована")),
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
    row = {
        "Глава": entry["глава"],
        "Код": entry["код"],
        "Статья": entry["статья"],
        "База": round_money(base_value),
        "Ед.": entry["единица"],
        "Ставка": rate,
        "Коэфф.": coefficient,
        "Сумма": round_money(amount),
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
        return float(budget.get("cmr") or 0)
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


def _sort_code(code: str) -> tuple[int, ...]:
    return tuple(int(part) for part in code.split(".") if part.isdigit())


def _sum_items(item_amounts: dict[str, float], *names: str) -> float:
    return sum(item_amounts.get(name, 0.0) for name in names)


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

