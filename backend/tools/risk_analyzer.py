from __future__ import annotations

from typing import Any

from backend.tools.norms import RISK_THRESHOLDS


ABOVE_GROUND_NORMATIVE_RATE = 23_120
ENVELOPE_NORMATIVE_RATE = 11_560
EARTHWORKS_PILE_NO_UNDERGROUND_RATE = 800
EARTHWORKS_UNDERGROUND_RATE = 3_000
EARTHWORKS_BASE_RATE = 1_800


def _risk(code: str, level: str, title: str, description: str, recommendation: str) -> dict[str, str]:
    return {
        "code": code,
        "level": level,
        "title": title,
        "description": description,
        "recommendation": recommendation,
    }


def analyze_risks(
    data: dict[str, Any],
    budget: dict[str, Any],
    credit: dict[str, Any],
    dscr: dict[str, Any],
    economics: dict[str, Any],
    cashflow: list[dict[str, Any]],
) -> list[dict[str, str]]:
    risks: list[dict[str, str]] = []
    sale_price = float(data["sale_price_per_m2"])
    cost_per_m2 = float(budget["cost_per_total_m2"])
    margin = float(economics["margin_after_interest"])
    min_dscr = dscr.get("minimum_dscr_after_sales_start")
    sellable_ratio = float(economics["sellable_ratio"])
    sellable_cost_ratio = float(economics["budget_per_sellable_m2"]) / sale_price if sale_price else 0
    recommended_price = float(economics.get("recommended_price_per_m2") or 0)
    market_price = float(economics.get("market_price_per_m2") or 0)
    break_even_price = float(economics.get("break_even_price_per_m2") or 0)

    risks.extend(_manual_rate_risks(data))

    if sellable_ratio < 0.65:
        risks.append(
            _risk(
                "low_sellable_ratio",
                "high",
                "Низкая продаваемая площадь",
                "Доля продаваемой площади ниже 65% от общей площади.",
                "Проверить планировки, МОП, техпомещения, паркинг и состав непродаваемых площадей.",
            )
        )
    elif sellable_ratio < 0.72:
        risks.append(
            _risk(
                "medium_sellable_ratio",
                "medium",
                "Продаваемая площадь ниже целевого уровня",
                "Доля продаваемой площади находится между 65% и 72%.",
                "Проверить эффективность планировок и коммерциализацию площадей.",
            )
        )
    else:
        risks.append(
            _risk(
                "sellable_ratio_ok",
                "ok",
                "Продаваемая площадь в рабочем диапазоне",
                "Доля продаваемой площади не ниже 72%.",
                "Сохранить контроль показателя при изменении концепции.",
            )
        )
    if market_price and recommended_price > market_price * 1.10:
        risks.append(
            _risk(
                "recommended_price_far_above_market",
                "high",
                "Требуемая цена выше рынка",
                "Требуемая цена продажи более чем на 10% выше рыночного ориентира.",
                "Проверить продукт, маркетинг, темп продаж и сценарий снижения цены.",
            )
        )
    elif market_price and recommended_price > market_price * 1.05:
        risks.append(
            _risk(
                "recommended_price_above_market",
                "medium",
                "Требуемая цена выше рыночного ориентира",
                "Требуемая цена продажи более чем на 5% выше рыночного ориентира.",
                "Проверить чувствительность проекта к цене реализации.",
            )
        )
    if market_price and break_even_price > market_price:
        risks.append(
            _risk(
                "break_even_above_market",
                "high",
                "Цена безубыточности выше рынка",
                "Цена безубыточности выше рыночного ориентира.",
                "Снизить бюджет, увеличить продаваемую площадь или пересмотреть условия финансирования.",
            )
        )

    if sale_price and cost_per_m2 / sale_price > RISK_THRESHOLDS["high_cost_to_sale_ratio"]:
        risks.append(
            _risk(
                "high_cost_per_m2",
                "high",
                "Высокая себестоимость м2",
                "Итоговая стоимость на м2 слишком близка к цене продажи.",
                "Проверить СМР, генподряд, сети и резерв, затем провести value engineering.",
            )
        )
    if sellable_cost_ratio > 0.85:
        risks.append(
            _risk(
                "high_sellable_cost_ratio",
                "high",
                "Высокая себестоимость продаваемого м2",
                "Бюджет на 1 м2 продаваемой площади выше 85% цены продажи.",
                "Проверить себестоимость, продуктовую программу и цену реализации.",
            )
        )
    elif sellable_cost_ratio > 0.75:
        risks.append(
            _risk(
                "medium_sellable_cost_ratio",
                "medium",
                "Повышенная себестоимость продаваемого м2",
                "Бюджет на 1 м2 продаваемой площади выше 75% цены продажи.",
                "Проверить чувствительность маржи к стоимости СМР и темпу продаж.",
            )
        )
    else:
        risks.append(
            _risk(
                "sellable_cost_ratio_ok",
                "ok",
                "Себестоимость продаваемого м2 в рабочем диапазоне",
                "Бюджет на 1 м2 продаваемой площади ниже 75% цены продажи.",
                "Сохранить контроль показателя в стресс-сценарии.",
            )
        )
    if margin < RISK_THRESHOLDS["low_margin"]:
        risks.append(
            _risk(
                "low_margin",
                "high",
                "Низкая маржа",
                "Маржа проекта ниже комфортного уровня для девелоперского риска.",
                "Повысить цену, сократить бюджет или пересмотреть продуктовую программу.",
            )
        )
    if float(data["credit_share"]) > RISK_THRESHOLDS["high_credit_share"]:
        risks.append(
            _risk(
                "high_credit",
                "medium",
                "Высокая доля кредита",
                "Проект сильно зависит от заемного финансирования.",
                "Снизить LTV, добавить собственные средства или фазировать проект.",
            )
        )
    if int(data["construction_months"]) < RISK_THRESHOLDS["short_construction_months"]:
        risks.append(
            _risk(
                "short_construction",
                "medium",
                "Короткий срок строительства",
                "Срок строительства выглядит агрессивным для девелоперского проекта.",
                "Проверить ГПР с технической командой и заложить буфер.",
            )
        )
    if min_dscr is not None and float(min_dscr) < RISK_THRESHOLDS["min_dscr"]:
        risks.append(
            _risk(
                "weak_dscr",
                "high",
                "Слабый DSCR",
                "Минимальный DSCR ниже 1.2, обслуживание долга напряженное.",
                "Сместить продажи раньше, снизить долг или увеличить капитал.",
            )
        )
    if float(data["reserve"]) < RISK_THRESHOLDS["minimum_reserve"]:
        risks.append(
            _risk(
                "low_reserve",
                "medium",
                "Недостаточный резерв",
                "Резерв ниже базового нормативного уровня 5% от СМР.",
                "Увеличить резерв или раскрыть риск в инвестиционном комитете.",
            )
        )
    if not data["external_networks_included"]:
        risks.append(
            _risk(
                "external_networks_excluded",
                "medium",
                "Наружные сети исключены",
                "Наружные сети не включены в бюджет, возможен скрытый CAPEX.",
                "Подтвердить техусловия и границы ответственности ресурсоснабжающих организаций.",
            )
        )
    if float(credit["max_balance"]) > float(economics["revenue"]) * 0.35:
        risks.append(
            _risk(
                "sales_dependency",
                "medium",
                "Высокая зависимость от продаж",
                "Пиковый долг значителен относительно выручки.",
                "Проверить скорость продаж и стресс-сценарий цены.",
            )
        )
    if min(float(row["accumulated_cashflow"]) for row in cashflow) < -0.01:
        risks.append(
            _risk(
                "cash_gap",
                "high",
                "Кассовый разрыв",
                "После учета кредита накопленный денежный поток уходит ниже нуля.",
                "Увеличить лимит кредита или изменить график затрат и продаж.",
            )
        )

    if not risks:
        risks.append(
            _risk(
                "no_material_risks",
                "low",
                "Критические риски не выявлены",
                "Базовые показатели находятся в рабочем диапазоне.",
                "Проверить модель на стресс-сценариях цены, сроков и бюджета.",
            )
        )
    return risks


