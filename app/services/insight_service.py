import json
from groq import Groq
from app.models.schemas import Transaction, Insight
from app.core.config import get_settings
from app.core.prompts import INSIGHT_SYSTEM_PROMPT, INSIGHT_USER_PROMPT
from app.services.transaction_service import TransactionService


class InsightService:
    def __init__(self):
        self.settings = get_settings()
        self.client = Groq(api_key=self.settings.groq_api_key)
        self.transaction_service = TransactionService()

    def generate(self, transactions: list[Transaction]) -> list[Insight]:
        if not transactions:
            return []

        formatted = self.transaction_service.format_for_prompt(transactions)

        response = self.client.chat.completions.create(
            model=self.settings.groq_model,
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

        raw = response.choices[0].message.content
        clean = raw.strip().replace("```json", "").replace("```", "").strip()

        try:
            parsed = json.loads(clean)
            return [
                Insight(
                    title=item.get("title", ""),
                    description=item.get("description", ""),
                    severity=item.get("severity", "info"),
                    amount=item.get("amount")
                )
                for item in parsed
            ]
        except Exception:
            return []


def get_insight_service() -> InsightService:
    return InsightService()