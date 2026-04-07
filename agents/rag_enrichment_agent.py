"""RAG Enrichment Agent — uses Apify to scrape event context for analysis."""

from __future__ import annotations

import structlog

from agents.base_agent import BaseAgent
from rag.context_store import ContextStore
from tools.apify_scraper import ApifyScraper

logger = structlog.get_logger(__name__)

SYSTEM_PROMPT = """\
You are a research synthesis agent for prediction markets. Your job is to:
- Analyze scraped web content about prediction market events
- Extract key facts, probabilities, and expert opinions
- Summarize the information concisely for trader analysis
- Identify factors that could affect market outcomes

Be factual. Cite sources when possible. Keep summaries under 200 words.
"""


class RAGEnrichmentAgent(BaseAgent):
    """Agent that enriches prediction market events with web-scraped context.

    Uses Apify to scrape relevant news articles and analysis,
    stores them in the RAG context store, and provides
    summarized context to other agents.

    Usage:
        agent = RAGEnrichmentAgent()
        context = agent.enrich_event("Will Trump win 2024 election?")
    """

    def __init__(self):
        super().__init__(name="rag_enrichment_agent", system_prompt=SYSTEM_PROMPT)
        self.scraper = ApifyScraper()
        self.context_store = ContextStore()

    def enrich_event(self, event_title: str) -> str:
        """Research and enrich a prediction market event.

        Args:
            event_title: The market/event title to research.

        Returns:
            Summarized context string from scraped sources.
        """
        self.logger.info("enrich_event_start", event_title=event_title[:60])

        # Check if we already have context cached
        existing = self.context_store.get_context(event_title)
        if existing:
            self.logger.info("enrich_cache_hit", event_title=event_title[:40], entries=len(existing))
            summary = self.context_store.get_summary(event_title)
            return self._summarize_with_llm(event_title, summary)

        # Scrape new context via Apify
        if not self.scraper.is_available:
            self.logger.warning("enrich_no_apify")
            return self._fallback_context(event_title)

        scraped = self.scraper.scrape_prediction_market_context(event_title)

        if not scraped:
            self.logger.warning("enrich_no_results", event_title=event_title[:40])
            return self._fallback_context(event_title)

        # Store scraped content in context store
        for item in scraped:
            self.context_store.add_context(
                topic=event_title,
                content=item.get("text", item.get("description", "")),
                source_url=item.get("url", ""),
                tags=["prediction_market", "enrichment"],
            )

        # Summarize with LLM
        summary = self.context_store.get_summary(event_title)
        return self._summarize_with_llm(event_title, summary)

    def enrich_batch(self, event_titles: list[str], max_events: int = 3) -> dict[str, str]:
        """Enrich multiple events at once.

        Args:
            event_titles: List of event titles to research.
            max_events: Max events to actually scrape (for rate limiting).

        Returns:
            Dict mapping event title to enriched context summary.
        """
        results = {}
        for title in event_titles[:max_events]:
            try:
                results[title] = self.enrich_event(title)
            except Exception as e:
                self.logger.error("enrich_batch_item_failed", event_title=title[:40], error=str(e))
                results[title] = self._fallback_context(title)
        return results

    def _summarize_with_llm(self, event_title: str, raw_context: str) -> str:
        """Use LLM to summarize scraped context."""
        if not raw_context.strip():
            return self._fallback_context(event_title)

        prompt = (
            f"Summarize the following research about the prediction market event: "
            f"\"{event_title}\"\n\n"
            f"Raw research data:\n{raw_context[:3000]}\n\n"
            f"Provide a concise analysis covering:\n"
            f"1. Key facts about the event\n"
            f"2. Current market sentiment (if available)\n"
            f"3. Factors that could influence the outcome\n"
            f"4. Any risks or uncertainties"
        )

        try:
            return self.run(prompt)
        except Exception as e:
            self.logger.warning("enrich_llm_failed", error=str(e))
            return raw_context[:500]

    def _fallback_context(self, event_title: str) -> str:
        """Return basic context when scraping is unavailable."""
        return (
            f"Event: {event_title}\n"
            f"Note: Detailed context unavailable (Apify scraping not configured or no results found). "
            f"Analysis based on available market data only."
        )
