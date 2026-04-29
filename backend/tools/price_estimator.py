from __future__ import annotations

import math
import re
from typing import Any


BASE_MARKET_PRICES = {
    "якутск": {"эконом": 155_000, "комфорт": 180_000, "бизнес": 220_000, "премиум": 280_000},
    "москва": {"эконом": 280_000, "комфорт": 360_000, "бизнес": 520_000, "премиум": 750_000},
    "санктпетербург": {"эконом": 220_000, "комфорт": 290_000, "бизнес": 420_000, "премиум": 600_000},
    "новосибирск": {"эконом": 135_000, "комфорт": 170_000, "бизнес": 220_000, "премиум": 300_000},
    "екатеринбург": {"эконом": 145_000, "комфорт": 185_000, "бизнес": 240_000, "премиум": 320_000},
    "казань": {"эконом": 155_000, "комфорт": 200_000, "бизнес": 270_000, "премиум": 360_000},
    "краснодар": {"эконом": 140_000, "комфорт": 180_000, "бизнес": 240_000, "премиум": 320_000},
    "default": {"эконом": 140_000, "комфорт": 180_000, "бизнес": 240_000, "премиум": 320_000},
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
    "standard": "эконом",
    "стандарт": "эконом",
}

TARGET_MARGIN = 0.15


def estimate_sale_price(inputs: dict[str, Any], budget: dict[str, Any], economics: dict[str, Any] | None = None) -> dict[str, Any]:
    economics = economics or {}
    warnings: list[str] = []
    city_key = _resolve_city(inputs.get("city"), warnings)
    object_class = _resolve_object_class(inputs.get("object_class"), warnings)
    object_type_coefficient = _object_type_coefficient(inputs.get("object_type"))
    floors_price_coefficient = _floors_price_coefficient(int(inputs.get("floors") or 0))
    scale_price_coefficient = _scale_price_coefficient(float(inputs.get("total_area") or 0))
    base_market_price = BASE_MARKET_PRICES[city_key][object_class]
    market_price = _round_to_step(
        base_market_price * object_type_coefficient * floors_price_coefficient * scale_price_coefficient,
        1000,
    )

    total_budget = float(budget["total_budget"])
    sellable_area = float(inputs.get("sellable_area") or 0)
    estimated_interest = float(economics.get("total_interest") or _estimate_interest(inputs, total_budget))
    break_even = _ceil_to_step((total_budget + estimated_interest) / sellable_area if sellable_area else 0, 1000)
    target_margin_price = _ceil_to_step(
        ((total_budget + estimated_interest) / sellable_area / (1 - TARGET_MARGIN)) if sellable_area else 0,
        1000,
    )

    if market_price >= target_margin_price:
        recommended = market_price
    else:
        recommended = target_margin_price
        warnings.append(
            "Цена для целевой маржи выше рыночного ориентира. Есть риск, что проект не продастся по требуемой цене."
        )

    manual_price = float(inputs.get("sale_price_per_m2") or 0)
    price_source = "Ручная цена продажи" if manual_price > 0 else "Расчётная цена продажи агента"
    price_gap = recommended - market_price
    price_components = {
        "city": city_key,
        "object_class": object_class,
        "base_market_price_per_m2": base_market_price,
        "estimated_interest": round(estimated_interest, 2),
        "target_margin": TARGET_MARGIN,
    }
    assumptions = [
        {
            "field": "base_market_price_per_m2",
            "value": base_market_price,
            "reason": "Базовая рыночная цена является MVP-допущением, а не официальной рыночной оценкой.",
            "source": "price_estimator",
        },
        {
            "field": "object_type_price_coefficient",
            "value": object_type_coefficient,
            "reason": "Коэффициент типа объекта для рыночного ориентира цены.",
            "source": "price_estimator",
        },
        {
            "field": "floors_price_coefficient",
            "value": floors_price_coefficient,
            "reason": "Коэффициент этажности для рыночного ориентира цены.",
            "source": "price_estimator",
        },
        {
            "field": "scale_price_coefficient",
            "value": scale_price_coefficient,
            "reason": "Коэффициент масштаба для рыночного ориентира цены.",
            "source": "price_estimator",
        },
        {
            "field": "market_price_per_m2",
            "value": market_price,
            "reason": "Рыночный ориентир цены продажи по MVP-допущениям.",
            "source": "price_estimator",
        },
        {
            "field": "target_margin",
            "value": TARGET_MARGIN,
            "reason": "Целевая маржа модели для расчёта рекомендованной цены.",
            "source": "price_estimator",
        },
    ]
    return {
        "estimated_sale_price_per_m2": recommended,
        "price_source": price_source,
        "market_price_per_m2": market_price,
        "break_even_price_per_m2": break_even,
        "target_margin_price_per_m2": target_margin_price,
        "recommended_price_per_m2": recommended,
        "price_gap_to_market": price_gap,
        "price_components": price_components,
        "coefficients": {
            "object_type_price_coefficient": object_type_coefficient,
            "floors_price_coefficient": floors_price_coefficient,
            "scale_price_coefficient": scale_price_coefficient,
        },
        "assumptions": assumptions,
        "warnings": warnings,
        "trace": [
            {
                "step": "estimate_sale_price",
                "inputs": {
                    "city": inputs.get("city"),
                    "object_class": inputs.get("object_class"),
                    "object_type": inputs.get("object_type"),
                    "total_budget": total_budget,
                    "sellable_area": sellable_area,
                    "estimated_interest": estimated_interest,
                },
                "formula": "recommended = max(market_price, target_margin_price)",
                "output": {
                    "market_price_per_m2": market_price,
                    "break_even_price_per_m2": break_even,
                    "target_margin_price_per_m2": target_margin_price,
                    "recommended_price_per_m2": recommended,
                    "price_gap_to_market": price_gap,
                    "warnings": warnings,
                },
            }
        ],
    }


