from __future__ import annotations

from backend.tools.norms import round_money


def generate_credit_schedule(
    operations: list[dict[str, float]],
    credit_share: float,
    annual_rate: float,
    total_budget: float,
) -> dict[str, object]:
    limit = total_budget * credit_share
    monthly_rate = annual_rate / 12
    balance = 0.0
    rows: list[dict[str, float]] = []
    total_drawdown = 0.0
    total_interest = 0.0
    total_repayment = 0.0
    max_balance = 0.0

    for operation in operations:
        opening_balance = balance
        interest = opening_balance * monthly_rate
        operating_cashflow_before_financing = operation["sales_receipts"] - operation["project_costs"]
        cash_after_interest_before_financing = operating_cashflow_before_financing - interest
        required_drawdown = max(0.0, -cash_after_interest_before_financing) * credit_share
        available_limit = max(0.0, limit - opening_balance)
        drawdown = min(required_drawdown, available_limit)
        surplus_after_interest = max(0.0, cash_after_interest_before_financing)
        repayment = min(surplus_after_interest, opening_balance + drawdown)
        balance = opening_balance + drawdown - repayment

        total_drawdown += drawdown
        total_interest += interest
        total_repayment += repayment
        max_balance = max(max_balance, balance)
        rows.append(
            {
                "month": operation["month"],
                "opening_balance": round_money(opening_balance),
                "drawdown": round_money(drawdown),
                "interest": round_money(interest),
                "repayment": round_money(repayment),
                "closing_balance": round_money(balance),
            }
        )

    return {
        "limit": round_money(limit),
        "total_drawdown": round_money(total_drawdown),
        "total_interest": round_money(total_interest),
        "total_repayment": round_money(total_repayment),
        "max_balance": round_money(max_balance),
        "schedule": rows,
        "trace": [
            {
                "step": "generate_credit_schedule",
                "inputs": {"credit_share": credit_share, "annual_rate": annual_rate, "total_budget": total_budget},
                "formula": "drawdown covers credit_share of negative cash flow up to limit; interest = opening_balance * rate / 12",
                "output": {
                    "limit": round_money(limit),
                    "total_drawdown": round_money(total_drawdown),
                    "total_interest": round_money(total_interest),
                    "max_balance": round_money(max_balance),
                },
            }
        ],
    }
