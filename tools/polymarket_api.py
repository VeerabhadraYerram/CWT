"""Polymarket Data API client — async HTTP with retries."""

from __future__ import annotations

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = structlog.get_logger(__name__)

BASE_URL = "https://data-api.polymarket.com"


class PolymarketAPI:
    """Thin async client for the Polymarket public Data API.

    Usage:
        async with PolymarketAPI() as api:
            leaders = await api.get_leaderboard(limit=10)
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
    async def get_leaderboard(
        self,
        category: str = "OVERALL",
        time_period: str = "ALL",
        order_by: str = "PNL",
        limit: int = 50,
    ) -> list[dict]:
        """Fetch the Polymarket leaderboard.

        Args:
            category: OVERALL, POLITICS, SPORTS, CRYPTO, etc.
            time_period: ALL, DAILY, WEEKLY, MONTHLY.
            order_by: PNL, VOLUME, etc.
            limit: Max traders to return.

        Returns:
            List of raw trader dicts from the API.
        """
        logger.info("polymarket_leaderboard", category=category, limit=limit)

        try:
            resp = await self._client.get(
                "/v1/leaderboard",
                params={
                    "category": category,
                    "timePeriod": time_period,
                    "orderBy": order_by,
                    "limit": limit,
                },
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("polymarket_failed", error=str(e))
            return []

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
    async def get_trades(
        self,
        wallet_address: str,
        limit: int = 100,
    ) -> list[dict]:
        """Fetch trade history for a wallet.

        Args:
            wallet_address: Ethereum address (0x...).
            limit: Max trades to return.

        Returns:
            List of raw trade dicts.
        """
        logger.info("polymarket_trades", wallet=wallet_address[:10], limit=limit)

        try:
            resp = await self._client.get(
                "/trades",
                params={"user": wallet_address, "limit": limit},
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("polymarket_failed", error=str(e))
            return []

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
    async def get_positions(self, wallet_address: str) -> list[dict]:
        """Fetch current open positions for a wallet.

        Args:
            wallet_address: Ethereum address (0x...).

        Returns:
            List of raw position dicts.
        """
        logger.info("polymarket_positions", wallet=wallet_address[:10])

        try:
            resp = await self._client.get(
                "/positions",
                params={"user": wallet_address},
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("polymarket_failed", error=str(e))
            return []
