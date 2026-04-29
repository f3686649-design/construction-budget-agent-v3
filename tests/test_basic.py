from __future__ import annotations

import pytest
from openpyxl import load_workbook

from backend.main import OUTPUT_DIR, build_financial_model, generate_model, health
from backend.models import ProjectInput
from backend.tools.cmr_splitter import split_cmr
from backend.tools.excel_exporter import export_model_to_excel


def _minimal_model() -> dict:
    return build_financial_model(ProjectInput(project_name="Минимальный проект"))


def _model_with_market_gap() -> dict:
    return build_financial_model(
        ProjectInput(
            project_name="Разрыв к рынку",
            city="Якутск",
            object_type="Жилой дом",
            object_class="комфорт",
            total_area=10_000,
            sellable_area=7_800,
            floors=9,
        )
    )


def _technology_model(**kwargs) -> dict:
    base = {
        "project_name": "Технология 6666",
        "total_area": 6_666,
        "sellable_area": 5_200,
        "foundation_type": "сваи",
        "has_underground_part": False,
        "sellable_finish_level": "черновая",
    }
    base.update(kwargs)
    return build_financial_model(ProjectInput(**base))


def _detail_item(model: dict, name: str) -> dict:
    return next(row for row in model["detailed_budget"]["items"] if row["Статья"] == name)


def test_health_works() -> None:
    assert health() == {"status": "ok"}


def test_model_is_created_from_minimal_data() -> None:
    payload = generate_model(ProjectInput(project_name="Минимальный проект"))
    assert payload["status"] == "ok"
    assert payload["budget"]["total_budget"] > 0
    assert payload["economics"]["revenue"] > 0
    assert payload["estimated_cmr_cost_per_m2"] > 0
    assert payload["cmr_cost_source"] == "Расчётная себестоимость агента"
    assert payload["recommended_price_per_m2"] > 0
    assert payload["sale_price_source"] == "Расчётная цена продажи агента"
    assert payload["improvement_plan"]["priority_actions"]
    assert payload["assumptions"]


def test_excel_is_saved() -> None:
    before = set(OUTPUT_DIR.glob("*.xlsx")) if OUTPUT_DIR.exists() else set()
    payload = generate_model(ProjectInput(project_name="Excel test"))
    filename = payload["output_filename"]
    output_path = OUTPUT_DIR / filename
    try:
        assert output_path.exists()
        assert output_path.suffix == ".xlsx"
    finally:
        for path in set(OUTPUT_DIR.glob("*.xlsx")) - before:
            path.unlink(missing_ok=True)


def test_gpr_sum_equals_budget() -> None:
    model = _minimal_model()
    gpr_sum = sum(row["amount"] for row in model["gpr"])
    assert gpr_sum == pytest.approx(model["budget"]["total_budget"], abs=0.05)


def test_sales_sum_equals_sellable_area() -> None:
    model = _minimal_model()
    sold_area = sum(row["sold_area"] for row in model["sales_plan"])
    assert sold_area == pytest.approx(model["input"]["sellable_area"], abs=0.001)


def test_cmr_split_sum_is_correct() -> None:
    cmr = split_cmr(100_000_000)
    assert sum(item["amount"] for item in cmr["items"]) == pytest.approx(100_000_000, abs=0.01)
    assert cmr["items"][0]["amount"] == pytest.approx(55_000_000)


def test_minimum_dscr_ignores_empty_first_month() -> None:
    model = _minimal_model()
    first_month = model["dscr"]["schedule"][0]
    assert first_month["sales_receipts"] == 0
    assert first_month["dscr"] is None
    assert model["dscr"]["minimum_dscr_after_sales_start"] is None or model["dscr"]["minimum_dscr_after_sales_start"] > 0


def test_sellable_ratio_is_calculated() -> None:
    model = build_financial_model(
        ProjectInput(
            project_name="Sellable ratio",
            total_area=10_000,
            sellable_area=7_000,
        )
    )
    assert model["tep"]["sellable_ratio"] == pytest.approx(0.7)
    assert model["economics"]["sellable_ratio"] == pytest.approx(0.7)


def test_equity_required_when_credit_is_less_than_full_deficit() -> None:
    model = build_financial_model(
        ProjectInput(
            project_name="Equity gap",
            total_area=10_000,
            sellable_area=7_800,
            credit_share=0.7,
        )
    )
    assert max(row["equity_required"] for row in model["cashflow"]) > 0
    assert model["economics"]["total_equity_required"] > 0


