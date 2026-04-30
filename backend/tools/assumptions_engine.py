from __future__ import annotations

from typing import Any

from backend.models import ProjectInput
from backend.tools.norms import DEFAULT_ASSUMPTIONS, round_money


def apply_assumptions(project_input: ProjectInput) -> dict[str, Any]:
    data = project_input.model_dump()
    assumptions: list[dict[str, Any]] = []
    trace: list[dict[str, Any]] = []

    def set_default(field: str, value: Any, reason: str) -> None:
        if data.get(field) in (None, ""):
            data[field] = value
            assumptions.append(
                {
                    "field": field,
                    "value": value,
                    "reason": reason,
                    "source": "developer_assumption",
                }
            )

    set_default("project_name", DEFAULT_ASSUMPTIONS["project_name"], "Название проекта не указано.")
    set_default("city", DEFAULT_ASSUMPTIONS["city"], "Город не указан.")
    set_default("object_type", DEFAULT_ASSUMPTIONS["object_type"], "Тип объекта не указан.")
    set_default("object_class", DEFAULT_ASSUMPTIONS["object_class"], "Класс объекта не указан.")
    set_default("land_area", DEFAULT_ASSUMPTIONS["land_area"], "Площадь участка не указана.")
    set_default("land_cost", DEFAULT_ASSUMPTIONS["land_cost"], "Стоимость земли не указана.")
    set_default("total_area", DEFAULT_ASSUMPTIONS["total_area"], "Общая площадь не указана.")
    set_default("floors", DEFAULT_ASSUMPTIONS["floors"], "Этажность не указана.")
    set_default(
        "construction_months",
        DEFAULT_ASSUMPTIONS["construction_months"],
        "Срок строительства не указан.",
    )
    set_default("sales_months", DEFAULT_ASSUMPTIONS["sales_months"], "Срок продаж не указан.")
    set_default("credit_share", DEFAULT_ASSUMPTIONS["credit_share"], "Доля кредита не указана.")
    set_default("credit_rate", DEFAULT_ASSUMPTIONS["credit_rate"], "Ставка кредита не указана.")
    set_default(
        "external_networks_included",
        DEFAULT_ASSUMPTIONS["external_networks_included"],
        "Признак включения наружных сетей не указан.",
    )
    set_default(
        "gas_only_cooking",
        DEFAULT_ASSUMPTIONS["gas_only_cooking"],
        "Признак газа только для пищеприготовления не указан.",
    )
    set_default("foundation_type", "сваи", "Тип фундамента не указан.")
    set_default("has_underground_part", False, "Признак подземной части не указан.")
    set_default("sellable_finish_level", "черновая", "Уровень отделки реализуемых помещений не указан.")
    set_default("foundation_optimization_mode", "оптимизированный", "Режим расчёта свайного основания не указан.")

    if data.get("sellable_area") in (None, ""):
        data["sellable_area"] = data["total_area"] * DEFAULT_ASSUMPTIONS["sellable_area_ratio"]
        assumptions.append(
            {
                "field": "sellable_area",
                "value": data["sellable_area"],
                "reason": "Продаваемая площадь оценена как 78% от общей площади.",
                "source": "developer_assumption",
            }
        )

    for field in (
        "reserve",
        "design",
        "technical_customer",
        "general_contractor",
        "landscaping",
        "external_networks",
    ):
        data[field] = DEFAULT_ASSUMPTIONS[field]
        assumptions.append(
            {
                "field": field,
                "value": data[field],
                "reason": "Нормативное допущение модели v3.",
                "source": "developer_norm",
            }
        )

    total_area = float(data.get("total_area") or 0)
    design_override = float(data.get("design_cost_override") or 0)
    if design_override > 0:
        data["design_cost_amount"] = round_money(design_override)
        assumptions.append(
            {
                "field": "design_cost_override",
                "value": data["design_cost_amount"],
                "reason": "Использована ручная сумма проектирования.",
                "source": "user_input",
            }
        )
    else:
        calculated_design = total_area * 1_500
        if total_area <= 12_000:
            calculated_design = min(calculated_design, 10_000_000)
        data["design_cost_amount"] = round_money(calculated_design)
        assumptions.append(
            {
                "field": "design_cost_amount",
                "value": data["design_cost_amount"],
                "reason": "Проектирование рассчитано по ставке 1 500 ₽/м² общей площади; для объектов до 12 000 м² применяется ограничение 10 000 000 ₽.",
                "source": "developer_norm",
            }
        )

    preparation_override = float(data.get("preparation_cost_override") or 0)
    if preparation_override > 0:
        data["preparation_cost_amount"] = round_money(preparation_override)
        assumptions.append(
            {
                "field": "preparation_cost_override",
                "value": data["preparation_cost_amount"],
                "reason": "Использована ручная сумма подготовительных работ.",
                "source": "user_input",
            }
        )
    else:
        data["preparation_cost_amount"] = round_money(total_area * 750)
        assumptions.append(
            {
                "field": "preparation_cost_amount",
                "value": data["preparation_cost_amount"],
                "reason": "Подготовительные работы рассчитаны по ставке 750 ₽/м² общей площади.",
                "source": "developer_norm",
            }
        )

    foundation_type = str(data.get("foundation_type") or "").lower().replace("ё", "е")
    has_underground_part = bool(data.get("has_underground_part"))
    above_ground_override = float(data.get("above_ground_structures_rate_override") or 0)
    envelope_override = float(data.get("envelope_roof_walls_rate_override") or 0)
    earthworks_override = float(data.get("earthworks_rate_override") or 0)
    object_class = str(data.get("object_class") or "").lower().replace("ё", "е")
    assumptions.extend(
        [
            {
                "field": "foundation_type",
                "value": data.get("foundation_type"),
                "reason": "Тип фундамента используется для расчёта свай, земляных работ и подземной части.",
                "source": "developer_assumption",
            },
            {
                "field": "foundation_optimization_mode",
                "value": data.get("foundation_optimization_mode"),
                "reason": "Режим расчёта свайного основания определяет ставку 5 500 или 6 500 ₽/м².",
                "source": "developer_assumption",
            },
        ]
    )

    if above_ground_override > 0:
        above_ground_rate = above_ground_override
        above_ground_reason = "Ставка 2.5 надземных конструкций задана пользователем."
    elif foundation_type == "сваи" and not has_underground_part:
        above_ground_rate = 19_500
        above_ground_reason = "Ставка 2.5 снижена для типового надземного конструктива на сваях без подземной части."
    else:
        above_ground_rate = 23_120
        above_ground_reason = "Ставка 2.5 принята по нормативному ориентиру модели."
    data["above_ground_structures_rate"] = above_ground_rate
    assumptions.append(
        {
            "field": "above_ground_structures_rate",
            "value": above_ground_rate,
            "reason": above_ground_reason,
            "source": "user_input" if above_ground_override > 0 else "developer_norm",
        }
    )

    if envelope_override > 0:
        envelope_rate = envelope_override
        envelope_reason = "Ставка 2.6 ограждающих конструкций задана пользователем."
    elif object_class in {"эконом", "economy", "комфорт", "comfort"}:
        envelope_rate = 8_500
        envelope_reason = "Ставка 2.6 снижена для эконом/комфорт класса без повышенной отделки ограждающих конструкций."
    else:
        envelope_rate = 11_560
        envelope_reason = "Ставка 2.6 принята по нормативному ориентиру модели."
    data["envelope_roof_walls_rate"] = envelope_rate
    assumptions.append(
        {
            "field": "envelope_roof_walls_rate",
            "value": envelope_rate,
            "reason": envelope_reason,
            "source": "user_input" if envelope_override > 0 else "developer_norm",
        }
    )

    if earthworks_override > 0:
        earthworks_rate = earthworks_override
        earthworks_reason = "Ставка земляных работ задана пользователем."
        earthworks_source = "user_input"
    elif foundation_type == "сваи" and not has_underground_part:
        earthworks_rate = 800
        earthworks_reason = "Земляные работы снижены из-за свайного фундамента и отсутствия подземной части."
        earthworks_source = "developer_norm"
    elif has_underground_part:
        earthworks_rate = 3_000
        earthworks_reason = "Земляные работы рассчитаны с учётом подземной части."
        earthworks_source = "developer_norm"
    else:
        earthworks_rate = 1_800
        earthworks_reason = "Земляные работы рассчитаны по базовому нормативу модели."
        earthworks_source = "developer_norm"
    data["earthworks_rate"] = earthworks_rate
    assumptions.append(
        {
            "field": "earthworks_rate",
            "value": earthworks_rate,
            "reason": earthworks_reason,
            "source": earthworks_source,
        }
    )
    assumptions.append(
        {
            "field": "manual_budget_adjustments_comment",
            "value": "Ручные корректировки ключевых ставок имеют приоритет над нормативами, если значение больше 0.",
            "reason": "Добавлена прозрачная настройка ключевых статей 2.5, 2.6, 3.1, 2.1, 2.2 и 2.8.",
            "source": "developer_norm",
        }
    )
    sellable_finish_rate = _sellable_finish_rate(data)
    data["sellable_finish_rate"] = sellable_finish_rate
    assumptions.extend(
        [
            {
                "field": "sellable_finish_level",
                "value": data["sellable_finish_level"],
                "reason": f"Уровень отделки реализуемых помещений: {data['sellable_finish_level']}.",
                "source": "developer_assumption",
            },
            {
                "field": "sellable_finish_rate",
                "value": sellable_finish_rate,
                "reason": "Ставка отделки реализуемых помещений рассчитана по уровню отделки или ручной корректировке.",
                "source": "user_input" if float(data.get("sellable_finish_rate_override") or 0) > 0 else "developer_norm",
            },
            {
                "field": "sellable_finish_calculation_logic",
                "value": "2.8 = продаваемая площадь NSA × ставка отделки реализуемых помещений",
                "reason": "Черновая отделка — 11 450 ₽/м² NSA; white box — 14 000 ₽/м²; чистовая — 24 000 ₽/м²; без отделки — 0 ₽/м².",
                "source": "developer_norm",
            },
        ]
    )

    pile_rate = _pile_foundation_rate(data)
    data["pile_foundation_rate"] = pile_rate
    assumptions.append(
        {
            "field": "pile_foundation_rate",
            "value": pile_rate,
            "reason": "Ставка свайного основания рассчитана по выбранному режиму или ручной корректировке.",
            "source": "user_input"
            if any(float(data.get(field) or 0) > 0 for field in ("pile_foundation_rate_override", "pile_foundation_cost_override", "pile_count", "pile_unit_cost"))
            else "developer_norm",
        }
    )
    for field, label, rate in (
        ("plumbing_rate", "Ставка 2.11 сантехнических систем", _engineering_rate(data, "plumbing_rate_override", 4_200)),
        ("heating_rate", "Ставка 2.12 отопления / ИТП", _engineering_rate(data, "heating_rate_override", 5_200)),
        ("electrical_rate", "Ставка 2.13 электроснабжения", _engineering_rate(data, "electrical_rate_override", 4_600)),
        ("low_voltage_rate", "Ставка 2.14 слаботочных систем", _engineering_rate(data, "low_voltage_rate_override", 1_500)),
        ("ventilation_rate", "Ставка 2.15 вентиляции / дымоудаления", _engineering_rate(data, "ventilation_rate_override", 2_500)),
    ):
        data[field] = rate
        assumptions.append(
            {
                "field": field,
                "value": rate,
                "reason": f"{label}: используется ручная ставка или оптимизированный норматив модели.",
                "source": "user_input" if _override_source_field(field, data) else "developer_norm",
            }
        )
    if not has_underground_part:
        assumptions.append(
            {
                "field": "pit_fencing_excluded",
                "value": "Исключено",
                "reason": "Ограждение котлована исключено: подземная часть не предусмотрена.",
                "source": "developer_norm",
            }
        )

    if foundation_type == "сваи" and not has_underground_part:
        assumptions.extend(
            [
                {
                    "field": "earthworks_adjustment",
                    "value": "800 ₽/м²",
                    "reason": "Земляные работы снижены из-за свайного фундамента и отсутствия подземной части.",
                    "source": "developer_norm",
                },
                {
                    "field": "underground_part_adjustment",
                    "value": 0,
                    "reason": "Подземная часть исключена: выбран свайный фундамент без подземной части.",
                    "source": "developer_norm",
                },
            ]
        )
    trace.append(
        {
            "step": "apply_assumptions",
            "inputs": project_input.model_dump(exclude_none=True),
            "output": {"normalized_input": data, "assumptions": assumptions},
        }
    )
    return {"data": data, "assumptions": assumptions, "trace": trace}


