"""Kalshi Agent — fetches real market data and converts to TraderProfiles."""

from __future__ import annotations

from datetime import datetime, timezone

import structlog

from agents.base_agent import BaseAgent
from models.trader import TraderProfile
from tools.kalshi_api import KalshiAPI

logger = structlog.get_logger(__name__)

# Kalshi event ticker prefix → niche category mapping
TICKER_NICHE_MAP = {
    "KXMLB": "SPORTS/MLB",
    "KXNBA": "SPORTS/NBA",
    "KXNFL": "SPORTS/NFL",
    "KXNHL": "SPORTS/NHL",
    "KXSOCCER": "SPORTS/SOCCER",
    "KXMMA": "SPORTS/MMA",
    "KXPGA": "SPORTS/GOLF",
    "KXTENNIS": "SPORTS/TENNIS",
    "KXNCAA": "SPORTS/NCAA",
    "KXPOLITICS": "POLITICS",
    "KXELECTION": "POLITICS",
    "KXTRUMP": "POLITICS",
    "KXBIDEN": "POLITICS",
    "KXGOV": "POLITICS",
    "KXWEATHER": "WEATHER",
    "KXTEMP": "WEATHER",
    "KXHURRICANE": "WEATHER",
    "KXSNOW": "WEATHER",
    "KXCPI": "ECONOMICS",
    "KXGDP": "ECONOMICS",
    "KXFED": "ECONOMICS",
    "KXJOBS": "ECONOMICS",
    "KXINFL": "ECONOMICS",
    "KXRATE": "ECONOMICS",
    "KXCRYPTO": "CRYPTO",
    "KXBTC": "CRYPTO",
    "KXETH": "CRYPTO",
    "KXMOVIE": "ENTERTAINMENT",
    "KXAWARD": "ENTERTAINMENT",
    "KXOSCAR": "ENTERTAINMENT",
    "KXAI": "SCIENCE/TECH",
    "KXSPACE": "SCIENCE/TECH",
}

SYSTEM_PROMPT = (
    "You are the Kalshi Market Agent. Your job is to find and analyze "
    "active prediction markets on the Kalshi platform and represent "
    "high-volume markets as pseudo-trader profiles for analysis."
)


def _infer_niche_from_ticker(event_ticker: str) -> str:
    """Infer a niche category from a Kalshi event ticker prefix."""
    upper = event_ticker.upper()
    for prefix, niche in TICKER_NICHE_MAP.items():
        if upper.startswith(prefix):
            return niche
    return "GENERAL"


class KalshiAgent(BaseAgent):
    """Agent for fetching Kalshi market data and creating pseudo-trader profiles.

    Since Kalshi doesn't expose a public leaderboard of individual traders,
    we model high-volume markets as pseudo-traders — each representing the
    collective trading activity on that market.
    """

    def __init__(self):
        super().__init__(name="kalshi_agent", system_prompt=SYSTEM_PROMPT)
        self.api = KalshiAPI()

    async def fetch_traders(self, limit: int = 10) -> list[TraderProfile]:
        """Fetch markets from Kalshi and convert to TraderProfiles.

        Args:
            limit: Max markets to fetch.

        Returns:
            List of TraderProfile objects representing Kalshi markets.
        """
        self.logger.info("kalshi_fetch_traders", limit=limit)

        try:
            data = await self.api.get_markets(limit=limit, status="open")
            markets = data.get("markets", [])
        except Exception as e:
            self.logger.error("kalshi_api_failed", error=str(e))
            return []

        if not markets:
            self.logger.warning("kalshi_no_markets")
            return []

        traders = []
        for market in markets:
            trader = self._parse_market(market)
            if trader:
                traders.append(trader)

        self.logger.info("kalshi_traders_created", count=len(traders))
        return traders

    def _parse_market(self, market: dict) -> TraderProfile | None:
        """Convert a Kalshi market dict into a TraderProfile.

        Handles missing/malformed fields gracefully.
        """
        try:
            ticker = market.get("ticker", "")
            title = market.get("title", "Unknown Market")
            event_ticker = market.get("event_ticker", "")
            volume = float(market.get("volume", 0) or 0)

            # Use volume-based heuristics for PnL estimate
            # Kalshi doesn't expose individual trader PnL
            estimated_pnl = volume * 0.03  # ~3% of volume as estimated edge

            now = datetime.now(timezone.utc)

            # Infer niche from event ticker
            niche = _infer_niche_from_ticker(event_ticker)

            return TraderProfile(
                platform="kalshi",
                wallet_or_username=ticker,
                display_name=title,
                total_pnl=estimated_pnl,
                total_volume=volume,
                num_trades=0,  # Not available from market-level API
                num_wins=0,
                active_positions=0,
                first_seen=now,
                last_updated=now,
                data_source="api",
                niches={niche: 0.8},
                category=niche,
            )
        except (ValueError, TypeError, KeyError) as e:
            logger.warning("kalshi_parse_failed", error=str(e))
            return None

    async def close(self):
        """Close API connections."""
        await self.api.close()
