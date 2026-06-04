from __future__ import annotations

from typing import Any

from backend.tools.escrow_credit_model import generate_escrow_financing
from backend.tools.norms import BANK_REQUIREMENTS, round_money

VERDICT_TEXT = {
    "approved": "Проект проходит банковское проектное финансирование по базовым критериям.",
    "conditional": "Проект пройдёт банк только с условиями — есть замечания, которые банк потребует закрыть.",
    "rejected": "Проект в текущем виде НЕ пройдёт банковское проектное финансирование.",
}


def evaluate_bank_approval(
    *,
    escrow: dict[str, Any],
    gpr: list[dict[str, Any]],
    sales_plan: list[dict[str, Any]],
    total_budget: float,
    credit_share: float,
    base_rate: float,
    construction_months: int,
    requirements: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Банковский чек-лист проектного финансирования (эскроу, 214-ФЗ).

    Критерии не подгоняются под желаемый результат: если проект не проходит —
    вердикт отрицательный с перечнем причин и рекомендациями.
    """
    req = {**BANK_REQUIREMENTS, **(requirements or {})}
    criteria: list[dict[str, Any]] = []
    recommendations: list[str] = []

    equity_share = float(escrow.get("equity_share") or 0)
    margin = float(escrow.get("margin") or 0)
    llcr = escrow.get("llcr")
    coverage = escrow.get("escrow_coverage_at_delivery")
    funding_gap = float(escrow.get("funding_gap_total") or 0)
    revenue_total = float(escrow.get("revenue_total") or 0)

    # 1. Собственное участие.
    passed = equity_share >= req["min_equity_share"]
    criteria.append(_criterion(
        code="equity_share",
        name="Собственное участие девелопера",
        threshold=f">= {req['min_equity_share']:.0%}",
        actual=f"{equity_share:.1%}",
        passed=passed,
        severity="critical",
        comment="Банки требуют подтверждённые собственные средства до открытия кредитной линии.",
    ))
    if not passed:
        delta = (req["min_equity_share"] - equity_share) * total_budget
        recommendations.append(
            f"Увеличить собственное участие минимум на {_fmt(delta)} ₽ "
            f"(до {req['min_equity_share']:.0%} бюджета): снизить долю кредита."
        )

    # 2. Маржа проекта по эскроу-модели.
    passed = margin >= req["min_margin"]
    criteria.append(_criterion(
        code="project_margin",
        name="Маржа проекта (эскроу-проценты)",
        threshold=f">= {req['min_margin']:.0%}",
        actual=f"{margin:.1%}",
        passed=passed,
        severity="critical",
        comment="Рентабельность ниже порога банк расценивает как отсутствие запаса прочности.",
    ))
    if not passed:
        recommendations.append(
            "Поднять маржу до порога: снизить себестоимость, пересмотреть цену продажи "
            "или отказаться от проекта в текущей конфигурации."
        )

    # 3. LLCR.
    if llcr is None:
        criteria.append(_criterion(
            code="llcr",
            name="LLCR (покрытие долга будущими поступлениями)",
            threshold=f">= {req['min_llcr']:.2f}",
            actual="долг не возникает",
            passed=True,
            severity="critical",
            comment="Кредит не выбирается — критерий не применим.",
        ))
    else:
        passed = float(llcr) >= req["min_llcr"]
        criteria.append(_criterion(
            code="llcr",
            name="LLCR (покрытие долга будущими поступлениями)",
            threshold=f">= {req['min_llcr']:.2f}",
            actual=f"{float(llcr):.2f}",
            passed=passed,
            severity="critical",
            comment="PV будущих чистых поступлений к пиковому долгу.",
        ))
        if not passed:
            recommendations.append(
                "Повысить LLCR: ускорить старт продаж, увеличить долю собственных средств "
                "или сократить пиковый долг (фазировка строительства)."
            )

    # 4. Покрытие долга эскроу на вводе.
    if coverage is None:
        criteria.append(_criterion(
            code="escrow_coverage",
            name="Покрытие долга эскроу на вводе",
            threshold=f">= {req['min_escrow_coverage']:.0%}",
            actual="долг на вводе отсутствует",
            passed=True,
            severity="warning",
            comment="Раскрытие эскроу полностью закрывает обязательства.",
        ))
    else:
        cov = float(coverage)
        if cov < req["critical_escrow_coverage"]:
            passed_flag, severity = False, "critical"
        elif cov < req["min_escrow_coverage"]:
            passed_flag, severity = False, "warning"
        else:
            passed_flag, severity = True, "warning"
        criteria.append(_criterion(
            code="escrow_coverage",
            name="Покрытие долга эскроу на вводе",
            threshold=f">= {req['min_escrow_coverage']:.0%}",
            actual=f"{cov:.0%}",
            passed=passed_flag,
            severity=severity,
            comment="Наполнение эскроу к моменту раскрытия относительно долга с процентами.",
        ))
        if not passed_flag:
            recommendations.append(
                "Увеличить наполнение эскроу к вводу: ускорить темпы продаж в стройке "
                "или удлинить график продаж до ввода."
            )

    # 5. Обеспеченность бюджета финансированием.
    passed = funding_gap <= 0.005
    criteria.append(_criterion(
        code="funding_gap",
        name="Обеспеченность бюджета (equity + кредитный лимит)",
        threshold="кассовый разрыв = 0",
        actual=f"{_fmt(funding_gap)} ₽",
        passed=passed,
        severity="critical",
        comment="Затраты, не покрытые ни собственными средствами, ни лимитом кредита.",
    ))
    if not passed:
        recommendations.append(
            f"Закрыть кассовый разрыв {_fmt(funding_gap)} ₽: увеличить кредитный лимит или equity."
        )

    # 6. Доля кредита (LTC).
    passed = credit_share <= req["max_credit_share"]
    criteria.append(_criterion(
        code="credit_share",
        name="Доля кредита в бюджете (LTC)",
        threshold=f"<= {req['max_credit_share']:.0%}",
        actual=f"{credit_share:.0%}",
        passed=passed,
        severity="warning",
        comment="Выше порога банк потребует дополнительное обеспечение.",
    ))
    if not passed:
        recommendations.append("Снизить долю кредита до приемлемого LTC.")

    # 7-8. Стресс-тесты: цена −10% и себестоимость +10% (по отдельности).
    stress_price = _stress_run(
        gpr=gpr,
        sales_plan=sales_plan,
        total_budget=total_budget,
        credit_share=credit_share,
        base_rate=base_rate,
        construction_months=construction_months,
        escrow_covered_rate=escrow.get("escrow_covered_rate"),
        price_factor=1.0 - req["stress_price_drop"],
        cost_factor=1.0,
    )
    passed = stress_price["profit"] >= 0
    criteria.append(_criterion(
        code="stress_price",
        name=f"Стресс-тест: цена продажи −{req['stress_price_drop']:.0%}",
        threshold="прибыль >= 0",
        actual=f"{_fmt(stress_price['profit'])} ₽ (маржа {stress_price['margin']:.1%})",
        passed=passed,
        severity="critical",
        comment="Банковский стресс по выручке.",
    ))
    if not passed:
        recommendations.append(
            f"Проект уходит в убыток при снижении цены на {req['stress_price_drop']:.0%} — "
            "нужен запас маржи или снижение себестоимости."
        )

    stress_cost = _stress_run(
        gpr=gpr,
        sales_plan=sales_plan,
        total_budget=total_budget,
        credit_share=credit_share,
        base_rate=base_rate,
        construction_months=construction_months,
        escrow_covered_rate=escrow.get("escrow_covered_rate"),
        price_factor=1.0,
        cost_factor=1.0 + req["stress_cost_increase"],
    )
    passed = stress_cost["profit"] >= 0
    criteria.append(_criterion(
        code="stress_cost",
        name=f"Стресс-тест: себестоимость +{req['stress_cost_increase']:.0%}",
        threshold="прибыль >= 0",
        actual=f"{_fmt(stress_cost['profit'])} ₽ (маржа {stress_cost['margin']:.1%})",
        passed=passed,
        severity="critical",
        comment="Банковский стресс по затратам.",
    ))
    if not passed:
        recommendations.append(
            f"Проект уходит в убыток при удорожании стройки на {req['stress_cost_increase']:.0%} — "
            "резерв непредвиденных недостаточен."
        )

    failed_critical = [c for c in criteria if not c["passed"] and c["severity"] == "critical"]
    failed_warning = [c for c in criteria if not c["passed"] and c["severity"] == "warning"]

    if failed_critical:
        verdict_code = "rejected"
        verdict_level = "critical"
    elif failed_warning:
        verdict_code = "conditional"
        verdict_level = "warning"
    else:
        verdict_code = "approved"
        verdict_level = "ok"

    verdict = VERDICT_TEXT[verdict_code]
    if failed_critical:
        names = "; ".join(c["name"] for c in failed_critical)
        verdict += f" Не пройдено: {names}."
    elif failed_warning:
        names = "; ".join(c["name"] for c in failed_warning)
        verdict += f" Замечания: {names}."

    return {
        "verdict": verdict,
        "verdict_code": verdict_code,
        "verdict_level": verdict_level,
        "criteria": criteria,
        "passed_count": sum(1 for c in criteria if c["passed"]),
        "failed_critical_count": len(failed_critical),
        "failed_warning_count": len(failed_warning),
        "recommendations": recommendations,
        "stress_tests": {
            "price_drop": stress_price,
            "cost_increase": stress_cost,
        },
        "requirements": req,
        "trace": [
            {
                "step": "evaluate_bank_approval",
                "inputs": {
                    "equity_share": equity_share,
                    "margin": margin,
                    "llcr": llcr,
                    "escrow_coverage_at_delivery": coverage,
                    "funding_gap_total": funding_gap,
                    "credit_share": credit_share,
                    "revenue_total": round_money(revenue_total),
                },
                "formula": "Чек-лист банка: критерии с порогами + стресс-тесты −10% цена / +10% себестоимость.",
                "output": {
                    "verdict_code": verdict_code,
                    "failed_critical": [c["code"] for c in failed_critical],
                    "failed_warning": [c["code"] for c in failed_warning],
                },
            }
        ],
    }


def _stress_run(
    *,
    gpr: list[dict[str, Any]],
    sales_plan: list[dict[str, Any]],
    total_budget: float,
    credit_share: float,
    base_rate: float,
    construction_months: int,
    escrow_covered_rate: float | None,
    price_factor: float,
    cost_factor: float,
) -> dict[str, Any]:
    stressed_gpr = [
        {"month": row["month"], "amount": float(row["amount"]) * cost_factor} for row in gpr
    ]
    stressed_sales = [
        {"month": row["month"], "revenue": float(row["revenue"]) * price_factor} for row in sales_plan
    ]
    stressed = generate_escrow_financing(
        gpr=stressed_gpr,
        sales_plan=stressed_sales,
        total_budget=total_budget * cost_factor,
        credit_share=credit_share,
        base_rate=base_rate,
        construction_months=construction_months,
        escrow_covered_rate=escrow_covered_rate,
    )
    return {
        "price_factor": price_factor,
        "cost_factor": cost_factor,
        "profit": stressed["profit"],
        "margin": stressed["margin"],
        "llcr": stressed["llcr"],
        "escrow_coverage_at_delivery": stressed["escrow_coverage_at_delivery"],
        "max_debt": stressed["max_debt"],
        "total_interest": stressed["total_interest"],
    }


def _criterion(
    *,
    code: str,
    name: str,
    threshold: str,
    actual: str,
    passed: bool,
    severity: str,
    comment: str,
) -> dict[str, Any]:
    return {
        "code": code,
        "name": name,
        "threshold": threshold,
        "actual": actual,
        "passed": passed,
        "severity": severity,
        "status": "пройден" if passed else ("критично" if severity == "critical" else "замечание"),
        "comment": comment,
    }


def _fmt(value: float) -> str:
    return f"{value:,.0f}".replace(",", " ")
