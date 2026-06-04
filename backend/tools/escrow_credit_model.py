from __future__ import annotations

from typing import Any

from backend.tools.norms import ESCROW_DEFAULTS, round_money


def generate_escrow_financing(
    *,
    gpr: list[dict[str, Any]],
    sales_plan: list[dict[str, Any]],
    total_budget: float,
    credit_share: float,
    base_rate: float,
    construction_months: int,
    escrow_covered_rate: float | None = None,
) -> dict[str, Any]:
    """Проектное финансирование с эскроу-счетами (214-ФЗ).

    Механика:
    - поступления от продаж до ввода в эксплуатацию копятся на эскроу-счетах
      и недоступны девелоперу;
    - стройка финансируется сначала собственными средствами (equity), затем
      кредитной линией банка;
    - проценты капитализируются в долг сверх лимита на затраты (ИОС —
      проценты на инвестиционной фазе входят в структуру кредита);
    - ставка blended: на часть долга, покрытую эскроу, действует льготная
      ставка, на непокрытую — базовая;
    - при вводе (конец construction_months) эскроу раскрывается и гасит долг,
      остаток уходит девелоперу; продажи после ввода поступают напрямую.
    """
    covered_rate = (
        float(escrow_covered_rate)
        if escrow_covered_rate is not None
        else float(ESCROW_DEFAULTS["escrow_covered_rate"])
    )
    base_rate = float(base_rate)
    total_budget = float(total_budget)
    credit_share = min(max(float(credit_share), 0.0), 1.0)
    delivery_month = max(1, int(construction_months))

    equity_pool = total_budget * (1.0 - credit_share)
    credit_limit = total_budget * credit_share

    costs_by_month: dict[int, float] = {}
    for row in gpr:
        costs_by_month[int(row["month"])] = costs_by_month.get(int(row["month"]), 0.0) + float(row["amount"])
    sales_by_month: dict[int, float] = {}
    for row in sales_plan:
        sales_by_month[int(row["month"])] = sales_by_month.get(int(row["month"]), 0.0) + float(row["revenue"])

    horizon = max(
        max(costs_by_month, default=1),
        max(sales_by_month, default=1),
        delivery_month,
    )

    debt = 0.0
    escrow_balance = 0.0
    equity_used = 0.0
    drawdown_used = 0.0
    developer_cash = 0.0
    total_interest = 0.0
    funding_gap_total = 0.0
    max_debt = 0.0
    max_debt_month = 0
    escrow_at_delivery = 0.0
    debt_at_delivery_before_release = 0.0
    escrow_released_to_debt = 0.0
    escrow_released_to_developer = 0.0
    repayment_finished_month: int | None = None
    schedule: list[dict[str, Any]] = []

    for month in range(1, horizon + 1):
        debt_opening = debt
        escrow_opening = escrow_balance
        cost = costs_by_month.get(month, 0.0)
        sale = sales_by_month.get(month, 0.0)

        # Проценты по blended-ставке, капитализируются в долг.
        covered = min(debt_opening, escrow_opening)
        uncovered = max(0.0, debt_opening - covered)
        interest = covered * covered_rate / 12.0 + uncovered * base_rate / 12.0
        debt = debt_opening + interest
        total_interest += interest

        # Финансирование затрат месяца: сначала equity, затем кредитная линия.
        equity_payment = min(cost, max(0.0, equity_pool - equity_used))
        equity_used += equity_payment
        need_from_credit = cost - equity_payment
        # Лимит расходуется выборками на затраты; капитализированные проценты (ИОС)
        # учитываются в долге сверх лимита затрат.
        available_limit = max(0.0, credit_limit - drawdown_used)
        drawdown = min(need_from_credit, available_limit)
        drawdown_used += drawdown
        funding_gap = need_from_credit - drawdown
        funding_gap_total += funding_gap
        debt += drawdown

        # Продажи: до ввода — на эскроу, после — напрямую.
        escrow_inflow = 0.0
        direct_receipts = 0.0
        if month <= delivery_month:
            escrow_inflow = sale
            escrow_balance += sale
        else:
            direct_receipts = sale

        # Раскрытие эскроу при вводе в эксплуатацию.
        escrow_release = 0.0
        repayment = 0.0
        if month == delivery_month:
            escrow_at_delivery = escrow_balance
            debt_at_delivery_before_release = debt
            escrow_release = escrow_balance
            repayment = min(debt, escrow_release)
            escrow_released_to_debt = repayment
            escrow_released_to_developer = escrow_release - repayment
            developer_cash += escrow_release - repayment
            debt -= repayment
            escrow_balance = 0.0

        # Прямые поступления после ввода гасят остаток долга.
        if direct_receipts > 0:
            direct_repayment = min(debt, direct_receipts)
            repayment += direct_repayment
            debt -= direct_repayment
            developer_cash += direct_receipts - direct_repayment

        if debt_opening > 0 and debt <= 0.005 and repayment_finished_month is None:
            repayment_finished_month = month

        if debt > max_debt:
            max_debt = debt
            max_debt_month = month

        coverage = (escrow_balance / debt) if debt > 0 else None
        schedule.append(
            {
                "month": month,
                "construction_cost": round_money(cost),
                "equity_payment": round_money(equity_payment),
                "drawdown": round_money(drawdown),
                "interest": round_money(interest),
                "escrow_inflow": round_money(escrow_inflow),
                "escrow_balance": round_money(escrow_balance),
                "escrow_release": round_money(escrow_release),
                "direct_receipts": round_money(direct_receipts),
                "repayment": round_money(repayment),
                "debt_balance": round_money(debt),
                "escrow_coverage": round(coverage, 4) if coverage is not None else None,
                "funding_gap": round_money(funding_gap),
            }
        )

    escrow_coverage_at_delivery = (
        escrow_at_delivery / debt_at_delivery_before_release
        if debt_at_delivery_before_release > 0
        else None
    )

    llcr, llcr_details = _calculate_llcr(
        schedule=schedule,
        costs_by_month=costs_by_month,
        sales_by_month=sales_by_month,
        delivery_month=delivery_month,
        max_debt_month=max_debt_month,
        discount_rate=base_rate,
        horizon=horizon,
    )

    ending_debt = debt
    revenue_total = sum(sales_by_month.values())
    profit_escrow = revenue_total - total_budget - total_interest
    margin_escrow = profit_escrow / revenue_total if revenue_total else 0.0

    return {
        "schedule": schedule,
        "delivery_month": delivery_month,
        "equity_pool": round_money(equity_pool),
        "equity_used": round_money(equity_used),
        "equity_share": round(equity_pool / total_budget, 4) if total_budget else 0.0,
        "credit_limit": round_money(credit_limit),
        "drawdown_used": round_money(drawdown_used),
        "base_rate": base_rate,
        "escrow_covered_rate": covered_rate,
        "total_interest": round_money(total_interest),
        "max_debt": round_money(max_debt),
        "max_debt_month": max_debt_month,
        "escrow_at_delivery": round_money(escrow_at_delivery),
        "debt_at_delivery": round_money(debt_at_delivery_before_release),
        "escrow_coverage_at_delivery": round(escrow_coverage_at_delivery, 4)
        if escrow_coverage_at_delivery is not None
        else None,
        "escrow_released_to_debt": round_money(escrow_released_to_debt),
        "escrow_released_to_developer": round_money(escrow_released_to_developer),
        "ending_debt": round_money(ending_debt),
        "repayment_finished_month": repayment_finished_month,
        "funding_gap_total": round_money(funding_gap_total),
        "llcr": llcr,
        "llcr_details": llcr_details,
        "revenue_total": round_money(revenue_total),
        "profit": round_money(profit_escrow),
        "margin": round(margin_escrow, 4),
        "trace": [
            {
                "step": "generate_escrow_financing",
                "inputs": {
                    "total_budget": round_money(total_budget),
                    "credit_share": credit_share,
                    "base_rate": base_rate,
                    "escrow_covered_rate": covered_rate,
                    "delivery_month": delivery_month,
                },
                "formula": (
                    "Эскроу: продажи до ввода копятся на счетах; проценты blended "
                    "(покрытая часть — льготная ставка) капитализируются; раскрытие на вводе гасит долг. "
                    "LLCR = PV(будущие чистые поступления, дисконт по базовой ставке) / пиковый долг."
                ),
                "output": {
                    "max_debt": round_money(max_debt),
                    "total_interest": round_money(total_interest),
                    "escrow_coverage_at_delivery": escrow_coverage_at_delivery,
                    "llcr": llcr,
                    "funding_gap_total": round_money(funding_gap_total),
                    "profit": round_money(profit_escrow),
                },
            }
        ],
    }


