import json
from langsmith import traceable
from groq import Groq
from app.models.schemas import Transaction, FinanceResponse
from app.core.config import get_settings
from app.services.transaction_service import TransactionService
from app.services.insight_service import InsightService
from app.services.verification_service import VerificationService
from app.services.cache_service import get_cache_service
from app.memory.memory_store import MemoryStore


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
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_largest_transaction",
            "description": "Find the single largest transaction",
            "parameters": {"type": "object", "properties": {}, "required": []}
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
    },
    {
        "type": "function",
        "function": {
            "name": "generate_chart",
            "description": "Generate a Plotly chart for spending visualization. Call this when the user asks for a chart, graph, breakdown, or visual comparison.",
            "parameters": {
                "type": "object",
                "properties": {
                    "chart_type": {
                        "type": "string",
                        "enum": ["pie", "bar", "line", "treemap"],
                        "description": "Type of chart to generate"
                    },
                    "group_by": {
                        "type": "string",
                        "enum": ["category", "description", "date"],
                        "description": "How to group the data"
                    },
                    "title": {
                        "type": "string",
                        "description": "Chart title"
                    }
                },
                "required": ["chart_type", "group_by", "title"]
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
        self.cache = get_cache_service()
        self._chart_json = None

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
            return "\n".join([f"{k}: ₹{v:,.2f}" for k, v in filtered.items()])

        if tool_name == "find_largest_transaction":
            if df.empty:
                return "No transactions found"
            largest = df.loc[df["amount"].idxmax()]
            return f"Largest: {largest['description']} — ₹{largest['amount']:,.2f} on {largest['date']}"

        if tool_name == "get_merchant_spending":
            merchant = args.get("merchant", "").lower()
            filtered = df[df["description"].str.lower().str.contains(merchant, na=False)]
            if filtered.empty:
                return f"No transactions found for: {merchant}"
            total = filtered["amount"].sum()
            count = len(filtered)
            return f"{merchant.title()}: ₹{total:,.2f} across {count} transaction(s)"

        if tool_name == "generate_chart":
            return self._build_chart(
                args.get("chart_type", "bar"),
                args.get("group_by", "category"),
                args.get("title", "Spending Chart"),
                df
            )

        return "Unknown tool"

    def _build_chart(self, chart_type: str, group_by: str, title: str, df) -> str:
        """Build Plotly chart JSON and stash it for the response."""
        try:
            import plotly.express as px
            import plotly.graph_objects as go

            if group_by == "date":
                df["date_str"] = df["date"].dt.strftime("%Y-%m-%d")
                grouped = df.groupby("date_str")["amount"].sum().reset_index()
                grouped.columns = [group_by, "amount"]
            else:
                grouped = df.groupby(group_by)["amount"].sum().reset_index()
                grouped.columns = [group_by, "amount"]

            colors = ["#00C9A7", "#FFB347", "#FF6B6B", "#6C63FF", "#00A8E8", "#FF9A8B"]

            if chart_type == "pie":
                fig = px.pie(grouped, names=group_by, values="amount", title=title,
                             hole=0.45, color_discrete_sequence=colors)
                fig.update_traces(textposition="inside", textinfo="percent+label")
            elif chart_type == "treemap":
                fig = px.treemap(grouped, path=[group_by], values="amount", title=title,
                                 color_discrete_sequence=colors)
            elif chart_type == "line":
                fig = px.line(grouped, x=group_by, y="amount", title=title,
                              markers=True, color_discrete_sequence=["#00C9A7"])
            else:  # bar
                grouped_sorted = grouped.sort_values("amount", ascending=True)
                fig = go.Figure(go.Bar(
                    x=grouped_sorted["amount"],
                    y=grouped_sorted[group_by],
                    orientation="h",
                    marker=dict(color=grouped_sorted["amount"],
                                colorscale=[[0, "#00C9A7"], [1, "#6C63FF"]])
                ))
                fig.update_layout(title=title)

            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=40, b=20, l=20, r=20),
                font=dict(color="#1A1A2E")
            )

            self._chart_json = fig.to_json()
            return f"Chart generated: {chart_type} chart grouped by {group_by} with {len(grouped)} data points."

        except Exception as e:
            return f"Chart generation failed: {e}"

    @traceable(name="react_loop")
    def _react_loop(self, question: str, transactions: list[Transaction], memory_context: str) -> str:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a personal finance assistant with access to tools that query transaction data. "
                    "Use tools to get exact numbers before answering. Never guess amounts. "
                    "Always use at least one tool before giving a final answer. "
                    "If the user asks for a chart, graph, or visual, call generate_chart. "
                    f"Previous context: {memory_context}"
                )
            },
            {"role": "user", "content": question}
        ]

        for _ in range(4):
            response = self.client.chat.completions.create(
                model=self.settings.groq_model,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                temperature=0.1
            )

            message = response.choices[0].message

            if not message.tool_calls:
                return message.content

            messages.append({
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                    }
                    for tc in message.tool_calls
                ]
            })

            for tool_call in message.tool_calls:
                args = json.loads(tool_call.function.arguments)
                result = self._execute_tool(tool_call.function.name, args, transactions)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })

        return "I was unable to complete the analysis. Please try rephrasing your question."

    @traceable(name="finance_agent_run")
    def run(self, question: str, transactions: list[Transaction], use_memory: bool = True) -> FinanceResponse:
        self._chart_json = None

        # Step 1 — Check cache
        txn_dicts = [t.model_dump() for t in transactions]
        cached = self.cache.get(question, txn_dicts)
        if cached:
            cached["cache_hit"] = True
            return FinanceResponse(**cached)

        # Step 2 — Memory context
        memory_context = self.memory_store.format_for_prompt(limit=3) if use_memory else ""

        # Step 3 — ReAct loop
        answer = self._react_loop(question, transactions, memory_context)

        # Step 4 — LLM-as-a-Judge verification
        verification = self.verification_service.verify(question, answer, transactions)
        final_answer = verification["corrected_answer"]

        # Step 5 — Insights
        insights = self.insight_service.generate(transactions)

        # Step 6 — Summary
        summary = self.transaction_service.get_summary(transactions)

        # Step 7 — Save memory
        if use_memory:
            self.memory_store.save(question=question, answer=final_answer, context=str(summary))

        result = FinanceResponse(
            question=question,
            answer=final_answer,
            insights=insights,
            total_spent=summary.get("total_spent"),
            top_category=summary.get("top_category"),
            model_used=self.settings.groq_model,
            verified=verification["verified"],
            verification_warning=verification.get("warning"),
            cache_hit=False,
            chart_json=self._chart_json
        )

        # Step 8 — Cache result
        self.cache.set(question, txn_dicts, result.model_dump())

        return result


def get_agent_service() -> AgentService:
    return AgentService()
