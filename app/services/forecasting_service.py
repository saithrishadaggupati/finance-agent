from collections import defaultdict
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error
import numpy as np
from app.models.schemas import Transaction


class ForecastResult:
    def __init__(self, category: str, next_month_forecast: float, mae: float, months_of_data: int):
        self.category = category
        self.next_month_forecast = round(next_month_forecast, 2)
        self.mae = round(mae, 2)
        self.months_of_data = months_of_data


class ForecastingService:
    def forecast(self, transactions: list[Transaction]) -> list[dict]:
        if not transactions:
            return []

        # Group total spend by (category, year-month)
        monthly: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        for txn in transactions:
            try:
                ym = txn.date[:7]  # "YYYY-MM"
            except Exception:
                continue
            category = txn.category or "Uncategorized"
            monthly[category][ym] += abs(txn.amount)

        results = []

        for category, month_data in monthly.items():
            sorted_months = sorted(month_data.keys())

            # Need at least 3 months to train + backtest meaningfully
            if len(sorted_months) < 3:
                continue

            X = np.array(range(len(sorted_months))).reshape(-1, 1)
            y = np.array([month_data[m] for m in sorted_months])

            # Backtest: train on all but last month, predict last month
            X_train, X_test = X[:-1], X[-1].reshape(1, -1)
            y_train, y_test = y[:-1], y[-1]

            model = LinearRegression()
            model.fit(X_train, y_train)

            y_pred_backtest = model.predict(X_test)[0]
            mae = mean_absolute_error([y_test], [y_pred_backtest])

            # Retrain on all data, forecast next month
            model.fit(X, y)
            next_index = np.array([[len(sorted_months)]])
            next_month_forecast = max(0.0, model.predict(next_index)[0])

            results.append({
                "category": category,
                "next_month_forecast": round(float(next_month_forecast), 2),
                "mae": round(float(mae), 2),
                "months_of_data": len(sorted_months)
            })

        # Sort by forecast amount descending
        results.sort(key=lambda x: x["next_month_forecast"], reverse=True)
        return results


def get_forecasting_service() -> ForecastingService:
    return ForecastingService()