from fastapi import APIRouter, HTTPException
from app.models.schemas import FinanceRequest, FinanceResponse, ErrorResponse
from app.services.agent_service import get_agent_service

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