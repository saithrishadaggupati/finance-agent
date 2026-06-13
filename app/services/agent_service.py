from groq import Groq
from app.models.schemas import Transaction, FinanceResponse
from app.core.config import get_settings
from app.services.transaction_service import TransactionService
from app.services.insight_service import InsightService
from app.services.verification_service import VerificationService
from app.memory.memory_store import MemoryStore


# ── Tools the agent can call ──────────────────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_category_summary",
            "description": "Get total spending per category from transactions",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Category to filter by. Use 'all' for all categories."
                    }
                },
                "required": ["category"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_total_spending",
            "description": "Get total amount spent across all transactions",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_largest_transaction",
            "description": "Find the single largest transaction",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_merchant_spending",
            "description": "Get spending for a specific merchant or description",
            "parameters": {
                "type": "object",
                "properties": {
                    "merchant": {
                        "type": "string",
                        "description": "Merchant name to search for"
                    }
                },
                "required": ["merchant"]
            }
        }
    }
]


class AgentService:
    def __init__(self):
        self.settings = get_settings()
        self.client = Groq(api_key=self.settings.groq_api_key)
        self.transaction_service = TransactionService()
        self.insight_service = InsightService()
        self.verification_service = VerificationService()
        self.memory_store = MemoryStore()

    # ── Tool Execution ────────────────────────────────────────────────────────

    def _execute_tool(self, tool_name: str, args: dict, transactions: list[Transaction]) -> str:
        summary = self.transaction_service.get_summary(transactions)
        df = self.transaction_service.parse_from_list(transactions)

        if tool_name == "get_total_spending":
            total = summary.get("total_spent", 0)
            return f"Total spending: ₹{total:,.2f}"

        if tool_name == "get_category_summary":
            category = args.get("category", "all")
            breakdown = summary.get("category_breakdown", {})
            if category == "all":
                lines = [f"{k}: ₹{v:,.2f}" for k, v in breakdown.items()]
                return "\n".join(lines)
            filtered = {k: v for k, v in breakdown.items() if category.lower() in k.lower()}
            if not filtered:
                return f"No transactions found for category: {category}"
            lines = [f"{k}: ₹{v:,.2f}" for k, v in filtered.items()]
            return "\n".join(lines)

        if tool_name == "find_largest_transaction":
            if df.empty:
                return "No transactions found"
            largest = df.loc[df["amount"].idxmax()]
            return f"Largest transaction: {largest['description']} — ₹{largest['amount']:,.2f} on {largest['date']}"

        if tool_name == "get_merchant_spending":
            merchant = args.get("merchant", "").lower()
            filtered = df[df["description"].str.lower().str.contains(merchant, na=False)]
            if filtered.empty:
                return f"No transactions found for merchant: {merchant}"
            total = filtered["amount"].sum()
            count = len(filtered)
            return f"{merchant.title()}: ₹{total:,.2f} across {count} transaction(s)"

        return "Unknown tool"

    # ── ReAct Loop ────────────────────────────────────────────────────────────

    def _react_loop(self, question: str, transactions: list[Transaction], memory_context: str) -> str:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a personal finance assistant with access to tools that query transaction data. "
                    "Use tools to get exact numbers before answering. Never guess amounts. "
                    "Always use at least one tool before giving a final answer. "
                    f"Previous context: {memory_context}"
                )
            },
            {
                "role": "user",
                "content": question
            }
        ]

        # ReAct loop — max 3 iterations
        for _ in range(3):
            response = self.client.chat.completions.create(
                model=self.settings.groq_model,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                temperature=0.1
            )

            message = response.choices[0].message

            # No tool call — agent has final answer
            if not message.tool_calls:
                return message.content

            # Execute each tool the agent requested
            messages.append({
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in message.tool_calls
                ]
            })

            import json
            for tool_call in message.tool_calls:
                args = json.loads(tool_call.function.arguments)
                result = self._execute_tool(
                    tool_call.function.name,
                    args,
                    transactions
                )
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })

        # Fallback if loop exhausted
        return "I was unable to complete the analysis. Please try rephrasing your question."

    # ── Main Entry Point ──────────────────────────────────────────────────────

    def run(
        self,
        question: str,
        transactions: list[Transaction],
        use_memory: bool = True
    ) -> FinanceResponse:

        # Step 1 — Get memory context
        memory_context = ""
        if use_memory:
            memory_context = self.memory_store.format_for_prompt(limit=3)

        # Step 2 — Run ReAct loop
        answer = self._react_loop(question, transactions, memory_context)

        # Step 3 — Verify answer against actual data
        verification = self.verification_service.verify(question, answer, transactions)
        final_answer = verification["corrected_answer"]

        # Step 4 — Generate insights
        insights = self.insight_service.generate(transactions)

        # Step 5 — Get summary
        summary = self.transaction_service.get_summary(transactions)

        # Step 6 — Save to memory
        if use_memory:
            self.memory_store.save(
                question=question,
                answer=final_answer,
                context=str(summary)
            )

        return FinanceResponse(
            question=question,
            answer=final_answer,
            insights=insights,
            total_spent=summary.get("total_spent"),
            top_category=summary.get("top_category"),
            model_used=self.settings.groq_model
        )


def get_agent_service() -> AgentService:
    return AgentService()