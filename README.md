# Construction Budget Agent v3

Construction Budget Agent v3 generates a developer financial model from core project parameters. It does not read legacy Excel files: the model is built from assumptions, market norms, and the user input.

## What It Generates

- Project assumptions and TEP
- Budget: land, CMR, design, technical customer, general contractor, networks, landscaping, reserve
- Detailed ModDEV-style budget by chapters, articles, materials, works, machinery, and overheads
- Technology-aware budget adjustments for foundation type, underground part, finish level, design cost, and site preparation
- CMR split: materials, works, machinery, overheads, reserve
- Developer-ready construction GPR with stage schedule, monthly CAPEX, cumulative CAPEX, and readiness
- Supply plan for concrete, rebar, facade materials, and engineering equipment
- Sales plan with slow start, mid-period peak, and final tail
- Credit schedule with drawdown, interest, repayment, closing balance
- Cashflow, DSCR, economics, risks
- Scenario analysis, market-price optimization, and an automatic project improvement plan
- Excel workbook with sheets `01_Вводные` through `17_Свод`

## Optimization And Improvement Plan

The agent now checks whether the project passes at the market sale price and then builds a practical improvement plan. It shows the required budget reduction, target CMR per m², required sellable area, value-engineering items, planning improvements, sales actions, financing actions, and 5–7 priority actions for the developer.

## Run API

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8001
```

Endpoints:

- `GET /health`
- `POST /generate-model`
- `GET /download/{filename}`

## Run Streamlit

```powershell
.\.venv\Scripts\streamlit.exe run app.py
```

## Test

```powershell
.\.venv\Scripts\python.exe -m pytest
```
