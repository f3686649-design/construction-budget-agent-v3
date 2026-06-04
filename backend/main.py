from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import FileResponse, JSONResponse

from backend.api.routes import router as api_router
from backend.models import GeneratedModel, ProjectInput
from backend.project_history import save_project_metadata
from backend.tools.assumptions_engine import apply_assumptions
from backend.tools.budget_generator import generate_budget
from backend.tools.cashflow_model import build_operations, generate_cashflow
from backend.tools.cmr_splitter import split_cmr
from backend.tools.credit_model import generate_credit_schedule
from backend.tools.detailed_budget_generator import (
    apply_detailed_budget_to_budget,
    generate_detailed_budget,
    generate_supply_plan,
    generate_work_schedule,
)
from backend.tools.dscr_model import calculate_dscr
from backend.tools.excel_exporter import export_model_to_excel
from backend.tools.gpr_generator import generate_gpr
from backend.tools.bank_approval import evaluate_bank_approval
from backend.tools.escrow_credit_model import generate_escrow_financing
from backend.tools.improvement_plan import build_improvement_plan
from backend.tools.land_value_estimator import evaluate_land_value
from backend.tools.norms import round_money
from backend.tools.optimization_advisor import advise_project_optimization
from backend.tools.price_estimator import estimate_sale_price, recalculate_price_with_actual_interest
from backend.tools.risk_analyzer import analyze_risks
from backend.tools.scenario_generator import generate_scenarios
from backend.tools.sales_plan_generator import generate_sales_plan
from backend.tools.tech_connection_estimator import estimate_tech_connection


OUTPUT_DIR = Path(__file__).resolve().parent / "storage" / "outputs"
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if origin.strip()
]
# Публичные legacy-endpoints без авторизации (/generate-model, /download).
# Локально удобны; в проде выключить: ALLOW_PUBLIC_GENERATE=false (есть /api/* с авторизацией).
ALLOW_PUBLIC_GENERATE = os.getenv("ALLOW_PUBLIC_GENERATE", "true").strip().lower() not in ("false", "0", "no")

