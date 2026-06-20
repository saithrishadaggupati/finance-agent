# Finance Agent

Most budgeting tools show you charts. This one tells you what to do about them.

The agent takes your transaction data, answers specific questions using a ReAct loop with real tool calls, verifies every number through a second LLM critique pass, generates charts on demand, caches repeated queries in Redis, and remembers your conversation so follow-up questions actually make sense.

I built this because I wanted to see what a finance assistant looks like when you treat accuracy as a hard requirement rather than a nice-to-have. The Critique Agent was the most interesting part — it compares the LLM answer against Pandas ground truth and rewrites anything that does not match.

## Screenshots



![Home](images/finance-agent-home.png)





![Result](images/finance-agent-result.png)



## How it works

1. You paste your transactions in CSV format
2. Ask anything — "where am I overspending?" or "show me a chart of my spending"
3. A ReAct agent calls tools to get exact numbers before answering — it never guesses
4. A Critique Agent (second LLM) compares the answer against Pandas ground truth and corrects any errors
5. If the agent detects a chart request, it calls generate_chart and returns a Plotly visualization
6. Repeated questions are served from Redis cache — sub-millisecond on the second call
7. Every question and answer gets saved to SQLite so the next question has context
8. Every request is traced end-to-end in LangSmith
9. A forecasting module predicts next-month spend per category using scikit-learn LinearRegression, backtested with leave-last-out MAE

The memory piece is what makes this feel like a real assistant rather than a one-shot query tool. Ask "how much did I spend on transport?" then ask "compare that to food" — it knows what "that" means.

## What it catches automatically

- Hallucinated amounts — the Critique Agent cross-checks every number against Pandas
- High spending in a single category
- Large one-off purchases that distort the monthly picture
- Categories creeping up compared to others
- Spend trends that are forecast to worsen next month

## Forecasting

POST /api/v1/finance/forecast takes your transaction history and returns a per-category prediction for next month's spend, trained on monthly aggregates using linear regression.

Each forecast includes a MAE score from a leave-last-out backtest — the model trains on all months except the most recent, predicts that month, and measures the error. This gives an honest signal of how reliable each category's trend line actually is before trusting the next-month number.

Example response:

{"forecasts": [{"category": "Food", "next_month_forecast": 111.67, "mae": 12.50, "months_of_data": 4}, {"category": "Transport", "next_month_forecast": 71.67, "mae": 8.20, "months_of_data": 4}], "total_forecast": 183.34}

## Stack

- FastAPI + Uvicorn — backend API
- Streamlit + Plotly — frontend with agent-generated dynamic charts
- Groq (Llama 3.3 70B) — ReAct agent, insight generation, LLM-as-a-Judge critique
- scikit-learn — LinearRegression forecasting with MAE backtesting per category
- Pandas — transaction parsing, category aggregation, ground truth verification
- Redis — query cache with in-memory fallback when Redis is not running
- SQLite — conversation memory, no external DB needed
- LangSmith — full request tracing and ReAct loop observability
- Plaid API — OAuth link token flow and webhook handler (sandbox-ready)
- Pydantic v2 — request and response validation
- pytest — 7 tests, all external calls mocked
- Docker + docker-compose — containerization with Redis service
- GitHub Actions — CI on every push

## Project structure

app/
  core/
    config.py               # env config, validated at startup
    prompts.py              # all prompts as constants
  memory/
    memory_store.py         # SQLite read/write, formats context for prompts
  models/
    schemas.py              # Transaction, FinanceRequest, FinanceResponse, ForecastResponse
  routers/
    finance.py              # all endpoints including /finance/forecast
  services/
    transaction_service.py  # parsing, formatting, summary stats
    insight_service.py      # proactive insight generation
    agent_service.py        # ReAct loop, tool execution, cache, tracing
    verification_service.py # LLM-as-a-Judge critique agent
    cache_service.py        # Redis + in-memory fallback
    plaid_service.py        # OAuth flow, token exchange, webhook handler
    forecasting_service.py  # LinearRegression forecast + MAE backtest per category
frontend/
  streamlit_app.py          # UI with dynamic charts, cache indicator, badges
evals/
  eval_finance.py           # DeepEval evaluation - accuracy and hallucination detection
tests/
  test_finance.py           # 7 tests, no API key needed

## Run locally

git clone https://github.com/saithrishadaggupati/finance-agent
cd finance-agent
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# add GROQ_API_KEY and optionally PLAID_CLIENT_ID, PLAID_SECRET
uvicorn app.main:app --reload --port 8001
streamlit run frontend/streamlit_app.py

## Run with Docker

docker-compose up --build

## API endpoints

- POST /api/v1/finance — main agent endpoint
- POST /api/v1/finance/forecast — next-month spend forecast per category with MAE backtest
- DELETE /api/v1/finance/memory — clear conversation memory
- GET /api/v1/finance/memory — view recent memory
- DELETE /api/v1/finance/cache — flush cache
- GET /api/v1/finance/cache/status — check Redis connection
- GET /api/v1/plaid/link-token — start Plaid OAuth flow
- POST /api/v1/plaid/exchange-token — exchange public token
- POST /api/v1/plaid/sync — sync transactions
- POST /api/v1/plaid/webhook — handle Plaid webhooks

## Evaluations

python evals/eval_finance.py

Runs 5 queries through the live system and checks numerical accuracy against Pandas ground truth. Results saved to evals/results.json.

## Tests

pytest tests/ -v
# 7 passed - all external calls are mocked