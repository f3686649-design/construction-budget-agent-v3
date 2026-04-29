from __future__ import annotations

from backend.tools.norms import CMR_SPLIT, round_money


def split_cmr(cmr_amount: float) -> dict[str, object]:
    materials = cmr_amount * CMR_SPLIT["materials"]
    works = cmr_amount * CMR_SPLIT["works"]
    machinery = cmr_amount * CMR_SPLIT["machinery"]
    overheads = cmr_amount * CMR_SPLIT["overheads"]
    reserve = cmr_amount - materials - works - machinery - overheads
    items = [
        {"name": "Материалы", "share": CMR_SPLIT["materials"], "amount": round_money(materials)},
        {"name": "Работы", "share": CMR_SPLIT["works"], "amount": round_money(works)},
        {"name": "Механизмы", "share": CMR_SPLIT["machinery"], "amount": round_money(machinery)},
        {"name": "Накладные", "share": CMR_SPLIT["overheads"], "amount": round_money(overheads)},
        {"name": "Резерв", "share": CMR_SPLIT["reserve"], "amount": round_money(reserve)},
    ]
    return {
        "items": items,
        "total": round_money(sum(item["amount"] for item in items)),
        "trace": [
            {
                "step": "split_cmr",
                "inputs": {"cmr_amount": cmr_amount, "shares": CMR_SPLIT},
                "formula": "CMR * share by category",
                "output": {"items": items},
            }
        ],
    }
