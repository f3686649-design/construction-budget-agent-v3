from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from backend.models import GeneratedModel, ProjectInput
from backend.tools.assumptions_engine import apply_assumptions
from backend.tools.budget_generator import generate_budget
from backend.tools.cashflow_model import build_operations, generate_cashflow
from backend.tools.cmr_splitter import split_cmr
from backend.tools.credit_model import generate_credit_schedule
from backend.tools.dscr_model import calculate_dscr
from backend.tools.excel_exporter import export_model_to_excel
from backend.tools.gpr_generator import generate_gpr
from backend.tools.norms import round_money
from backend.tools.optimization_advisor import advise_project_optimization
from backend.tools.price_estimator import estimate_sale_price
from backend.tools.risk_analyzer import analyze_risks
from backend.tools.scenario_generator import generate_scenarios
from backend.tools.sales_plan_generator import generate_sales_plan


OUTPUT_DIR = Path(__file__).resolve().parent / "storage" / "outputs"
app = FastAPI(title="Агент строительного бюджета v3", version="3.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/generate-model")
def generate_model(project_input: ProjectInput) -> dict[str, Any]:
    model = build_financial_model(project_input)
    excel_path = export_model_to_excel(model, OUTPUT_DIR)
    model["output_filename"] = excel_path.name
    return GeneratedModel(**model).model_dump()


@app.get("/download/{filename}")
def download(filename: str) -> FileResponse:
    path = (OUTPUT_DIR / filename).resolve()
    if OUTPUT_DIR.resolve() not in path.parents or not path.exists():
        raise HTTPException(status_code=404, detail="Файл не найден.")
    return FileResponse(path, filename=path.name)


