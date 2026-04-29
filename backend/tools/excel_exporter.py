from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter


SHEET_NAMES = (
    "01_Вводные",
    "02_Допущения",
    "03_ТЭП",
    "04_Бюджет",
    "05_СМР",
    "06_ГПР",
    "07_План_продаж",
    "08_Кредит",
    "09_ДДС",
    "10_DSCR",
    "11_Экономика",
    "12_Риски",
    "13_Сценарии",
    "14_Оптимизация",
)

RU_LABELS = {
    "project_name": "Название проекта",
    "city": "Город",
    "object_type": "Тип объекта",
    "object_class": "Класс объекта",
    "land_area": "Площадь участка",
    "land_cost": "Стоимость земли",
    "total_area": "Общая площадь",
    "sellable_area": "Продаваемая площадь",
    "sellable_ratio": "Доля продаваемой площади",
    "floors": "Этажность",
    "sale_price_per_m2": "Цена продажи за м²",
    "estimated_sale_price_per_m2": "Расчётная цена продажи за м²",
    "sale_price_source": "Источник цены продажи",
    "market_price_per_m2": "Рыночный ориентир",
    "break_even_price_per_m2": "Цена безубыточности",
    "target_margin_price_per_m2": "Цена для целевой маржи",
    "recommended_price_per_m2": "Рекомендованная цена продажи",
    "price_gap_to_market": "Разница к рынку",
    "base_market_price_per_m2": "Базовая рыночная цена за м²",
    "object_type_price_coefficient": "Коэффициент типа объекта",
    "floors_price_coefficient": "Коэффициент этажности для цены",
    "scale_price_coefficient": "Коэффициент масштаба для цены",
    "target_margin": "Целевая маржа",
    "construction_cost_per_m2": "Стоимость строительства за м²",
    "gp_contract_price_per_m2": "Цена генподряда за м²",
    "estimated_cmr_cost_per_m2": "Расчётная себестоимость СМР за м²",
    "cmr_cost_source": "Источник себестоимости",
    "construction_price_per_m2": "Использованная себестоимость СМР за м²",
    "base_cmr_cost_per_m2": "Базовая стоимость СМР за м²",
    "city_coefficient": "Коэффициент города",
    "floors_coefficient": "Коэффициент этажности",
    "area_coefficient": "Коэффициент масштаба",
    "engineering_coefficient": "Коэффициент инженерии",
    "construction_months": "Срок строительства, мес.",
    "sales_months": "Срок продаж, мес.",
    "credit_share": "Доля кредита",
    "credit_rate": "Ставка кредита",
    "external_networks_included": "Наружные сети включены",
    "gas_only_cooking": "Газ только пищеприготовление",
    "reserve": "Резерв",
    "design": "Проектирование",
    "technical_customer": "Технический заказчик",
    "general_contractor": "Генподряд",
    "landscaping": "Благоустройство",
    "external_networks": "Наружные сети",
    "field": "Параметр",
    "value": "Значение",
    "reason": "Причина",
    "source": "Источник",
    "name": "Статья",
    "amount": "Сумма",
    "formula": "Формула",
    "share": "Доля",
    "month": "Месяц",
    "weight": "Вес",
    "construction_cost": "Затраты строительства",
    "construction_costs": "Затраты строительства",
    "land_payment": "Платеж за землю",
    "accumulated": "Накопительно",
    "sold_area": "Проданная площадь",
    "revenue": "Выручка",
    "accumulated_sold_area": "Проданная площадь накопительно",
    "accumulated_revenue": "Выручка накопительно",
    "opening_balance": "Остаток кредита на начало",
    "drawdown": "Выборка кредита",
    "interest": "Проценты",
    "repayment": "Погашение кредита",
    "closing_balance": "Остаток кредита на конец",
    "sales_receipts": "Поступления от продаж",
    "land": "Земля",
    "other_expenses": "Прочие расходы",
    "operating_cashflow_before_financing": "Операционный денежный поток до финансирования",
    "credit_drawdown": "Выборка кредита",
    "credit_repayment": "Погашение кредита",
    "equity_required": "Собственные средства",
    "cumulative_equity_required": "Собственные средства накопительно",
    "net_cashflow": "Чистый денежный поток",
    "accumulated_cashflow": "Накопленный денежный поток",
    "cash_balance_after_financing": "Остаток денежных средств после финансирования",
    "debt_service": "Обслуживание долга",
    "dscr": "DSCR",
    "total_budget": "Итоговый бюджет",
    "budget_per_total_m2": "Бюджет на 1 м² общей площади",
    "budget_per_sellable_m2": "Бюджет на 1 м² продаваемой площади",
    "revenue_per_total_m2": "Выручка на 1 м² общей площади",
    "profit_before_interest": "Прибыль до процентов",
    "profit_after_interest": "Прибыль после процентов",
    "margin_before_interest": "Маржа до процентов",
    "margin_after_interest": "Маржа после процентов",
    "total_interest": "Всего процентов",
    "max_credit_balance": "Максимальный остаток кредита",
    "total_equity_required": "Потребность в собственных средствах",
    "minimum_dscr": "Минимальный DSCR",
    "minimum_dscr_after_sales_start": "Минимальный DSCR после начала продаж",
    "average_dscr_after_sales_start": "Средний DSCR после начала продаж",
    "months_below_1_2": "Месяцев с DSCR ниже 1.2",
    "roi_on_budget": "ROI на бюджет",
    "profit": "Прибыль",
    "margin": "Маржа",
    "code": "Код риска",
    "level": "Уровень",
    "title": "Риск",
    "description": "Описание",
    "recommendation": "Рекомендация",
    "scenario": "Код сценария",
    "scenario_name": "Сценарий",
    "margin_assessment": "Оценка маржи",
    "dscr_assessment": "Оценка DSCR",
    "margin_color": "Цвет оценки маржи",
    "dscr_color": "Цвет оценки DSCR",
    "market_revenue": "Выручка по рыночной цене",
    "target_profit": "Целевая прибыль по рынку",
    "allowed_total_cost_with_interest": "Допустимые затраты с процентами",
    "current_total_cost_with_interest": "Текущий бюджет с процентами",
    "required_budget_reduction_for_market_price": "Требуемое снижение бюджета для прохождения по рынку",
    "required_budget_reduction_mln_rub": "Снижение бюджета, млн ₽",
    "required_cmr_cost_per_m2_for_market_price": "Требуемая СМР за м² для рынка",
    "required_sellable_area_for_market_price": "Требуемая продаваемая площадь",
    "required_sale_price_for_target_margin": "Цена для целевой маржи",
    "gap_to_market_price": "Разница к рынку",
    "most_realistic_option": "Наиболее реалистичный рычаг",
    "recommendations": "Рекомендации",
}