def recalculate_price_with_actual_interest(
    *,
    total_budget: float,
    actual_total_interest: float,
    sellable_area: float,
    market_price_per_m2: float,
    target_margin: float = TARGET_MARGIN,
) -> dict[str, Any]:
    final_target_margin_price = _ceil_to_step(
        ((total_budget + actual_total_interest) / sellable_area / (1 - target_margin))
        if sellable_area and target_margin < 1
        else 0,
        1000,
    )
    final_recommended_price = max(float(market_price_per_m2), final_target_margin_price)
    return {
        "final_target_margin_price_per_m2": final_target_margin_price,
        "final_recommended_price_per_m2": final_recommended_price,
        "actual_total_interest_used_for_price": round(float(actual_total_interest), 2),
        "price_gap_to_market": final_recommended_price - float(market_price_per_m2),
        "trace": [
            {
                "step": "recalculate_price_with_actual_interest",
                "inputs": {
                    "total_budget": total_budget,
                    "actual_total_interest": actual_total_interest,
                    "sellable_area": sellable_area,
                    "market_price_per_m2": market_price_per_m2,
                    "target_margin": target_margin,
                },
                "formula": "final_recommended = max(market_price, (total_budget + actual_interest) / sellable_area / (1 - target_margin))",
                "output": {
                    "final_target_margin_price_per_m2": final_target_margin_price,
                    "final_recommended_price_per_m2": final_recommended_price,
                },
            }
        ],
    }


def _estimate_interest(inputs: dict[str, Any], total_budget: float) -> float:
    credit_share = float(inputs.get("credit_share") or 0)
    credit_rate = float(inputs.get("credit_rate") or 0)
    construction_months = float(inputs.get("construction_months") or 0)
    return total_budget * credit_share * credit_rate * construction_months / 24


def _resolve_city(value: Any, warnings: list[str]) -> str:
    normalized = _normalize(value)
    if normalized in BASE_MARKET_PRICES:
        return normalized
    warnings.append("Город не найден в MVP-таблице цен. Использован рыночный ориентир default.")
    return "default"


def _resolve_object_class(value: Any, warnings: list[str]) -> str:
    object_class = CLASS_ALIASES.get(_normalize(value))
    if object_class:
        return object_class
    warnings.append("Класс объекта не найден в MVP-таблице цен. Использован класс комфорт.")
    return "комфорт"


def _object_type_coefficient(value: Any) -> float:
    normalized = _normalize(value)
    if "апартамент" in normalized:
        return 0.95
    if any(marker in normalized for marker in ("коммер", "офис", "торгов", "ритейл")):
        return 1.10
    return 1.00


def _floors_price_coefficient(floors: int) -> float:
    if floors <= 5:
        return 1.03
    if floors <= 12:
        return 1.00
    if floors <= 20:
        return 0.98
    return 0.97


def _scale_price_coefficient(total_area: float) -> float:
    if total_area < 3_000:
        return 1.03
    if total_area <= 10_000:
        return 1.00
    if total_area <= 30_000:
        return 0.98
    return 0.96


def _round_to_step(value: float, step: int) -> float:
    return float(round(value / step) * step)


def _ceil_to_step(value: float, step: int) -> float:
    return float(math.ceil(value / step) * step)


def _normalize(value: Any) -> str:
    text = str(value or "").lower().replace("ё", "е")
    return re.sub(r"[^a-zа-я0-9]+", "", text)
