"""Niche Mapper Agent — LLM-powered trader/market classification into niches."""

from __future__ import annotations

import structlog

from agents.base_agent import BaseAgent
from models.trader import TraderProfile

logger = structlog.get_logger(__name__)

SYSTEM_PROMPT = """\
You are a classification agent for prediction markets. Your job is to classify
traders and markets into specific niche categories based on their names and
available data.

Categories (pick ONE primary, optionally one secondary):
- POLITICS (elections, government, policy)
- SPORTS/NBA, SPORTS/NFL, SPORTS/MLB, SPORTS/NHL, SPORTS/SOCCER, SPORTS/OTHER
- WEATHER (temperature, storms, climate events)
- ECONOMICS (CPI, GDP, Fed rate, jobs)
- CRYPTO (Bitcoin, Ethereum, crypto markets)
- ENTERTAINMENT (movies, awards, TV, music)
- SCIENCE/TECH (AI, space, technology)
- GENERAL (catch-all when unclear)

Respond ONLY with a JSON object like:
{"primary": "POLITICS", "confidence": 0.9}
or
{"primary": "SPORTS/NBA", "confidence": 0.85}

Do not include any other text.
"""

# Extended keyword map for fast fallback classification
KEYWORD_MAP = {
    "POLITICS": [
        "election", "trump", "biden", "president", "senate", "congress",
        "democrat", "republican", "vote", "political", "governor", "mayor",
        "impeach", "cabinet", "legislation", "bill", "law", "supreme court",
        "scotus", "gop", "dnc", "rnc", "primary", "swing state", "ballot",
    ],
    "SPORTS/NBA": [
        "nba", "basketball", "lakers", "celtics", "warriors", "bucks",
        "nets", "knicks", "nuggets", "suns", "playoffs", "lebron", "curry",
    ],
    "SPORTS/NFL": [
        "nfl", "football", "super bowl", "chiefs", "eagles", "cowboys",
        "49ers", "touchdowns", "quarterback", "mahomes",
    ],
    "SPORTS/MLB": [
        "mlb", "baseball", "yankees", "dodgers", "red sox", "world series",
        "home run", "pitcher", "batting", "mets", "astros",
    ],
    "SPORTS/OTHER": [
        "soccer", "tennis", "golf", "f1", "formula 1", "ufc", "mma",
        "boxing", "hockey", "nhl", "ncaa", "olympics", "cricket", "rugby",
    ],
    "WEATHER": [
        "weather", "temperature", "hurricane", "storm", "tornado", "snow",
        "rainfall", "heat", "cold", "climate", "flood", "wildfire",
    ],
    "ECONOMICS": [
        "cpi", "gdp", "inflation", "federal reserve", "fed rate", "interest rate",
        "unemployment", "jobs", "recession", "stock market", "s&p", "nasdaq",
        "dow jones", "treasury", "yield", "tariff",
    ],
    "CRYPTO": [
        "bitcoin", "btc", "ethereum", "eth", "crypto", "blockchain",
        "defi", "token", "coin", "solana", "sol",
    ],
    "ENTERTAINMENT": [
        "oscar", "emmy", "grammy", "movie", "film", "box office",
        "netflix", "streaming", "tv show", "music", "album", "award",
        "celebrity", "reality tv",
    ],
    "SCIENCE/TECH": [
        "ai", "artificial intelligence", "space", "spacex", "nasa",
        "launch", "satellite", "mars", "tesla", "technology", "quantum",
    ],
}


class NicheAgent(BaseAgent):
    """Agent that classifies traders into niche categories.

    Uses LLM for intelligent classification with a fast keyword
    fallback when LLM is rate-limited.

    Usage:
        agent = NicheAgent()
        trader = agent.map_niche(trader_profile)
    """

    def __init__(self):
        super().__init__(name="niche_mapper", system_prompt=SYSTEM_PROMPT)

    def map_niche(self, trader: TraderProfile) -> TraderProfile:
        """Classify a trader into niche categories using keyword matching.

        LLM classification is disabled to preserve rate limit budget for
        the recommendation engine (the most valuable LLM output).

        Args:
            trader: TraderProfile to classify.

        Returns:
            The same TraderProfile with updated niches dict.
        """
        # If trader already has non-default niches (e.g., from Kalshi ticker), keep them
        if trader.niches and "GENERAL" not in trader.niches:
            return trader

        name = (trader.display_name or trader.wallet_or_username or "").lower()

        # Keyword classification (fast, no API calls)
        niche, confidence = self._keyword_classify(name)
        trader.niches = {niche: confidence}
        trader.category = niche
        return trader

    def map_niches_batch(self, traders: list[TraderProfile]) -> list[TraderProfile]:
        """Classify multiple traders at once.

        Args:
            traders: List of TraderProfiles.

        Returns:
            Same list with updated niches.
        """
        return [self.map_niche(t) for t in traders]

    def _keyword_classify(self, text: str) -> tuple[str, float]:
        """Classify using keyword matching.

        Returns:
            Tuple of (niche_category, confidence_score).
        """
        text_lower = text.lower()
        best_niche = "GENERAL"
        best_score = 0

        for niche, keywords in KEYWORD_MAP.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > best_score:
                best_score = score
                best_niche = niche

        # Convert match count to confidence
        if best_score >= 3:
            confidence = 0.9
        elif best_score == 2:
            confidence = 0.8
        elif best_score == 1:
            confidence = 0.7
        else:
            confidence = 0.5
            best_niche = "GENERAL"

        return best_niche, confidence

    def _llm_classify(self, text: str) -> tuple[str, float]:
        """Classify using LLM.

        Returns:
            Tuple of (niche_category, confidence_score).
        """
        import json

        prompt = f"Classify this prediction market trader/event: \"{text}\""
        response = self.run(prompt)

        try:
            result = json.loads(response.strip())
            niche = result.get("primary", "GENERAL")
            confidence = float(result.get("confidence", 0.5))
            return niche, confidence
        except (json.JSONDecodeError, ValueError):
            self.logger.warning("niche_llm_parse_failed", response=response[:100])
            return "GENERAL", 0.5
