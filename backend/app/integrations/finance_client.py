"""Finance data client — public financial data API client.

Designed to work with stock-data-pro skill or similar public APIs.
All configurable parameters read from Settings (env vars / .env file).
"""
from typing import Optional, List, Dict
import httpx
from app.config import get_settings


class FinanceClient:
    """Client for public financial data APIs."""

    def __init__(self, api_key: Optional[str] = None, base_url: str = ""):
        settings = get_settings()
        self.api_key = api_key or settings.stock_data_api_key
        self.base_url = base_url or settings.stock_data_base_url
        self._client = httpx.Client(timeout=settings.ima_api_timeout)

    def get_company_financials(self, ticker: str) -> Optional[Dict]:
        """Get financial data for a public company by ticker."""
        url = f"{self.base_url}/companies/{ticker}/financials"
        headers = {"X-API-Key": self.api_key} if self.api_key else {}
        try:
            resp = self._client.get(url, headers=headers)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return None

    def get_earnings_reports(self, ticker: str, limit: int = 4) -> List[Dict]:
        """Get recent earnings reports."""
        url = f"{self.base_url}/companies/{ticker}/earnings"
        headers = {"X-API-Key": self.api_key} if self.api_key else {}
        params = {"limit": limit}
        try:
            resp = self._client.get(url, headers=headers, params=params)
            if resp.status_code == 200:
                return resp.json().get("data", [])
        except Exception:
            pass
        return []

    def search_company(self, name: str) -> List[Dict]:
        """Search for a company by name."""
        url = f"{self.base_url}/search"
        headers = {"X-API-Key": self.api_key} if self.api_key else {}
        try:
            resp = self._client.get(url, headers=headers, params={"query": name})
            if resp.status_code == 200:
                return resp.json().get("results", [])
        except Exception:
            pass
        return []
