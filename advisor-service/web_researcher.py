"""
Web Researcher — Search latest trends using DuckDuckGo
"""
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class WebResearcher:
    def __init__(self):
        """Initialize web researcher (DuckDuckGo search)."""
        try:
            from duckduckgo_search import DDGS
            self.ddgs = DDGS()
            self.enabled = True
            logger.info("✓ Web researcher enabled (DuckDuckGo)")
        except ImportError:
            logger.warning("duckduckgo-search not installed, web research disabled")
            self.ddgs = None
            self.enabled = False

    def search_trends(
        self, keywords: List[str], max_results: int = 3
    ) -> Optional[str]:
        """
        Search latest trends for given keywords.
        Returns summary text or None if disabled.
        """
        if not self.enabled:
            return None

        if not keywords:
            return None

        results_text = []

        for keyword in keywords[:3]:  # Limit to 3 keywords
            try:
                # Search news
                search_results = self.ddgs.news(
                    keywords=keyword,
                    max_results=max_results,
                )

                if search_results:
                    results_text.append(f"\n### '{keyword}' 최신 뉴스:")
                    for item in search_results:
                        title = item.get("title", "")
                        snippet = item.get("body", "")[:150]
                        source = item.get("source", "")
                        results_text.append(f"- [{source}] {title}\n  {snippet}")

            except Exception as e:
                logger.warning(f"Search failed for '{keyword}': {e}")
                continue

        if results_text:
            return "\n".join(results_text)
        return None

    def search_text(self, query: str, max_results: int = 5) -> Optional[str]:
        """General text search."""
        if not self.enabled:
            return None

        try:
            results = self.ddgs.text(keywords=query, max_results=max_results)
            if results:
                lines = [f"\n### 검색 결과: '{query}'"]
                for item in results:
                    title = item.get("title", "")
                    snippet = item.get("body", "")[:150]
                    lines.append(f"- {title}\n  {snippet}")
                return "\n".join(lines)
        except Exception as e:
            logger.warning(f"Text search failed: {e}")

        return None
