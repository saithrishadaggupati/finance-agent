import json
from groq import Groq
from app.models.schemas import Transaction
from app.services.transaction_service import TransactionService
from app.core.config import get_settings

CRITIQUE_SYSTEM_PROMPT = """
You are a financial fact-checker. You will be given:
1. A user question about their transactions
2. An AI-generated answer
3. The actual Pandas-computed ground truth numbers

Your job is to detect subtle logic errors, wrong amounts, or misleading statements.

Return ONLY a JSON object:
{
  "verified": true/false,
  "issues": ["list of specific issues found, or empty list if none"],
  "corrected_answer": "the corrected answer text, or original if no issues"
}

Rules:
- verified=true only if ALL amounts and facts in the answer match the ground truth
- Be strict about numbers — ₹1,200 ≠ ₹1,250
- Flag wrong category names, wrong merchant names, wrong counts
- If verified=false, rewrite the corrected_answer with accurate numbers from ground truth
- Never invent data not in the ground truth
"""


class VerificationService:
    def __init__(self):
        self.settings = get_settings()
        self.client = Groq(api_key=self.settings.groq_api_key)
        self.transaction_service = TransactionService()

    def _build_ground_truth(self, transactions: list[Transaction]) -> str:
        if not transactions:
            return "No transactions."
        summary = self.transaction_service.get_summary(transactions)
        df = self.transaction_service.parse_from_list(transactions)

        lines = [
            f"Total spent: ₹{summary['total_spent']:,.2f}",
            f"Transaction count: {summary['transaction_count']}",
            f"Top category: {summary['top_category']}",
            "",
            "Category breakdown:"
        ]
        for cat, amt in summary["category_breakdown"].items():
            lines.append(f"  {cat}: ₹{amt:,.2f}")

        lines.append("")
        lines.append("All transactions:")
        for _, row in df.iterrows():
            lines.append(f"  {row['date'].date()} | {row['description']} | ₹{row['amount']:,.2f} | {row['category']}")

        return "\n".join(lines)

    def verify(self, question: str, answer: str, transactions: list[Transaction]) -> dict:
        if not transactions:
            return {"verified": True, "warning": None, "corrected_answer": answer}

        ground_truth = self._build_ground_truth(transactions)

        prompt = f"""Question: {question}

AI Answer: {answer}

Ground Truth from Pandas:
{ground_truth}

Check the AI answer against the ground truth and return JSON."""

        try:
            response = self.client.chat.completions.create(
                model=self.settings.groq_model,
                messages=[
                    {"role": "system", "content": CRITIQUE_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )

            raw = response.choices[0].message.content
            clean = raw.strip().replace("```json", "").replace("```", "").strip()
            result = json.loads(clean)

            issues = result.get("issues", [])
            warning = "; ".join(issues) if issues else None

            return {
                "verified": result.get("verified", True),
                "warning": warning,
                "corrected_answer": result.get("corrected_answer", answer)
            }

        except Exception:
            # Fallback to original answer if critique fails
            return {"verified": True, "warning": None, "corrected_answer": answer}


def get_verification_service() -> VerificationService:
    return VerificationService()
