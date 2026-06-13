import pandas as pd
from app.models.schemas import Transaction


class TransactionService:
    MAX_TOKENS_ESTIMATE = 2000  # ~500 transactions max per prompt

    def parse_from_list(self, transactions: list[Transaction]) -> pd.DataFrame:
        data = [t.model_dump() for t in transactions]
        df = pd.DataFrame(data)
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        return df

    def format_for_prompt(self, transactions: list[Transaction]) -> str:
        if not transactions:
            return "No transactions provided."

        # Step 1 — Summarize by category first
        df = self.parse_from_list(transactions)
        category_summary = (
            df.groupby("category")["amount"]
            .agg(["sum", "count"])
            .reset_index()
        )
        category_summary.columns = ["category", "total", "count"]

        summary_lines = ["=== Category Summary ==="]
        for _, row in category_summary.iterrows():
            summary_lines.append(
                f"{row['category']}: ₹{row['total']:.2f} across {int(row['count'])} transactions"
            )

        # Step 2 — Only include individual transactions if under limit
        individual_lines = ["=== Individual Transactions ==="]
        chunk = transactions[:100]  # Hard cap at 100 rows
        for t in chunk:
            individual_lines.append(
                f"{t.date} | {t.description} | ₹{t.amount:.2f} | {t.category}"
            )

        if len(transactions) > 100:
            individual_lines.append(
                f"... and {len(transactions) - 100} more transactions (summarized above)"
            )

        return "\n".join(summary_lines) + "\n\n" + "\n".join(individual_lines)

    def get_relevant_chunk(self, transactions: list[Transaction], question: str) -> list[Transaction]:
        """Return only transactions relevant to the question."""
        question_lower = question.lower()

        # Keywords → categories
        category_keywords = {
            "food": ["Food", "food"],
            "transport": ["Transport", "transport"],
            "entertainment": ["Entertainment", "entertainment"],
            "shopping": ["Shopping", "shopping"],
            "health": ["Health", "health"],
            "utilities": ["Utilities", "utilities"]
        }

        for keyword, categories in category_keywords.items():
            if keyword in question_lower:
                filtered = [t for t in transactions if t.category in categories]
                if filtered:
                    return filtered

        return transactions  # Return all if no match

    def get_summary(self, transactions: list[Transaction]) -> dict:
        if not transactions:
            return {}
        df = self.parse_from_list(transactions)
        total_spent = df["amount"].sum()
        top_category = (
            df.groupby("category")["amount"]
            .sum()
            .idxmax()
        )
        category_breakdown = (
            df.groupby("category")["amount"]
            .sum()
            .to_dict()
        )
        return {
            "total_spent": round(total_spent, 2),
            "top_category": top_category,
            "category_breakdown": category_breakdown,
            "transaction_count": len(transactions)
        }


def get_transaction_service() -> TransactionService:
    return TransactionService()