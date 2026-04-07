"""Apify web scraper tool — scrapes URLs and search results for RAG enrichment."""

from __future__ import annotations

import structlog
from apify_client import ApifyClient

from config.settings import settings

logger = structlog.get_logger(__name__)


class ApifyScraper:
    """Apify-powered web scraper for enriching prediction market analysis.

    Uses Apify actors to:
    - Scrape web pages for event context
    - Search the web for relevant articles

    Requires APIFY_API_TOKEN in environment.
    """

    def __init__(self):
        token = settings.APIFY_API_TOKEN
        if not token:
            logger.warning("apify_no_token", msg="APIFY_API_TOKEN not set — scraping disabled")
            self._client = None
        else:
            self._client = ApifyClient(token)

    @property
    def is_available(self) -> bool:
        """Check if Apify client is configured."""
        return self._client is not None

    def scrape_urls(self, urls: list[str], max_pages: int = 5) -> list[dict]:
        """Scrape content from a list of URLs using Apify's Web Scraper.

        Args:
            urls: List of URLs to scrape.
            max_pages: Max pages to scrape per URL.

        Returns:
            List of dicts with 'url', 'title', 'text' keys.
        """
        if not self.is_available:
            logger.warning("apify_unavailable", action="scrape_urls")
            return []

        logger.info("apify_scrape_urls", count=len(urls))

        try:
            run_input = {
                "startUrls": [{"url": url} for url in urls[:max_pages]],
                "maxPagesPerCrawl": max_pages,
                "pageFunction": """
                    async function pageFunction(context) {
                        const { page, request } = context;
                        const title = await page.title();
                        const text = await page.evaluate(() => {
                            const el = document.querySelector('article') || document.querySelector('main') || document.body;
                            return el ? el.innerText.substring(0, 3000) : '';
                        });
                        return { url: request.url, title, text };
                    }
                """,
            }

            run = self._client.actor("apify/web-scraper").call(run_input=run_input)
            items = list(self._client.dataset(run["defaultDatasetId"]).iterate_items())

            logger.info("apify_scrape_done", results=len(items))
            return items

        except Exception as e:
            logger.error("apify_scrape_failed", error=str(e))
            return []

    def search_web(self, query: str, max_results: int = 5) -> list[dict]:
        """Search the web using Apify's Google Search Scraper.

        Args:
            query: Search query string.
            max_results: Max results to return.

        Returns:
            List of dicts with 'title', 'url', 'description' keys.
        """
        if not self.is_available:
            logger.warning("apify_unavailable", action="search_web")
            return []

        logger.info("apify_search", query=query[:80])

        try:
            run_input = {
                "queries": query,
                "maxPagesPerQuery": 1,
                "resultsPerPage": max_results,
            }

            run = self._client.actor("apify/google-search-scraper").call(run_input=run_input)
            items = list(self._client.dataset(run["defaultDatasetId"]).iterate_items())

            results = []
            for item in items:
                organic = item.get("organicResults", [])
                for r in organic[:max_results]:
                    results.append({
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "description": r.get("description", ""),
                    })

            logger.info("apify_search_done", results=len(results))
            return results

        except Exception as e:
            logger.error("apify_search_failed", error=str(e))
            return []

    def scrape_prediction_market_context(self, event_title: str) -> list[dict]:
        """Convenience method: search and scrape context for a prediction market event.

        Args:
            event_title: The event/market title to research.

        Returns:
            List of scraped content dicts.
        """
        logger.info("apify_enrich_event", event=event_title[:60])

        # Step 1: Search for relevant articles
        search_results = self.search_web(
            f"{event_title} prediction market analysis",
            max_results=3,
        )

        if not search_results:
            return []

        # Step 2: Scrape the top URLs
        urls = [r["url"] for r in search_results if r.get("url")]
        if not urls:
            return search_results  # Return search snippets if no URLs

        scraped = self.scrape_urls(urls, max_pages=3)
        return scraped if scraped else search_results