def build_financial_model(project_input: ProjectInput) -> dict[str, Any]:
    trace: list[dict[str, Any]] = []
    assumptions_result = apply_assumptions(project_input)
    data = assumptions_result["data"]
    assumptions = assumptions_result["assumptions"]
    total_area = float(data["total_area"])
    sellable_area = float(data["sellable_area"])
    data["sellable_ratio"] = round(sellable_area / total_area, 4) if total_area else 0
    trace.extend(assumptions_result["trace"])

    budget = generate_budget(data)
    trace.extend(budget.pop("trace"))
    assumptions.extend(budget["cost_estimation_assumptions"])
    data["estimated_cmr_cost_per_m2"] = budget["estimated_cmr_cost_per_m2"]
    data["cmr_cost_source"] = budget["cmr_cost_source"]

    price_estimation = estimate_sale_price(data, budget, {})
    trace.extend(price_estimation["trace"])
    assumptions.extend(price_estimation["assumptions"])
    manual_sale_price = float(data.get("sale_price_per_m2") or 0)
    if manual_sale_price > 0:
        sale_price_source = "Ручная цена продажи"
    else:
        data["sale_price_per_m2"] = price_estimation["recommended_price_per_m2"]
        sale_price_source = "Расчётная цена продажи агента"
    data["estimated_sale_price_per_m2"] = price_estimation["estimated_sale_price_per_m2"]
    data["sale_price_source"] = sale_price_source
    data["market_price_per_m2"] = price_estimation["market_price_per_m2"]
    data["break_even_price_per_m2"] = price_estimation["break_even_price_per_m2"]
    data["target_margin_price_per_m2"] = price_estimation["target_margin_price_per_m2"]
    data["recommended_price_per_m2"] = price_estimation["recommended_price_per_m2"]
    data["price_gap_to_market"] = price_estimation["price_gap_to_market"]

    cmr = split_cmr(float(budget["cmr"]))
    trace.extend(cmr.pop("trace"))

    gpr = generate_gpr(
        total_budget=float(budget["total_budget"]),
        land_cost=float(budget["land"]),
        construction_months=int(data["construction_months"]),
    )
    trace.append(
        {
            "step": "generate_gpr",
            "inputs": {
                "total_budget": budget["total_budget"],
                "land_cost": budget["land"],
                "construction_months": data["construction_months"],
            },
            "formula": "S-curve weights normalized to total budget",
            "output": {"sum": round_money(sum(row["amount"] for row in gpr)), "months": len(gpr)},
        }
    )

    sales_plan = generate_sales_plan(
        sellable_area=float(data["sellable_area"]),
        sale_price_per_m2=float(data["sale_price_per_m2"]),
        sales_months=int(data["sales_months"]),
    )
    trace.append(
        {
            "step": "generate_sales_plan",
            "inputs": {
                "sellable_area": data["sellable_area"],
                "sale_price_per_m2": data["sale_price_per_m2"],
                "sales_months": data["sales_months"],
            },
            "formula": "slow start, mid-project peak, final tail; area normalized to sellable_area",
            "output": {
                "sold_area": round(sum(row["sold_area"] for row in sales_plan), 4),
                "revenue": round_money(sum(row["revenue"] for row in sales_plan)),
            },
        }
    )

    operations = build_operations(gpr, sales_plan)
    credit = generate_credit_schedule(
        operations=operations,
        credit_share=float(data["credit_share"]),
        annual_rate=float(data["credit_rate"]),
        total_budget=float(budget["total_budget"]),
    )
    trace.extend(credit["trace"])

    cashflow = generate_cashflow(operations, credit["schedule"])
    trace.append(
        {
            "step": "generate_cashflow",
            "inputs": {"operations": len(operations), "credit_rows": len(credit["schedule"])},
            "formula": "operating cashflow + credit drawdown + equity - interest - repayment",
            "output": {
                "ending_cashflow": cashflow[-1]["accumulated_cashflow"] if cashflow else 0,
                "total_equity_required": max((row["cumulative_equity_required"] for row in cashflow), default=0),
            },
        }
    )

    dscr = calculate_dscr(cashflow)
    trace.extend(dscr["trace"])

    revenue = sellable_area * float(data["sale_price_per_m2"])
    total_budget = float(budget["total_budget"])
    total_interest = float(credit["total_interest"])
    profit_before_interest = revenue - total_budget
    profit_after_interest = profit_before_interest - total_interest
    margin_before_interest = profit_before_interest / revenue if revenue else 0.0
    margin_after_interest = profit_after_interest / revenue if revenue else 0.0
    total_equity_required = max((float(row["cumulative_equity_required"]) for row in cashflow), default=0)
    economics = {
        "revenue": round_money(revenue),
        "total_budget": budget["total_budget"],
        "sellable_ratio": data["sellable_ratio"],
        "budget_per_total_m2": round_money(total_budget / total_area if total_area else 0),
        "budget_per_sellable_m2": round_money(total_budget / sellable_area if sellable_area else 0),
        "revenue_per_total_m2": round_money(revenue / total_area if total_area else 0),
        "profit_before_interest": round_money(profit_before_interest),
        "profit_after_interest": round_money(profit_after_interest),
        "margin_before_interest": round(margin_before_interest, 4),
        "margin_after_interest": round(margin_after_interest, 4),
        "profit": round_money(profit_after_interest),
        "margin": round(margin_after_interest, 4),
        "roi_on_budget": round(profit_after_interest / total_budget, 4) if total_budget else 0,
        "total_interest": credit["total_interest"],
        "max_credit_balance": credit["max_balance"],
        "total_equity_required": round_money(total_equity_required),
        "minimum_dscr": dscr["minimum_dscr"],
        "minimum_dscr_after_sales_start": dscr["minimum_dscr_after_sales_start"],
        "average_dscr_after_sales_start": dscr["average_dscr_after_sales_start"],
        "months_below_1_2": dscr["months_below_1_2"],
        "sale_price_source": sale_price_source,
        "sale_price_per_m2": data["sale_price_per_m2"],
        "estimated_sale_price_per_m2": price_estimation["estimated_sale_price_per_m2"],
        "market_price_per_m2": price_estimation["market_price_per_m2"],
        "break_even_price_per_m2": price_estimation["break_even_price_per_m2"],
        "target_margin_price_per_m2": price_estimation["target_margin_price_per_m2"],
        "recommended_price_per_m2": price_estimation["recommended_price_per_m2"],
        "price_gap_to_market": price_estimation["price_gap_to_market"],
    }
    trace.append(
        {
            "step": "calculate_economics",
            "inputs": {"revenue": revenue, "total_budget": budget["total_budget"], "interest": credit["total_interest"]},
            "formula": "profit_before_interest = revenue - total_budget; profit_after_interest = profit_before_interest - interest",
            "output": economics,
        }
    )

    optimization = advise_project_optimization(data, budget, economics)
    trace.extend(optimization.pop("trace"))

    risks = analyze_risks(data, budget, credit, dscr, economics, cashflow)
    trace.append(
        {
            "step": "analyze_risks",
            "inputs": {"risk_count": len(risks)},
            "output": {"risks": risks},
        }
    )
    scenarios = generate_scenarios(data)
    trace.append(
        {
            "step": "generate_scenarios",
            "inputs": {"base_input": data},
            "formula": "base, optimistic, stress scenario modifiers",
            "output": {"scenarios": scenarios},
        }
    )

    tep = {
        "project_name": data["project_name"],
        "city": data["city"],
        "object_type": data["object_type"],
        "object_class": data["object_class"],
        "land_area": data["land_area"],
        "total_area": data["total_area"],
        "sellable_area": data["sellable_area"],
        "sellable_ratio": data["sellable_ratio"],
        "floors": data["floors"],
        "sale_price_per_m2": data["sale_price_per_m2"],
        "estimated_sale_price_per_m2": price_estimation["estimated_sale_price_per_m2"],
        "sale_price_source": sale_price_source,
        "market_price_per_m2": price_estimation["market_price_per_m2"],
        "break_even_price_per_m2": price_estimation["break_even_price_per_m2"],
        "target_margin_price_per_m2": price_estimation["target_margin_price_per_m2"],
        "recommended_price_per_m2": price_estimation["recommended_price_per_m2"],
        "price_gap_to_market": price_estimation["price_gap_to_market"],
        "construction_cost_per_m2": data["construction_cost_per_m2"],
        "gp_contract_price_per_m2": data.get("gp_contract_price_per_m2"),
        "estimated_cmr_cost_per_m2": budget["estimated_cmr_cost_per_m2"],
        "cmr_cost_source": budget["cmr_cost_source"],
        "budget_per_total_m2": economics["budget_per_total_m2"],
        "budget_per_sellable_m2": economics["budget_per_sellable_m2"],
        "construction_months": data["construction_months"],
        "sales_months": data["sales_months"],
    }

    return {
        "status": "ok",
        "input": data,
        "assumptions": assumptions,
        "tep": tep,
        "budget": budget,
        "estimated_cmr_cost_per_m2": budget["estimated_cmr_cost_per_m2"],
        "cmr_cost_source": budget["cmr_cost_source"],
        "cost_estimation_components": budget["cost_estimation_components"],
        "cost_estimation_coefficients": budget["cost_estimation_coefficients"],
        "estimated_sale_price_per_m2": price_estimation["estimated_sale_price_per_m2"],
        "sale_price_source": sale_price_source,
        "market_price_per_m2": price_estimation["market_price_per_m2"],
        "break_even_price_per_m2": price_estimation["break_even_price_per_m2"],
        "target_margin_price_per_m2": price_estimation["target_margin_price_per_m2"],
        "recommended_price_per_m2": price_estimation["recommended_price_per_m2"],
        "price_gap_to_market": price_estimation["price_gap_to_market"],
        "price_estimation_components": price_estimation["price_components"],
        "price_estimation_coefficients": price_estimation["coefficients"],
        "price_estimation_warnings": price_estimation["warnings"],
        "cmr": cmr,
        "gpr": gpr,
        "sales_plan": sales_plan,
        "credit": credit,
        "cashflow": cashflow,
        "dscr": dscr,
        "economics": economics,
        "optimization": optimization,
        "scenarios": scenarios,
        "risks": risks,
        "trace": trace,
        "output_filename": None,
    }
