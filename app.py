from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from backend.auth import USERS_FILE, authenticate_user, load_users
from backend.main import OUTPUT_DIR, build_financial_model
from backend.models import ProjectInput
from backend.project_history import PROJECTS_DIR, load_project_history, save_project_metadata
from backend.tools.excel_exporter import export_model_to_excel


st.set_page_config(page_title="ИИ-агент девелоперской модели", layout="wide")

APP_VERSION = os.getenv("APP_VERSION", "3.0.0")


MENU_ITEMS = (
    "Главная",
    "Новый расчёт",
    "Бюджет",
    "ГПР",
    "Продажи",
    "Кредит и ДДС",
    "DSCR",
    "Сценарии",
    "Оптимизация",
    "План улучшений",
    "История проектов",
    "Скачать Excel",
    "Настройки",
)

FINISH_LABEL_TO_VALUE = {
    "черновая": "черновая",
    "без отделки": "без отделки",
    "предчистовая": "white box",
    "чистовая": "чистовая",
}


def format_number(value: Any, digits: int = 0) -> str:
    if value is None:
        return "нет данных"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    formatted = f"{number:,.{digits}f}".replace(",", " ").replace(".", ",")
    if digits == 0:
        formatted = formatted.split(",")[0]
    return formatted


def format_rub(value: Any) -> str:
    return f"{format_number(value)} ₽"


def format_percent(value: Any) -> str:
    if value is None:
        return "нет данных"
    return f"{format_number(float(value) * 100, 1)}%"


def format_area(value: Any) -> str:
    return f"{format_number(value)} м²"


def optional_number(value: float) -> float | None:
    return None if value == 0 else value


def optional_int(value: int) -> int | None:
    return None if value == 0 else int(value)


def model() -> dict[str, Any] | None:
    return st.session_state.get("model")


def excel_path() -> Path | None:
    value = st.session_state.get("excel_path")
    return Path(value) if value else None


def current_user() -> dict[str, str] | None:
    return st.session_state.get("user")


def is_authenticated() -> bool:
    return current_user() is not None


def show_login() -> None:
    apply_style()
    hero()
    st.subheader("Вход в кабинет")
    users = load_users()
    if not users:
        st.warning("В users.json пока нет пользователей. Администратору нужно добавить хотя бы одного пользователя.")
        st.code(
            ".\\.venv\\Scripts\\python.exe -c \"from backend.auth import hash_password; print(hash_password('ВАШ_ПАРОЛЬ'))\"",
            language="powershell",
        )
        st.info(
            "Скопируйте полученный хэш в users.json. Пароль в открытом виде хранить нельзя. "
            "Роли: admin или user."
        )
        st.code(
            '{\n  "users": [\n    {\n      "login": "ivan",\n      "password_hash": "pbkdf2_sha256$...",\n      "role": "user"\n    }\n  ]\n}',
            language="json",
        )
        return

    with st.form("login_form"):
        login = st.text_input("Логин")
        password = st.text_input("Пароль", type="password")
        submitted = st.form_submit_button("Войти", use_container_width=True)
    if not submitted:
        return
    user = authenticate_user(login, password)
    if user is None:
        st.error("Неверный логин или пароль.")
        return
    st.session_state["user"] = user
    st.success("Вход выполнен.")
    st.rerun()


