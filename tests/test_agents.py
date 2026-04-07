"""Tests for agent components (no live API calls)."""

import pytest
from datetime import datetime, timezone

from models.trader import TraderProfile
from agents.niche_agent import NicheAgent
from memory.memory_manager import MemoryManager
from memory.skills_manager import SkillsManager


class TestTraderProfile:
    """Test the TraderProfile data model."""

    def test_create_minimal(self):
        """Minimal TraderProfile creation."""
        t = TraderProfile(
            platform="polymarket",
            wallet_or_username="0xtest",
            data_source="test",
        )
        assert t.platform == "polymarket"
        assert t.composite_score == 0.0
        assert t.trust_score == 50.0

    def test_score_clamping(self):
        """Scores should be clamped to 0-100."""
        t = TraderProfile(
            platform="polymarket",
            wallet_or_username="0xtest",
            composite_score=150.0,
            trust_score=-10.0,
        )
        assert t.composite_score == 100.0
        assert t.trust_score == 0.0

    def test_computed_win_rate(self):
        """Computed win rate should be num_wins / num_trades."""
        t = TraderProfile(
            platform="polymarket",
            wallet_or_username="0xtest",
            num_trades=100,
            num_wins=70,
        )
        assert t.computed_win_rate == 0.7

    def test_computed_win_rate_zero_trades(self):
        """Win rate with zero trades should be 0."""
        t = TraderProfile(
            platform="polymarket",
            wallet_or_username="0xtest",
            num_trades=0,
        )
        assert t.computed_win_rate == 0.0

    def test_to_summary_dict(self):
        """Summary dict should have expected keys."""
        t = TraderProfile(
            platform="kalshi",
            wallet_or_username="kalshi_test",
            display_name="Test Market",
            total_pnl=1000,
            niches={"POLITICS": 0.9},
        )
        summary = t.to_summary_dict()
        assert summary["name"] == "Test Market"
        assert summary["platform"] == "kalshi"
        assert summary["niche"] == "POLITICS"


class TestNicheAgent:
    """Test niche classification (keyword path only — no LLM)."""

    @pytest.fixture
    def agent(self):
        return NicheAgent()

    def test_politics_keyword(self, agent):
        """'election' should classify as POLITICS."""
        t = TraderProfile(
            platform="kalshi",
            wallet_or_username="test",
            display_name="Will the election be contested?",
        )
        result = agent.map_niche(t)
        assert "POLITICS" in result.niches

    def test_sports_keyword(self, agent):
        """'nba' should classify as SPORTS/NBA."""
        t = TraderProfile(
            platform="kalshi",
            wallet_or_username="test",
            display_name="NBA Finals MVP prediction",
        )
        result = agent.map_niche(t)
        primary = max(result.niches, key=result.niches.get)
        assert "SPORTS" in primary

    def test_weather_keyword(self, agent):
        """'hurricane' should classify as WEATHER."""
        t = TraderProfile(
            platform="kalshi",
            wallet_or_username="test",
            display_name="Will a hurricane hit Florida?",
        )
        result = agent.map_niche(t)
        assert "WEATHER" in result.niches

    def test_general_fallback(self, agent):
        """Opaque username should default to GENERAL."""
        t = TraderProfile(
            platform="polymarket",
            wallet_or_username="0xabc123",
            display_name="xyzUser42",
        )
        result = agent.map_niche(t)
        assert "GENERAL" in result.niches

    def test_preserves_existing_niches(self, agent):
        """Should not overwrite pre-set niches from Kalshi ticker."""
        t = TraderProfile(
            platform="kalshi",
            wallet_or_username="test",
            display_name="Some market",
            niches={"SPORTS/MLB": 0.8},
        )
        result = agent.map_niche(t)
        assert "SPORTS/MLB" in result.niches


class TestMemoryManager:
    """Test the persistent memory system."""

    @pytest.fixture
    def memory(self, tmp_path):
        return MemoryManager(store_path=tmp_path / "test_memory.json")

    def test_save_and_search(self, memory):
        """Save a memory and find it by keyword."""
        memory.save_memory("Found profitable trader on polymarket", tags=["polymarket"])
        results = memory.search_memory("polymarket")
        assert len(results) >= 1
        assert "polymarket" in results[0]["content"].lower()

    def test_get_recent(self, memory):
        """Recent memories should be in reverse chronological order."""
        memory.save_memory("First memory")
        memory.save_memory("Second memory")
        memory.save_memory("Third memory")
        recent = memory.get_recent(2)
        assert len(recent) == 2
        assert "Third" in recent[0]["content"]

    def test_count(self, memory):
        """Count should reflect saved memories."""
        assert memory.count() == 0
        memory.save_memory("Test")
        assert memory.count() == 1

    def test_clear(self, memory):
        """Clear should remove all memories."""
        memory.save_memory("Test")
        memory.clear()
        assert memory.count() == 0


class TestSkillsManager:
    """Test the Hermes-inspired skills system."""

    @pytest.fixture
    def skills(self, tmp_path):
        return SkillsManager(skills_dir=tmp_path / "skills")

    def test_save_and_load(self, skills):
        """Save a skill and load it back."""
        skills.save_skill("test_skill", "When scoring traders, check PnL first.")
        content = skills.load_skill("test_skill")
        assert content is not None
        assert "PnL" in content

    def test_list_skills(self, skills):
        """Should list all saved skills."""
        skills.save_skill("skill_a", "Content A")
        skills.save_skill("skill_b", "Content B")
        skill_list = skills.list_skills()
        assert len(skill_list) == 2

    def test_find_relevant(self, skills):
        """Should find skills relevant to a query."""
        skills.save_skill(
            "polymarket_tip",
            "Polymarket traders with high volume are more reliable.",
            description="Polymarket analysis tip",
            tags=["polymarket", "volume"],
        )
        skills.save_skill(
            "kalshi_tip",
            "Kalshi weather markets have the most volume.",
            description="Kalshi weather insight",
            tags=["kalshi", "weather"],
        )
        results = skills.find_relevant_skills("polymarket volume")
        assert len(results) >= 1
        assert "Polymarket" in results[0]

    def test_delete_skill(self, skills):
        """Should delete a skill file."""
        skills.save_skill("temp_skill", "Temporary")
        assert skills.delete_skill("temp_skill")
        assert skills.load_skill("temp_skill") is None
