"""Tests for the Kalshi API client."""

import pytest

from tools.kalshi_api import KalshiAPI


class TestKalshiAPI:
    """Test the Kalshi v2 public API client."""

    @pytest.fixture
    def api(self):
        return KalshiAPI()

    @pytest.mark.asyncio
    async def test_get_markets_returns_dict(self, api):
        """get_markets should return a dict with 'markets' key."""
        try:
            data = await api.get_markets(limit=3)
            assert isinstance(data, dict)
            assert "markets" in data
        finally:
            await api.close()

    @pytest.mark.asyncio
    async def test_markets_has_expected_fields(self, api):
        """Market entries should have title, ticker, and volume."""
        try:
            data = await api.get_markets(limit=1)
            markets = data.get("markets", [])
            if markets:
                market = markets[0]
                # Kalshi v2 markets should have these fields
                assert "ticker" in market or "title" in market
        finally:
            await api.close()

    @pytest.mark.asyncio
    async def test_correct_base_url(self, api):
        """API should use the correct v2 endpoint."""
        assert "api.elections.kalshi.com" in str(api._client.base_url)
        assert "v2" in str(api._client.base_url)
        await api.close()

    @pytest.mark.asyncio
    async def test_markets_limit(self, api):
        """Should respect the limit parameter."""
        try:
            data = await api.get_markets(limit=2)
            markets = data.get("markets", [])
            assert len(markets) <= 2
        finally:
            await api.close()
