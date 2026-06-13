from app.models.schemas import Transaction
from app.services.transaction_service import TransactionService


class VerificationService:
    def __init__(self):
        self.transaction_service = TransactionService()

    def verify(self, question: str, answer: str, transactions: list[Transaction]) -> dict:
        """
        Cross-checks LLM answer against actual Pandas computed values.
        Returns verified answer + flag if hallucination detected.
        """
        if not transactions:
            return {"verified": True, "warning": None, "corrected_answer": answer}

        summary = self.transaction_service.get_summary(transactions)
        df = self.transaction_service.parse_from_list(transactions)
        question_lower = question.lower()

        # Check 1 — Total spending claim
        if "total" in question_lower or "overall" in question_lower:
            actual_total = summary["total_spent"]
            if str(int(actual_total)) not in answer.replace(",", ""):
                return {
                    "verified": False,
                    "warning": f"The actual total spent is ₹{actual_total:,.2f}",
                    "corrected_answer": answer + f"\n\n⚠️ Verified: Actual total is ₹{actual_total:,.2f}"
                }

        # Check 2 — Category specific claim
        category_breakdown = summary.get("category_breakdown", {})
        for category, actual_amount in category_breakdown.items():
            if category.lower() in question_lower:
                if str(int(actual_amount)) not in answer.replace(",", ""):
                    return {
                        "verified": False,
                        "warning": f"Actual {category} spend is ₹{actual_amount:,.2f}",
                        "corrected_answer": answer + f"\n\n⚠️ Verified: Actual {category} spend is ₹{actual_amount:,.2f}"
                    }

        # Check 3 — Specific merchant claim
        for _, row in df.iterrows():
            desc = row["description"].lower()
            if desc in question_lower:
                actual = row["amount"]
                if str(int(actual)) not in answer.replace(",", ""):
                    return {
                        "verified": False,
                        "warning": f"Actual {row['description']} spend is ₹{actual:,.2f}",
                        "corrected_answer": answer + f"\n\n⚠️ Verified: Actual {row['description']} spend is ₹{actual:,.2f}"
                    }

        return {"verified": True, "warning": None, "corrected_answer": answer}


def get_verification_service() -> VerificationService:
    return VerificationService()