VALUE_LABELS = {
    "source": {
        "developer_assumption": "Девелоперское допущение",
        "developer_norm": "Норматив модели",
        "cost_estimator": "Оценщик себестоимости",
        "price_estimator": "Оценщик цены продажи",
    },
    "field": {
        "project_name": "Название проекта",
        "city": "Город",
        "object_type": "Тип объекта",
        "object_class": "Класс объекта",
        "land_area": "Площадь участка",
        "land_cost": "Стоимость земли",
        "total_area": "Общая площадь",
        "sellable_area": "Продаваемая площадь",
        "floors": "Этажность",
        "sale_price_per_m2": "Цена продажи за м²",
        "estimated_sale_price_per_m2": "Расчётная цена продажи за м²",
        "base_market_price_per_m2": "Базовая рыночная цена за м²",
        "object_type_price_coefficient": "Коэффициент типа объекта",
        "floors_price_coefficient": "Коэффициент этажности для цены",
        "scale_price_coefficient": "Коэффициент масштаба для цены",
        "market_price_per_m2": "Рыночный ориентир цены продажи",
        "target_margin": "Целевая маржа",
        "construction_months": "Срок строительства, мес.",
        "sales_months": "Срок продаж, мес.",
        "credit_share": "Доля кредита",
        "credit_rate": "Ставка кредита",
        "external_networks_included": "Наружные сети включены",
        "gas_only_cooking": "Газ только пищеприготовление",
        "reserve": "Резерв",
        "design": "Проектирование",
        "technical_customer": "Технический заказчик",
        "general_contractor": "Генподряд",
        "landscaping": "Благоустройство",
        "external_networks": "Наружные сети",
        "base_cmr_cost_per_m2": "Базовая стоимость СМР за м²",
        "city_coefficient": "Коэффициент города",
        "floors_coefficient": "Коэффициент этажности",
        "area_coefficient": "Коэффициент масштаба",
        "engineering_coefficient": "Коэффициент инженерии",
        "estimated_cmr_cost_per_m2": "Итоговая расчётная себестоимость СМР за м²",
    },
    "level": {
        "high": "Высокий",
        "medium": "Средний",
        "low": "Низкий",
        "ok": "Норма",
    },
    "object_class": {
        "economy": "эконом",
        "comfort": "комфорт",
        "business": "бизнес",
        "premium": "премиум",
        "standard": "стандарт",
    },
}

SCENARIO_COLUMNS = (
    "scenario",
    "scenario_name",
    "sale_price_per_m2",
    "sales_months",
    "gp_contract_price_per_m2",
    "construction_cost_per_m2",
    "credit_rate",
    "revenue",
    "total_budget",
    "profit_before_interest",
    "profit_after_interest",
    "margin_after_interest",
    "max_credit_balance",
    "total_equity_required",
    "minimum_dscr_after_sales_start",
    "months_below_1_2",
    "margin_assessment",
    "dscr_assessment",
)

SCENARIO_LABELS = {
    "max_credit_balance": "Максимальный кредит",
    "total_equity_required": "Собственные средства",
    "minimum_dscr_after_sales_start": "Minimum DSCR",
    "months_below_1_2": "Месяцев DSCR ниже 1.2",
}