app = FastAPI(title="Агент строительного бюджета v3", version="3.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    fields: list[str] = []
    for error in exc.errors():
        location = error.get("loc", [])
        field = ".".join(str(part) for part in location if part not in ("body", "query", "path"))
        if field:
            fields.append(field)
    message = "Некорректные параметры проекта."
    if fields:
        message = f"{message} Проверьте поля: {', '.join(sorted(set(fields)))}."
    return JSONResponse(status_code=422, content={"detail": message})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _require_public_api() -> None:
    if not ALLOW_PUBLIC_GENERATE:
        raise HTTPException(
            status_code=403,
            detail="Публичный endpoint отключён. Используйте /api/generate-model с авторизацией.",
        )


@app.post("/generate-model")
def generate_model(project_input: ProjectInput) -> dict[str, Any]:
    _require_public_api()
    model = build_financial_model(project_input)
    excel_path = export_model_to_excel(model, OUTPUT_DIR)
    model["output_filename"] = excel_path.name
    model["project_metadata"] = save_project_metadata(model=model, excel_path=excel_path, username="api")
    return GeneratedModel(**model).model_dump()


@app.get("/download/{filename}")
def download(filename: str) -> FileResponse:
    _require_public_api()
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

    detailed_budget = generate_detailed_budget(data, budget, {})
    trace.extend(detailed_budget.pop("trace"))
    budget = apply_detailed_budget_to_budget(data, budget, detailed_budget)
    trace.append(
        {
            "step": "apply_detailed_budget_to_budget",
            "inputs": {"base_budget_total": budget.get("base_total_budget")},
            "formula": "Итоговый бюджет модели принимается равным сумме детального бюджета без компенсационного распределения.",
            "output": {
                "total_budget": budget["total_budget"],
                "cmr": budget["cmr"],
                "engineering_systems_amount": data.get("engineering_systems_amount"),
                "pile_foundation_amount": data.get("pile_foundation_amount"),
            },
        }
    )

    price_estimation = estimate_sale_price(data, budget, {})
    trace.extend(price_estimation["trace"])
    assumptions.extend(price_estimation["assumptions"])
    manual_sale_price = float(data.get("sale_price_per_m2") or 0)
    preliminary_recommended_price = float(price_estimation["recommended_price_per_m2"])
    if manual_sale_price > 0:
        sale_price_source = "Ручная цена продажи"
    else:
        data["sale_price_per_m2"] = preliminary_recommended_price
        sale_price_source = "Расчётная цена продажи агента"
    data["estimated_sale_price_per_m2"] = preliminary_recommended_price
    data["sale_price_source"] = sale_price_source
    data["preliminary_recommended_price_per_m2"] = preliminary_recommended_price
    data["market_price_per_m2"] = price_estimation["market_price_per_m2"]
    data["break_even_price_per_m2"] = price_estimation["break_even_price_per_m2"]
    data["target_margin_price_per_m2"] = price_estimation["target_margin_price_per_m2"]
    data["recommended_price_per_m2"] = preliminary_recommended_price
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

    price_iteration_count = 0
    price_recalculation: dict[str, Any] | None = None
    while True:
        financials = _calculate_financial_outputs(
            data=data,
            budget=budget,
            gpr=gpr,
            price_estimation=price_estimation,
            sale_price_source=sale_price_source,
            trace=trace,
            iteration=price_iteration_count,
        )
        sales_plan = financials["sales_plan"]
        credit = financials["credit"]
        cashflow = financials["cashflow"]
        dscr = financials["dscr"]
        economics = financials["economics"]
        price_recalculation = recalculate_price_with_actual_interest(
            total_budget=float(budget["total_budget"]),
            actual_total_interest=float(credit["total_interest"]),
            sellable_area=sellable_area,
            market_price_per_m2=float(price_estimation["market_price_per_m2"]),
        )
        trace.extend(price_recalculation["trace"])
        final_recommended_price = float(price_recalculation["final_recommended_price_per_m2"])
        current_price = float(data["sale_price_per_m2"])
        if manual_sale_price > 0 or abs(final_recommended_price - current_price) <= 1000 or price_iteration_count >= 3:
            break
        data["sale_price_per_m2"] = final_recommended_price
        price_iteration_count += 1

    assert price_recalculation is not None
    data["final_target_margin_price_per_m2"] = price_recalculation["final_target_margin_price_per_m2"]
    data["final_recommended_price_per_m2"] = price_recalculation["final_recommended_price_per_m2"]
    data["actual_total_interest_used_for_price"] = price_recalculation["actual_total_interest_used_for_price"]
    data["price_iteration_count"] = price_iteration_count
    data["target_margin_price_per_m2"] = price_recalculation["final_target_margin_price_per_m2"]
    data["price_gap_to_market"] = price_recalculation["price_gap_to_market"]
    if manual_sale_price <= 0:
        data["sale_price_per_m2"] = price_recalculation["final_recommended_price_per_m2"]
        data["estimated_sale_price_per_m2"] = price_recalculation["final_recommended_price_per_m2"]
        data["recommended_price_per_m2"] = price_recalculation["final_recommended_price_per_m2"]
    else:
        data["recommended_price_per_m2"] = price_recalculation["final_recommended_price_per_m2"]
    economics.update(_pricing_metrics(data, price_estimation, sale_price_source))

    land_valuation = evaluate_land_value(
        revenue=float(economics["revenue"]),
        total_budget=float(budget["total_budget"]),
        land_cost=float(budget["land"]),
        total_interest=float(credit["total_interest"]),
        land_area=float(data.get("land_area") or 0),
        market_revenue=float(data["market_price_per_m2"]) * sellable_area if data.get("market_price_per_m2") else None,
        profit_after_interest=float(economics["profit_after_interest"]),
        margin_after_interest=float(economics["margin_after_interest"]),
    )
    trace.extend(land_valuation.pop("trace"))
    assumptions.extend(land_valuation.pop("assumption_records"))

    escrow_financing = generate_escrow_financing(
        gpr=gpr,
        sales_plan=sales_plan,
        total_budget=float(budget["total_budget"]),
        credit_share=float(data["credit_share"]),
        base_rate=float(data["credit_rate"]),
        construction_months=int(data["construction_months"]),
    )
    trace.extend(escrow_financing.pop("trace"))
    bank_approval = evaluate_bank_approval(
        escrow=escrow_financing,
        gpr=gpr,
        sales_plan=sales_plan,
        total_budget=float(budget["total_budget"]),
        credit_share=float(data["credit_share"]),
        base_rate=float(data["credit_rate"]),
        construction_months=int(data["construction_months"]),
    )
    trace.extend(bank_approval.pop("trace"))
    assumptions.append(
        {
            "field": "escrow_covered_rate",
            "value": escrow_financing["escrow_covered_rate"],
            "reason": "Льготная ставка на часть долга, покрытую эскроу (проектное финансирование, 214-ФЗ).",
            "source": "developer_assumption",
        }
    )
    economics["llcr"] = escrow_financing["llcr"]
    economics["escrow_coverage_at_delivery"] = escrow_financing["escrow_coverage_at_delivery"]
    economics["escrow_total_interest"] = escrow_financing["total_interest"]
    economics["bank_verdict_code"] = bank_approval["verdict_code"]

    tech_connection = estimate_tech_connection(data, budget)
    trace.extend(tech_connection.pop("trace"))
    assumptions.extend(tech_connection.pop("assumption_records"))

    price_warning = "Цена для целевой маржи выше рыночного ориентира. Есть риск, что проект не продастся по требуемой цене."
    price_estimation_warnings = [warning for warning in price_estimation["warnings"] if warning != price_warning]
    if data["final_target_margin_price_per_m2"] > data["market_price_per_m2"]:
        price_estimation_warnings.append(price_warning)

    work_schedule = generate_work_schedule(data, budget, detailed_budget)
    trace.extend(work_schedule.pop("trace"))
    supply_plan = generate_supply_plan(data, detailed_budget, work_schedule)
    summary_metrics = _build_summary_metrics(budget, economics, credit, detailed_budget)
    economics.update(summary_metrics)

    risks = analyze_risks(data, budget, credit, dscr, economics, cashflow)
    if land_valuation["verdict_level"] == "critical":
        risks.insert(
            0,
            {
                "code": "land_price_infeasible",
                "level": "high",
                "title": "Цена земли экономически не обоснована",
                "description": land_valuation["verdict"],
                "recommendation": (
                    "Торговаться до цены не выше "
                    f"{round_money(max(land_valuation['max_land_price'], 0))} ₽ "
                    "или отказаться от покупки участка."
                ),
            },
        )
    elif land_valuation["verdict_level"] == "warning":
        risks.insert(
            0,
            {
                "code": "land_price_borderline",
                "level": "medium",
                "title": "Запас по цене земли ниже порога",
                "description": land_valuation["verdict"],
                "recommendation": "Зафиксировать цену продажи и себестоимость до сделки по участку.",
            },
        )
    if bank_approval["verdict_code"] == "rejected":
        risks.insert(
            0,
            {
                "code": "bank_financing_rejected",
                "level": "high",
                "title": "Проект не проходит банковское финансирование",
                "description": bank_approval["verdict"],
                "recommendation": " ".join(bank_approval["recommendations"][:3])
                or "Пересмотреть структуру финансирования проекта.",
            },
        )
    elif bank_approval["verdict_code"] == "conditional":
        risks.insert(
            0,
            {
                "code": "bank_financing_conditional",
                "level": "medium",
                "title": "Банк согласует проект только с условиями",
                "description": bank_approval["verdict"],
                "recommendation": " ".join(bank_approval["recommendations"][:3])
                or "Закрыть замечания банка до подачи заявки.",
            },
        )
    if tech_connection["verdict_level"] == "critical":
        risks.insert(
            0,
            {
                "code": "tech_connection_deficit",
                "level": "high",
                "title": "Техприсоединение не обеспечено бюджетом",
                "description": tech_connection["verdict"],
                "recommendation": (
                    f"Заложить в бюджет плату за ТП {round_money(tech_connection['total_cost'])} ₽ "
                    "и запросить ТУ у ресурсоснабжающих организаций до сделки по участку."
                ),
            },
        )
    elif tech_connection["verdict_level"] == "warning":
        risks.insert(
            0,
            {
                "code": "tech_connection_warning",
                "level": "medium",
                "title": "Риски по техприсоединению",
                "description": tech_connection["verdict"],
                "recommendation": "Уточнить плату и сроки по фактическим ТУ, подать заявки до старта стройки.",
            },
        )
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
    optimization = advise_project_optimization(data, budget, economics)
    trace.extend(optimization.get("trace", []))
    improvement_plan = build_improvement_plan(data, budget, economics, optimization, risks, scenarios)
    trace.extend(improvement_plan.get("trace", []))

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
        "estimated_sale_price_per_m2": data["estimated_sale_price_per_m2"],
        "sale_price_source": sale_price_source,
        "market_price_per_m2": price_estimation["market_price_per_m2"],
        "break_even_price_per_m2": price_estimation["break_even_price_per_m2"],
        "target_margin_price_per_m2": data["target_margin_price_per_m2"],
        "recommended_price_per_m2": data["recommended_price_per_m2"],
        "preliminary_recommended_price_per_m2": data["preliminary_recommended_price_per_m2"],
        "final_recommended_price_per_m2": data["final_recommended_price_per_m2"],
        "final_target_margin_price_per_m2": data["final_target_margin_price_per_m2"],
        "price_iteration_count": data["price_iteration_count"],
        "price_gap_to_market": data["price_gap_to_market"],
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
        "estimated_sale_price_per_m2": data["estimated_sale_price_per_m2"],
        "sale_price_source": sale_price_source,
        "market_price_per_m2": price_estimation["market_price_per_m2"],
        "break_even_price_per_m2": price_estimation["break_even_price_per_m2"],
        "target_margin_price_per_m2": data["target_margin_price_per_m2"],
        "recommended_price_per_m2": data["recommended_price_per_m2"],
        "preliminary_recommended_price_per_m2": data["preliminary_recommended_price_per_m2"],
        "final_recommended_price_per_m2": data["final_recommended_price_per_m2"],
        "final_target_margin_price_per_m2": data["final_target_margin_price_per_m2"],
        "price_iteration_count": data["price_iteration_count"],
        "actual_total_interest_used_for_price": data["actual_total_interest_used_for_price"],
        "price_gap_to_market": data["price_gap_to_market"],
        "price_estimation_components": price_estimation["price_components"],
        "price_estimation_coefficients": price_estimation["coefficients"],
        "price_estimation_warnings": price_estimation_warnings,
        "cmr": cmr,
        "gpr": gpr,
        "sales_plan": sales_plan,
        "credit": credit,
        "cashflow": cashflow,
        "dscr": dscr,
        "economics": economics,
        "land_valuation": land_valuation,
        "escrow_financing": escrow_financing,
        "bank_approval": bank_approval,
        "tech_connection": tech_connection,
        "detailed_budget": detailed_budget,
        "work_schedule": work_schedule,
        "gpr_summary": work_schedule["summary"],
        "supply_plan": supply_plan,
        "summary_metrics": summary_metrics,
        "optimization": optimization,
        "improvement_plan": improvement_plan,
        "scenarios": scenarios,
        "risks": risks,
        "trace": trace,
        "output_filename": None,
    }


