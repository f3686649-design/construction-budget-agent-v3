from __future__ import annotations

import pytest

from backend.main import build_financial_model
from backend.models import ProjectInput
from backend.tools.bank_approval import evaluate_bank_approval
from backend.tools.escrow_credit_model import generate_escrow_financing


def _make_gpr(months: int, monthly_cost: float) -> list[dict[str, float]]:
    return [{"month": month, "amount": monthly_cost} for month in range(1, months + 1)]


def _make_sales(start: int, months: int, monthly_revenue: float) -> list[dict[str, float]]:
    return [{"month": start + i, "revenue": monthly_revenue} for i in range(months)]


def _base_case(monthly_revenue: float = 62_500_000.0) -> dict:
    return generate_escrow_financing(
        gpr=_make_gpr(12, 50_000_000),
        sales_plan=_make_sales(3, 12, monthly_revenue),
        total_budget=600_000_000,
        credit_share=0.70,
        base_rate=0.18,
        construction_months=12,
    )


def test_escrow_equity_spent_before_credit() -> None:
    result = _base_case()
    schedule = result["schedule"]
    # Equity 180 млн покрывает первые месяцы: пока equity не исчерпан, выборки кредита нет.
    assert schedule[0]["equity_payment"] == 50_000_000
    assert schedule[0]["drawdown"] == 0
    assert result["equity_pool"] == 180_000_000
    assert result["equity_used"] == pytest.approx(180_000_000, abs=1)
    # После исчерпания equity затраты финансирует кредит.
    assert any(row["drawdown"] > 0 for row in schedule)


def test_escrow_accumulates_until_delivery_and_releases() -> None:
    result = _base_case()
    schedule = result["schedule"]
    delivery = result["delivery_month"]
    pre_delivery = [row for row in schedule if row["month"] < delivery]
    assert all(row["direct_receipts"] == 0 for row in pre_delivery)
    assert all(row["escrow_release"] == 0 for row in pre_delivery)
    delivery_row = next(row for row in schedule if row["month"] == delivery)
    # На вводе эскроу раскрывается полностью.
    assert delivery_row["escrow_release"] > 0
    assert delivery_row["escrow_balance"] == 0
    # Эскроу на вводе = продажи месяцев 3..12 = 10 × 62.5 млн.
    assert result["escrow_at_delivery"] == pytest.approx(625_000_000, abs=1)
    # Продажи после ввода идут напрямую.
    post_delivery = [row for row in schedule if row["month"] > delivery]
    assert all(row["escrow_inflow"] == 0 for row in post_delivery)
    assert sum(row["direct_receipts"] for row in post_delivery) == pytest.approx(125_000_000, abs=1)


def test_escrow_coverage_reduces_interest() -> None:
    covered = _base_case()
    no_sales_during_construction = generate_escrow_financing(
        gpr=_make_gpr(12, 50_000_000),
        sales_plan=_make_sales(13, 12, 62_500_000),
        total_budget=600_000_000,
        credit_share=0.70,
        base_rate=0.18,
        construction_months=12,
    )
    # При наполнении эскроу blended-ставка ниже базовой — процентов меньше.
    assert covered["total_interest"] < no_sales_during_construction["total_interest"]


def test_escrow_debt_repaid_after_delivery() -> None:
    result = _base_case()
    assert result["escrow_coverage_at_delivery"] is not None
    assert result["escrow_coverage_at_delivery"] > 1.0
    assert result["ending_debt"] == pytest.approx(0, abs=1)
    assert result["repayment_finished_month"] is not None
    assert result["funding_gap_total"] == 0
    assert result["llcr"] is not None and result["llcr"] > 1


def test_bank_approval_good_project() -> None:
    escrow = _base_case(monthly_revenue=68_000_000)  # выручка 816 млн, маржа высокая
    bank = evaluate_bank_approval(
        escrow=escrow,
        gpr=_make_gpr(12, 50_000_000),
        sales_plan=_make_sales(3, 12, 68_000_000),
        total_budget=600_000_000,
        credit_share=0.70,
        base_rate=0.18,
        construction_months=12,
    )
    assert bank["verdict_code"] in ("approved", "conditional")
    assert len(bank["criteria"]) == 8
    assert bank["failed_critical_count"] == 0


def test_bank_approval_rejects_thin_margin() -> None:
    # Выручка 615 млн при бюджете 600 млн + проценты — маржа около нуля, стрессы проваливаются.
    escrow = _base_case(monthly_revenue=51_250_000)
    bank = evaluate_bank_approval(
        escrow=escrow,
        gpr=_make_gpr(12, 50_000_000),
        sales_plan=_make_sales(3, 12, 51_250_000),
        total_budget=600_000_000,
        credit_share=0.70,
        base_rate=0.18,
        construction_months=12,
    )
    assert bank["verdict_code"] == "rejected"
    assert "НЕ пройдёт" in bank["verdict"]
    assert bank["failed_critical_count"] >= 1
    assert bank["recommendations"]
    stress = bank["stress_tests"]["price_drop"]
    assert stress["profit"] < 0


def test_bank_approval_flags_low_equity() -> None:
    escrow = generate_escrow_financing(
        gpr=_make_gpr(12, 50_000_000),
        sales_plan=_make_sales(3, 12, 68_000_000),
        total_budget=600_000_000,
        credit_share=0.95,  # equity всего 5%
        base_rate=0.18,
        construction_months=12,
    )
    bank = evaluate_bank_approval(
        escrow=escrow,
        gpr=_make_gpr(12, 50_000_000),
        sales_plan=_make_sales(3, 12, 68_000_000),
        total_budget=600_000_000,
        credit_share=0.95,
        base_rate=0.18,
        construction_months=12,
    )
    equity_criterion = next(c for c in bank["criteria"] if c["code"] == "equity_share")
    assert not equity_criterion["passed"]
    ltc_criterion = next(c for c in bank["criteria"] if c["code"] == "credit_share")
    assert not ltc_criterion["passed"]
    assert bank["verdict_code"] == "rejected"


def test_build_financial_model_includes_bank_blocks() -> None:
    model = build_financial_model(
        ProjectInput(
            project_name="Тест банк",
            city="Якутск",
            object_type="Жилой комплекс",
            object_class="comfort",
            total_area=12_000,
            sellable_area=9_000,
            floors=9,
            land_area=5_000,
            land_cost=30_000_000,
        )
    )
    escrow = model["escrow_financing"]
    bank = model["bank_approval"]
    assert escrow["schedule"]
    assert bank["verdict_code"] in ("approved", "conditional", "rejected")
    assert model["economics"]["llcr"] == escrow["llcr"]
    assert any(step.get("step") == "generate_escrow_financing" for step in model["trace"])
    assert any(step.get("step") == "evaluate_bank_approval" for step in model["trace"])
    assert any(item.get("field") == "escrow_covered_rate" for item in model["assumptions"])
    if bank["verdict_code"] == "rejected":
        assert any(risk.get("code") == "bank_financing_rejected" for risk in model["risks"])
    elif bank["verdict_code"] == "conditional":
        assert any(risk.get("code") == "bank_financing_conditional" for risk in model["risks"])