def _calculate_llcr(
    *,
    schedule: list[dict[str, Any]],
    costs_by_month: dict[int, float],
    sales_by_month: dict[int, float],
    delivery_month: int,
    max_debt_month: int,
    discount_rate: float,
    horizon: int,
) -> tuple[float | None, dict[str, Any]]:
    """LLCR на момент пикового долга.

    PV будущих средств, доступных на обслуживание долга (поступления от продаж
    минус оставшиеся затраты стройки), дисконтированных по базовой ставке,
    делённый на пиковый долг.
    """
    debt_at_peak = 0.0
    for row in schedule:
        if row["month"] == max_debt_month:
            debt_at_peak = float(row["debt_balance"])
            break
    if debt_at_peak <= 0:
        return None, {"reason": "Долг не возникает — LLCR не применим."}

    monthly_rate = discount_rate / 12.0
    pv_inflows = 0.0
    pv_outflows = 0.0
    escrow_now = 0.0
    for row in schedule:
        if row["month"] <= max_debt_month:
            escrow_now = float(row["escrow_balance"])

    # Эскроу, уже накопленное к пику, доступно для погашения при раскрытии — PV на момент раскрытия.
    if delivery_month > max_debt_month:
        periods = delivery_month - max_debt_month
        pv_inflows += escrow_now / (1 + monthly_rate) ** periods
    else:
        pv_inflows += escrow_now

    for month in range(max_debt_month + 1, horizon + 1):
        periods = month - max_debt_month
        discount = (1 + monthly_rate) ** periods
        sale = sales_by_month.get(month, 0.0)
        cost = costs_by_month.get(month, 0.0)
        if month <= delivery_month:
            # поступит на эскроу, станет доступно при раскрытии
            release_periods = delivery_month - max_debt_month
            pv_inflows += sale / (1 + monthly_rate) ** max(release_periods, periods)
        else:
            pv_inflows += sale / discount
        pv_outflows += cost / discount

    pv_available = pv_inflows - pv_outflows
    llcr = pv_available / debt_at_peak if debt_at_peak > 0 else None
    return (
        round(llcr, 4) if llcr is not None else None,
        {
            "debt_at_peak": round_money(debt_at_peak),
            "peak_month": max_debt_month,
            "pv_future_inflows": round_money(pv_inflows),
            "pv_future_costs": round_money(pv_outflows),
            "pv_available_for_debt": round_money(pv_available),
            "discount_rate": discount_rate,
        },
    )
