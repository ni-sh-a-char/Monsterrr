import logging
import asyncio
from ddgs import DDGS
import requests
from typing import List

class SearchService:
    def __init__(self, llm_client, logger=None):
        self.llm_client = llm_client
        self.logger = logger or logging.getLogger("search_service")

    async def search_and_summarize(self, query: str, num_results: int = 5) -> str:
        self.logger.info(f"[SearchService] Searching DuckDuckGo for: {query}")
        try:
            results = list(DDGS().text(query, max_results=num_results))
        except Exception as e:
            self.logger.error(f"DuckDuckGo search failed: {e}")
            return "Search failed. Please try again later."
        if not results:
            return "No results found."
        urls = []
        titles = []
        for r in results:
            url = r.get("href") or r.get("url")
            title = r.get("title") or url
            if url:
                urls.append(url)
                titles.append(title)
        if not urls:
            return "No results found."
        self.logger.info(f"[SearchService] Top URLs: {urls}")
        # Crawl URLs using requests (sync, in thread)
        extracted = []
        for url in urls:
            try:
                resp = await asyncio.to_thread(requests.get, url, timeout=10)
                if resp.status_code == 200:
                    # crude text extraction: just use the raw text
                    text = resp.text
                    if text:
                        extracted.append((url, text))
            except Exception as e:
                self.logger.warning(f"Crawl failed for {url}: {e}")
        if not extracted:
            return "Unable to retrieve content from search results."
        # Concatenate text for LLM
        # Truncate each source to 1500 chars, max 3 sources, and total text to 3500 chars for LLM
        max_sources = 3
        max_chars_per_source = 1500
        concat_text = "\n\n".join([
            f"Source: {titles[i]} ({url})\n{text[:max_chars_per_source]}" for i, (url, text) in enumerate(extracted[:max_sources])
        ])[:3500]
        prompt = (
            f"Summarize the following web search results for the query: '{query}'. "
            "Focus on the most important points. Use bullet points. Be concise.\n\n"
            f"{concat_text}"
        )
        try:
            summary = self.llm_client.groq_llm(prompt)
        except Exception as e:
            self.logger.error(f"LLM summarization failed: {e}")
            return "Search succeeded, but summarization failed."
        # Prepare sources list (truncate if needed)
        sources_md = "\n".join([
            f"{i+1}. [{titles[i]}]({urls[i]})" for i in range(min(len(extracted), max_sources))
        ])
        # Compose final message and ensure it's under 4000 chars
        result = f"**Search Results for:** {query}\n\n**Summary:**\n{summary}\n\n**Sources:**\n{sources_md}"
        if len(result) > 4000:
            # Truncate summary to fit
            allowed = 4000 - len(f"**Search Results for:** {query}\n\n**Summary:**\n\n\n**Sources:**\n{sources_md}")
            summary = summary[:max(0, allowed)]
            result = f"**Search Results for:** {query}\n\n**Summary:**\n{summary}\n\n**Sources:**\n{sources_md}"
        return result
