"""Learning Loop Agent — Hermes-inspired closed learning loop implementation.

Implements the core Hermes self-improvement cycle:
    Experience → Skill Extraction → Memory → Trust Updates → Self-Assessment
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import structlog

from agents.base_agent import BaseAgent
from models.trader import TraderProfile
from memory.memory_manager import MemoryManager
from memory.skills_manager import SkillsManager

logger = structlog.get_logger(__name__)

SYSTEM_PROMPT = """\
You are a self-improvement agent for a prediction market analysis system.
Your job is to:
1. Analyze completed pipeline runs and extract reusable lessons
2. Identify patterns in successful trader recommendations
3. Generate concise, actionable skills for future use
4. Assess what could be improved in the analysis

When extracting skills, write them as clear markdown instructions that
another agent could follow. Focus on concrete heuristics, not vague advice.

Be concise. Each skill should be under 100 words.
"""


class LearningLoopAgent(BaseAgent):
    """Closed learning loop agent — self-improving through experience.

    Implements Hermes' core learning cycle:

    1. **Experience Capture**: After each pipeline run, capture full context
    2. **Skill Extraction**: LLM analyzes outcomes and creates reusable skill files
    3. **Trust Score Updates**: Adjust trader trust scores based on observed accuracy
    4. **Memory Consolidation**: Summarize learnings into persistent knowledge
    5. **Self-Assessment**: Identify improvement opportunities

    Usage:
        agent = LearningLoopAgent()
        agent.process_run_outcome(traders, recommendation)
    """

    def __init__(self):
        super().__init__(name="learning_loop", system_prompt=SYSTEM_PROMPT)
        self.memory = MemoryManager()
        self.skills_mgr = SkillsManager()

    def process_run_outcome(
        self,
        traders: list[TraderProfile],
        recommendation: str,
        user_feedback: str | None = None,
    ) -> dict:
        """Process a completed pipeline run through the learning loop.

        Args:
            traders: The scored and ranked traders from the run.
            recommendation: The AI-generated recommendation text.
            user_feedback: Optional user feedback on the recommendation.

        Returns:
            Dict with learning loop results (skills extracted, memories saved).
        """
        self.logger.info("learning_loop_start", trader_count=len(traders))

        results = {
            "memories_saved": 0,
            "skills_extracted": [],
            "trust_updates": 0,
            "self_assessment": "",
        }

        # Step 1: Save run as memory
        run_summary = self._build_run_summary(traders, recommendation)
        self.memory.save_memory(
            content=run_summary,
            category="run_outcome",
            tags=["pipeline", "traders", "recommendation"],
            metadata={
                "trader_count": len(traders),
                "top_score": traders[0].composite_score if traders else 0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        results["memories_saved"] += 1

        # Step 2: Extract skills from successful patterns
        skills = self._extract_skills(traders, recommendation)
        results["skills_extracted"] = skills

        # Step 3: Update trust scores based on feedback
        if user_feedback:
            trust_updates = self._update_trust_scores(traders, user_feedback)
            results["trust_updates"] = trust_updates
            self.memory.save_memory(
                content=f"User feedback: {user_feedback}",
                category="feedback",
                tags=["user_feedback"],
            )
            results["memories_saved"] += 1

        # Step 4: Self-assessment
        assessment = self._self_assess(traders, recommendation)
        results["self_assessment"] = assessment
        self.memory.save_memory(
            content=assessment,
            category="self_assessment",
            tags=["improvement", "learning"],
        )
        results["memories_saved"] += 1

        self.logger.info(
            "learning_loop_done",
            memories=results["memories_saved"],
            skills=len(results["skills_extracted"]),
        )

        return results

    def consolidate_knowledge(self) -> str:
        """Periodic knowledge consolidation.

        Reviews all memories, identifies patterns, and creates
        consolidated skill files. This is the Hermes "nudge" mechanism.

        Returns:
            Consolidation summary.
        """
        self.logger.info("consolidation_start")

        # Get all memories
        all_memories = self.memory.get_all()
        if len(all_memories) < 3:
            return "Not enough memories to consolidate."

        # Get recent run outcomes
        outcomes = self.memory.get_recent(n=10, category="run_outcome")
        if not outcomes:
            return "No run outcomes to consolidate."

        # Build consolidation prompt
        outcomes_text = "\n".join(m["content"][:200] for m in outcomes)
        prompt = (
            "Review these recent prediction market analysis outcomes and extract "
            "the most important patterns and learnings:\n\n"
            f"{outcomes_text}\n\n"
            "Provide:\n"
            "1. Top 3 insights about trader selection\n"
            "2. Any repeating patterns in successful recommendations\n"
            "3. Areas where the analysis could improve"
        )

        try:
            consolidation = self.run(prompt)

            # Save consolidated knowledge as a skill
            self.skills_mgr.save_skill(
                name="consolidated_insights",
                content=consolidation,
                description="Auto-consolidated insights from recent pipeline runs",
                tags=["consolidation", "auto-generated"],
            )

            self.memory.save_memory(
                content=f"Knowledge consolidation completed: {consolidation[:200]}",
                category="consolidation",
                tags=["consolidation"],
            )

            return consolidation
        except Exception as e:
            self.logger.warning("consolidation_failed", error=str(e))
            return f"Consolidation failed: {e}"

    def _build_run_summary(self, traders: list[TraderProfile], recommendation: str) -> str:
        """Build a text summary of a pipeline run."""
        top_traders = traders[:5]
        trader_lines = []
        for t in top_traders:
            niche = max(t.niches, key=t.niches.get) if t.niches else "GENERAL"
            trader_lines.append(
                f"  - {t.display_name or t.wallet_or_username} "
                f"({t.platform}) | Score: {t.composite_score} | "
                f"Niche: {niche} | PnL: ${t.total_pnl:,.0f}"
            )

        return (
            f"Pipeline run at {datetime.now(timezone.utc).isoformat()}\n"
            f"Total traders analyzed: {len(traders)}\n"
            f"Top 5 traders:\n" + "\n".join(trader_lines) + "\n"
            f"Recommendation excerpt: {recommendation[:300]}"
        )

    def _extract_skills(self, traders: list[TraderProfile], recommendation: str) -> list[str]:
        """Extract reusable skills from a pipeline run.

        Uses heuristic-based extraction by default to preserve LLM rate limits.
        Attempts LLM extraction as a bonus if available.
        """
        if not traders:
            return []

        top = traders[0]
        niche = max(top.niches, key=top.niches.get) if top.niches else "GENERAL"

        # Heuristic-based skill (always works, no LLM needed)
        skill_name = f"insight_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}"

        if top.total_pnl > 100000:
            heuristic = (
                f"When analyzing {top.platform} traders, prioritize those with "
                f"PnL > ${top.total_pnl:,.0f} and volume > ${top.total_volume:,.0f}. "
                f"These high-value traders tend to score well (score: {top.composite_score}/100)."
            )
        elif top.computed_win_rate > 0.6 and top.num_trades > 10:
            heuristic = (
                f"Traders with win rate > {top.computed_win_rate:.0%} across {top.num_trades}+ "
                f"trades are strong copy-trade candidates on {top.platform}."
            )
        else:
            heuristic = (
                f"Top trader in this run: {top.display_name or top.wallet_or_username} "
                f"({top.platform}) scored {top.composite_score}/100 in the {niche} niche. "
                f"PnL: ${top.total_pnl:,.0f}, Volume: ${top.total_volume:,.0f}."
            )

        self.skills_mgr.save_skill(
            name=skill_name,
            content=heuristic,
            description=f"Auto-extracted from pipeline run analyzing {len(traders)} traders",
            tags=["auto-extracted", top.platform, niche.lower()],
        )
        return [skill_name]

    def _update_trust_scores(self, traders: list[TraderProfile], feedback: str) -> int:
        """Update trust scores based on user feedback.

        Simple heuristic: positive feedback increases trust for top traders,
        negative feedback decreases it.
        """
        feedback_lower = feedback.lower()
        is_positive = any(w in feedback_lower for w in ["good", "great", "correct", "yes", "accurate", "helpful"])
        is_negative = any(w in feedback_lower for w in ["bad", "wrong", "incorrect", "no", "poor", "useless"])

        updates = 0
        for t in traders[:3]:  # Top 3 traders affected
            if is_positive:
                t.trust_score = min(100, t.trust_score + 5)
                updates += 1
            elif is_negative:
                t.trust_score = max(0, t.trust_score - 5)
                updates += 1

        if updates:
            self.logger.info("trust_scores_updated", count=updates, direction="up" if is_positive else "down")

        return updates

    def _self_assess(self, traders: list[TraderProfile], recommendation: str) -> str:
        """Self-assess the current run and identify improvements."""
        issues = []

        # Check for data quality issues
        zero_trade_count = sum(1 for t in traders if t.num_trades == 0)
        if zero_trade_count > len(traders) * 0.5:
            issues.append(
                f"Data quality: {zero_trade_count}/{len(traders)} traders have no trade count data. "
                "Scoring relies on volume/PnL proxies instead of actual win rates."
            )

        all_general = all(
            "GENERAL" in t.niches for t in traders if t.niches
        )
        if all_general:
            issues.append(
                "Niche classification: All traders classified as GENERAL. "
                "Need better market title data or LLM classification."
            )

        kalshi_count = sum(1 for t in traders if t.platform == "kalshi")
        polymarket_count = sum(1 for t in traders if t.platform == "polymarket")
        if kalshi_count == 0:
            issues.append("No Kalshi data retrieved — API may have failed.")
        if polymarket_count == 0:
            issues.append("No Polymarket data retrieved — API may have failed.")

        if not issues:
            return "Run completed successfully with no notable issues."

        return "Self-assessment:\n" + "\n".join(f"- {issue}" for issue in issues)
