from __future__ import annotations

from typing import Any

from backend.models import ProjectInput
from backend.tools.norms import DEFAULT_ASSUMPTIONS


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

    trace.append(
        {
            "step": "apply_assumptions",
            "inputs": project_input.model_dump(exclude_none=True),
            "output": {"normalized_input": data, "assumptions": assumptions},
        }
    )
    return {"data": data, "assumptions": assumptions, "trace": trace}
