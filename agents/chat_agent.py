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

        Uses keyword matching (specific → generic priority) and trader data
        to answer common questions without any LLM call.
        """
        msg = message.lower()

        # ── 1. SPECIFIC patterns first (these contain words like "best" too) ──

        # Risk / reward / safe
        if any(kw in msg for kw in ["risk", "reward", "safe", "conservative", "stable", "ratio"]):
            by_ratio = sorted(traders, key=lambda t: t.total_pnl / max(t.total_volume, 1), reverse=True)
            top3 = by_ratio[:3]
            lines = ["📊 **Risk/Reward Analysis** (data-driven fallback):\n"]
            for i, t in enumerate(top3, 1):
                ratio = t.total_pnl / max(t.total_volume, 1)
                name = t.display_name or t.wallet_or_username
                lines.append(f"  {i}. **{name}** — ratio: {ratio:.2%}, PnL: ${t.total_pnl:,.0f}")
            lines.append(f"\n💡 Higher PnL/Volume ratio = better capital efficiency.")
            return "\n".join(lines)

        # Strategy / how / approach
        if any(kw in msg for kw in ["strategy", "strateg", "approach", "how to", "method", "copy"]):
            best = traders[0]
            return (
                f"📊 **Trading Strategy Analysis** (data-driven fallback):\n\n"
                f"Based on the top traders analyzed:\n"
                f"  • **Copy top-scorers**: {best.display_name} leads with {best.composite_score:.1f}/100\n"
                f"  • **Diversify platforms**: Mix Polymarket traders + Kalshi markets\n"
                f"  • **Track volume**: Higher volume = more liquid, safer to follow\n"
                f"  • **Watch win rate**: Target traders with >50% win rate\n"
                f"  • **Size positions**: Start small, scale based on performance\n\n"
                f"🏆 Top trader to copy: **{best.display_name}** "
                f"(${best.total_pnl:,.0f} PnL, {best.platform.title()})"
            )

        # Compare / vs / difference
        if any(kw in msg for kw in ["compare", "vs", "versus", "difference", "between"]):
            if len(traders) >= 2:
                t1, t2 = traders[0], traders[1]
                return (
                    f"📊 **Head-to-Head Comparison** (data-driven fallback):\n\n"
                    f"| Metric | {t1.display_name or t1.wallet_or_username} | "
                    f"{t2.display_name or t2.wallet_or_username} |\n"
                    f"|--------|--------|--------|\n"
                    f"| Score | {t1.composite_score:.1f} | {t2.composite_score:.1f} |\n"
                    f"| PnL | ${t1.total_pnl:,.0f} | ${t2.total_pnl:,.0f} |\n"
                    f"| Volume | ${t1.total_volume:,.0f} | ${t2.total_volume:,.0f} |\n"
                    f"| Platform | {t1.platform.title()} | {t2.platform.title()} |\n"
                    f"| Trades | {t1.num_trades} | {t2.num_trades} |"
                )

        # Platform-specific
        if any(kw in msg for kw in ["kalshi", "polymarket", "platform"]):
            poly = [t for t in traders if t.platform == "polymarket"]
            kal = [t for t in traders if t.platform == "kalshi"]
            poly_avg = sum(t.composite_score for t in poly) / max(len(poly), 1)
            kal_avg = sum(t.composite_score for t in kal) / max(len(kal), 1)
            return (
                f"📊 **Platform Breakdown** (data-driven fallback):\n\n"
                f"**Polymarket** — {len(poly)} traders, avg score: {poly_avg:.1f}\n"
                f"  Top: {poly[0].display_name if poly else 'N/A'} "
                f"(${poly[0].total_pnl:,.0f} PnL)\n\n" if poly else ""
                f"**Kalshi** — {len(kal)} markets, avg score: {kal_avg:.1f}\n"
                f"  Top: {kal[0].display_name if kal else 'N/A'} "
                f"(${kal[0].total_pnl:,.0f} PnL)" if kal else ""
            )

        # Niche / category / sector
        if any(kw in msg for kw in ["niche", "category", "sector", "politics", "sports", "crypto", "weather"]):
            niche_counts: dict[str, list] = {}
            for t in traders:
                niche = max(t.niches, key=t.niches.get) if t.niches else "GENERAL"
                niche_counts.setdefault(niche, []).append(t)
            lines = ["📊 **Niche Breakdown** (data-driven fallback):\n"]
            for niche, ts in sorted(niche_counts.items(), key=lambda x: -len(x[1])):
                best = max(ts, key=lambda t: t.composite_score)
                lines.append(
                    f"  • **{niche}**: {len(ts)} entries, "
                    f"best: {best.display_name} ({best.composite_score:.1f})"
                )
            return "\n".join(lines)

        # Volume / liquidity / active
        if any(kw in msg for kw in ["volume", "liquid", "active", "most traded"]):
            by_vol = sorted(traders, key=lambda t: t.total_volume, reverse=True)[:5]
            lines = ["📊 **Most Active by Volume** (data-driven fallback):\n"]
            for i, t in enumerate(by_vol, 1):
                name = t.display_name or t.wallet_or_username
                lines.append(f"  {i}. **{name}** — ${t.total_volume:,.0f} ({t.platform.title()})")
            return "\n".join(lines)

        # PnL / profit / earnings
        if any(kw in msg for kw in ["pnl", "profit", "earn", "money", "income"]):
            by_pnl = sorted(traders, key=lambda t: t.total_pnl, reverse=True)[:5]
            lines = ["📊 **Top Earners by PnL** (data-driven fallback):\n"]
            for i, t in enumerate(by_pnl, 1):
                name = t.display_name or t.wallet_or_username
                lines.append(f"  {i}. **{name}** — ${t.total_pnl:,.0f} ({t.platform.title()})")
            return "\n".join(lines)

        # Score / rank / list
        if any(kw in msg for kw in ["score", "rank", "list", "all", "show"]):
            top5 = traders[:5]
            lines = ["📊 **Top 5 Ranked** (data-driven fallback):\n"]
            for i, t in enumerate(top5, 1):
                name = t.display_name or t.wallet_or_username
                lines.append(
                    f"  {i}. **{name}** — Score: {t.composite_score:.1f}, "
                    f"PnL: ${t.total_pnl:,.0f} ({t.platform.title()})"
                )
            return "\n".join(lines)

        # ── 2. GENERIC patterns (catch-all for "best", "top", "who", etc.) ──

        if any(kw in msg for kw in ["best", "top", "recommend", "who", "which", "performance"]):
            top3 = traders[:3]
            lines = ["📊 **Top Recommendations** (data-driven fallback):\n"]
            for i, t in enumerate(top3, 1):
                name = t.display_name or t.wallet_or_username
                lines.append(
                    f"  {i}. 🏆 **{name}** — Score: {t.composite_score:.1f}/100, "
                    f"PnL: ${t.total_pnl:,.0f} ({t.platform.title()})"
                )
            lines.append(f"\n💡 Ask about: risk analysis, strategy, comparisons, "
                        f"platforms, niches, or volume.")
            return "\n".join(lines)

        # ── 3. DEFAULT — always useful ──

        top5 = traders[:5]
        poly_count = sum(1 for t in traders if t.platform == "polymarket")
        kal_count = sum(1 for t in traders if t.platform == "kalshi")
        lines = [
            f"📊 **Data Summary** (LLM unavailable — {len(traders)} entries analyzed):\n",
            f"  Platforms: {poly_count} Polymarket traders, {kal_count} Kalshi markets\n",
        ]
        for i, t in enumerate(top5, 1):
            name = t.display_name or t.wallet_or_username
            lines.append(
                f"  {i}. **{name}** — {t.composite_score:.1f}/100, "
                f"${t.total_pnl:,.0f} PnL ({t.platform.title()})"
            )
        lines.append(f"\n💡 Try asking about: risk/reward, strategy, compare traders, "
                    f"platforms, niches, volume, profits, or rankings.")
        return "\n".join(lines)