def test_scenarios_are_generated() -> None:
    model = _minimal_model()
    scenarios = {row["scenario"]: row for row in model["scenarios"]}
    assert set(scenarios) == {"base", "optimistic", "stress"}
    assert scenarios["optimistic"]["revenue"] > scenarios["base"]["revenue"]
    assert scenarios["stress"]["revenue"] < scenarios["base"]["revenue"]
    assert scenarios["stress"]["construction_cost_per_m2"] > scenarios["base"]["construction_cost_per_m2"]
    assert scenarios["stress"]["credit_rate"] == pytest.approx(model["input"]["credit_rate"] + 0.02)
    assert scenarios["stress"]["margin_assessment"] in {"плохо", "средне", "хорошо"}
    assert scenarios["stress"]["dscr_assessment"] in {"риск", "норма", "нет данных"}


def test_excel_contains_scenarios_sheet() -> None:
    model = _minimal_model()
    path = export_model_to_excel(model, OUTPUT_DIR)
    workbook = None
    try:
        workbook = load_workbook(path, read_only=True)
        assert "13_Сценарии" in workbook.sheetnames
        sheet = workbook["13_Сценарии"]
        headers = [cell.value for cell in next(sheet.iter_rows(min_row=1, max_row=1))]
        assert headers == [
            "Код сценария",
            "Сценарий",
            "Цена продажи за м²",
            "Срок продаж, мес.",
            "Цена генподряда за м²",
            "Стоимость строительства за м²",
            "Ставка кредита",
            "Выручка",
            "Итоговый бюджет",
            "Прибыль до процентов",
            "Прибыль после процентов",
            "Маржа после процентов",
            "Максимальный кредит",
            "Собственные средства",
            "Minimum DSCR",
            "Месяцев DSCR ниже 1.2",
            "Оценка маржи",
            "Оценка DSCR",
        ]
        assert sheet.max_row == 4
    finally:
        if workbook is not None:
            workbook.close()
        path.unlink(missing_ok=True)


def test_excel_uses_russian_user_headers() -> None:
    model = _minimal_model()
    path = export_model_to_excel(model, OUTPUT_DIR)
    workbook = None
    try:
        workbook = load_workbook(path, read_only=True)
        tep_labels = [row[0].value for row in workbook["03_ТЭП"].iter_rows(min_row=2, max_col=1)]
        assumptions_labels = [row[0].value for row in workbook["02_Допущения"].iter_rows(min_row=2, max_col=1)]
        economics_labels = [row[0].value for row in workbook["11_Экономика"].iter_rows(min_row=2, max_col=1)]
        cashflow_headers = [cell.value for cell in next(workbook["09_ДДС"].iter_rows(min_row=1, max_row=1))]
        risks_headers = [cell.value for cell in next(workbook["12_Риски"].iter_rows(min_row=1, max_row=1))]
        assert "Название проекта" in tep_labels
        assert "Доля продаваемой площади" in tep_labels
        assert "Расчётная себестоимость СМР за м²" in tep_labels
        assert "Расчётная цена продажи за м²" in tep_labels
        assert "Рыночный ориентир" in tep_labels
        assert "Бюджет на 1 м² общей площади" in tep_labels
        assert "Базовая стоимость СМР за м²" in assumptions_labels
        assert "Коэффициент города" in assumptions_labels
        assert "Базовая рыночная цена за м²" in assumptions_labels
        assert "Коэффициент типа объекта" in assumptions_labels
        assert "Прибыль после процентов" in economics_labels
        assert "Источник цены продажи" in economics_labels
        assert "Цена безубыточности" in economics_labels
        assert "Собственные средства" in cashflow_headers
        assert "Риск" in risks_headers
    finally:
        if workbook is not None:
            workbook.close()
        path.unlink(missing_ok=True)


def test_model_estimates_cost_without_manual_cmr_price() -> None:
    model = build_financial_model(
        ProjectInput(
            project_name="Автооценка",
            city="Москва",
            object_type="Жилой дом",
            object_class="комфорт",
            total_area=10_000,
            sellable_area=7_800,
            floors=10,
        )
    )
    assert model["input"]["construction_cost_per_m2"] is None
    assert model["input"]["gp_contract_price_per_m2"] is None
    assert model["estimated_cmr_cost_per_m2"] > 0
    assert model["cmr_cost_source"] == "Расчётная себестоимость агента"
    assert model["budget"]["construction_price_per_m2"] == model["estimated_cmr_cost_per_m2"]


