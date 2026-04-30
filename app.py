from __future__ import annotations

from pathlib import Path

import streamlit as st

from backend.main import OUTPUT_DIR, build_financial_model
from backend.models import ProjectInput
from backend.tools.excel_exporter import export_model_to_excel


st.set_page_config(page_title="Агент строительного бюджета v3", layout="wide")
st.title("Агент строительного бюджета v3")
st.caption("Генератор девелоперской финансовой модели с бюджетом, ГПР, продажами, кредитом, ДДС и рисками.")


def _optional_number(value: float) -> float | None:
    return None if value == 0 else value


with st.form("model_form"):
    left, right = st.columns(2)
    with left:
        project_name = st.text_input("Название проекта", value="")
        city = st.text_input("Город", value="")
        object_type = st.text_input("Тип объекта", value="Жилой комплекс")
        object_class = st.text_input("Класс объекта", value="комфорт")
        land_area = st.number_input("Площадь участка", min_value=0.0, value=0.0, step=100.0)
        land_cost = st.number_input("Стоимость земли", min_value=0.0, value=0.0, step=1_000_000.0)
        total_area = st.number_input("Общая площадь", min_value=0.0, value=0.0, step=100.0)
        sellable_area = st.number_input("Продаваемая площадь", min_value=0.0, value=0.0, step=100.0)
        floors = st.number_input("Этажность", min_value=0, value=0, step=1)
    with right:
        sale_price_per_m2 = st.number_input("Цена продажи за м² (необязательно)", min_value=0.0, value=0.0, step=10_000.0)
        st.caption("Можно оставить пустым — агент предложит цену продажи сам.")
        construction_cost_per_m2 = st.number_input(
            "Стоимость строительства за м² (необязательно)",
            min_value=0.0,
            value=0.0,
            step=10_000.0,
        )
        gp_contract_price_per_m2 = st.number_input(
            "Цена генподряда за м² (необязательно)",
            min_value=0.0,
            value=0.0,
            step=10_000.0,
        )
        st.caption("Можно оставить пустым — агент рассчитает себестоимость сам.")
        construction_months = st.number_input("Срок строительства", min_value=0, value=0, step=1)
        sales_months = st.number_input("Срок продаж", min_value=0, value=0, step=1)
        credit_share = st.number_input("Доля кредита", min_value=0.0, value=0.0, step=0.05)
        credit_rate = st.number_input("Ставка кредита", min_value=0.0, value=0.0, step=0.01)
        external_networks_included = st.selectbox("Наружные сети включены?", ["нет", "да"]) == "да"
        gas_only_cooking = st.selectbox("Газ только пищеприготовление?", ["да", "нет"]) == "да"
        foundation_type = st.selectbox("Тип фундамента", ["сваи", "плита", "лента", "подземная часть"])
        has_underground_part = st.selectbox("Есть подземная часть?", ["нет", "да"]) == "да"
        sellable_finish_level = st.selectbox("Отделка реализуемых помещений", ["черновая", "без отделки", "white box", "чистовая"])
        st.markdown("**Ручные корректировки ключевых статей бюджета**")
        st.caption("Если поле пустое или 0, агент использует норматив. Если заполнено — ручное значение имеет приоритет.")
        above_ground_structures_rate_override = st.number_input(
            "Ставка надземных несущих конструкций, ₽/м² — можно оставить пустым",
            min_value=0.0,
            value=0.0,
            step=500.0,
        )
        envelope_roof_walls_rate_override = st.number_input(
            "Ставка ограждающих конструкций / стен / кровли, ₽/м² — можно оставить пустым",
            min_value=0.0,
            value=0.0,
            step=500.0,
        )
        design_cost_override = st.number_input("Проектирование, ₽ — можно оставить пустым", min_value=0.0, value=0.0, step=1_000_000.0)
        preparation_cost_override = st.number_input("Подготовительные работы, ₽ — можно оставить пустым", min_value=0.0, value=0.0, step=1_000_000.0)
        earthworks_rate_override = st.number_input("Земляные работы, ₽/м² — можно оставить пустым", min_value=0.0, value=0.0, step=100.0)
        sellable_finish_rate_override = st.number_input(
            "Ставка отделки реализуемых помещений, ₽/м² NSA",
            min_value=0.0,
            value=0.0,
            step=500.0,
        )
        st.caption("Если поле пустое или 0, агент использует ставку по уровню отделки.")
        st.markdown("**Ручные корректировки свайного основания**")
        st.caption("Если поле пустое или 0, агент использует оптимизированный норматив. Если заполнено — ручное значение имеет приоритет.")
        foundation_optimization_mode = st.selectbox("Режим расчёта свайного основания", ["оптимизированный", "нормативный"])
        pile_foundation_rate_override = st.number_input("Ставка свайного основания, ₽/м²", min_value=0.0, value=0.0, step=500.0)
        pile_foundation_cost_override = st.number_input("Сумма свайного основания, ₽", min_value=0.0, value=0.0, step=1_000_000.0)
        pile_count = st.number_input("Количество свай", min_value=0, value=0, step=1)
        average_pile_depth = st.number_input("Средняя глубина сваи, м", min_value=0.0, value=0.0, step=1.0)
        pile_unit_cost = st.number_input("Стоимость одной сваи, ₽", min_value=0.0, value=0.0, step=10_000.0)
        grillage_rate_override = st.number_input("Ростверк / оголовки, ₽/м²", min_value=0.0, value=0.0, step=500.0)
        st.markdown("**Ручные корректировки инженерных систем**")
        st.caption("Если поле пустое или 0, агент использует оптимизированный норматив. Если заполнено — ручное значение имеет приоритет.")
        plumbing_rate_override = st.number_input("Сантехнические системы, ₽/м²", min_value=0.0, value=0.0, step=500.0)
        heating_rate_override = st.number_input("Отопление / ИТП, ₽/м²", min_value=0.0, value=0.0, step=500.0)
        electrical_rate_override = st.number_input("Электроснабжение, ₽/м²", min_value=0.0, value=0.0, step=500.0)
        low_voltage_rate_override = st.number_input("Слаботочные системы, ₽/м²", min_value=0.0, value=0.0, step=250.0)
        ventilation_rate_override = st.number_input("Вентиляция / дымоудаление, ₽/м²", min_value=0.0, value=0.0, step=250.0)
        budget_format = st.selectbox("Формат бюджета", ["Укрупнённый", "Детальный по статьям"])

    submitted = st.form_submit_button("Сформировать финансовую модель")