def _manual_rate_risks(data: dict[str, Any]) -> list[dict[str, str]]:
    risks: list[dict[str, str]] = []
    checks = (
        (
            "manual_above_ground_structures_rate_low",
            "Ставка надземных несущих конструкций снижена",
            float(data.get("above_ground_structures_rate_override") or 0),
            ABOVE_GROUND_NORMATIVE_RATE,
        ),
        (
            "manual_envelope_roof_walls_rate_low",
            "Ставка ограждающих конструкций / стен / кровли снижена",
            float(data.get("envelope_roof_walls_rate_override") or 0),
            ENVELOPE_NORMATIVE_RATE,
        ),
        (
            "manual_earthworks_rate_low",
            "Ставка земляных работ снижена",
            float(data.get("earthworks_rate_override") or 0),
            _earthworks_normative_rate(data),
        ),
    )
    for code, title, manual_rate, normative_rate in checks:
        if manual_rate > 0 and normative_rate > 0 and manual_rate < normative_rate * 0.85:
            risks.append(
                _risk(
                    code,
                    "medium",
                    title,
                    "Ставка снижена относительно норматива. Нужно подтвердить КП подрядчика или локальный сметный расчёт.",
                    "Запросить коммерческое предложение подрядчика, смету или локальный расчёт, подтверждающий ручную ставку.",
                )
            )
    return risks


def _earthworks_normative_rate(data: dict[str, Any]) -> float:
    foundation_type = str(data.get("foundation_type") or "").lower().replace("ё", "е").replace(" ", "")
    if foundation_type == "сваи" and not bool(data.get("has_underground_part")):
        return EARTHWORKS_PILE_NO_UNDERGROUND_RATE
    if bool(data.get("has_underground_part")):
        return EARTHWORKS_UNDERGROUND_RATE
    return EARTHWORKS_BASE_RATE
