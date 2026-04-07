"""Trader composite scoring engine — pure Python, no LLM calls."""

from __future__ import annotations

import math
from datetime import datetime, timezone

from models.trader import TraderProfile


class TraderScorer:
    """Computes a 0–100 composite score for ranking traders.

    Formula (when trade data available):
        composite = (
            win_rate_norm   × 0.30
          + roi_norm        × 0.25
          + frequency_norm  × 0.15
          + recency_norm    × 0.20
          - volatility_norm × 0.10
        ) × 100

    Fallback (no trade data — Kalshi markets):
        Uses log-scaled PnL + volume as a proxy score.

    All components are normalized to 0.0–1.0 before weighting.
    """

    WEIGHTS = {
        "win_rate":   0.30,
        "roi":        0.25,
        "frequency":  0.15,
        "recency":    0.20,
        "volatility": 0.10,  # subtracted
    }

    # ── Normalization caps ──────────────────────────────
    ROI_CAP = 0.5           # 50% avg ROI → normalized to 1.0
    FREQUENCY_CAP = 100     # 100+ trades → normalized to 1.0
    RECENCY_HALFLIFE = 30   # days — exponential decay constant
    VOLATILITY_CAP = 0.5    # std_dev ≥ 0.5 → full penalty
    DEFAULT_VOLATILITY = 0.5  # penalty when data is insufficient

    def score(self, trader: TraderProfile) -> float:
        """Return a composite score between 0 and 100."""

        if trader.num_trades == 0:
            # Fallback for Kalshi pseudo-traders (no individual trade data)
            pnl = max(trader.total_pnl, 1)
            vol = max(trader.total_volume, 1)

            pnl_score = math.log10(pnl)
            vol_score = math.log10(vol)

            raw = (0.7 * pnl_score + 0.3 * vol_score)
            score = (raw - 3) * 20

            return round(max(0, min(score, 100)), 2)

        # Full scoring with trade data
        win_rate_norm = trader.computed_win_rate

        # ── 2. ROI — capped at ROI_CAP ─────────────────
        roi_norm = min(max(trader.avg_roi_per_trade, 0.0) / self.ROI_CAP, 1.0)

        # ── 3. Frequency — saturates at FREQUENCY_CAP ──
        freq_norm = min(trader.num_trades / self.FREQUENCY_CAP, 1.0)

        # ── 4. Recency — exponential time decay ────────
        days_inactive = (datetime.now(timezone.utc) - trader.last_active).total_seconds() / 86400
        days_inactive = max(days_inactive, 0.0)
        recency_norm = math.exp(-days_inactive / self.RECENCY_HALFLIFE)

        # ── 5. Volatility penalty ───────────────────────
        if trader.num_trades < 5:
            vol_norm = self.DEFAULT_VOLATILITY
        else:
            vol_norm = 1.0 - abs(trader.computed_win_rate - 0.5) * 2
            vol_norm = max(0.0, min(vol_norm, 1.0))

        # ── Weighted combination ────────────────────────
        raw = (
            win_rate_norm * self.WEIGHTS["win_rate"]
            + roi_norm    * self.WEIGHTS["roi"]
            + freq_norm   * self.WEIGHTS["frequency"]
            + recency_norm * self.WEIGHTS["recency"]
            - vol_norm    * self.WEIGHTS["volatility"]
        )

        return round(max(0.0, min(raw * 100, 100.0)), 1)

    def rank(self, traders: list[TraderProfile]) -> list[TraderProfile]:
        """Score every trader and return the list sorted descending."""
        for t in traders:
            t.composite_score = self.score(t)
        return sorted(traders, key=lambda x: x.composite_score, reverse=True)

    def breakdown(self, trader: TraderProfile) -> dict:
        """Return per-component breakdown (useful for explanation cards)."""
        if trader.num_trades == 0:
            return {k: {"raw": 0, "normalized": 0.0, "weight": w}
                    for k, w in self.WEIGHTS.items()}

        win_rate_norm = trader.computed_win_rate
        roi_norm = min(max(trader.avg_roi_per_trade, 0.0) / self.ROI_CAP, 1.0)
        freq_norm = min(trader.num_trades / self.FREQUENCY_CAP, 1.0)
        days_inactive = max(
            (datetime.now(timezone.utc) - trader.last_active).total_seconds() / 86400, 0.0
        )
        recency_norm = math.exp(-days_inactive / self.RECENCY_HALFLIFE)

        if trader.num_trades < 5:
            vol_norm = self.DEFAULT_VOLATILITY
        else:
            vol_norm = 1.0 - abs(trader.computed_win_rate - 0.5) * 2
            vol_norm = max(0.0, min(vol_norm, 1.0))

        return {
            "win_rate": {
                "raw": trader.computed_win_rate,
                "normalized": round(win_rate_norm, 3),
                "weight": self.WEIGHTS["win_rate"],
            },
            "roi": {
                "raw": trader.avg_roi_per_trade,
                "normalized": round(roi_norm, 3),
                "weight": self.WEIGHTS["roi"],
            },
            "frequency": {
                "raw": trader.num_trades,
                "normalized": round(freq_norm, 3),
                "weight": self.WEIGHTS["frequency"],
            },
            "recency": {
                "raw": f"{days_inactive:.1f}d",
                "normalized": round(recency_norm, 3),
                "weight": self.WEIGHTS["recency"],
            },
            "volatility": {
                "raw": round(vol_norm, 3),
                "normalized": round(vol_norm, 3),
                "weight": -self.WEIGHTS["volatility"],
            },
        }
