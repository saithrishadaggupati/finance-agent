import pytest
from unittest.mock import MagicMock, patch
from app.models.schemas import Transaction, FinanceRequest
from app.services.transaction_service import TransactionService
from app.services.insight_service import InsightService
from app.services.agent_service import AgentService


@pytest.fixture
def sample_transactions():
    return [
        Transaction(date="2024-01-01", description="Swiggy", amount=850, category="Food"),
        Transaction(date="2024-01-02", description="Uber", amount=320, category="Transport"),
        Transaction(date="2024-01-03", description="Netflix", amount=649, category="Entertainment"),
        Transaction(date="2024-01-04", description="Grocery", amount=2100, category="Food"),
    ]


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.groq_api_key = "fake-key"
    settings.groq_model = "llama-3.3-70b-versatile"
    settings.memory_db_path = "data/test_memory.db"
    settings.max_memory_items = 50
    return settings


class TestTransactionService:
    def test_format_for_prompt(self, sample_transactions):
        service = TransactionService()
        result = service.format_for_prompt(sample_transactions)
        assert "Swiggy" in result
        assert "₹850.00" in result
        assert "Food" in result

    def test_get_summary(self, sample_transactions):
        service = TransactionService()
        summary = service.get_summary(sample_transactions)
        assert summary["total_spent"] == 3919.0
        assert summary["top_category"] == "Food"
        assert summary["transaction_count"] == 4

    def test_empty_transactions(self):
        service = TransactionService()
        result = service.format_for_prompt([])
        assert result == "No transactions provided."

    def test_get_summary_empty(self):
        service = TransactionService()
        result = service.get_summary([])
        assert result == {}


class TestInsightService:
    @patch("app.services.insight_service.instructor")
    @patch("app.services.insight_service.Groq")
    @patch("app.services.insight_service.get_settings")
    def test_generate_insights(self, mock_get_settings, mock_groq, mock_instructor, mock_settings, sample_transactions):
        mock_get_settings.return_value = mock_settings
        mock_groq.return_value = MagicMock()
        mock_client = MagicMock()
        mock_instructor.from_groq.return_value = mock_client
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content='[{"title": "High Food Spending", "description": "Food costs ₹2950", "severity": "warning", "amount": 2950.0}]'))]
        )

        service = InsightService()
        insights = service.generate(sample_transactions)

        assert len(insights) == 1
        assert insights[0].title == "High Food Spending"
        assert insights[0].severity == "warning"

    @patch("app.services.insight_service.instructor")
    @patch("app.services.insight_service.Groq")
    @patch("app.services.insight_service.get_settings")
    def test_generate_empty_transactions(self, mock_get_settings, mock_groq, mock_instructor, mock_settings):
        mock_get_settings.return_value = mock_settings
        mock_groq.return_value = MagicMock()
        mock_instructor.from_groq.return_value = MagicMock()

        service = InsightService()
        insights = service.generate([])

        assert insights == []

    @patch("app.services.insight_service.instructor")
@patch("app.services.insight_service.Groq")
@patch("app.services.insight_service.get_settings")
def test_generate_insights(self, mock_get_settings, mock_groq, mock_instructor, mock_settings, sample_transactions):
    mock_get_settings.return_value = mock_settings
    mock_groq.return_value = MagicMock()
    mock_client = MagicMock()
    mock_instructor.from_groq.return_value = mock_client

    from app.services.insight_service import InsightItem, InsightList
    mock_client.chat.completions.create.return_value = InsightList(
        insights=[InsightItem(title="High Food Spending", description="Food costs ₹2950", severity="warning", amount=2950.0)]
    )

    service = InsightService()
    insights = service.generate(sample_transactions)

    assert len(insights) == 1
    assert insights[0].title == "High Food Spending"
    assert insights[0].severity == "warning"