def apply_style() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
        }
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #102A2C 0%, #173F42 58%, #DFAF68 180%);
        }
        section[data-testid="stSidebar"] * {
            color: #F6F1E7;
        }
        .hero {
            padding: 28px 30px;
            border-radius: 24px;
            background:
                radial-gradient(circle at top right, rgba(223, 175, 104, 0.32), transparent 34%),
                linear-gradient(135deg, #102A2C 0%, #1B4B4E 58%, #E7C27C 140%);
            color: #F9F4EA;
            box-shadow: 0 18px 44px rgba(16, 42, 44, 0.18);
            margin-bottom: 22px;
        }
        .hero h1 {
            margin: 0 0 8px 0;
            font-size: 44px;
            line-height: 1.05;
            letter-spacing: -0.04em;
        }
        .hero p {
            margin: 0;
            font-size: 18px;
            opacity: 0.9;
        }
        .metric-card {
            min-height: 130px;
            padding: 18px 18px 16px;
            border: 1px solid rgba(22, 51, 52, 0.12);
            border-radius: 20px;
            background: linear-gradient(180deg, #FFFFFF 0%, #F7F3EA 100%);
            box-shadow: 0 10px 26px rgba(32, 46, 45, 0.08);
        }
        .metric-label {
            font-size: 13px;
            color: #61706E;
            margin-bottom: 12px;
        }
        .metric-value {
            font-size: 25px;
            font-weight: 760;
            color: #102A2C;
            line-height: 1.1;
        }
        .section-card {
            padding: 18px;
            border-radius: 18px;
            border: 1px solid rgba(22, 51, 52, 0.10);
            background: #FFFFFF;
            box-shadow: 0 8px 24px rgba(32, 46, 45, 0.05);
            margin-bottom: 16px;
        }
        .hint {
            padding: 14px 16px;
            border-radius: 16px;
            background: #F4EAD7;
            color: #4B3A20;
            border: 1px solid rgba(223, 175, 104, 0.35);
        }
        div[data-testid="stMetric"] {
            padding: 16px;
            border-radius: 18px;
            border: 1px solid rgba(22, 51, 52, 0.10);
            background: #FFFFFF;
            box-shadow: 0 8px 22px rgba(32, 46, 45, 0.05);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def hero() -> None:
    st.markdown(
        """
        <div class="hero">
            <h1>ИИ-агент девелоперской модели</h1>
            <p>Бюджет, ГПР, продажи, кредит, ДДС, DSCR, сценарии и оптимизация проекта</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: str) -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def dashboard_cards(current_model: dict[str, Any]) -> None:
    economics = current_model["economics"]
    budget = current_model["budget"]
    credit = current_model["credit"]
    dscr = current_model["dscr"]
    values = (
        ("Итоговый бюджет", format_rub(budget["total_budget"])),
        ("СМР", format_rub(budget["cmr"])),
        ("Выручка", format_rub(economics["revenue"])),
        ("Прибыль", format_rub(economics["profit_after_interest"])),
        ("Маржа", format_percent(economics["margin_after_interest"])),
        ("Пик кредита", format_rub(credit["max_balance"])),
        ("Собственные средства", format_rub(economics["total_equity_required"])),
        ("Minimum DSCR", format_number(dscr["minimum_dscr_after_sales_start"], 2)),
    )
    for row_start in range(0, len(values), 4):
        columns = st.columns(4)
        for column, (label, value) in zip(columns, values[row_start : row_start + 4], strict=True):
            with column:
                metric_card(label, value)


def result_dashboard(current_model: dict[str, Any]) -> None:
    economics = current_model["economics"]
    budget = current_model["budget"]
    credit = current_model["credit"]
    dscr = current_model["dscr"]
    metrics = (
        ("Итоговый бюджет", format_rub(budget["total_budget"])),
        ("Бюджет на 1 м² GBA", format_rub(economics["budget_per_total_m2"])),
        ("Бюджет на 1 м² NSA", format_rub(economics["budget_per_sellable_m2"])),
        ("Выручка", format_rub(economics["revenue"])),
        ("Прибыль после процентов", format_rub(economics["profit_after_interest"])),
        ("Маржа после процентов", format_percent(economics["margin_after_interest"])),
        ("Собственные средства", format_rub(economics["total_equity_required"])),
        ("Пик кредита", format_rub(credit["max_balance"])),
        ("Minimum DSCR", format_number(dscr["minimum_dscr_after_sales_start"], 2)),
    )
    for row_start in range(0, len(metrics), 3):
        columns = st.columns(3)
        for column, (label, value) in zip(columns, metrics[row_start : row_start + 3], strict=False):
            with column:
                metric_card(label, value)


def require_model() -> dict[str, Any] | None:
    current_model = model()
    if current_model is None:
        st.markdown('<div class="hint">Создайте новый расчёт во вкладке Новый расчёт.</div>', unsafe_allow_html=True)
        return None
    return current_model


def make_chart_frame(rows: list[dict[str, Any]], columns: dict[str, str]) -> pd.DataFrame:
    return pd.DataFrame([{label: row.get(key) for key, label in columns.items()} for row in rows])


def show_home() -> None:
    hero()
    current_model = model()
    if current_model is None:
        st.markdown('<div class="hint">Создайте новый расчёт во вкладке Новый расчёт.</div>', unsafe_allow_html=True)
        return
    st.subheader(current_model["input"].get("project_name") or "Текущий расчёт")
    dashboard_cards(current_model)
    st.divider()
    show_overview_charts(current_model)


def show_overview_charts(current_model: dict[str, Any]) -> None:
    left, right = st.columns(2)
    with left:
        st.subheader("Бюджет по главам")
        chapter_df = pd.DataFrame(
            {
                "Глава": [row["Статья"] for row in current_model["detailed_budget"]["chapter_totals"]],
                "Сумма": [row["Сумма"] for row in current_model["detailed_budget"]["chapter_totals"]],
            }
        )
        st.bar_chart(chapter_df, x="Глава", y="Сумма", use_container_width=True)
    with right:
        st.subheader("Накопленный CAPEX")
        capex_df = pd.DataFrame(
            {
                "Месяц": list(range(1, len(current_model["work_schedule"]["cumulative_capex"]) + 1)),
                "Накопленный CAPEX": current_model["work_schedule"]["cumulative_capex"],
            }
        )
        st.line_chart(capex_df, x="Месяц", y="Накопленный CAPEX", use_container_width=True)


def show_new_calculation() -> None:
    st.header("Новый расчёт")
    st.caption("Заполните ключевые параметры проекта. Поля с ручными ставками можно оставить пустыми.")

    with st.form("model_form"):
        st.subheader("А. Основные параметры")
        col1, col2 = st.columns(2)
        with col1:
            project_name = st.text_input("Название проекта", value="")
            city = st.text_input("Город", value="")
            object_type = st.text_input("Тип объекта", value="Жилой дом")
        with col2:
            object_class = st.text_input("Класс объекта", value="комфорт")
            land_area = st.number_input("Площадь участка", min_value=0.0, value=0.0, step=100.0)
            land_cost = st.number_input("Стоимость земли", min_value=0.0, value=0.0, step=1_000_000.0)

        st.subheader("Б. Площади и продукт")
        col1, col2, col3 = st.columns(3)
        with col1:
            total_area = st.number_input("Общая площадь", min_value=0.0, value=0.0, step=100.0)
            sellable_area = st.number_input("Продаваемая площадь", min_value=0.0, value=0.0, step=100.0)
        with col2:
            floors = st.number_input("Этажность", min_value=0, value=0, step=1)
            sellable_finish_label = st.selectbox(
                "Уровень отделки реализуемых помещений",
                list(FINISH_LABEL_TO_VALUE),
            )
        with col3:
            sale_price_per_m2 = st.number_input("Цена продажи м², необязательно", min_value=0.0, value=0.0, step=10_000.0)
            st.caption("Можно оставить пустым: агент предложит цену продажи сам.")

        st.subheader("В. Строительство")
        col1, col2, col3 = st.columns(3)
        with col1:
            foundation_type = st.selectbox("Тип фундамента", ["сваи", "плита", "лента", "подземная часть"])
            foundation_optimization_mode = st.selectbox("Режим расчёта свайного основания", ["оптимизированный", "нормативный"])
            has_underground_part = st.selectbox("Есть подземная часть?", ["нет", "да"]) == "да"
        with col2:
            external_networks_included = st.selectbox("Наружные сети включены?", ["нет", "да"]) == "да"
            gas_only_cooking = st.selectbox("Газ только пищеприготовление?", ["да", "нет"]) == "да"
        with col3:
            construction_months = st.number_input("Срок строительства", min_value=0, value=0, step=1)
            sales_months = st.number_input("Срок продаж", min_value=0, value=0, step=1)

        st.subheader("Г. Ручные корректировки бюджета")
        st.caption("Если поле пустое или 0, агент использует норматив или собственный расчёт.")
        col1, col2, col3 = st.columns(3)
        with col1:
            gp_contract_price_per_m2 = st.number_input("Цена генподряда м²", min_value=0.0, value=0.0, step=10_000.0)
            construction_cost_per_m2 = st.number_input("Стоимость строительства м²", min_value=0.0, value=0.0, step=10_000.0)
            design_cost_override = st.number_input("Проектирование, ₽", min_value=0.0, value=0.0, step=1_000_000.0)
        with col2:
            preparation_cost_override = st.number_input("Подготовительные работы, ₽", min_value=0.0, value=0.0, step=1_000_000.0)
            above_ground_structures_rate_override = st.number_input("Ставка надземных несущих конструкций, ₽/м²", min_value=0.0, value=0.0, step=500.0)
            envelope_roof_walls_rate_override = st.number_input("Ставка ограждающих конструкций / стен / кровли, ₽/м²", min_value=0.0, value=0.0, step=500.0)
        with col3:
            earthworks_rate_override = st.number_input("Земляные работы, ₽/м²", min_value=0.0, value=0.0, step=100.0)
            sellable_finish_rate_override = st.number_input("Ставка отделки реализуемых помещений, ₽/м² NSA", min_value=0.0, value=0.0, step=500.0)
            st.caption("Если поле пустое или 0, агент использует ставку по уровню отделки.")

        st.subheader("Д. Сваи")
        col1, col2, col3 = st.columns(3)
        with col1:
            pile_foundation_rate_override = st.number_input("Ставка свайного основания, ₽/м²", min_value=0.0, value=0.0, step=500.0)
            pile_foundation_cost_override = st.number_input("Сумма свайного основания, ₽", min_value=0.0, value=0.0, step=1_000_000.0)
        with col2:
            pile_count = st.number_input("Количество свай", min_value=0, value=0, step=1)
            pile_unit_cost = st.number_input("Стоимость одной сваи", min_value=0.0, value=0.0, step=10_000.0)
        with col3:
            average_pile_depth = st.number_input("Средняя глубина сваи, м", min_value=0.0, value=0.0, step=1.0)
            grillage_rate_override = st.number_input("Ростверк / оголовки, ₽/м²", min_value=0.0, value=0.0, step=500.0)

        st.subheader("Е. Инженерия")
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            plumbing_rate_override = st.number_input("Сантехнические системы, ₽/м²", min_value=0.0, value=0.0, step=500.0)
        with col2:
            heating_rate_override = st.number_input("Отопление / ИТП, ₽/м²", min_value=0.0, value=0.0, step=500.0)
        with col3:
            electrical_rate_override = st.number_input("Электроснабжение, ₽/м²", min_value=0.0, value=0.0, step=500.0)
        with col4:
            low_voltage_rate_override = st.number_input("Слаботочные системы, ₽/м²", min_value=0.0, value=0.0, step=250.0)
        with col5:
            ventilation_rate_override = st.number_input("Вентиляция / дымоудаление, ₽/м²", min_value=0.0, value=0.0, step=250.0)

        st.subheader("Ж. Финансирование")
        col1, col2 = st.columns(2)
        with col1:
            credit_share = st.number_input("Доля кредита", min_value=0.0, value=0.0, step=0.05)
        with col2:
            credit_rate = st.number_input("Ставка кредита", min_value=0.0, value=0.0, step=0.01)

        submitted = st.form_submit_button("Сформировать финансовую модель", use_container_width=True)

    if not submitted:
        return

    errors = validate_required_fields(project_name, city, object_type, object_class, total_area, sellable_area, floors)
    if errors:
        for error in errors:
            st.error(error)
        st.info("Заполните обязательные поля и повторите расчёт. Ручные ставки, цена продажи и цена строительства могут оставаться пустыми.")
        return

    try:
        project_input = ProjectInput(
            project_name=project_name or None,
            city=city or None,
            object_type=object_type or None,
            object_class=object_class or None,
            land_area=optional_number(land_area),
            land_cost=land_cost,
            total_area=optional_number(total_area),
            sellable_area=optional_number(sellable_area),
            floors=optional_int(floors),
            sale_price_per_m2=optional_number(sale_price_per_m2),
            construction_cost_per_m2=optional_number(construction_cost_per_m2),
            gp_contract_price_per_m2=optional_number(gp_contract_price_per_m2),
            construction_months=optional_int(construction_months),
            sales_months=optional_int(sales_months),
            credit_share=optional_number(credit_share),
            credit_rate=optional_number(credit_rate),
            external_networks_included=external_networks_included,
            gas_only_cooking=gas_only_cooking,
            foundation_type=foundation_type,
            has_underground_part=has_underground_part,
            sellable_finish_level=FINISH_LABEL_TO_VALUE[sellable_finish_label],
            above_ground_structures_rate_override=optional_number(above_ground_structures_rate_override),
            envelope_roof_walls_rate_override=optional_number(envelope_roof_walls_rate_override),
            design_cost_override=optional_number(design_cost_override),
            preparation_cost_override=optional_number(preparation_cost_override),
            earthworks_rate_override=optional_number(earthworks_rate_override),
            sellable_finish_rate_override=optional_number(sellable_finish_rate_override),
            pile_foundation_rate_override=optional_number(pile_foundation_rate_override),
            pile_foundation_cost_override=optional_number(pile_foundation_cost_override),
            pile_count=optional_int(pile_count),
            average_pile_depth=optional_number(average_pile_depth),
            pile_unit_cost=optional_number(pile_unit_cost),
            grillage_rate_override=optional_number(grillage_rate_override),
            foundation_optimization_mode=foundation_optimization_mode,
            plumbing_rate_override=optional_number(plumbing_rate_override),
            heating_rate_override=optional_number(heating_rate_override),
            electrical_rate_override=optional_number(electrical_rate_override),
            low_voltage_rate_override=optional_number(low_voltage_rate_override),
            ventilation_rate_override=optional_number(ventilation_rate_override),
        )
        with st.spinner("Формируем финансовую модель, графики и Excel..."):
            calculated_model = build_financial_model(project_input)
            calculated_excel_path = export_model_to_excel(calculated_model, OUTPUT_DIR)
            metadata = save_project_metadata(
                model=calculated_model,
                excel_path=calculated_excel_path,
                username=(current_user() or {}).get("login", "unknown"),
            )
        st.session_state["model"] = calculated_model
        st.session_state["excel_path"] = str(calculated_excel_path)
        st.session_state["project_metadata"] = metadata
        st.success("Финансовая модель сформирована.")
        result_dashboard(calculated_model)
    except Exception as exc:  # noqa: BLE001
        st.error("Расчёт не прошёл. Проверьте площади, сроки, ставки и повторите попытку.")
        st.info(f"Техническая подсказка: {exc}")


def validate_required_fields(
    project_name: str,
    city: str,
    object_type: str,
    object_class: str,
    total_area: float,
    sellable_area: float,
    floors: int,
) -> list[str]:
    errors: list[str] = []
    if not project_name.strip():
        errors.append("Укажите название проекта.")
    if not city.strip():
        errors.append("Укажите город.")
    if not object_type.strip():
        errors.append("Укажите тип объекта.")
    if not object_class.strip():
        errors.append("Укажите класс объекта.")
    if total_area <= 0:
        errors.append("Укажите общую площадь больше 0.")
    if sellable_area <= 0:
        errors.append("Укажите продаваемую площадь больше 0.")
    if sellable_area > total_area:
        errors.append("Продаваемая площадь не должна быть больше общей площади.")
    if floors <= 0:
        errors.append("Укажите этажность больше 0.")
    return errors


def show_budget() -> None:
    current_model = require_model()
    if current_model is None:
        return
    st.header("Бюджет")
    result_dashboard(current_model)
    st.subheader("Итоги по главам")
    st.dataframe(format_budget_table(current_model["detailed_budget"]["chapter_totals"]), use_container_width=True)
    st.subheader("Детальный бюджет по главам")
    st.dataframe(format_budget_table(current_model["detailed_budget"]["items"]), use_container_width=True, height=560)
    st.subheader("Материалы / работы / механизмы / накладные")
    split = current_model["detailed_budget"]["split_totals"]
    cols = st.columns(4)
    for column, (label, key) in zip(
        cols,
        (("Материалы", "materials"), ("Работы", "works"), ("Механизмы", "machinery"), ("Накладные", "overheads")),
        strict=True,
    ):
        column.metric(label, format_rub(split[key]))
    st.subheader("Ключевые корректировки бюджета")
    st.dataframe(format_budget_table(current_model["detailed_budget"]["budget_adjustments"]), use_container_width=True)


def format_budget_table(rows: list[dict[str, Any]]) -> pd.DataFrame:
    money_columns = {
        "Сумма",
        "Нормативная сумма",
        "Разница к нормативу",
        "Материалы, ₽",
        "Работы, ₽",
        "Механизмы, ₽",
        "Накладные, ₽",
    }
    formatted_rows = []
    for row in rows:
        formatted = {}
        for key, value in row.items():
            if key in money_columns:
                formatted[key] = format_rub(value)
            elif key in {"База"}:
                formatted[key] = format_number(value, 2)
            elif key in {"Ставка", "Нормативная ставка"} and isinstance(value, int | float):
                formatted[key] = format_rub(value)
            else:
                formatted[key] = value
        formatted_rows.append(formatted)
    return pd.DataFrame(formatted_rows)


def show_gpr() -> None:
    current_model = require_model()
    if current_model is None:
        return
    st.header("ГПР")
    summary = current_model["gpr_summary"]
    cols = st.columns(4)
    cols[0].metric("Срок строительства", f"{summary['construction_months']} мес.")
    cols[1].metric("Пиковый месяц CAPEX", f"{summary['peak_capex_month']} мес.")
    cols[2].metric("Средний CAPEX", format_rub(summary["average_monthly_capex"]))
    cols[3].metric("Окончание основных работ", f"{summary['main_work_end_month']} мес.")
    if summary["is_short_schedule"]:
        st.warning("Срок строительства выглядит слишком коротким. Проверьте реализуемость графика, поставки и сезонность.")

    capex_df = pd.DataFrame(
        {
            "Месяц": list(range(1, len(current_model["work_schedule"]["month_totals"]) + 1)),
            "CAPEX за месяц": current_model["work_schedule"]["month_totals"],
            "Накопленный CAPEX": current_model["work_schedule"]["cumulative_capex"],
        }
    )
    left, right = st.columns(2)
    with left:
        st.subheader("CAPEX по месяцам")
        st.bar_chart(capex_df, x="Месяц", y="CAPEX за месяц", use_container_width=True)
    with right:
        st.subheader("Накопленный CAPEX")
        st.line_chart(capex_df, x="Месяц", y="Накопленный CAPEX", use_container_width=True)
    st.subheader("Помесячный график работ")
    schedule_rows = []
    for row in current_model["work_schedule"]["stages"]:
        schedule_rows.append(
            {
                "Этап": row["Этап"],
                "Начало, мес.": row["Начало, мес."],
                "Длительность, мес.": row["Длительность, мес."],
                "Окончание, мес.": row["Окончание, мес."],
                "Стоимость": format_rub(row["Стоимость"]),
            }
        )
    st.dataframe(pd.DataFrame(schedule_rows), use_container_width=True)


def show_sales() -> None:
    current_model = require_model()
    if current_model is None:
        return
    st.header("Продажи")
    sales_df = make_chart_frame(
        current_model["sales_plan"],
        {
            "month": "Месяц",
            "sold_area": "Проданная площадь",
            "revenue": "Выручка",
            "accumulated_revenue": "Выручка накопительно",
        },
    )
    left, right = st.columns(2)
    with left:
        st.subheader("План продаж по месяцам")
        st.bar_chart(sales_df, x="Месяц", y="Выручка", use_container_width=True)
    with right:
        st.subheader("Проданная площадь")
        st.bar_chart(sales_df, x="Месяц", y="Проданная площадь", use_container_width=True)
    st.dataframe(format_sales_table(current_model["sales_plan"]), use_container_width=True)


def format_sales_table(rows: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Месяц": row["month"],
                "Проданная площадь": format_area(row["sold_area"]),
                "Выручка": format_rub(row["revenue"]),
                "Площадь накопительно": format_area(row["accumulated_sold_area"]),
                "Выручка накопительно": format_rub(row["accumulated_revenue"]),
            }
            for row in rows
        ]
    )


def show_credit_cashflow() -> None:
    current_model = require_model()
    if current_model is None:
        return
    st.header("Кредит и ДДС")
    credit_rows = current_model["credit"]["schedule"]
    credit_df = make_chart_frame(
        credit_rows,
        {
            "month": "Месяц",
            "closing_balance": "Остаток кредита",
            "drawdown": "Выборка",
            "interest": "Проценты",
            "repayment": "Погашение",
        },
    )
    left, right = st.columns(2)
    with left:
        st.subheader("Остаток кредита по месяцам")
        st.line_chart(credit_df, x="Месяц", y="Остаток кредита", use_container_width=True)
    with right:
        st.subheader("Выборка и погашение")
        st.bar_chart(credit_df, x="Месяц", y=["Выборка", "Погашение"], use_container_width=True)
    st.subheader("График кредита")
    st.dataframe(format_credit_table(credit_rows), use_container_width=True)
    st.subheader("ДДС")
    st.dataframe(format_cashflow_table(current_model["cashflow"]), use_container_width=True, height=520)


def format_credit_table(rows: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Месяц": row["month"],
                "Остаток на начало": format_rub(row["opening_balance"]),
                "Выборка": format_rub(row["drawdown"]),
                "Проценты": format_rub(row["interest"]),
                "Погашение": format_rub(row["repayment"]),
                "Остаток на конец": format_rub(row["closing_balance"]),
            }
            for row in rows
        ]
    )


def format_cashflow_table(rows: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Месяц": row["month"],
                "Поступления от продаж": format_rub(row["sales_receipts"]),
                "Затраты строительства": format_rub(row["construction_costs"]),
                "Земля": format_rub(row["land"]),
                "Прочие расходы": format_rub(row["other_expenses"]),
                "Операционный поток до финансирования": format_rub(row["operating_cashflow_before_financing"]),
                "Выборка кредита": format_rub(row["credit_drawdown"]),
                "Проценты": format_rub(row["interest"]),
                "Погашение кредита": format_rub(row["credit_repayment"]),
                "Собственные средства": format_rub(row["equity_required"]),
                "Собственные средства накопительно": format_rub(row["cumulative_equity_required"]),
                "Чистый поток": format_rub(row["net_cashflow"]),
                "Накопленный поток": format_rub(row["accumulated_cashflow"]),
            }
            for row in rows
        ]
    )


def show_dscr() -> None:
    current_model = require_model()
    if current_model is None:
        return
    st.header("DSCR")
    dscr = current_model["dscr"]
    cols = st.columns(3)
    cols[0].metric("Minimum DSCR", format_number(dscr["minimum_dscr_after_sales_start"], 2))
    cols[1].metric("Средний DSCR после старта продаж", format_number(dscr["average_dscr_after_sales_start"], 2))
    cols[2].metric("Месяцев ниже 1.2", format_number(dscr["months_below_1_2"]))
    dscr_df = pd.DataFrame(
        [
            {
                "Месяц": row["month"],
                "Поступления от продаж": row["sales_receipts"],
                "Обслуживание долга": row["debt_service"],
                "DSCR": row["dscr"],
            }
            for row in dscr["schedule"]
        ]
    )
    st.subheader("DSCR по месяцам")
    st.line_chart(dscr_df, x="Месяц", y="DSCR", use_container_width=True)
    st.dataframe(format_dscr_table(dscr["schedule"]), use_container_width=True)


def format_dscr_table(rows: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Месяц": row["month"],
                "Поступления от продаж": format_rub(row["sales_receipts"]),
                "Обслуживание долга": format_rub(row["debt_service"]),
                "DSCR": format_number(row["dscr"], 2) if row["dscr"] is not None else "нет обслуживания",
            }
            for row in rows
        ]
    )


def show_scenarios() -> None:
    current_model = require_model()
    if current_model is None:
        return
    st.header("Сценарии")
    scenario_rows = []
    for scenario in current_model["scenarios"]:
        scenario_rows.append(
            {
                "Сценарий": scenario["scenario_name"],
                "Выручка": scenario["revenue"],
                "Итоговый бюджет": scenario["total_budget"],
                "Прибыль после процентов": scenario["profit_after_interest"],
                "Маржа после процентов": scenario["margin_after_interest"],
                "Максимальный кредит": scenario["max_credit_balance"],
                "Собственные средства": scenario["total_equity_required"],
                "Minimum DSCR": scenario["minimum_dscr_after_sales_start"],
                "Оценка маржи": scenario["margin_assessment"],
                "Оценка DSCR": scenario["dscr_assessment"],
            }
        )
    raw_df = pd.DataFrame(scenario_rows)
    left, right = st.columns(2)
    with left:
        st.subheader("Прибыль по сценариям")
        st.bar_chart(raw_df, x="Сценарий", y="Прибыль после процентов", use_container_width=True)
    with right:
        st.subheader("Маржа по сценариям")
        st.bar_chart(raw_df, x="Сценарий", y="Маржа после процентов", use_container_width=True)
    st.subheader("Сценарная таблица")
    display_df = raw_df.copy()
    for column in ("Выручка", "Итоговый бюджет", "Прибыль после процентов", "Максимальный кредит", "Собственные средства"):
        display_df[column] = display_df[column].apply(format_rub)
    display_df["Маржа после процентов"] = display_df["Маржа после процентов"].apply(format_percent)
    display_df["Minimum DSCR"] = display_df["Minimum DSCR"].apply(lambda value: format_number(value, 2))
    st.dataframe(
        display_df.style.map(scenario_color, subset=["Оценка маржи", "Оценка DSCR"]),
        use_container_width=True,
    )


def scenario_color(value: str) -> str:
    colors = {
        "плохо": "background-color: #F8D7DA; color: #842029",
        "средне": "background-color: #FFF3CD; color: #664D03",
        "хорошо": "background-color: #D1E7DD; color: #0F5132",
        "риск": "background-color: #F8D7DA; color: #842029",
        "норма": "background-color: #D1E7DD; color: #0F5132",
        "нет данных": "background-color: #E2E3E5; color: #41464B",
    }
    return colors.get(value, "")


def show_optimization() -> None:
    current_model = require_model()
    if current_model is None:
        return
    st.header("Оптимизация")
    optimization = current_model["optimization"]
    cols = st.columns(4)
    cols[0].metric("Что нужно снизить из бюджета", format_rub(optimization["required_budget_reduction_for_market_price"]))
    cols[1].metric("Целевая СМР", format_rub(optimization["required_cmr_cost_per_m2_for_market_price"]))
    cols[2].metric("Нужная продаваемая площадь", format_area(optimization["required_sellable_area_for_market_price"]))
    cols[3].metric("Цена для целевой маржи", format_rub(optimization["required_sale_price_for_target_margin"]))
    st.info(f"Наиболее реалистичный рычаг: {optimization['most_realistic_option']}")
    st.subheader("Рекомендации")
    for recommendation in optimization["recommendations"]:
        st.write(f"- {recommendation}")


def show_improvement_plan() -> None:
    current_model = require_model()
    if current_model is None:
        return
    st.header("План улучшений")
    plan = current_model["improvement_plan"]
    st.metric("Целевое снижение бюджета", format_rub(plan["target_budget_reduction"]))
    if plan["summary"]:
        st.info(plan["summary"])
    st.subheader("Статьи экономии")
    if plan["improvement_items"]:
        st.dataframe(format_improvement_items(plan["improvement_items"]), use_container_width=True)
    else:
        st.success("Обязательная экономия не требуется.")
    left, right = st.columns(2)
    with left:
        show_text_list("Планировочные улучшения", plan["planning_improvements"])
        show_text_list("Коммерческие улучшения", plan["sales_improvements"])
    with right:
        show_text_list("Финансовые улучшения", plan["financing_improvements"])
        show_text_list("Приоритетные действия", plan["priority_actions"], numbered=True)


def format_improvement_items(rows: list[dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    if "Потенциал экономии, ₽" in df:
        df["Потенциал экономии, ₽"] = df["Потенциал экономии, ₽"].apply(format_rub)
    if "Потенциал экономии, %" in df:
        df["Потенциал экономии, %"] = df["Потенциал экономии, %"].apply(lambda value: format_percent(float(value) / 100 if float(value) > 1 else value))
    return df


def show_text_list(title: str, items: list[str], numbered: bool = False) -> None:
    st.subheader(title)
    if not items:
        st.write("Нет рекомендаций.")
        return
    for index, item in enumerate(items, start=1):
        prefix = f"{index}. " if numbered else "- "
        st.write(f"{prefix}{item}")


def show_project_history() -> None:
    st.header("История проектов")
    rows = load_project_history()
    if not rows:
        st.info("История расчётов пока пуста. Сформируйте первый проект во вкладке Новый расчёт.")
        return

    header = st.columns([1.5, 2.4, 1.4, 1.5, 1.5, 1.5, 1.0, 1.0, 1.3])
    for column, title in zip(
        header,
        ("Дата", "Проект", "Город", "Бюджет", "Выручка", "Прибыль", "Маржа", "DSCR", "Скачать Excel"),
        strict=True,
    ):
        column.markdown(f"**{title}**")

    for row in rows:
        columns = st.columns([1.5, 2.4, 1.4, 1.5, 1.5, 1.5, 1.0, 1.0, 1.3])
        columns[0].write(str(row.get("calculated_at") or "").replace("T", " "))
        columns[1].write(row.get("project_name") or "Без названия")
        columns[2].write(row.get("city") or "Не указан")
        columns[3].write(format_rub(row.get("total_budget")))
        columns[4].write(format_rub(row.get("revenue")))
        columns[5].write(format_rub(row.get("profit")))
        columns[6].write(format_percent(row.get("margin")))
        columns[7].write(format_number(row.get("minimum_dscr"), 2))
        path = Path(str(row.get("excel_path") or ""))
        if path.exists():
            with path.open("rb") as handle:
                columns[8].download_button(
                    "Скачать",
                    data=handle.read(),
                    file_name=path.name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"history_download_{row.get('project_id')}",
                    use_container_width=True,
                )
        else:
            columns[8].warning("Файл не найден")


def show_download() -> None:
    current_model = require_model()
    if current_model is None:
        return
    st.header("Скачать Excel")
    current_path = excel_path()
    if current_path is None or not current_path.exists():
        current_path = export_model_to_excel(current_model, OUTPUT_DIR)
        st.session_state["excel_path"] = str(current_path)
    st.write("Финансовая модель сохранена в Excel и готова к скачиванию.")
    with current_path.open("rb") as handle:
        st.download_button(
            "Скачать финансовую модель Excel",
            data=handle.read(),
            file_name=current_path.name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    st.caption(f"Файл сохранён в папке: {current_path.parent}")


def show_settings() -> None:
    st.header("Настройки")
    user = current_user() or {}
    st.subheader("Приложение")
    st.write(f"Версия приложения: **{APP_VERSION}**")
    st.write(f"Текущий пользователь: **{user.get('login', 'неизвестно')}**")
    st.write(f"Роль: **{user.get('role', 'неизвестно')}**")
    st.write(f"Папка Excel-файлов: `{OUTPUT_DIR}`")
    st.write(f"Папка истории проектов: `{PROJECTS_DIR}`")
    st.write(f"Файл пользователей: `{USERS_FILE}`")

    st.subheader("Инструкция для администратора")
    st.write("1. Создайте пароль для сотрудника и получите хэш.")
    st.code(
        ".\\.venv\\Scripts\\python.exe -c \"from backend.auth import hash_password; print(hash_password('НОВЫЙ_ПАРОЛЬ'))\"",
        language="powershell",
    )
    st.write("2. Добавьте пользователя в `users.json`.")
    st.code(
        '{\n  "login": "ivan",\n  "password_hash": "pbkdf2_sha256$...",\n  "role": "user"\n}',
        language="json",
    )
    st.write("3. Для администратора укажите роль `admin`. Для обычного пользователя укажите роль `user`.")
    st.warning("Не храните пароль в открытом виде и не отправляйте users.json в общий чат.")


def main() -> None:
    apply_style()
    if not is_authenticated():
        show_login()
        return

    with st.sidebar:
        st.title("Девелоперская модель")
        st.caption("Внутренний кабинет девелоперской модели")
        page = st.radio("Навигация", MENU_ITEMS, label_visibility="collapsed")
        user = current_user() or {}
        st.divider()
        st.write(f"Пользователь: **{user.get('login')}**")
        st.write(f"Роль: **{user.get('role')}**")
        if st.button("Выйти", use_container_width=True):
            st.session_state.pop("user", None)
            st.session_state.pop("model", None)
            st.session_state.pop("excel_path", None)
            st.rerun()
        current_model = model()
        if current_model is not None:
            st.divider()
            st.write("Текущий проект")
            st.write(current_model["input"].get("project_name") or "Без названия")

    pages = {
        "Главная": show_home,
        "Новый расчёт": show_new_calculation,
        "Бюджет": show_budget,
        "ГПР": show_gpr,
        "Продажи": show_sales,
        "Кредит и ДДС": show_credit_cashflow,
        "DSCR": show_dscr,
        "Сценарии": show_scenarios,
        "Оптимизация": show_optimization,
        "План улучшений": show_improvement_plan,
        "История проектов": show_project_history,
        "Скачать Excel": show_download,
        "Настройки": show_settings,
    }
    pages[page]()


if __name__ == "__main__":
    main()
