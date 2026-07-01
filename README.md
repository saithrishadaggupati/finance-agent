# Finance Agent

Most budgeting apps show charts. This one tells you what to do about them.

Finance Agent is an AI-powered personal finance assistant that answers questions about your spending using verified transaction data instead of relying on model-generated estimates. It combines a ReAct agent, tool calling, numerical verification, forecasting, caching, and conversation memory to deliver accurate, context-aware financial insights.

I built this project to explore what an AI finance assistant looks like when accuracy is treated as a requirement rather than an afterthought. The most interesting part was designing a verification pipeline where every numerical answer is checked against Pandas before it reaches the user.

## Screenshots

![Home](images/finance-agent-home.png)

![Result](images/finance-agent-result.png)

## How it works

1. Upload your transactions as CSV or sync them through Plaid.
2. Ask questions like "Where am I overspending?" or "Show my monthly spending trend."
3. A ReAct agent selects the required tools and computes exact values instead of estimating them.
4. A verification agent compares every numerical response against Pandas calculations and rewrites the answer whenever discrepancies are detected.
5. When a visualization is requested, the agent generates an interactive Plotly chart.
6. Repeated questions are served from Redis cache to reduce response latency.
7. Every interaction is stored using SQLAlchemy and SQLite, enabling context-aware follow-up conversations.
8. Each request is traced end-to-end using LangSmith for debugging and observability.
9. A forecasting module predicts next month's spending per category using Linear Regression with MAE backtesting.

The conversation memory makes the assistant feel natural. Ask "How much did I spend on transport?" and then "Compare that with food." The assistant understands what "that" refers to without asking you to repeat yourself.

## What it catches automatically

- Hallucinated numerical values through Pandas verification
- Categories with unusually high spending
- Large one-time purchases that skew monthly trends
- Spending categories that are steadily increasing
- Spending trends that are likely to continue next month

## Forecasting

POST /api/v1/finance/forecast predicts next month's spending for each category using monthly historical data and scikit-learn LinearRegression.

Each forecast includes a Mean Absolute Error (MAE) calculated using a leave-last-out backtest. The model trains on historical months, predicts the most recent month, and measures the prediction error before forecasting the next month. This provides a simple reliability signal for every category.

Forecasts are intended to identify spending trends rather than provide precise financial predictions.

Example response:

    {
      "forecasts": [
        {
          "category": "Food",
          "next_month_forecast": 111.67,
          "mae": 12.50,
          "months_of_data": 4
        },
        {
          "category": "Transport",
          "next_month_forecast": 71.67,
          "mae": 8.20,
          "months_of_data": 4
        }
      ],
      "total_forecast": 183.34
    }

## Technical decisions worth explaining

**Why SQLAlchemy instead of raw sqlite3?**

The first version of the project stored conversation history using raw SQLite queries. While it worked, maintaining schema changes became increasingly difficult as the project grew.

I migrated the memory layer to SQLAlchemy to introduce a type-safe ORM, reduce handwritten SQL, and simplify future schema evolution. The migration replaced only the data-access layer while keeping the existing SQLite database and application interfaces unchanged, so no downstream services required modification.

## Stack

- Python — Core programming language
- FastAPI + Uvicorn — REST API backend
- Groq (Llama 3.3 70B) — ReAct agent and verification agent
- Pandas — Transaction processing and numerical ground truth
- scikit-learn — Spending forecasts using Linear Regression
- Redis — Query caching with in-memory fallback
- SQLite + SQLAlchemy ORM — Conversation memory
- Streamlit + Plotly — Interactive frontend and dynamic visualizations
- LangSmith — Agent tracing and observability
- Plaid API — Bank transaction integration (sandbox-ready)
- Pydantic v2 — Request and response validation
- pytest — Unit testing
- Docker + Docker Compose — Containerized deployment
- GitHub Actions — Continuous Integration

## Project structure

    app/
      core/
        config.py               # Environment configuration
        prompts.py               # Centralized prompt templates

      memory/
        memory_store.py         # SQLAlchemy conversation memory

      models/
        schemas.py               # Request and response models

      routers/
        finance.py               # Finance API endpoints

      services/
        transaction_service.py  # Transaction parsing and summaries
        insight_service.py      # Spending insights
        agent_service.py        # ReAct loop and tool execution
        verification_service.py # Numerical verification pipeline
        forecasting_service.py  # Spending forecasts
        cache_service.py        # Redis cache
        plaid_service.py        # Plaid integration

    frontend/
      streamlit_app.py           # User interface

    evals/
      eval_finance.py            # Evaluation pipeline

    tests/
      test_finance.py            # Unit tests

## Run locally

    git clone https://github.com/saithrishadaggupati/finance-agent

    cd finance-agent

    python -m venv .venv

    # Windows
    .venv\Scripts\activate

    # macOS/Linux
    source .venv/bin/activate

    pip install -r requirements.txt

    cp .env.example .env

    # Add GROQ_API_KEY
    # Optional:
    # PLAID_CLIENT_ID
    # PLAID_SECRET

    uvicorn app.main:app --reload --port 8001

    streamlit run frontend/streamlit_app.py

## Run with Docker

    docker compose up --build

## API endpoints

- POST /api/v1/finance — Main finance assistant
- POST /api/v1/finance/forecast — Forecast next month's spending
- GET /api/v1/finance/memory — View conversation history
- DELETE /api/v1/finance/memory — Clear conversation history
- GET /api/v1/finance/cache/status — Check Redis status
- DELETE /api/v1/finance/cache — Clear cached responses
- GET /api/v1/plaid/link-token — Start Plaid OAuth flow
- POST /api/v1/plaid/exchange-token — Exchange public token
- POST /api/v1/plaid/sync — Sync transactions
- POST /api/v1/plaid/webhook — Handle Plaid webhooks

## Evaluations

    python evals/eval_finance.py

Runs evaluation queries against the live agent and compares every numerical answer with Pandas ground truth to measure accuracy and detect hallucinations.

Results are saved to:

    evals/results.json

## Tests

    pytest tests/ -v

Includes 7 unit tests covering agent execution, verification, forecasting, caching, and API behavior. External services are mocked, allowing the test suite to run without API keys or third-party dependencies.