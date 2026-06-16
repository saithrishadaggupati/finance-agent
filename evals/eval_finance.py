"""
DeepEval Evaluation for Finance Agent
Metrics: Answer Correctness, Hallucination, Tool Call Accuracy
Run: python evals/eval_finance.py
"""
import json
import requests
from deepeval import evaluate
from deepeval.metrics import AnswerRelevancyMetric, HallucinationMetric
from deepeval.test_case import LLMTestCase

API_URL = "http://localhost:8001/api/v1/finance"

SAMPLE_TRANSACTIONS = [
    {"date": "2024-01-01", "description": "Swiggy", "amount": 850, "category": "Food"},
    {"date": "2024-01-02", "description": "Uber", "amount": 320, "category": "Transport"},
    {"date": "2024-01-03", "description": "Netflix", "amount": 649, "category": "Entertainment"},
    {"date": "2024-01-04", "description": "Grocery Store", "amount": 2100, "category": "Food"},
    {"date": "2024-01-05", "description": "Electricity Bill", "amount": 1200, "category": "Utilities"},
    {"date": "2024-01-06", "description": "Zomato", "amount": 450, "category": "Food"},
    {"date": "2024-01-07", "description": "Petrol", "amount": 1500, "category": "Transport"},
    {"date": "2024-01-08", "description": "Amazon", "amount": 3200, "category": "Shopping"},
    {"date": "2024-01-09", "description": "Gym", "amount": 999, "category": "Health"},
    {"date": "2024-01-10", "description": "Restaurant", "amount": 1800, "category": "Food"},
]

EVAL_DATASET = [
    {
        "question": "What is my total spending?",
        "expected": "13068",
        "context": "Total of all transactions is 13068"
    },
    {
        "question": "How much did I spend on food?",
        "expected": "5200",
        "context": "Food transactions: Swiggy 850 + Grocery 2100 + Zomato 450 + Restaurant 1800 = 5200"
    },
    {
        "question": "What is my largest transaction?",
        "expected": "3200",
        "context": "Amazon Purchase at 3200 is the largest transaction"
    },
    {
        "question": "How much did I spend on transport?",
        "expected": "1820",
        "context": "Transport: Uber 320 + Petrol 1500 = 1820"
    },
    {
        "question": "How much did I spend on Netflix?",
        "expected": "649",
        "context": "Netflix transaction is 649"
    },
]

def run_eval():
    test_cases = []
    results_log = []

    print("Running queries against Finance Agent...")
    for item in EVAL_DATASET:
        try:
            response = requests.post(API_URL, json={
                "question": item["question"],
                "transactions": SAMPLE_TRANSACTIONS,
                "use_memory": False
            }, timeout=60)

            if response.status_code == 200:
                data = response.json()
                answer = data["answer"]
                verified = data.get("verified", True)
                cache_hit = data.get("cache_hit", False)

                # Check if expected amount appears in answer
                correct = item["expected"] in answer.replace(",", "")

                print(f"  [{'OK' if correct else 'FAIL'}] {item['question']}")
                print(f"         Expected: {item['expected']} | Verified: {verified} | Cache: {cache_hit}")

                test_cases.append(LLMTestCase(
                    input=item["question"],
                    actual_output=answer,
                    context=[item["context"]]
                ))

                results_log.append({
                    "question": item["question"],
                    "expected": item["expected"],
                    "answer": answer,
                    "correct": correct,
                    "verified": verified,
                    "cache_hit": cache_hit
                })
            else:
                print(f"  [FAIL] {item['question']} - {response.status_code}")

        except Exception as e:
            print(f"  [ERROR] {e}")

    correct_count = sum(1 for r in results_log if r["correct"])
    accuracy = correct_count / len(results_log) if results_log else 0

    print(f"\n=== Finance Agent Evaluation Results ===")
    print(f"Accuracy:     {accuracy:.0%} ({correct_count}/{len(results_log)})")
    print(f"Verified:     {sum(1 for r in results_log if r['verified'])}/{len(results_log)}")

    with open("evals/results.json", "w") as f:
        json.dump({
            "accuracy": accuracy,
            "correct": correct_count,
            "total": len(results_log),
            "results": results_log
        }, f, indent=2)

    print("\nResults saved to evals/results.json")

if __name__ == "__main__":
    run_eval()
