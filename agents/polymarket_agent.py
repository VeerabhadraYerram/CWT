"""Polymarket Trader Agent — fetches and converts leaderboard data to TraderProfiles."""

from __future__ import annotations

from datetime import datetime, timezone

import structlog

from agents.base_agent import BaseAgent
from models.trader import TraderProfile
from tools.polymarket_api import PolymarketAPI

logger = structlog.get_logger(__name__)

SYSTEM_PROMPT = (
    "You are the Polymarket Trader Agent. Your job is to find and analyze "
    "consistent, profitable traders on the Polymarket prediction market platform."
)


class PolymarketAgent(BaseAgent):
    """Fetches Polymarket leaderboard data and converts to TraderProfile objects.

    Usage:
        agent = PolymarketAgent()
        traders = await agent.fetch_traders(limit=10)
    """

    def __init__(self):
        super().__init__(name="polymarket_agent", system_prompt=SYSTEM_PROMPT)
        self.api = PolymarketAPI()

    async def fetch_traders(
        self,
        category: str = "OVERALL",
        limit: int = 20,
    ) -> list[TraderProfile]:
        """Fetch leaderboard and convert raw data to TraderProfile objects.

        Args:
            category: Leaderboard category (OVERALL, POLITICS, SPORTS, etc.)
            limit: Max number of traders to fetch.

        Returns:
            List of TraderProfile objects with basic fields populated.
        """
        self.logger.info("fetch_traders", category=category, limit=limit)

        try:
            raw_data = await self.api.get_leaderboard(
                category=category,
                limit=limit,
            )
        except Exception as e:
            self.logger.error("api_failed", error=str(e))
            return []

        if not raw_data:
            self.logger.warning("no_leaderboard_data", category=category)
            return []

        traders = []
        for entry in raw_data:
            trader = self._parse_entry(entry)
            if trader:
                traders.append(trader)

        self.logger.info("traders_fetched", count=len(traders))
        return traders

    def _parse_entry(self, entry: dict) -> TraderProfile | None:
        """Convert a raw leaderboard dict to a TraderProfile.

        Handles missing/malformed fields gracefully — returns None on failure.
        """
        try:
            wallet = (
                entry.get("proxyWallet")
                or entry.get("userAddress")
                or entry.get("address")
                or entry.get("user")
                or ""
            )

            if not wallet:
                return None

            wallet = wallet.lower()

            display_name = entry.get("userName") or entry.get("displayName") or entry.get("username")
            now = datetime.now(timezone.utc)
            return TraderProfile(
                platform="polymarket",
                wallet_or_username=wallet,
                display_name=display_name,

                total_pnl=float(entry.get("pnl", 0) or 0),
                total_volume=float(entry.get("vol", 0) or entry.get("volume", 0) or 0),

                num_trades=int(entry.get("numTrades", 0) or 0),
                num_wins=int(entry.get("numWins", 0) or 0),

                active_positions=0,

                first_seen=now,
                last_updated=now,
                data_source="api",
            )
        except (ValueError, TypeError, KeyError) as e:
            logger.warning("parse_entry_failed", error=str(e), entry_keys=list(entry.keys()))
            return None

    async def close(self):
        """Clean up the HTTP client."""
        await self.api.close()
