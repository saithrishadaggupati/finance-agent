import pandas as pd
from app.models.schemas import Transaction


class TransactionService:
    def parse_from_list(self, transactions: list[Transaction]) -> pd.DataFrame:
        data = [t.model_dump() for t in transactions]
        df = pd.DataFrame(data)
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        return df

    def format_for_prompt(self, transactions: list[Transaction]) -> str:
        if not transactions:
            return "No transactions provided."
        lines = []
        for t in transactions:
            lines.append(
                f"{t.date} | {t.description} | ₹{t.amount:.2f} | {t.category}"
            )
        return "\n".join(lines)

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