def test_gp_contract_price_has_priority_over_estimated_cost() -> None:
    model = build_financial_model(
        ProjectInput(
            project_name="Ручной генподряд",
            city="Москва",
            total_area=10_000,
            sellable_area=7_800,
            gp_contract_price_per_m2=123_000,
        )
    )
    assert model["cmr_cost_source"] == "Ручная цена генподряда"
    assert model["budget"]["construction_price_per_m2"] == 123_000
    assert model["budget"]["cmr"] == pytest.approx(1_230_000_000)


def test_yakutsk_city_coefficient_is_applied() -> None:
    model = build_financial_model(
        ProjectInput(
            project_name="Якутск",
            city="Якутск",
            object_type="Жилой дом",
            object_class="комфорт",
            total_area=10_000,
            sellable_area=7_800,
            floors=9,
        )
    )
    assert model["cost_estimation_coefficients"]["city_coefficient"] == pytest.approx(1.12)


def test_model_estimates_sale_price_without_manual_price() -> None:
    model = build_financial_model(
        ProjectInput(
            project_name="Автоцена",
            city="Якутск",
            object_type="Жилой дом",
            object_class="комфорт",
            total_area=10_000,
            sellable_area=7_800,
            floors=9,
        )
    )
    assert model["input"]["sale_price_per_m2"] == model["recommended_price_per_m2"]
    assert model["sale_price_source"] == "Расчётная цена продажи агента"
    assert model["recommended_price_per_m2"] > 0


def test_manual_sale_price_has_priority() -> None:
    model = build_financial_model(
        ProjectInput(
            project_name="Ручная цена",
            city="Якутск",
            total_area=10_000,
            sellable_area=7_800,
            sale_price_per_m2=210_000,
        )
    )
    assert model["sale_price_source"] == "Ручная цена продажи"
    assert model["input"]["sale_price_per_m2"] == 210_000
    assert model["economics"]["revenue"] == pytest.approx(7_800 * 210_000)
    assert model["price_iteration_count"] == 0


def test_yakutsk_comfort_market_price_starts_from_180000() -> None:
    model = build_financial_model(
        ProjectInput(
            project_name="Рынок Якутск",
            city="Якутск",
            object_type="Жилой дом",
            object_class="комфорт",
            total_area=10_000,
            sellable_area=7_800,
            floors=9,
        )
    )
    assert model["price_estimation_components"]["base_market_price_per_m2"] == 180_000
    assert model["market_price_per_m2"] == pytest.approx(180_000)


def test_price_warning_when_target_margin_price_is_above_market() -> None:
    model = build_financial_model(
        ProjectInput(
            project_name="Дорогой бюджет",
            city="Новосибирск",
            object_type="Жилой дом",
            object_class="эконом",
            total_area=10_000,
            sellable_area=7_000,
            gp_contract_price_per_m2=250_000,
        )
    )
    assert model["target_margin_price_per_m2"] > model["market_price_per_m2"]
    assert model["price_estimation_warnings"]


def test_optimization_advisor_creates_recommendations() -> None:
    model = build_financial_model(
        ProjectInput(
            project_name="Оптимизация",
            city="Якутск",
            object_type="Жилой дом",
            object_class="комфорт",
            total_area=10_000,
            sellable_area=7_800,
            floors=9,
        )
    )
    optimization = model["optimization"]
    assert optimization["recommendations"]
    assert optimization["required_budget_reduction_for_market_price"] >= 0
    assert optimization["required_cmr_cost_per_m2_for_market_price"] >= 0


def test_optimization_gap_when_recommended_price_is_above_market() -> None:
    model = _model_with_market_gap()
    assert model["recommended_price_per_m2"] > model["market_price_per_m2"]
    assert model["optimization"]["gap_to_market_price"] == pytest.approx(
        model["recommended_price_per_m2"] - model["market_price_per_m2"]
    )


def test_excel_displays_english_object_class_in_russian() -> None:
    model = build_financial_model(
        ProjectInput(
            project_name="Класс comfort",
            city="Якутск",
            object_type="Жилой дом",
            object_class="comfort",
            total_area=10_000,
            sellable_area=7_800,
            floors=9,
        )
    )
    path = export_model_to_excel(model, OUTPUT_DIR)
    workbook = None
    try:
        workbook = load_workbook(path, read_only=True)
        assert "14_Оптимизация" in workbook.sheetnames
        rows = {row[0]: row[1] for row in workbook["03_ТЭП"].iter_rows(min_row=2, values_only=True)}
        assert rows["Класс объекта"] == "комфорт"
    finally:
        if workbook is not None:
            workbook.close()
        path.unlink(missing_ok=True)


