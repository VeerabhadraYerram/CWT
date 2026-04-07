"""Canonical trader data model used across all agents."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class TraderProfile(BaseModel):
    """Single source of truth for trader data throughout the system.

    Sections:
        Identity   — who this trader is and where they trade.
        Raw metrics — numbers pulled directly from APIs / scrapes.
        Computed    — derived by the scoring engine & niche mapper.
        Metadata    — bookkeeping fields.
    """

    # ── Identity ────────────────────────────────────────
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    platform: Literal["polymarket", "kalshi"]
    wallet_or_username: str
    display_name: str | None = None

    # ── Raw metrics (from API / scrape) ─────────────────
    total_pnl: float = 0.0            # Lifetime profit & loss (USD)
    total_volume: float = 0.0         # Lifetime trading volume (USD)
    num_trades: int = 0               # Total resolved trades
    num_wins: int = 0                 # Trades closed in profit
    win_rate: float = 0.0             # num_wins / num_trades (0–1)
    avg_roi_per_trade: float = 0.0    # mean(trade_pnl / trade_cost)
    last_active: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    active_positions: int = 0         # Currently open positions

    # ── Computed (by scoring engine & niche mapper) ─────
    composite_score: float = 0.0      # 0–100, set by scorer.py
    niches: dict[str, float] = Field(
        default_factory=dict,         # e.g. {"POLITICS": 0.6, "NBA": 0.3}
    )
    trust_score: float = 50.0         # Updated by learning loop (0–100)
    category: str = "GENERAL"         # Primary niche category

    # ── Metadata ────────────────────────────────────────
    first_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data_source: str = "api"          # "api", "scrape", "cache", "mock"

    @field_validator("composite_score", "trust_score")
    @classmethod
    def clamp_scores(cls, v: float) -> float:
        return max(0.0, min(v, 100.0))

    @property
    def computed_win_rate(self) -> float:
        if self.num_trades == 0:
            return 0.0
        return self.num_wins / self.num_trades

    def touch(self):
        """Update last_updated timestamp."""
        self.last_updated = datetime.now(timezone.utc)

    def to_summary_dict(self) -> dict:
        """Return a compact dict for display / serialization."""
        return {
            "name": self.display_name or self.wallet_or_username,
            "platform": self.platform,
            "score": self.composite_score,
            "pnl": self.total_pnl,
            "volume": self.total_volume,
            "win_rate": self.computed_win_rate,
            "niche": max(self.niches, key=self.niches.get) if self.niches else "GENERAL",
            "trust": self.trust_score,
        }
