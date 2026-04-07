"""Kalshi API Client — async HTTP with retries (v2 public API)."""

from __future__ import annotations

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = structlog.get_logger(__name__)

BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"


class KalshiAPI:
    """Async client for the Kalshi public Trade API (v2).

    Usage:
        async with KalshiAPI() as api:
            data = await api.get_markets(limit=10)
    """

    def __init__(self, timeout: float = 30.0):
        self._client = httpx.AsyncClient(
            base_url=BASE_URL,
            timeout=timeout,
            headers={"Accept": "application/json"},
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        await self.close()

    async def close(self):
        await self._client.aclose()

    # ── API methods ─────────────────────────────────────

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type((
            httpx.HTTPStatusError,
            httpx.ConnectError,
            httpx.ReadTimeout,
            httpx.ConnectTimeout,
        )),
    )
    async def get_markets(
        self,
        limit: int = 20,
        status: str = "open",
        cursor: str | None = None,
    ) -> dict:
        """Fetch markets from Kalshi's v2 API.

        Args:
            limit: Max markets to return.
            status: Market status filter (open, closed, settled).
            cursor: Pagination cursor from previous response.

        Returns:
            Dict with 'markets' list and 'cursor' for pagination.
        """
        logger.info("kalshi_get_markets", limit=limit, status=status)

        params: dict = {"limit": limit, "status": status}
        if cursor:
            params["cursor"] = cursor

        try:
            resp = await self._client.get("/markets", params=params)
            resp.raise_for_status()
            data = resp.json()
            logger.info("kalshi_markets_fetched", count=len(data.get("markets", [])))
            return data
        except Exception as e:
            logger.error("kalshi_markets_failed", error=str(e))
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type((
            httpx.HTTPStatusError,
            httpx.ConnectError,
            httpx.ReadTimeout,
            httpx.ConnectTimeout,
        )),
    )
    async def get_events(
        self,
        limit: int = 20,
        status: str = "open",
    ) -> dict:
        """Fetch events with nested markets from Kalshi's v2 API.

        Events are higher-level groupings of related markets and
        include real volume/open_interest data in their nested markets.

        Args:
            limit: Max events to return.
            status: Event status filter.

        Returns:
            Dict with 'events' list and 'cursor'.
        """
        logger.info("kalshi_get_events", limit=limit)

        try:
            resp = await self._client.get(
                "/events",
                params={
                    "limit": limit,
                    "status": status,
                    "with_nested_markets": "true",
                },
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("kalshi_events_failed", error=str(e))
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type((
            httpx.HTTPStatusError,
            httpx.ConnectError,
            httpx.ReadTimeout,
            httpx.ConnectTimeout,
        )),
    )
    async def get_market(self, ticker: str) -> dict:
        """Fetch a single market by ticker.

        Args:
            ticker: Market ticker string (e.g., 'KXPOLITICS-...')

        Returns:
            Dict with market details.
        """
        logger.info("kalshi_get_market", ticker=ticker)

        try:
            resp = await self._client.get(f"/markets/{ticker}")
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("kalshi_market_failed", ticker=ticker, error=str(e))
            raise
