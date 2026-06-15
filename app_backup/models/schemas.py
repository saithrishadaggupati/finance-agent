from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


class Transaction(BaseModel):
    date: str
    description: str
    amount: float
    category: Optional[str] = "Uncategorized"


class FinanceRequest(BaseModel):
    question: str
    transactions: Optional[List[Transaction]] = None
    use_memory: bool = True


class Insight(BaseModel):
    title: str
    description: str
    severity: str  # "info", "warning", "alert"
    amount: Optional[float] = None


class FinanceResponse(BaseModel):
    question: str
    answer: str
    insights: List[Insight]
    total_spent: Optional[float] = None
    top_category: Optional[str] = None
    model_used: str
    verified: bool = True
    verification_warning: Optional[str] = None
    cache_hit: bool = False
    chart_json: Optional[Any] = None


class MemoryItem(BaseModel):
    id: Optional[int] = None
    question: str
    answer: str
    timestamp: str
    context: Optional[str] = None


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None


class PlaidWebhookEvent(BaseModel):
    webhook_type: str
    webhook_code: str
    item_id: str
