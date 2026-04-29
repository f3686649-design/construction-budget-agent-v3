from __future__ import annotations

from backend.tools.norms import round_money


def calculate_dscr(cashflow: list[dict[str, float]]) -> dict[str, object]:
    rows: list[dict[str, float | None]] = []
    dscr_values: list[float] = []

    for row in cashflow:
        debt_service = float(row["interest"]) + float(row["credit_repayment"])
        sales_receipts = float(row["sales_receipts"])
        dscr = None
        if debt_service > 0 and sales_receipts > 0:
            dscr = sales_receipts / debt_service
            dscr_values.append(dscr)
        rows.append(
            {
                "month": row["month"],
                "sales_receipts": row["sales_receipts"],
                "debt_service": round_money(debt_service),
                "dscr": round(dscr, 4) if dscr is not None else None,
            }
        )

    minimum_dscr = min(dscr_values) if dscr_values else None
    average_dscr = sum(dscr_values) / len(dscr_values) if dscr_values else None
    months_below_1_2 = sum(1 for value in dscr_values if value < 1.2)
    return {
        "minimum_dscr": round(minimum_dscr, 4) if minimum_dscr is not None else None,
        "minimum_dscr_after_sales_start": round(minimum_dscr, 4) if minimum_dscr is not None else None,
        "average_dscr_after_sales_start": round(average_dscr, 4) if average_dscr is not None else None,
        "months_below_1_2": months_below_1_2,
        "is_weak": minimum_dscr is not None and minimum_dscr < 1.2,
        "schedule": rows,
        "trace": [
            {
                "step": "calculate_dscr",
                "inputs": {"cashflow_months": len(cashflow)},
                "formula": "DSCR = sales_receipts / (interest + repayment); only months with sales and debt service are included",
                "output": {
                    "minimum_dscr_after_sales_start": round(minimum_dscr, 4) if minimum_dscr is not None else None,
                    "average_dscr_after_sales_start": round(average_dscr, 4) if average_dscr is not None else None,
                    "months_below_1_2": months_below_1_2,
                },
            }
        ],
    }
