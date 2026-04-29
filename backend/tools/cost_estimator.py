from __future__ import annotations

import re
from typing import Any


BASE_CMR_COSTS = {
    "Жилой дом": {
        "эконом": 85_000,
        "комфорт": 100_000,
        "бизнес": 125_000,
        "премиум": 160_000,
    },
    "Апартаменты": {
        "эконом": 90_000,
        "комфорт": 110_000,
        "бизнес": 140_000,
        "премиум": 180_000,
    },
    "Коммерция": {
        "стандарт": 90_000,
        "комфорт": 115_000,
        "бизнес": 145_000,
    },
}

CITY_COEFFICIENTS = {
    "якутск": 1.12,
    "москва": 1.15,
    "санктпетербург": 1.10,
    "новосибирск": 1.00,
    "екатеринбург": 1.02,
    "казань": 1.03,
    "краснодар": 0.98,
}

CLASS_ALIASES = {
    "economy": "эконом",
    "эконом": "эконом",
    "comfort": "комфорт",
    "комфорт": "комфорт",
    "business": "бизнес",
    "бизнес": "бизнес",
    "premium": "премиум",
    "премиум": "премиум",
    "standard": "стандарт",
    "стандарт": "стандарт",
}


def estimate_construction_cost(inputs: dict[str, Any]) -> dict[str, Any]:
    warnings: list[str] = []
    object_type = _resolve_object_type(inputs.get("object_type"), warnings)
    object_class = _resolve_object_class(inputs.get("object_class"), object_type, warnings)
    city_coefficient = _city_coefficient(inputs.get("city"), warnings)
    floors_coefficient = _floors_coefficient(int(inputs.get("floors") or 0))
    area_coefficient = _area_coefficient(float(inputs.get("total_area") or 0))
    engineering_coefficient = 1.00 if inputs.get("gas_only_cooking") else 1.03
    base_cost_per_m2 = BASE_CMR_COSTS[object_type][object_class]
    raw_cost = (
        base_cost_per_m2
        * city_coefficient
        * floors_coefficient
        * area_coefficient
        * engineering_coefficient
    )
    estimated = _round_to_step(raw_cost, 500)

    cost_components = {
        "object_type": object_type,
        "object_class": object_class,
        "base_cost_per_m2": base_cost_per_m2,
        "raw_estimated_cost_per_m2": round(raw_cost, 2),
        "rounding_step": 500,
    }
    coefficients = {
        "city_coefficient": city_coefficient,
        "floors_coefficient": floors_coefficient,
        "area_coefficient": area_coefficient,
        "engineering_coefficient": engineering_coefficient,
    }
    assumptions = [
        {
            "field": "base_cmr_cost_per_m2",
            "value": base_cost_per_m2,
            "reason": f"База СМР для типа '{object_type}' и класса '{object_class}'.",
            "source": "cost_estimator",
        },
        {
            "field": "city_coefficient",
            "value": city_coefficient,
            "reason": "Коэффициент города является внутренним допущением MVP.",
            "source": "cost_estimator",
        },
        {
            "field": "floors_coefficient",
            "value": floors_coefficient,
            "reason": "Коэффициент этажности по диапазону этажей.",
            "source": "cost_estimator",
        },
        {
            "field": "area_coefficient",
            "value": area_coefficient,
            "reason": "Коэффициент масштаба по общей площади.",
            "source": "cost_estimator",
        },
        {
            "field": "engineering_coefficient",
            "value": engineering_coefficient,
            "reason": "Коэффициент инженерии по признаку газа.",
            "source": "cost_estimator",
        },
        {
            "field": "estimated_cmr_cost_per_m2",
            "value": estimated,
            "reason": "Итоговая расчётная себестоимость СМР за м² с округлением до 500 рублей.",
            "source": "cost_estimator",
        },
    ]
    return {
        "estimated_cmr_cost_per_m2": estimated,
        "calculation_method": "База × коэффициент города × коэффициент этажности × коэффициент масштаба × коэффициент инженерии",
        "cost_components": cost_components,
        "coefficients": coefficients,
        "assumptions": assumptions,
        "warnings": warnings,
        "trace": [
            {
                "step": "estimate_construction_cost",
                "inputs": {
                    "city": inputs.get("city"),
                    "object_type": inputs.get("object_type"),
                    "object_class": inputs.get("object_class"),
                    "total_area": inputs.get("total_area"),
                    "floors": inputs.get("floors"),
                    "gas_only_cooking": inputs.get("gas_only_cooking"),
                },
                "formula": "base_cost_per_m2 * city_coefficient * floors_coefficient * area_coefficient * engineering_coefficient",
                "output": {
                    "estimated_cmr_cost_per_m2": estimated,
                    "cost_components": cost_components,
                    "coefficients": coefficients,
                    "warnings": warnings,
                },
            }
        ],
    }


def _resolve_object_type(value: Any, warnings: list[str]) -> str:
    normalized = _normalize(value)
    if "апартамент" in normalized:
        return "Апартаменты"
    if any(marker in normalized for marker in ("коммер", "офис", "торгов", "ритейл")):
        return "Коммерция"
    if any(marker in normalized for marker in ("жил", "жк", "мкд")):
        return "Жилой дом"
    warnings.append("Тип объекта не распознан. Использовано допущение: Жилой дом.")
    return "Жилой дом"


def _resolve_object_class(value: Any, object_type: str, warnings: list[str]) -> str:
    normalized = _normalize(value)
    object_class = CLASS_ALIASES.get(normalized)
    if object_class and object_class in BASE_CMR_COSTS[object_type]:
        return object_class
    warnings.append("Класс объекта не распознан для выбранного типа. Использовано допущение: комфорт.")
    return "комфорт" if "комфорт" in BASE_CMR_COSTS[object_type] else next(iter(BASE_CMR_COSTS[object_type]))


def _city_coefficient(value: Any, warnings: list[str]) -> float:
    normalized = _normalize(value)
    coefficient = CITY_COEFFICIENTS.get(normalized)
    if coefficient is not None:
        return coefficient
    warnings.append("Город не найден в MVP-таблице коэффициентов. Использован коэффициент 1.00.")
    return 1.00


def _floors_coefficient(floors: int) -> float:
    if floors <= 5:
        return 0.95
    if floors <= 12:
        return 1.00
    if floors <= 20:
        return 1.06
    return 1.12


def _area_coefficient(total_area: float) -> float:
    if total_area < 3_000:
        return 1.08
    if total_area <= 10_000:
        return 1.00
    if total_area <= 30_000:
        return 0.97
    return 0.95


def _round_to_step(value: float, step: int) -> float:
    return float(round(value / step) * step)


def _normalize(value: Any) -> str:
    text = str(value or "").lower().replace("ё", "е")
    return re.sub(r"[^a-zа-я0-9]+", "", text)