def _pile_foundation_rate(data: dict[str, Any]) -> float:
    if float(data.get("pile_foundation_cost_override") or 0) > 0:
        total_area = float(data.get("total_area") or 0)
        return round_money(float(data["pile_foundation_cost_override"]) / total_area) if total_area else 0
    if float(data.get("pile_count") or 0) > 0 and float(data.get("pile_unit_cost") or 0) > 0:
        total_area = float(data.get("total_area") or 0)
        base = float(data["pile_count"]) * float(data["pile_unit_cost"])
        base += total_area * float(data.get("grillage_rate_override") or 0)
        return round_money(base / total_area) if total_area else 0
    if float(data.get("pile_foundation_rate_override") or 0) > 0:
        return float(data["pile_foundation_rate_override"])
    mode = str(data.get("foundation_optimization_mode") or "оптимизированный").lower().replace("ё", "е")
    return 6_500 if mode == "нормативный" else 5_500


def _engineering_rate(data: dict[str, Any], override_field: str, default_rate: float) -> float:
    override = float(data.get(override_field) or 0)
    return override if override > 0 else default_rate


def _override_source_field(field: str, data: dict[str, Any]) -> bool:
    mapping = {
        "plumbing_rate": "plumbing_rate_override",
        "heating_rate": "heating_rate_override",
        "electrical_rate": "electrical_rate_override",
        "low_voltage_rate": "low_voltage_rate_override",
        "ventilation_rate": "ventilation_rate_override",
    }
    return float(data.get(mapping[field]) or 0) > 0


def _sellable_finish_rate(data: dict[str, Any]) -> float:
    override = float(data.get("sellable_finish_rate_override") or 0)
    if override > 0:
        return override
    finish_level = str(data.get("sellable_finish_level") or "").lower().replace("ё", "е").replace(" ", "").replace("-", "")
    rates = {
        "безотделки": 0,
        "черновая": 11_450,
        "whitebox": 14_000,
        "чистовая": 24_000,
    }
    return float(rates.get(finish_level, 11_450))
