"""
Idea Generator Agent for Monsterrr.
"""


import requests
import json
import os
from typing import List, Dict, Any
from datetime import datetime

class IdeaGeneratorAgent:
    """
    Agent for discovering and ranking new open-source project ideas.
    Fetches from GitHub Trending, Dev.to, HackerNews, summarizes/ranks with Groq, and stores results.
    """
    IDEA_FILE = "monsterrr_state.json"

    def __init__(self, groq_client, logger):
        self.groq_client = groq_client
        self.logger = logger

    def fetch_trending_github(self) -> List[Dict[str, Any]]:
        """Fetch trending repos from GitHub Trending (via scraping)."""
        url = "https://ghapi.huchen.dev/repositories"
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            self.logger.error(f"[IdeaGeneratorAgent] GitHub trending fetch error: {e}")
            return []

    def fetch_trending_hackernews(self) -> List[Dict[str, Any]]:
        """Fetch top stories from Hacker News API."""
        try:
            top_ids = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=10).json()[:20]
            stories = []
            for sid in top_ids:
                item = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json", timeout=5).json()
                if item and 'title' in item:
                    stories.append(item)
            return stories
        except Exception as e:
            self.logger.error(f"[IdeaGeneratorAgent] HackerNews fetch error: {e}")
            return []

    def fetch_trending_devto(self) -> List[Dict[str, Any]]:
        """Fetch top articles from Dev.to API."""
        try:
            resp = requests.get("https://dev.to/api/articles?top=1&per_page=10", timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            self.logger.error(f"[IdeaGeneratorAgent] Dev.to fetch error: {e}")
            return []

    def fetch_and_rank_ideas(self, top_n: int = 5) -> List[Dict[str, Any]]:
        """
        Fetch trending ideas, summarize and rank with Groq, and store top N in monsterrr_state.json.
        Returns:
            List of top N idea dicts with metadata.
        """
        self.logger.info("[IdeaGeneratorAgent] Fetching trending ideas from sources.")
        github = self.fetch_trending_github()
        hn = self.fetch_trending_hackernews()
        devto = self.fetch_trending_devto()
        all_ideas = github + hn + devto
        prompt = (
            "Given the following trending open-source project ideas, summarize, filter for uniqueness and impact, "
            "and rank the top {n} ideas. For each, provide: name, description, tech stack, difficulty (easy/med/hard), "
            "estimated dev time (weeks), and a 3-5 bullet roadmap. Output as JSON list.\n\n"
            f"Ideas: {json.dumps(all_ideas)[:4000]}"
        )
        try:
            groq_response = self.groq_client.groq_llm(prompt, model="mixtral-8x7b")
            ideas = json.loads(groq_response)
            self.logger.info(f"[IdeaGeneratorAgent] Got {len(ideas)} ranked ideas from Groq.")
        except Exception as e:
            self.logger.error(f"[IdeaGeneratorAgent] Groq summarization error: {e}")
            ideas = []
        # Store in monsterrr_state.json
        state = self._load_state()
        state['ideas'] = {
            'generated_at': datetime.utcnow().isoformat(),
            'top_ideas': ideas[:top_n]
        }
        self._save_state(state)
        return ideas[:top_n]

    def _load_state(self) -> Dict[str, Any]:
        if os.path.exists(self.IDEA_FILE):
            with open(self.IDEA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _save_state(self, state: Dict[str, Any]):
        with open(self.IDEA_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2)

if __name__ == "__main__":
    import logging
    from services.groq_service import GroqService
    from utils.logger import setup_logger
    logger = setup_logger()
    groq = GroqService(api_key=os.getenv("GROQ_API_KEY"), logger=logger)
    agent = IdeaGeneratorAgent(groq, logger)
    ideas = agent.fetch_and_rank_ideas()
    print(json.dumps(ideas, indent=2))