def test_improvement_plan_is_created() -> None:
    model = _minimal_model()
    improvement_plan = model["improvement_plan"]
    assert improvement_plan["summary"]
    assert improvement_plan["priority_actions"]
    assert improvement_plan["assumptions"]


def test_improvement_items_exist_when_budget_reduction_is_required() -> None:
    model = _model_with_market_gap()
    assert model["optimization"]["required_budget_reduction_for_market_price"] > 0
    assert model["improvement_plan"]["improvement_items"]


def test_improvement_items_sum_to_required_budget_reduction() -> None:
    model = _model_with_market_gap()
    target = model["improvement_plan"]["target_budget_reduction"]
    savings_sum = sum(item["Потенциал экономии, ₽"] for item in model["improvement_plan"]["improvement_items"])
    assert savings_sum == pytest.approx(target, abs=0.05)


def test_reserve_is_not_first_improvement_source() -> None:
    model = _model_with_market_gap()
    items = model["improvement_plan"]["improvement_items"]
    assert items[0]["Статья"] != "Резерв"
    assert all(item["Статья"] != "Резерв" for item in items)


def test_excel_contains_improvement_plan_sheet() -> None:
    model = _model_with_market_gap()
    path = export_model_to_excel(model, OUTPUT_DIR)
    workbook = None
    try:
        workbook = load_workbook(path, read_only=True)
        assert "15_План_улучшений" in workbook.sheetnames
        first_cell = workbook["15_План_улучшений"]["A1"].value
        assert first_cell == "А. Цель оптимизации"
    finally:
        if workbook is not None:
            workbook.close()
        path.unlink(missing_ok=True)


def test_auto_price_is_consistent_between_tep_and_optimization_excel() -> None:
    model = _model_with_market_gap()
    path = export_model_to_excel(model, OUTPUT_DIR)
    workbook = None
    try:
        workbook = load_workbook(path, read_only=True)
        tep_rows = {row[0]: row[1] for row in workbook["03_ТЭП"].iter_rows(min_row=2, values_only=True)}
        optimization_rows = {
            row[0]: row[1]
            for row in workbook["14_Оптимизация"].iter_rows(min_row=2, values_only=True)
            if row[0] is not None
        }
        assert tep_rows["Финальная рекомендованная цена"] == model["final_recommended_price_per_m2"]
        assert tep_rows["Цена для целевой маржи по фактическим процентам"] == optimization_rows["Цена для целевой маржи"]
    finally:
        if workbook is not None:
            workbook.close()
        path.unlink(missing_ok=True)


def test_manual_sale_price_is_not_overwritten_by_final_recalculation() -> None:
    model = build_financial_model(
        ProjectInput(
            project_name="Ручная цена без перезаписи",
            city="Якутск",
            total_area=10_000,
            sellable_area=7_800,
            sale_price_per_m2=210_000,
        )
    )
    assert model["input"]["sale_price_per_m2"] == 210_000
    assert model["sale_price_source"] == "Ручная цена продажи"
    assert model["price_iteration_count"] == 0


def test_price_iteration_count_is_limited() -> None:
    model = _model_with_market_gap()
    assert model["price_iteration_count"] <= 3


def test_detailed_budget_generator_creates_budget_items() -> None:
    model = _minimal_model()
    detailed_budget = model["detailed_budget"]
    assert detailed_budget["items"]
    assert {"Глава", "Код", "Статья", "Сумма"}.issubset(detailed_budget["items"][0])


def test_detailed_budget_sum_equals_total_budget() -> None:
    model = _minimal_model()
    detail_sum = sum(row["Сумма"] for row in model["detailed_budget"]["items"])
    assert detail_sum == pytest.approx(model["budget"]["total_budget"], abs=0.05)


def test_detailed_budget_contains_materials_and_works() -> None:
    model = _minimal_model()
    split = model["detailed_budget"]["split_totals"]
    assert split["materials"] > 0
    assert split["works"] > 0


def test_excel_budget_sheet_contains_detailed_structure() -> None:
    model = _minimal_model()
    path = export_model_to_excel(model, OUTPUT_DIR)
    workbook = None
    try:
        workbook = load_workbook(path, read_only=True)
        sheet = workbook["04_Бюджет"]
        headers = [cell.value for cell in next(sheet.iter_rows(min_row=2, max_row=2))]
        assert headers[:15] == [
            "Глава",
            "Код",
            "Статья",
            "База",
            "Ед.",
            "Ставка",
            "Коэфф.",
            "Сумма",
            "Материалы, %",
            "Работы, %",
            "Материалы, ₽",
            "Работы, ₽",
            "Механизмы, ₽",
            "Накладные, ₽",
            "Примечание",
        ]
        labels = [row[2] for row in sheet.iter_rows(min_row=3, values_only=True) if row[2]]
        assert "ИТОГО БЮДЖЕТ" in labels
    finally:
        if workbook is not None:
            workbook.close()
        path.unlink(missing_ok=True)


