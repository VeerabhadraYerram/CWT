"""Chat Agent — turns scored trader data into natural language recommendations."""

from __future__ import annotations

from agents.base_agent import BaseAgent
from models.trader import TraderProfile
from scoring.scorer import TraderScorer

SYSTEM_PROMPT = """\
You are a prediction market analyst. Your job is to explain trader recommendations clearly and concisely.

Rules:
- Always back claims with data (score, win rate, trade count, PnL).
- Use the structured trader data provided — do not invent numbers.
- Be direct: name your top pick and explain why.
- Mention risks (low trade count, inactivity, concentration).
- If RAG context is available, incorporate it into your analysis.
- Keep responses under 300 words.
"""


class ChatAgent(BaseAgent):
    """Conversational agent that synthesizes trader data into recommendations.

    Integrates with:
    - Scoring engine for detailed breakdowns
    - Skills system for learned heuristics
    - Memory system for contextual awareness
    - RAG context for event enrichment

    Usage:
        agent = ChatAgent()
        reply = agent.recommend_traders("best NBA traders?", scored_traders)
    """

    def __init__(self):
        super().__init__(name="chat_agent", system_prompt=SYSTEM_PROMPT)
        self.scorer = TraderScorer()

    def recommend_traders(
        self,
        query: str,
        traders: list[TraderProfile],
        top_n: int = 5,
        rag_context: str = "",
    ) -> str:
        """Generate a natural language recommendation from scored traders.

        Args:
            query: The user's original question.
            traders: Scored and ranked TraderProfile list.
            top_n: How many traders to include in the recommendation.
            rag_context: Optional RAG-enriched context about relevant events.

        Returns:
            LLM-generated recommendation text.
        """
        top = traders[:top_n]

        if not top:
            return "No traders found matching your criteria."

        # Build structured context for the LLM
        context = self._build_context(top)

        prompt = (
            f"User question: {query}\n\n"
            f"Here are the top {len(top)} traders (already scored and ranked):\n\n"
            f"{context}\n\n"
        )

        if rag_context:
            prompt += (
                "--- MARKET RESEARCH CONTEXT ---\n"
                f"{rag_context[:1500]}\n"
                "--- END CONTEXT ---\n\n"
            )

        prompt += (
            "The first trader is the highest ranked — prioritize them in your recommendation.\n\n"
            "Based on this data, recommend the best traders to copy-trade. "
            "Explain your reasoning using the numbers provided."
        )

        try:
            response = self.run(prompt)

            # Save notable recommendation to memory
            self.remember(
                f"Recommended {top[0].display_name or top[0].wallet_or_username} "
                f"(score: {top[0].composite_score}) for query: {query[:50]}",
                category="recommendation",
                tags=["recommendation", top[0].platform],
            )

            return response

        except Exception:
            top_trader = top[0]

            return (
                f"🏆 **{top_trader.display_name or top_trader.wallet_or_username}** "
                f"is the top-ranked trader to copy.\n\n"
                f"📊 Score: {top_trader.composite_score}/100\n"
                f"💰 PnL: ${top_trader.total_pnl:,.2f}\n"
                f"📈 Volume: ${top_trader.total_volume:,.2f}\n"
                f"🏷️ Platform: {top_trader.platform.title()}\n\n"
                f"They stand out due to strong profitability and high trading "
                f"activity compared to {len(traders)} other traders analyzed."
            )

    def chat(self, message: str, traders: list[TraderProfile] | None = None) -> str:
        """Interactive chat — answer follow-up questions about traders.

        Args:
            message: User's chat message.
            traders: Optional trader data for context.

        Returns:
            Agent's response (LLM-generated or data-driven fallback).
        """
        try:
            if traders:
                context = self._build_context(traders[:3])
                augmented = (
                    f"Current trader data for reference:\n{context}\n\n"
                    f"User says: {message}"
                )
                return self.run(augmented)

            return self.run(message)

        except Exception:
            # Data-driven fallback — always available, never crashes
            if not traders:
                return (
                    "⚠️ LLM models are currently rate-limited and no trader data is loaded.\n"
                    "Please try again in a few minutes, or re-run the pipeline."
                )

            return self._fallback_chat(message, traders)

    def _build_context(self, traders: list[TraderProfile]) -> str:
        """Format trader data into a readable text block for the LLM."""
        lines = []
        for i, t in enumerate(traders, 1):
            breakdown = self.scorer.breakdown(t)
            niches_str = ", ".join(
                f"{k} ({v:.0%})" for k, v in t.niches.items()
            ) if t.niches else "GENERAL"

            lines.append(
                f"#{i} — {t.display_name or t.wallet_or_username}\n"
                f"  Platform:        {t.platform}\n"
                f"  Composite Score: {t.composite_score}/100\n"
                f"  Win Rate:        {t.computed_win_rate:.1%} ({t.num_trades} trades)\n"
                f"  Avg ROI/Trade:   {t.avg_roi_per_trade:.1%}\n"
                f"  Total PnL:       ${t.total_pnl:,.2f}\n"
                f"  Volume:          ${t.total_volume:,.2f}\n"
                f"  Active Positions:{t.active_positions}\n"
                f"  Niches:          {niches_str}\n"
                f"  Trust Score:     {t.trust_score}/100\n"
                f"  Score Breakdown:\n"
                f"    Win Rate:   norm={breakdown['win_rate']['normalized']:.3f}\n"
                f"    ROI:        norm={breakdown['roi']['normalized']:.3f}\n"
                f"    Frequency:  norm={breakdown['frequency']['normalized']:.3f}\n"
                f"    Recency:    norm={breakdown['recency']['normalized']:.3f}\n"
                f"    Volatility: norm={breakdown['volatility']['normalized']:.3f}\n"
            )

        return "\n".join(lines)

    def _fallback_chat(self, message: str, traders: list[TraderProfile]) -> str:
        """Generate a data-driven response when LLMs are unavailable.

        Uses keyword matching and trader data to answer common questions
        without requiring any LLM call.
        """
        msg_lower = message.lower()
        top = traders[:5]

        # Best / top / recommended
        if any(kw in msg_lower for kw in ["best", "top", "recommend", "which", "who", "performance"]):
            best = traders[0]
            lines = [
                f"📊 **Based on data analysis** (LLM currently unavailable):\n",
                f"🏆 **{best.display_name or best.wallet_or_username}** is the top trader.\n",
                f"  • Score: {best.composite_score:.1f}/100",
                f"  • PnL: ${best.total_pnl:,.0f}",
                f"  • Volume: ${best.total_volume:,.0f}",
                f"  • Platform: {best.platform.title()}",
            ]
            if best.computed_win_rate > 0:
                lines.append(f"  • Win Rate: {best.computed_win_rate:.0%}")
            return "\n".join(lines)

        # Risk / safe / conservative
        if any(kw in msg_lower for kw in ["risk", "safe", "conservative", "stable"]):
            # Find trader with best PnL-to-volume ratio (lower leverage = less risky)
            by_ratio = sorted(traders, key=lambda t: t.total_pnl / max(t.total_volume, 1), reverse=True)
            safest = by_ratio[0]
            return (
                f"📊 **Risk analysis** (LLM currently unavailable):\n\n"
                f"🛡️ **{safest.display_name or safest.wallet_or_username}** has the best "
                f"risk/reward ratio.\n"
                f"  • PnL/Volume ratio: {safest.total_pnl / max(safest.total_volume, 1):.2%}\n"
                f"  • PnL: ${safest.total_pnl:,.0f}\n"
                f"  • Platform: {safest.platform.title()}"
            )

        # Compare / vs / difference
        if any(kw in msg_lower for kw in ["compare", "vs", "difference", "versus"]):
            if len(traders) >= 2:
                t1, t2 = traders[0], traders[1]
                return (
                    f"📊 **Comparison** (LLM currently unavailable):\n\n"
                    f"| Metric | {t1.display_name or t1.wallet_or_username} | "
                    f"{t2.display_name or t2.wallet_or_username} |\n"
                    f"|--------|--------|--------|\n"
                    f"| Score | {t1.composite_score:.1f} | {t2.composite_score:.1f} |\n"
                    f"| PnL | ${t1.total_pnl:,.0f} | ${t2.total_pnl:,.0f} |\n"
                    f"| Volume | ${t1.total_volume:,.0f} | ${t2.total_volume:,.0f} |\n"
                    f"| Platform | {t1.platform} | {t2.platform} |"
                )

        # Kalshi / platform
        if any(kw in msg_lower for kw in ["kalshi", "polymarket", "platform"]):
            poly = [t for t in traders if t.platform == "polymarket"]
            kal = [t for t in traders if t.platform == "kalshi"]
            return (
                f"📊 **Platform breakdown** (LLM currently unavailable):\n\n"
                f"• Polymarket: {len(poly)} traders, "
                f"avg score {sum(t.composite_score for t in poly) / max(len(poly), 1):.1f}\n"
                f"• Kalshi: {len(kal)} events, "
                f"avg score {sum(t.composite_score for t in kal) / max(len(kal), 1):.1f}\n\n"
                f"Top Polymarket: {poly[0].display_name if poly else 'N/A'}\n"
                f"Top Kalshi: {kal[0].display_name if kal else 'N/A'}"
            )

        # Default: show summary
        return (
            f"📊 **Summary** (LLM currently unavailable — using data fallback):\n\n"
            f"Analyzed {len(traders)} traders across Polymarket and Kalshi.\n"
            f"Top trader: **{traders[0].display_name or traders[0].wallet_or_username}** "
            f"(score: {traders[0].composite_score:.1f}/100, "
            f"PnL: ${traders[0].total_pnl:,.0f})\n\n"
            f"Try asking about: best traders, risk analysis, platform comparison, "
            f"or specific trader names."
        )
