from groq import Groq
from app.models.schemas import Transaction, FinanceResponse
from app.core.config import get_settings
from app.core.prompts import FINANCE_SYSTEM_PROMPT, FINANCE_USER_PROMPT
from app.services.transaction_service import TransactionService
from app.services.insight_service import InsightService
from app.memory.memory_store import MemoryStore


class AgentService:
    def __init__(self):
        self.settings = get_settings()
        self.client = Groq(api_key=self.settings.groq_api_key)
        self.transaction_service = TransactionService()
        self.insight_service = InsightService()
        self.memory_store = MemoryStore()

    def run(
        self,
        question: str,
        transactions: list[Transaction],
        use_memory: bool = True
    ) -> FinanceResponse:

        # Step 1 — Format transactions
        formatted_transactions = self.transaction_service.format_for_prompt(
            transactions
        )

        # Step 2 — Get memory context
        memory_context = ""
        if use_memory:
            memory_context = self.memory_store.format_for_prompt(limit=3)

        # Step 3 — Generate answer
        response = self.client.chat.completions.create(
            model=self.settings.groq_model,
            messages=[
                {
                    "role": "system",
                    "content": FINANCE_SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": FINANCE_USER_PROMPT.format(
                        question=question,
                        transactions=formatted_transactions,
                        memory=memory_context
                    )
                }
            ],
            temperature=0.3
        )

        answer = response.choices[0].message.content

        # Step 4 — Generate insights
        insights = self.insight_service.generate(transactions)

        # Step 5 — Get summary
        summary = self.transaction_service.get_summary(transactions)

        # Step 6 — Save to memory
        if use_memory:
            self.memory_store.save(
                question=question,
                answer=answer,
                context=formatted_transactions[:500]
            )

        return FinanceResponse(
            question=question,
            answer=answer,
            insights=insights,
            total_spent=summary.get("total_spent"),
            top_category=summary.get("top_category"),
            model_used=self.settings.groq_model
        )


def get_agent_service() -> AgentService:
    return AgentService()