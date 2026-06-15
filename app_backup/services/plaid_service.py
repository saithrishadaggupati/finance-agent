"""
Plaid API Integration
---------------------
Handles OAuth link token creation, public token exchange, and transaction sync.
Requires PLAID_CLIENT_ID, PLAID_SECRET, PLAID_ENV in .env

To use with real Plaid:
  1. Sign up at https://dashboard.plaid.com
  2. Set PLAID_ENV=sandbox for testing (free)
  3. Add credentials to .env
"""
import os
from typing import Optional
from app.core.config import get_settings

try:
    import plaid
    from plaid.api import plaid_api
    from plaid.model.link_token_create_request import LinkTokenCreateRequest
    from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
    from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
    from plaid.model.transactions_sync_request import TransactionsSyncRequest
    from plaid.model.products import Products
    from plaid.model.country_code import CountryCode
    PLAID_AVAILABLE = True
except ImportError:
    PLAID_AVAILABLE = False

    
class PlaidService:
    def __init__(self):
        self.settings = get_settings()
        self.client = None
        self.enabled = False

        if not PLAID_AVAILABLE:
            return

        client_id = os.getenv("PLAID_CLIENT_ID", "")
        secret = os.getenv("PLAID_SECRET", "")
        env = os.getenv("PLAID_ENV", "sandbox")

        if not client_id or not secret:
            return

        env_map = {
            "sandbox": plaid.Environment.Sandbox,
            "development": plaid.Environment.Development,
            "production": plaid.Environment.Production,
        }

        configuration = plaid.Configuration(
            host=env_map.get(env, plaid.Environment.Sandbox),
            api_key={"clientId": client_id, "secret": secret}
        )
        api_client = plaid.ApiClient(configuration)
        self.client = plaid_api.PlaidApi(api_client)
        self.enabled = True

    def create_link_token(self, user_id: str = "default-user") -> dict:
        """Step 1: Create a link token to initialize Plaid Link UI."""
        if not self.enabled:
            return {"error": "Plaid not configured. Add PLAID_CLIENT_ID and PLAID_SECRET to .env"}

        request = LinkTokenCreateRequest(
            products=[Products("transactions")],
            client_name="Finance Agent",
            country_codes=[CountryCode("US")],
            language="en",
            user=LinkTokenCreateRequestUser(client_user_id=user_id)
        )
        response = self.client.link_token_create(request)
        return {"link_token": response["link_token"]}

    def exchange_public_token(self, public_token: str) -> dict:
        """Step 2: Exchange public token for permanent access token."""
        if not self.enabled:
            return {"error": "Plaid not configured"}

        request = ItemPublicTokenExchangeRequest(public_token=public_token)
        response = self.client.item_public_token_exchange(request)
        return {
            "access_token": response["access_token"],
            "item_id": response["item_id"]
        }

    def sync_transactions(self, access_token: str, cursor: Optional[str] = None) -> dict:
        """Step 3: Sync new/modified/removed transactions using cursor pagination."""
        if not self.enabled:
            return {"error": "Plaid not configured", "transactions": [], "cursor": None}

        request = TransactionsSyncRequest(
            access_token=access_token,
            cursor=cursor or ""
        )
        response = self.client.transactions_sync(request)

        transactions = []
        for txn in response["added"]:
            transactions.append({
                "date": str(txn["date"]),
                "description": txn.get("merchant_name") or txn["name"],
                "amount": abs(float(txn["amount"])),
                "category": txn["personal_finance_category"]["primary"]
                    if txn.get("personal_finance_category") else "Uncategorized"
            })

        return {
            "transactions": transactions,
            "cursor": response["next_cursor"],
            "has_more": response["has_more"]
        }

    def handle_webhook(self, webhook_type: str, webhook_code: str, item_id: str) -> dict:
        """
        Handle Plaid webhooks for real-time transaction updates.
        Webhook types: TRANSACTIONS, ITEM, AUTH
        """
        if webhook_type == "TRANSACTIONS":
            if webhook_code == "SYNC_UPDATES_AVAILABLE":
                return {"action": "sync", "item_id": item_id}
            if webhook_code == "DEFAULT_UPDATE":
                return {"action": "sync", "item_id": item_id}
        if webhook_type == "ITEM":
            if webhook_code == "ERROR":
                return {"action": "reauth_required", "item_id": item_id}

        return {"action": "ignored", "webhook_type": webhook_type, "webhook_code": webhook_code}


def get_plaid_service() -> PlaidService:
    return PlaidService()
