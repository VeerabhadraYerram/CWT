"""Tests for the composite scoring engine."""

import pytest
from datetime import datetime, timezone, timedelta

from models.trader import TraderProfile
from scoring.scorer import TraderScorer


@pytest.fixture
def scorer():
    return TraderScorer()


@pytest.fixture
def polymarket_trader():
    """Trader with full trade data (Polymarket-style)."""
    return TraderProfile(
        platform="polymarket",
        wallet_or_username="0xtest_polymarket",
        display_name="TestTrader1",
        total_pnl=50000,
        total_volume=200000,
        num_trades=50,
        num_wins=35,
        avg_roi_per_trade=0.15,
        last_active=datetime.now(timezone.utc),
        data_source="test",
    )


@pytest.fixture
def kalshi_trader():
    """Pseudo-trader with no individual trade data (Kalshi-style)."""
    return TraderProfile(
        platform="kalshi",
        wallet_or_username="kalshi_test",
        display_name="Will it rain tomorrow?",
        total_pnl=3000,
        total_volume=100000,
        num_trades=0,
        num_wins=0,
        data_source="api",
    )


class TestTraderScorer:
    """Test the composite scoring engine."""

    def test_score_with_trade_data(self, scorer, polymarket_trader):
        """Trader with 50 trades and 70% win rate should score reasonably."""
        score = scorer.score(polymarket_trader)
        assert 0 <= score <= 100
        assert score > 30  # 70% win rate + good ROI should score well

    def test_score_without_trade_data(self, scorer, kalshi_trader):
        """Kalshi pseudo-trader uses volume/PnL fallback scoring."""
        score = scorer.score(kalshi_trader)
        assert 0 <= score <= 100
        assert score > 0  # $3000 PnL + $100k volume should score something

    def test_score_clamping(self, scorer):
        """Score should always be between 0 and 100."""
        # Huge PnL trader
        trader = TraderProfile(
            platform="polymarket",
            wallet_or_username="whale",
            total_pnl=999_999_999,
            total_volume=999_999_999,
            num_trades=0,
            data_source="test",
        )
        score = scorer.score(trader)
        assert 0 <= score <= 100

    def test_score_zero_everything(self, scorer):
        """Trader with all zeros should score 0 or very low."""
        trader = TraderProfile(
            platform="polymarket",
            wallet_or_username="empty",
            total_pnl=0,
            total_volume=0,
            num_trades=0,
            data_source="test",
        )
        score = scorer.score(trader)
        assert score == 0 or score <= 5

    def test_rank_ordering(self, scorer, polymarket_trader, kalshi_trader):
        """Ranking should produce descending composite scores."""
        traders = [kalshi_trader, polymarket_trader]
        ranked = scorer.rank(traders)
        assert ranked[0].composite_score >= ranked[1].composite_score

    def test_rank_scores_set(self, scorer, polymarket_trader, kalshi_trader):
        """Ranking sets composite_score on all traders."""
        traders = [polymarket_trader, kalshi_trader]
        ranked = scorer.rank(traders)
        for t in ranked:
            assert t.composite_score > 0

    def test_breakdown_with_trades(self, scorer, polymarket_trader):
        """Breakdown should have all 5 components."""
        polymarket_trader.composite_score = scorer.score(polymarket_trader)
        bd = scorer.breakdown(polymarket_trader)
        assert "win_rate" in bd
        assert "roi" in bd
        assert "frequency" in bd
        assert "recency" in bd
        assert "volatility" in bd

    def test_breakdown_without_trades(self, scorer, kalshi_trader):
        """Breakdown for zero-trade trader should return zeroed components."""
        bd = scorer.breakdown(kalshi_trader)
        assert bd["win_rate"]["normalized"] == 0.0

    def test_recency_decay(self, scorer):
        """Inactive trader should score lower on recency."""
        active = TraderProfile(
            platform="polymarket",
            wallet_or_username="active",
            num_trades=20, num_wins=14,
            last_active=datetime.now(timezone.utc),
            data_source="test",
        )
        inactive = TraderProfile(
            platform="polymarket",
            wallet_or_username="inactive",
            num_trades=20, num_wins=14,
            last_active=datetime.now(timezone.utc) - timedelta(days=90),
            data_source="test",
        )
        assert scorer.score(active) > scorer.score(inactive)

    def test_higher_winrate_scores_better(self, scorer):
        """Higher win rate should produce higher score, all else equal."""
        good = TraderProfile(
            platform="polymarket", wallet_or_username="good",
            num_trades=50, num_wins=40,
            data_source="test",
        )
        bad = TraderProfile(
            platform="polymarket", wallet_or_username="bad",
            num_trades=50, num_wins=15,
            data_source="test",
        )
        assert scorer.score(good) > scorer.score(bad)
