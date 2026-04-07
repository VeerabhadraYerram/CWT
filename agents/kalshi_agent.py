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


def _ticker_to_display_name(event_ticker: str) -> str:
    """Convert a Kalshi event ticker into a human-readable short name.

    Uses known word boundaries to split ALLCAPS tickers into readable names.

    Examples:
        'KXELONMARS'         → '📈 Elon Mars Mkt'
        'KXNEXTPOPE'         → '📈 Next Pope Mkt'
        'KXMVESPORTS...'     → '📈 MV Esports Mkt'
        'KXPOLITICS-...'     → '📈 Politics Mkt'
    """
    import re

    ticker = event_ticker.strip()

    # Remove the KX prefix
    if ticker.upper().startswith("KX"):
        ticker = ticker[2:]

    # Remove anything after a dash (sub-identifiers)
    ticker = ticker.split("-")[0]

    # Known word boundaries for Kalshi tickers
    KNOWN_WORDS = [
        "MULTI", "GAME", "EXTENDED", "SPORTS", "ESPORTS",
        "ELON", "MARS", "POPE", "NEXT", "TRUMP", "BIDEN",
        "PRICE", "WEATHER", "TEMP", "SNOW", "HURRICANE",
        "POLITICS", "ELECTION", "SENATE", "HOUSE",
        "BTC", "ETH", "CRYPTO", "COIN",
        "GDP", "CPI", "FED", "JOBS", "RATE", "INFL",
        "MOVIE", "OSCAR", "AWARD", "EMMY",
        "AI", "SPACE", "NASA", "TECH",
        "NFL", "NBA", "MLB", "NHL", "FIFA",
        "MV", "MVE",
    ]

    # Try to split using known words (greedy, longest first)
    remaining = ticker.upper()
    parts = []
    while remaining:
        matched = False
        # Try longest known words first
        for word in sorted(KNOWN_WORDS, key=len, reverse=True):
            if remaining.startswith(word):
                parts.append(word.title())
                remaining = remaining[len(word):]
                matched = True
                break
        if not matched:
            # Take single character and continue
            parts.append(remaining[0])
            remaining = remaining[1:]

    name = " ".join(parts).strip()

    # Clean up single-letter fragments
    name = re.sub(r'\b[A-Z]\b', '', name).strip()
    name = re.sub(r'\s+', ' ', name)

    if not name:
        name = ticker.title()

    if len(name) > 20:
        name = name[:18] + ".."

    return f"{name} Mkt"


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
        """Fetch events from Kalshi and convert to TraderProfiles.

        Uses the events endpoint with nested markets to get real volume data.

        Args:
            limit: Max events to fetch.

        Returns:
            List of TraderProfile objects representing Kalshi events.
        """
        self.logger.info("kalshi_fetch_traders", limit=limit)

        try:
            data = await self.api.get_events(limit=limit, status="open")
            events = data.get("events", [])
        except Exception as e:
            self.logger.error("kalshi_api_failed", error=str(e))
            return []

        if not events:
            self.logger.warning("kalshi_no_events")
            return []

        traders = []
        for event in events:
            trader = self._parse_event(event)
            if trader:
                traders.append(trader)

        self.logger.info("kalshi_traders_created", count=len(traders))
        return traders

    def _parse_event(self, event: dict) -> TraderProfile | None:
        """Convert a Kalshi event (with nested markets) into a TraderProfile.

        Aggregates volume and open_interest across all nested markets.
        Uses event_ticker to generate a clean short name for display.
        """
        try:
            event_ticker = event.get("event_ticker", "")
            title = event.get("title", "Unknown Event")
            markets = event.get("markets", [])

            # Aggregate volume and open interest across all nested markets
            total_volume = sum(
                self._safe_float(m.get("volume_fp")) for m in markets
            )
            total_oi = sum(
                self._safe_float(m.get("open_interest_fp")) for m in markets
            )

            # Use the best available activity metric
            total_activity = max(total_volume, total_oi, 1)

            # Estimate PnL from activity
            estimated_pnl = total_activity * 0.05

            now = datetime.now(timezone.utc)
            niche = _infer_niche_from_ticker(event_ticker)

            # Generate a short display name from the ticker
            # e.g. "KXELONMARS" → "Elon Mars", "KXNEXTPOPE" → "Next Pope"
            short_name = _ticker_to_display_name(event_ticker)

            return TraderProfile(
                platform="kalshi",
                wallet_or_username=event_ticker,
                display_name=f"📈 {short_name}",
                total_pnl=estimated_pnl,
                total_volume=total_activity,
                num_trades=len(markets),
                num_wins=0,
                active_positions=len(markets),
                first_seen=now,
                last_updated=now,
                data_source="api",
                niches={niche: 0.8},
                category=niche,
            )
        except (ValueError, TypeError, KeyError) as e:
            logger.warning("kalshi_parse_failed", error=str(e))
            return None

    def _parse_market(self, market: dict) -> TraderProfile | None:
        """Convert a Kalshi market dict into a TraderProfile.

        Handles missing/malformed fields gracefully.
        Uses multiple volume fields as fallbacks.
        """
        try:
            ticker = market.get("ticker", "")
            title = market.get("title", "Unknown Market")
            event_ticker = market.get("event_ticker", "")

            # Kalshi v2 has several volume fields — try all of them
            volume = (
                self._safe_float(market.get("dollar_volume"))
                or self._safe_float(market.get("volume"))
                or self._safe_float(market.get("volume_24h"))
                or self._safe_float(market.get("open_interest"))
                or self._safe_float(market.get("dollar_open_interest"))
                or 0
            )

            # Use open interest as additional signal
            open_interest = (
                self._safe_float(market.get("dollar_open_interest"))
                or self._safe_float(market.get("open_interest"))
                or 0
            )

            # Combined activity metric (volume + open interest)
            total_activity = max(volume, open_interest)

            # Estimate PnL — more aggressive to compete with Polymarket scores
            # Kalshi markets with high activity deserve visibility
            estimated_pnl = total_activity * 0.05  # ~5% of activity as edge

            now = datetime.now(timezone.utc)

            # Infer niche from event ticker
            niche = _infer_niche_from_ticker(event_ticker)

            return TraderProfile(
                platform="kalshi",
                wallet_or_username=ticker,
                display_name=title,
                total_pnl=estimated_pnl,
                total_volume=total_activity,
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

    @staticmethod
    def _safe_float(val) -> float:
        """Convert a value to float, returning 0 for None/invalid."""
        if val is None:
            return 0.0
        try:
            return float(val)
        except (ValueError, TypeError):
            return 0.0

    async def close(self):
        """Close API connections."""
        await self.api.close()