def _calculate_financial_outputs(
    *,
    data: dict[str, Any],
    budget: dict[str, Any],
    gpr: list[dict[str, Any]],
    price_estimation: dict[str, Any],
    sale_price_source: str,
    trace: list[dict[str, Any]],
    iteration: int,
) -> dict[str, Any]:
    sales_plan = generate_sales_plan(
        sellable_area=float(data["sellable_area"]),
        sale_price_per_m2=float(data["sale_price_per_m2"]),
        sales_months=int(data["sales_months"]),
    )
    trace.append(
        {
            "step": "generate_sales_plan",
            "inputs": {
                "iteration": iteration,
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
            "inputs": {"iteration": iteration, "operations": len(operations), "credit_rows": len(credit["schedule"])},
            "formula": "operating cashflow + credit drawdown + equity - interest - repayment",
            "output": {
                "ending_cashflow": cashflow[-1]["accumulated_cashflow"] if cashflow else 0,
                "total_equity_required": max((row["cumulative_equity_required"] for row in cashflow), default=0),
            },
        }
    )

    dscr = calculate_dscr(cashflow)
    trace.extend(dscr["trace"])
    economics = _calculate_economics(
        data=data,
        budget=budget,
        credit=credit,
        cashflow=cashflow,
        dscr=dscr,
        price_estimation=price_estimation,
        sale_price_source=sale_price_source,
    )
    trace.append(
        {
            "step": "calculate_economics",
            "inputs": {
                "iteration": iteration,
                "revenue": economics["revenue"],
                "total_budget": budget["total_budget"],
                "interest": credit["total_interest"],
            },
            "formula": "profit_before_interest = revenue - total_budget; profit_after_interest = profit_before_interest - interest",
            "output": economics,
        }
    )
    return {
        "sales_plan": sales_plan,
        "credit": credit,
        "cashflow": cashflow,
        "dscr": dscr,
        "economics": economics,
    }


def _calculate_economics(
    *,
    data: dict[str, Any],
    budget: dict[str, Any],
    credit: dict[str, Any],
    cashflow: list[dict[str, Any]],
    dscr: dict[str, Any],
    price_estimation: dict[str, Any],
    sale_price_source: str,
) -> dict[str, Any]:
    total_area = float(data["total_area"])
    sellable_area = float(data["sellable_area"])
    revenue = sellable_area * float(data["sale_price_per_m2"])
    total_budget = float(budget["total_budget"])
    total_interest = float(credit["total_interest"])
    profit_before_interest = revenue - total_budget
    profit_after_interest = profit_before_interest - total_interest
    margin_before_interest = profit_before_interest / revenue if revenue else 0.0
    margin_after_interest = profit_after_interest / revenue if revenue else 0.0
    total_equity_required = max((float(row["cumulative_equity_required"]) for row in cashflow), default=0)
    return {
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
        **_pricing_metrics(data, price_estimation, sale_price_source),
    }


def _pricing_metrics(
    data: dict[str, Any],
    price_estimation: dict[str, Any],
    sale_price_source: str,
) -> dict[str, Any]:
    return {
        "sale_price_source": sale_price_source,
        "sale_price_per_m2": data["sale_price_per_m2"],
        "estimated_sale_price_per_m2": data.get("estimated_sale_price_per_m2", price_estimation["estimated_sale_price_per_m2"]),
        "market_price_per_m2": price_estimation["market_price_per_m2"],
        "break_even_price_per_m2": price_estimation["break_even_price_per_m2"],
        "target_margin_price_per_m2": data.get("target_margin_price_per_m2", price_estimation["target_margin_price_per_m2"]),
        "recommended_price_per_m2": data.get("recommended_price_per_m2", price_estimation["recommended_price_per_m2"]),
        "price_gap_to_market": data.get("price_gap_to_market", price_estimation["price_gap_to_market"]),
        "preliminary_recommended_price_per_m2": data.get(
            "preliminary_recommended_price_per_m2",
            price_estimation["recommended_price_per_m2"],
        ),
        "final_recommended_price_per_m2": data.get(
            "final_recommended_price_per_m2",
            data.get("recommended_price_per_m2", price_estimation["recommended_price_per_m2"]),
        ),
        "final_target_margin_price_per_m2": data.get(
            "final_target_margin_price_per_m2",
            data.get("target_margin_price_per_m2", price_estimation["target_margin_price_per_m2"]),
        ),
        "price_iteration_count": data.get("price_iteration_count", 0),
        "actual_total_interest_used_for_price": data.get("actual_total_interest_used_for_price", 0),
    }


def _build_summary_metrics(
    budget: dict[str, Any],
    economics: dict[str, Any],
    credit: dict[str, Any],
    detailed_budget: dict[str, Any],
) -> dict[str, Any]:
    chapter_totals = {str(row["Глава"]): float(row["Сумма"]) for row in detailed_budget["chapter_totals"]}
    ending_debt_balance = credit["schedule"][-1]["closing_balance"] if credit.get("schedule") else 0
    total_budget = float(budget.get("total_budget") or 0)
    total_equity_required = float(economics.get("total_equity_required") or 0)
    items_by_code = {str(row["Код"]): row for row in detailed_budget["items"]}
    engineering_systems_amount = sum(float(items_by_code.get(code, {}).get("Сумма") or 0) for code in ("2.11", "2.12", "2.13", "2.14", "2.15"))
    cmr_total = float(budget.get("cmr") or 0)
    return {
        "project_revenue": economics["revenue"],
        "project_cost": budget["total_budget"],
        "cmr_total": budget["cmr"],
        "chapter_1_total": round_money(chapter_totals.get("1", 0)),
        "chapter_2_total": round_money(chapter_totals.get("2", 0)),
        "chapter_3_total": round_money(chapter_totals.get("3", 0)),
        "margin_rub": economics["profit_after_interest"],
        "margin_percent": economics["margin_after_interest"],
        "cost_per_sellable_m2": economics["budget_per_sellable_m2"],
        "average_sale_price_per_m2": economics["sale_price_per_m2"],
        "peak_debt": credit["max_balance"],
        "accrued_interest": credit["total_interest"],
        "minimum_dscr_for_summary": economics["minimum_dscr_after_sales_start"],
        "equity_share": round(total_equity_required / total_budget, 4) if total_budget else 0,
        "ending_debt_balance": ending_debt_balance,
        "pile_foundation_amount": round_money(float(items_by_code.get("2.3", {}).get("Сумма") or 0)),
        "engineering_systems_amount": round_money(engineering_systems_amount),
        "engineering_systems_share_of_cmr": round(engineering_systems_amount / cmr_total, 4) if cmr_total else 0,
        "adjusted_total_budget": budget["total_budget"],
    }