def export_model_to_excel(model: dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_name = _safe_filename(model["input"].get("project_name") or "model")
    path = output_dir / f"{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

    workbook = Workbook()
    workbook.remove(workbook.active)
    sheets = {name: workbook.create_sheet(name) for name in SHEET_NAMES}

    _write_key_values(sheets["01_Вводные"], model["input"])
    _write_table(sheets["02_Допущения"], model["assumptions"])
    _write_key_values(sheets["03_ТЭП"], model["tep"])
    _write_table(sheets["04_Бюджет"], model["budget"]["items"])
    _write_table(sheets["05_СМР"], model["cmr"]["items"])
    _write_table(sheets["06_ГПР"], model["gpr"])
    _write_table(sheets["07_План_продаж"], model["sales_plan"])
    _write_table(sheets["08_Кредит"], model["credit"]["schedule"])
    _write_table(sheets["09_ДДС"], model["cashflow"])
    _write_table(sheets["10_DSCR"], model["dscr"]["schedule"])
    _write_key_values(sheets["11_Экономика"], model["economics"])
    _write_table(sheets["12_Риски"], model["risks"])
    _write_table(sheets["13_Сценарии"], model["scenarios"], columns=SCENARIO_COLUMNS, labels=SCENARIO_LABELS)
    _write_optimization(sheets["14_Оптимизация"], model["optimization"])

    for sheet in workbook.worksheets:
        _style_sheet(sheet)
    _style_scenario_sheet(sheets["13_Сценарии"])
    workbook.save(path)
    return path


def _write_key_values(sheet: Any, values: dict[str, Any]) -> None:
    sheet.append(["Показатель", "Значение"])
    for key, value in values.items():
        if isinstance(value, list | dict):
            continue
        sheet.append([_label(key), _display_value(key, value)])


def _write_table(
    sheet: Any,
    rows: list[dict[str, Any]],
    columns: tuple[str, ...] | None = None,
    labels: dict[str, str] | None = None,
) -> None:
    if not rows:
        sheet.append(["Нет данных"])
        return
    headers = list(columns or rows[0].keys())
    sheet.append([_label(header, labels) for header in headers])
    for row in rows:
        sheet.append([_display_table_value(row, header) for header in headers])


def _write_optimization(sheet: Any, optimization: dict[str, Any]) -> None:
    _write_key_values(sheet, optimization)
    recommendations = optimization.get("recommendations") or []
    if recommendations:
        sheet.append([])
        sheet.append(["Рекомендации"])
        for recommendation in recommendations:
            sheet.append([recommendation])


def _style_sheet(sheet: Any) -> None:
    header_fill = PatternFill("solid", fgColor="1F4E78")
    header_font = Font(color="FFFFFF", bold=True)
    for cell in sheet[1]:
        cell.fill = header_fill
        cell.font = header_font
    for column_cells in sheet.columns:
        max_length = max(len(str(cell.value or "")) for cell in column_cells)
        column_letter = get_column_letter(column_cells[0].column)
        sheet.column_dimensions[column_letter].width = min(max(max_length + 2, 12), 48)
    sheet.freeze_panes = "A2"


def _style_scenario_sheet(sheet: Any) -> None:
    if sheet.max_row < 2:
        return
    headers = {cell.value: cell.column for cell in sheet[1]}
    color_map = {
        "red": "FFC7CE",
        "yellow": "FFEB9C",
        "green": "C6EFCE",
        "gray": "D9E1F2",
    }
    margin_column = headers.get("Оценка маржи")
    dscr_column = headers.get("Оценка DSCR")
    for row in range(2, sheet.max_row + 1):
        margin_value = str(sheet.cell(row=row, column=margin_column).value or "") if margin_column else ""
        dscr_value = str(sheet.cell(row=row, column=dscr_column).value or "") if dscr_column else ""
        margin_color = {"плохо": "red", "средне": "yellow", "хорошо": "green"}.get(margin_value)
        dscr_color = {"риск": "red", "норма": "green", "нет данных": "gray"}.get(dscr_value)
        if margin_column and margin_color:
            sheet.cell(row=row, column=margin_column).fill = PatternFill("solid", fgColor=color_map[margin_color])
        if dscr_column and dscr_color:
            sheet.cell(row=row, column=dscr_column).fill = PatternFill("solid", fgColor=color_map[dscr_color])


def _label(key: str, labels: dict[str, str] | None = None) -> str:
    if labels and key in labels:
        return labels[key]
    return RU_LABELS.get(key, key)


def _display_value(key: str, value: Any) -> Any:
    if isinstance(value, bool):
        return "Да" if value else "Нет"
    return VALUE_LABELS.get(key, {}).get(value, value)


def _display_table_value(row: dict[str, Any], header: str) -> Any:
    value = row.get(header)
    if header == "value":
        value_key = str(row.get("field") or "")
        return _display_value(value_key, value)
    return _display_value(header, value)


def _safe_filename(value: str) -> str:
    safe = "".join(char if char.isalnum() else "_" for char in value.strip())
    return safe[:40] or "model"
