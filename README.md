# Construction Budget Agent v3

Construction Budget Agent v3 generates a developer financial model from core project parameters. It does not read legacy Excel files: the model is built from assumptions, market norms, and the user input.

## What It Generates

- Project assumptions and TEP
- Budget: land, CMR, design, technical customer, general contractor, networks, landscaping, reserve
- CMR split: materials, works, machinery, overheads, reserve
- Construction GPR by S-curve
- Sales plan with slow start, mid-period peak, and final tail
- Credit schedule with drawdown, interest, repayment, closing balance
- Cashflow, DSCR, economics, risks
- Excel workbook with sheets `01_Вводные` through `12_Риски`

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
