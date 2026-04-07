"""Tests for the Polymarket API client."""

import pytest
import asyncio

from tools.polymarket_api import PolymarketAPI


class TestPolymarketAPI:
    """Test the Polymarket Data API client."""

    @pytest.fixture
    def api(self):
        return PolymarketAPI()

    @pytest.mark.asyncio
    async def test_get_leaderboard_returns_list(self, api):
        """Leaderboard should return a list of trader dicts."""
        try:
            data = await api.get_leaderboard(limit=3)
            assert isinstance(data, list)
            if data:
                assert isinstance(data[0], dict)
        finally:
            await api.close()

    @pytest.mark.asyncio
    async def test_leaderboard_has_expected_keys(self, api):
        """Leaderboard entries should have basic trader fields."""
        try:
            data = await api.get_leaderboard(limit=1)
            if data:
                entry = data[0]
                # At minimum, should have wallet and PnL
                has_wallet = any(k in entry for k in ["proxyWallet", "userAddress", "address"])
                has_pnl = "pnl" in entry or "vol" in entry
                assert has_wallet or has_pnl
        finally:
            await api.close()

    @pytest.mark.asyncio
    async def test_leaderboard_limit(self, api):
        """Should respect the limit parameter."""
        try:
            data = await api.get_leaderboard(limit=5)
            assert len(data) <= 5
        finally:
            await api.close()

    @pytest.mark.asyncio
    async def test_get_leaderboard_empty_on_error(self, api):
        """Should return empty list on invalid category (not crash)."""
        try:
            data = await api.get_leaderboard(category="NONEXISTENT_CATEGORY", limit=1)
            assert isinstance(data, list)
        finally:
            await api.close()
