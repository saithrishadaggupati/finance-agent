from app.services.forecasting_service import get_forecasting_service
from app.models.schemas import ForecastResponse, CategoryForecast
from fastapi import APIRouter, HTTPException, Request
from app.models.schemas import FinanceRequest, FinanceResponse, ErrorResponse, PlaidWebhookEvent
from app.services.agent_service import get_agent_service
from app.services.cache_service import get_cache_service
from app.services.plaid_service import get_plaid_service

router = APIRouter()


@router.post(
    "/finance",
    response_model=FinanceResponse,
    responses={500: {"model": ErrorResponse}}
)
def finance(request: FinanceRequest):
    try:
        agent = get_agent_service()
        return agent.run(
            question=request.question,
            transactions=request.transactions or [],
            use_memory=request.use_memory
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/finance/memory")
def clear_memory():
    try:
        from app.memory.memory_store import get_memory_store
        store = get_memory_store()
        store.clear()
        return {"status": "memory cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/finance/memory")
def get_memory():
    try:
        from app.memory.memory_store import get_memory_store
        store = get_memory_store()
        items = store.get_recent(limit=10)
        return {"memory": [item.model_dump() for item in items]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/finance/cache")
def clear_cache():
    try:
        cache = get_cache_service()
        cache.flush()
        return {"status": "cache cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/finance/cache/status")
def cache_status():
    cache = get_cache_service()
    return {"redis_connected": cache.is_redis_connected()}


# ── Plaid endpoints ───────────────────────────────────────────────────────────

@router.get("/plaid/link-token")
def create_link_token(user_id: str = "default-user"):
    try:
        plaid = get_plaid_service()
        return plaid.create_link_token(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plaid/exchange-token")
def exchange_token(payload: dict):
    try:
        plaid = get_plaid_service()
        return plaid.exchange_public_token(payload["public_token"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plaid/sync")
def sync_transactions(payload: dict):
    try:
        plaid = get_plaid_service()
        return plaid.sync_transactions(
            access_token=payload["access_token"],
            cursor=payload.get("cursor")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plaid/webhook")
def plaid_webhook(event: PlaidWebhookEvent):
    try:
        plaid = get_plaid_service()
        return plaid.handle_webhook(
            webhook_type=event.webhook_type,
            webhook_code=event.webhook_code,
            item_id=event.item_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/finance/forecast", response_model=ForecastResponse)
def forecast_spending(request: FinanceRequest):
    try:
        if not request.transactions:
            raise HTTPException(status_code=400, detail="Transactions are required for forecasting.")
        service = get_forecasting_service()
        forecasts = service.forecast(request.transactions)
        total = sum(f["next_month_forecast"] for f in forecasts)
        return ForecastResponse(
            forecasts=[CategoryForecast(**f) for f in forecasts],
            total_forecast=round(total, 2)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