def test_excel_gpr_sheet_contains_monthly_work_structure() -> None:
    model = _minimal_model()
    path = export_model_to_excel(model, OUTPUT_DIR)
    workbook = None
    try:
        workbook = load_workbook(path, read_only=True)
        sheet = workbook["06_ГПР"]
        headers = [cell.value for cell in next(sheet.iter_rows(min_row=6, max_row=6))]
        assert headers[:6] == ["Этап", "Начало, мес.", "Длительность, мес.", "Окончание, мес.", "Стоимость", "Месяц 1"]
        labels = [row[0] for row in sheet.iter_rows(values_only=True) if row[0]]
        assert "ИТОГО CAPEX В МЕСЯЦ" in labels
        assert "НАКОПЛЕННЫЙ CAPEX" in labels
        assert "% ГОТОВНОСТИ" in labels
    finally:
        if workbook is not None:
            workbook.close()
        path.unlink(missing_ok=True)


def test_excel_contains_supply_plan_sheet() -> None:
    model = _minimal_model()
    path = export_model_to_excel(model, OUTPUT_DIR)
    workbook = None
    try:
        workbook = load_workbook(path, read_only=True)
        assert "16_Поставки" in workbook.sheetnames
        sheet = workbook["16_Поставки"]
        headers = [cell.value for cell in next(sheet.iter_rows(min_row=2, max_row=2))]
        assert headers == [
            "Месяц",
            "Дата потребности",
            "Бетон, м3",
            "Арматура, т",
            "Фасадные материалы, ₽",
            "Инженерное оборудование, ₽",
            "Дата заказа бетона",
            "Дата заказа арматуры",
            "Дата заказа фасада",
            "Комментарий",
        ]
    finally:
        if workbook is not None:
            workbook.close()
        path.unlink(missing_ok=True)


def test_design_cost_for_6666_m2_is_about_10_million() -> None:
    model = _technology_model()
    design = _detail_item(model, "Проектирование")
    assert design["Сумма"] == pytest.approx(9_999_000, abs=1)
    assert model["budget"]["design"] == pytest.approx(9_999_000, abs=1)


def test_preparation_cost_for_6666_m2_is_about_5_million() -> None:
    model = _technology_model()
    preparation = _detail_item(model, "Подготовительный период")
    assert preparation["Сумма"] == pytest.approx(4_999_500, abs=1)


def test_pile_foundation_without_underground_part_zeroes_underground_part() -> None:
    model = _technology_model()
    underground = _detail_item(model, "Устройство несущих конструкций подземной части")
    assert underground["Сумма"] == 0
    assert "подземная часть отсутствует" in underground["Примечание"].lower()


def test_pile_earthworks_are_lower_than_underground_earthworks() -> None:
    pile_model = _technology_model(foundation_type="сваи", has_underground_part=False)
    underground_model = _technology_model(foundation_type="подземная часть", has_underground_part=True)
    pile_earthworks = _detail_item(pile_model, "Земляные работы")
    underground_earthworks = _detail_item(underground_model, "Земляные работы")
    assert pile_earthworks["Сумма"] < underground_earthworks["Сумма"]
    assert pile_earthworks["Ставка"] == pytest.approx(800)


def test_rough_finish_is_cheaper_than_white_box_and_finished() -> None:
    rough = _technology_model(sellable_finish_level="черновая")
    white_box = _technology_model(sellable_finish_level="white box")
    finished = _technology_model(sellable_finish_level="чистовая")
    rough_amount = _detail_item(rough, "Отделка реализуемых площадей")["Сумма"]
    white_box_amount = _detail_item(white_box, "Отделка реализуемых площадей")["Сумма"]
    finished_amount = _detail_item(finished, "Отделка реализуемых площадей")["Сумма"]
    assert rough_amount < white_box_amount < finished_amount


def test_detailed_budget_total_still_matches_budget_after_technology_adjustments() -> None:
    model = _technology_model()
    assert model["detailed_budget"]["total_budget"] == pytest.approx(model["budget"]["total_budget"], abs=0.05)