if submitted:
    project_input = ProjectInput(
        project_name=project_name or None,
        city=city or None,
        object_type=object_type or None,
        object_class=object_class or None,
        land_area=_optional_number(land_area),
        land_cost=land_cost,
        total_area=_optional_number(total_area),
        sellable_area=_optional_number(sellable_area),
        floors=int(floors) if floors else None,
        sale_price_per_m2=_optional_number(sale_price_per_m2),
        construction_cost_per_m2=_optional_number(construction_cost_per_m2),
        gp_contract_price_per_m2=_optional_number(gp_contract_price_per_m2),
        construction_months=int(construction_months) if construction_months else None,
        sales_months=int(sales_months) if sales_months else None,
        credit_share=_optional_number(credit_share),
        credit_rate=_optional_number(credit_rate),
        external_networks_included=external_networks_included,
        gas_only_cooking=gas_only_cooking,
        foundation_type=foundation_type,
        has_underground_part=has_underground_part,
        sellable_finish_level=sellable_finish_level,
        above_ground_structures_rate_override=_optional_number(above_ground_structures_rate_override),
        envelope_roof_walls_rate_override=_optional_number(envelope_roof_walls_rate_override),
        design_cost_override=_optional_number(design_cost_override),
        preparation_cost_override=_optional_number(preparation_cost_override),
        earthworks_rate_override=_optional_number(earthworks_rate_override),
        sellable_finish_rate_override=_optional_number(sellable_finish_rate_override),
        pile_foundation_rate_override=_optional_number(pile_foundation_rate_override),
        pile_foundation_cost_override=_optional_number(pile_foundation_cost_override),
        pile_count=int(pile_count) if pile_count else None,
        average_pile_depth=_optional_number(average_pile_depth),
        pile_unit_cost=_optional_number(pile_unit_cost),
        grillage_rate_override=_optional_number(grillage_rate_override),
        foundation_optimization_mode=foundation_optimization_mode,
        plumbing_rate_override=_optional_number(plumbing_rate_override),
        heating_rate_override=_optional_number(heating_rate_override),
        electrical_rate_override=_optional_number(electrical_rate_override),
        low_voltage_rate_override=_optional_number(low_voltage_rate_override),
        ventilation_rate_override=_optional_number(ventilation_rate_override),
    )
    model = build_financial_model(project_input)
    excel_path = export_model_to_excel(model, OUTPUT_DIR)

    budget = model["budget"]
    economics = model["economics"]
    credit = model["credit"]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Итоговый бюджет", f"{budget['total_budget']:,.0f}")
    col2.metric("СМР", f"{budget['cmr']:,.0f}")
    col3.metric("Бюджет на 1 м² общей", f"{economics['budget_per_total_m2']:,.0f}")
    col4.metric("Выручка", f"{economics['revenue']:,.0f}")

    col5, col6, col7, col8 = st.columns(4)
    col5.metric("Прибыль после процентов", f"{economics['profit_after_interest']:,.0f}")
    col6.metric("Маржа после процентов", f"{economics['margin_after_interest']:.1%}")
    col7.metric("Кредит", f"{credit['max_balance']:,.0f}")
    col8.metric("Проценты", f"{credit['total_interest']:,.0f}")

    col9, col10, col11, col12 = st.columns(4)
    col9.metric("Доля продаваемой площади", f"{economics['sellable_ratio']:.1%}")
    col10.metric("Бюджет на 1 м² продаваемой", f"{economics['budget_per_sellable_m2']:,.0f}")
    col11.metric("Собственные средства", f"{economics['total_equity_required']:,.0f}")
    col12.metric("Минимальный DSCR", model["dscr"]["minimum_dscr_after_sales_start"] or "нет обслуживания долга")

    if economics["sellable_ratio"] < 0.65:
        st.error("Продаваемая площадь слишком низкая: доля продаваемой площади ниже 65%.")
    elif economics["sellable_ratio"] < 0.72:
        st.warning("Продаваемая площадь ниже целевого уровня: доля продаваемой площади меньше 72%.")

    st.subheader("Расчёт цены продажи")
    price_col1, price_col2, price_col3, price_col4 = st.columns(4)
    price_col1.metric("Предварительная рекомендованная цена", f"{model['preliminary_recommended_price_per_m2']:,.0f}")
    price_col2.metric("Источник цены продажи", model["sale_price_source"])
    price_col3.metric("Рыночный ориентир", f"{model['market_price_per_m2']:,.0f}")
    price_col4.metric("Цена безубыточности", f"{model['break_even_price_per_m2']:,.0f}")
    price_col5, price_col6, price_col7, price_col8 = st.columns(4)
    price_col5.metric("Цена для целевой маржи по фактическим процентам", f"{model['final_target_margin_price_per_m2']:,.0f}")
    price_col6.metric("Финальная рекомендованная цена", f"{model['final_recommended_price_per_m2']:,.0f}")
    price_col7.metric("Разница к рынку", f"{model['price_gap_to_market']:,.0f}")
    price_col8.metric("Итераций расчёта цены", model["price_iteration_count"])
    for warning in model["price_estimation_warnings"]:
        st.warning(warning)

    st.subheader("Что нужно для прохождения проекта по рынку")
    optimization = model["optimization"]
    opt_col1, opt_col2, opt_col3, opt_col4, opt_col5 = st.columns(5)
    opt_col1.metric("Снизить бюджет, млн ₽", f"{optimization['required_budget_reduction_mln_rub']:,.1f}")
    opt_col2.metric("Целевая СМР за м²", f"{optimization['required_cmr_cost_per_m2_for_market_price']:,.0f}")
    opt_col3.metric("Нужная продаваемая площадь", f"{optimization['required_sellable_area_for_market_price']:,.0f}")
    opt_col4.metric("Цена для целевой маржи", f"{optimization['required_sale_price_for_target_margin']:,.0f}")
    opt_col5.metric("Разница к рынку", f"{optimization['gap_to_market_price']:,.0f}")
    st.write(f"**Что реалистичнее:** {optimization['most_realistic_option']}")
    for recommendation in optimization["recommendations"]:
        st.info(recommendation)

    st.subheader("Автоматический план улучшения проекта")
    improvement_plan = model["improvement_plan"]
    st.metric("Целевое снижение бюджета", f"{improvement_plan['target_budget_reduction']:,.0f}")
    if improvement_plan["summary"]:
        st.write(improvement_plan["summary"])
    if improvement_plan["improvement_items"]:
        st.write("**Потенциал экономии по статьям**")
        st.dataframe(improvement_plan["improvement_items"], use_container_width=True)
    else:
        st.success("Проект проходит по рыночной цене: обязательное снижение бюджета не требуется.")

    plan_col1, plan_col2 = st.columns(2)
    with plan_col1:
        st.write("**Планировочные улучшения**")
        for item in improvement_plan["planning_improvements"]:
            st.write(f"- {item}")
        st.write("**Коммерческие улучшения**")
        for item in improvement_plan["sales_improvements"]:
            st.write(f"- {item}")
    with plan_col2:
        st.write("**Финансовые улучшения**")
        for item in improvement_plan["financing_improvements"]:
            st.write(f"- {item}")
        st.write("**Приоритетные действия**")
        for index, item in enumerate(improvement_plan["priority_actions"], start=1):
            st.write(f"{index}. {item}")
    for warning in improvement_plan["warnings"]:
        st.warning(warning)

    st.subheader("Расчёт себестоимости")
    components = model["cost_estimation_components"]
    coefficients = model["cost_estimation_coefficients"]
    cost_col1, cost_col2, cost_col3 = st.columns(3)
    cost_col1.metric("Расчётная себестоимость СМР за м²", f"{model['estimated_cmr_cost_per_m2']:,.0f}")
    cost_col2.metric("Источник себестоимости", model["cmr_cost_source"])
    cost_col3.metric("Базовая ставка", f"{components['base_cost_per_m2']:,.0f}")
    coeff_col1, coeff_col2, coeff_col3, coeff_col4 = st.columns(4)
    coeff_col1.metric("Коэффициент города", f"{coefficients['city_coefficient']:.2f}")
    coeff_col2.metric("Коэффициент этажности", f"{coefficients['floors_coefficient']:.2f}")
    coeff_col3.metric("Коэффициент масштаба", f"{coefficients['area_coefficient']:.2f}")
    coeff_col4.metric("Коэффициент инженерии", f"{coefficients['engineering_coefficient']:.2f}")

    st.subheader("Бюджет проекта")
    if budget_format == "Детальный по статьям":
        st.write("**Ключевые корректировки бюджета**")
        st.dataframe(model["detailed_budget"]["budget_adjustments"], use_container_width=True)
        chapter_rows = [
            {"Глава": row["Глава"], "Статья": row["Статья"], "Сумма": row["Сумма"]}
            for row in model["detailed_budget"]["chapter_totals"]
        ]
        st.write("**Итоги по главам**")
        st.dataframe(chapter_rows, use_container_width=True)
        st.write("**Детальная структура бюджета**")
        st.dataframe(model["detailed_budget"]["items"], use_container_width=True)
        split = model["detailed_budget"]["split_totals"]
        split_col1, split_col2, split_col3, split_col4 = st.columns(4)
        split_col1.metric("Материалы", f"{split['materials']:,.0f}")
        split_col2.metric("Работы", f"{split['works']:,.0f}")
        split_col3.metric("Механизмы", f"{split['machinery']:,.0f}")
        split_col4.metric("Накладные", f"{split['overheads']:,.0f}")
    else:
        st.dataframe(budget["items"], use_container_width=True)

    st.subheader("График производства работ")
    gpr_summary = model["gpr_summary"]
    gpr_col1, gpr_col2, gpr_col3, gpr_col4 = st.columns(4)
    gpr_col1.metric("Длительность строительства", f"{gpr_summary['construction_months']} мес.")
    gpr_col2.metric("Пиковый месяц CAPEX", f"{gpr_summary['peak_capex_month']} мес.")
    gpr_col3.metric("Средний CAPEX в месяц", f"{gpr_summary['average_monthly_capex']:,.0f}")
    gpr_col4.metric("Окончание основных работ", f"{gpr_summary['main_work_end_month']} мес.")
    if gpr_summary["is_short_schedule"]:
        st.warning("Срок строительства выглядит слишком коротким: проверьте реализуемость графика, поставки и сезонность.")
    st.dataframe(
        [
            {
                "Этап": row["Этап"],
                "Начало, мес.": row["Начало, мес."],
                "Длительность, мес.": row["Длительность, мес."],
                "Окончание, мес.": row["Окончание, мес."],
                "Стоимость": row["Стоимость"],
            }
            for row in model["work_schedule"]["stages"]
        ],
        use_container_width=True,
    )

    st.subheader("Риски")
    risk_levels = {"high": "Высокий", "medium": "Средний", "low": "Низкий", "ok": "Норма"}
    for risk in model["risks"]:
        level = risk_levels.get(risk["level"], risk["level"])
        st.write(f"**{level}** — {risk['title']}: {risk['description']}")

    st.subheader("Сценарный анализ")
    scenario_rows = []
    for scenario in model["scenarios"]:
        scenario_rows.append(
            {
                "Сценарий": scenario["scenario_name"],
                "Выручка": scenario["revenue"],
                "Итоговый бюджет": scenario["total_budget"],
                "Прибыль до процентов": scenario["profit_before_interest"],
                "Прибыль после процентов": scenario["profit_after_interest"],
                "Маржа после процентов": f"{scenario['margin_after_interest']:.1%}",
                "Максимальный кредит": scenario["max_credit_balance"],
                "Собственные средства": scenario["total_equity_required"],
                "Минимальный DSCR": scenario["minimum_dscr_after_sales_start"],
                "Месяцев DSCR ниже 1.2": scenario["months_below_1_2"],
                "Оценка маржи": scenario["margin_assessment"],
                "Оценка DSCR": scenario["dscr_assessment"],
            }
        )
    st.dataframe(scenario_rows, use_container_width=True)
    for scenario in model["scenarios"]:
        margin_label = {"red": "красный", "yellow": "желтый", "green": "зеленый"}.get(
            scenario["margin_color"],
            "серый",
        )
        dscr_label = {"red": "красный", "green": "зеленый", "gray": "серый"}.get(
            scenario["dscr_color"],
            "серый",
        )
        st.write(
            f"{scenario['scenario_name']}: маржа {scenario['margin_assessment']} ({margin_label}); "
            f"DSCR {scenario['dscr_assessment']} ({dscr_label})"
        )

    with Path(excel_path).open("rb") as handle:
        st.download_button(
            "Скачать Excel",
            data=handle.read(),
            file_name=Path(excel_path).name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
