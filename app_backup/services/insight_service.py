import instructor
from groq import Groq
from pydantic import BaseModel, field_validator
from typing import List
from app.models.schemas import Transaction, Insight
from app.core.config import get_settings
from app.core.prompts import INSIGHT_SYSTEM_PROMPT, INSIGHT_USER_PROMPT
from app.services.transaction_service import TransactionService


class InsightItem(BaseModel):
    title: str
    description: str
    severity: str
    amount: float = 0.0

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v):
        if v not in ["info", "warning", "alert"]:
            return "info"
        return v


class InsightList(BaseModel):
    insights: List[InsightItem]


class InsightService:
    def __init__(self):
        self.settings = get_settings()
        self.client = instructor.from_groq(
            Groq(api_key=self.settings.groq_api_key),
            mode=instructor.Mode.JSON
        )
        self.transaction_service = TransactionService()

    def generate(self, transactions: list[Transaction]) -> list[Insight]:
        if not transactions:
            return []

        formatted = self.transaction_service.format_for_prompt(transactions)

        result = self.client.chat.completions.create(
            model=self.settings.groq_model,
            response_model=InsightList,
            messages=[
                {
                    "role": "system",
                    "content": INSIGHT_SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": INSIGHT_USER_PROMPT.format(
                        transactions=formatted
                    )
                }
            ],
            temperature=0.2
        )

        return [
            Insight(
                title=item.title,
                description=item.description,
                severity=item.severity,
                amount=item.amount
            )
            for item in result.insights
        ]


def get_insight_service() -> InsightService:
    return InsightService()