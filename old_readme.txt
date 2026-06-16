@'
# Finance Agent

I built this because most budgeting tools just show you charts. They don't tell you what to do about them.

This agent analyzes your transactions, answers specific questions about your spending, verifies its own answers using a second LLM critique pass, generates dynamic charts on demand, and remembers what you've already asked ΓÇö so you don't have to repeat yourself every time.

## Screenshots



![Home](images/finance-agent-home.png)




![Result](images/finance-agent-result.png)



## How it works

1. You paste your transactions in CSV format
2. Ask anything ΓÇö "where am I overspending?" or "show me a chart of my spending"
3. A ReAct agent calls tools to get exact numbers before answering ΓÇö it never guesses
4. A second LLM (Critique Agent) compares the answer against Pandas ground truth and corrects any errors
5. If the agent detects a chart request, it calls generate_chart and returns a Plotly visualization
6. Repeated questions are served from Redis cache ΓÇö sub-millisecond on the second call
7. Every question and answer gets saved to SQLite so the next question has context

The memory piece is what makes this feel like a real assistant rather than a one-shot query tool. Ask "how much did I spend on transport?" then ask "compare that to food" ΓÇö it knows what "that" means.

## What it catches automatically

- Hallucinated amounts ΓÇö the Critique Agent cross-checks every number against Pandas
- High spending in a single category
- Large one-off purchases that distort the monthly picture
- Categories creeping up compared to others

## Stack

- FastAPI + Uvicorn ΓÇö backend API
- Streamlit + Plotly ΓÇö frontend with agent-generated dynamic charts
- Groq (Llama 3.3 70B) ΓÇö ReAct agent, insight generation, LLM-as-a-Judge critique
- Pandas ΓÇö transaction parsing, category aggregation, ground truth verification
- Redis ΓÇö query cache with in-memory fallback when Redis isn't running
- SQLite ΓÇö conversation memory, no external DB needed
- LangSmith ΓÇö full request tracing and ReAct loop observability
- Plaid API ΓÇö OAuth link token flow and webhook handler (sandbox-ready)
- Pydantic v2 ΓÇö request and response validation
- pytest ΓÇö 7 tests, all external calls mocked

## Project structure

app/
  core/
    config.py              # env config, validated at startup
    prompts.py             # all prompts as constants
  memory/
    memory_store.py        # SQLite read/write, formats context for prompts
  models/
    schemas.py             # Transaction, FinanceRequest, FinanceResponse
  routers/
    finance.py             # POST /finance, cache/memory/plaid endpoints
  services/
    transaction_service.py # parsing, formatting, summary stats
    insight_service.py     # proactive insight generation
    agent_service.py       # ReAct loop, tool execution, cache, tracing
    verification_service.py # LLM-as-a-Judge critique agent
    cache_service.py       # Redis + in-memory fallback
    plaid_service.py       # OAuth flow, token exchange, webhook handler
frontend/
  streamlit_app.py         # UI with dynamic charts, cache indicator, badges
tests/
  test_finance.py          # 7 tests, no API key needed

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

## API endpoints

- POST /api/v1/finance ΓÇö main agent endpoint
- DELETE /api/v1/finance/memory ΓÇö clear conversation memory
- GET /api/v1/finance/memory ΓÇö view recent memory
- DELETE /api/v1/finance/cache ΓÇö flush cache
- GET /api/v1/finance/cache/status ΓÇö check Redis connection
- GET /api/v1/plaid/link-token ΓÇö start Plaid OAuth flow
- POST /api/v1/plaid/exchange-token ΓÇö exchange public token
- POST /api/v1/plaid/sync ΓÇö sync transactions
- POST /api/v1/plaid/webhook ΓÇö handle Plaid webhooks

## Tests

pytest tests/ -v
# 7 passed ΓÇö all external calls are mocked
'@ | Set-Content "C:\Users\ASUS\finance_agent\README.md" -Encoding UTF8; git add .; git commit -m "docs: update README to reflect all upgrades"; git push
