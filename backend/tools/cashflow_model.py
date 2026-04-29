from __future__ import annotations

from backend.tools.norms import round_money


def build_operations(gpr: list[dict[str, float]], sales_plan: list[dict[str, float]]) -> list[dict[str, float]]:
    max_month = max(
        [row["month"] for row in gpr] + [row["month"] for row in sales_plan],
        default=1,
    )
    gpr_by_month = {row["month"]: row for row in gpr}
    sales_by_month = {row["month"]: row for row in sales_plan}
    operations: list[dict[str, float]] = []

    for month in range(1, int(max_month) + 1):
        gpr_row = gpr_by_month.get(month, {})
        sales_row = sales_by_month.get(month, {})
        construction_costs = float(gpr_row.get("construction_cost", 0.0))
        land = float(gpr_row.get("land_payment", 0.0))
        operations.append(
            {
                "month": month,
                "sales_receipts": float(sales_row.get("revenue", 0.0)),
                "construction_costs": construction_costs,
                "land": land,
                "other_expenses": 0.0,
                "project_costs": construction_costs + land,
            }
        )
    return operations


def generate_cashflow(
    operations: list[dict[str, float]],
    credit_schedule: list[dict[str, float]],
) -> list[dict[str, float]]:
    credit_by_month = {row["month"]: row for row in credit_schedule}
    accumulated_cashflow = 0.0
    rows: list[dict[str, float]] = []

    for operation in operations:
        credit = credit_by_month.get(operation["month"], {})
        operating_cashflow_before_financing = (
            operation["sales_receipts"]
            - operation["construction_costs"]
            - operation["land"]
            - operation["other_expenses"]
        )
        interest = float(credit.get("interest", 0.0))
        drawdown = float(credit.get("drawdown", 0.0))
        repayment = float(credit.get("repayment", 0.0))
        cash_after_credit_before_equity = operating_cashflow_before_financing + drawdown - interest - repayment
        equity_required = max(0.0, -cash_after_credit_before_equity)
        net_cashflow = (
            cash_after_credit_before_equity
            + equity_required
        )
        accumulated_cashflow += net_cashflow
        cumulative_equity_required = (
            rows[-1]["cumulative_equity_required"] if rows else 0.0
        ) + equity_required
        rows.append(
            {
                "month": operation["month"],
                "sales_receipts": round_money(operation["sales_receipts"]),
                "construction_costs": round_money(operation["construction_costs"]),
                "land": round_money(operation["land"]),
                "other_expenses": round_money(operation["other_expenses"]),
                "operating_cashflow_before_financing": round_money(operating_cashflow_before_financing),
                "credit_drawdown": round_money(drawdown),
                "interest": round_money(interest),
                "credit_repayment": round_money(repayment),
                "equity_required": round_money(equity_required),
                "cumulative_equity_required": round_money(cumulative_equity_required),
                "net_cashflow": round_money(net_cashflow),
                "accumulated_cashflow": round_money(accumulated_cashflow),
                "cash_balance_after_financing": round_money(accumulated_cashflow),
            }
        )
    return rows
