# Finance Agent

I built this because most budgeting tools just show you charts. They don't tell you what to do about them.

This agent analyzes your transactions, answers specific questions about your spending, flags things that need attention, and remembers what you've already asked — so you don't have to repeat yourself every time.

## How it works

1. You paste your transactions in CSV format
2. Ask anything — "where am I overspending?" or "compare food vs transport"
3. The agent answers using only your actual transaction data
4. A separate step generates 3 proactive insights you didn't ask for but probably need
5. Every question and answer gets saved to SQLite so the next question has context

The memory piece is what makes this feel like a real assistant rather than a one-shot query tool. Ask "how much did I spend on transport?" then ask "compare that to food" — it knows what "that" means.

## What it catches automatically

- High spending in a single category
- Large one-off purchases that distort the monthly picture
- Categories that are creeping up compared to others

## Stack

- FastAPI + Uvicorn — backend
- Streamlit + Plotly — frontend with spending pie chart
- Groq (Llama 3.3 70B) — answer generation and insight scoring
- Pandas — transaction parsing and category aggregation
- SQLite — conversation memory, no external DB needed
- Pydantic v2 — request and response validation
- pytest — 7 tests, all external calls mocked

## Project structure

```
app/
  core/
    config.py              # env config, validated at startup
    prompts.py             # all prompts as constants
  memory/
    memory_store.py        # SQLite read/write, formats context for prompts
  models/
    schemas.py             # Transaction, FinanceRequest, FinanceResponse
  routers/
    finance.py             # POST /finance, DELETE /finance/memory
  services/
    transaction_service.py # parsing, formatting, summary stats
    insight_service.py     # proactive insight generation
    agent_service.py       # orchestrates all services end to end
frontend/
  streamlit_app.py         # UI with chart and memory toggle
tests/
  test_finance.py          # 7 tests, no API key needed
```

## Run locally

```bash
git clone https://github.com/saithrishadaggupati/finance-agent
cd finance-agent

python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# add your GROQ_API_KEY

uvicorn app.main:app --reload --port 8000
streamlit run frontend/streamlit_app.py
```

## Tests

```bash
pytest tests/ -v
# 7 passed — all external calls are mocked
```

## What I'd add next

- CSV file upload instead of pasting raw text
- Month-over-month comparison across multiple CSV files
- Budget limits per category with alerts when exceeded
- Export insights as a PDF report
- Plaid API integration for real bank data