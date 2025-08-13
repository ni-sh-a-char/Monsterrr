"""
Idea Generator Agent for Monsterrr.
"""


import requests
import json
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import time
from typing import List, Dict, Any
from datetime import datetime

class IdeaGeneratorAgent:
    def fetch_trending_producthunt(self) -> list:
        """Fetch trending products from Product Hunt (HTML scrape)."""
        try:
            import requests
            from bs4 import BeautifulSoup
            resp = requests.get("https://www.producthunt.com/", timeout=10)
            bs = BeautifulSoup(resp.text, "html.parser")
            products = []
            for post in bs.select("ul[class*='postsList_'] li"):
                name = post.select_one("h3")
                desc = post.select_one("p")
                if name:
                    products.append({
                        "name": name.text.strip(),
                        "description": desc.text.strip() if desc else ""
                    })
            return products
        except Exception as e:
            self.logger.error(f"[IdeaGeneratorAgent] Product Hunt fetch error: {e}")
            return []

    def fetch_trending_reddit(self, subreddit="MachineLearning") -> list:
        """Fetch top posts from Reddit (subreddit, week)."""
        try:
            import requests
            url = f"https://www.reddit.com/r/{subreddit}/top/.json?limit=10&t=week"
            headers = {"User-Agent": "MonsterrrBot/1.0"}
            resp = requests.get(url, headers=headers, timeout=10)
            posts = resp.json()["data"]["children"]
            return [{
                "name": post["data"]["title"],
                "description": post["data"].get("selftext", "")
            } for post in posts]
        except Exception as e:
            self.logger.error(f"[IdeaGeneratorAgent] Reddit fetch error: {e}")
            return []
    """
    Agent for discovering and ranking new open-source project ideas.
    Fetches from GitHub Trending, Dev.to, HackerNews, summarizes/ranks with Groq, and stores results.
    """
    IDEA_FILE = "monsterrr_state.json"

    def __init__(self, groq_client, logger):
        self.groq_client = groq_client
        self.logger = logger

    from tenacity import retry, stop_after_attempt, wait_exponential
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch_trending_github(self) -> List[Dict[str, Any]]:
        """Fetch trending repos using GitHub Search API (primary) or HTML scrape (fallback)."""
        token = os.getenv("GITHUB_TOKEN")
        headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"} if token else {}
        search_url = "https://api.github.com/search/repositories?q=stars:>1000&sort=stars&order=desc&per_page=25"
        try:
            resp = requests.get(search_url, headers=headers, timeout=10)
            if resp.status_code == 403 and 'X-RateLimit-Remaining' in resp.headers and int(resp.headers['X-RateLimit-Remaining']) == 0:
                reset = int(resp.headers.get('X-RateLimit-Reset', 0))
                wait_time = max(0, reset - int(time.time()))
                self.logger.error(f"GitHub rate limit hit. Backing off for {wait_time} seconds.")
                time.sleep(wait_time)
                return []
            resp.raise_for_status()
            data = resp.json()
            repos = []
            for item in data.get("items", []):
                repos.append({"name": item["name"], "description": item.get("description", "")})
            if repos:
                return repos
        except Exception as e:
            self.logger.error(f"[IdeaGeneratorAgent] GitHub Search API error: {e}")
        # Fallback: scrape HTML
        try:
            from bs4 import BeautifulSoup
            html_url = "https://github.com/trending?since=weekly"
            resp = requests.get(html_url, timeout=10)
            bs = BeautifulSoup(resp.text, "html.parser")
            repos = []
            for repo_tag in bs.select("article.Box-row"):
                name_tag = repo_tag.select_one("h2 a")
                desc_tag = repo_tag.select_one("p")
                name = name_tag.text.strip().replace("\n", "").replace(" ", "") if name_tag else ""
                desc = desc_tag.text.strip() if desc_tag else ""
                if name:
                    repos.append({"name": name, "description": desc})
            if repos:
                return repos
        except Exception as e:
            self.logger.error(f"[IdeaGeneratorAgent] GitHub trending HTML scrape error: {e}")
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
        Fetch trending ideas from multiple sources, deduplicate, summarize and rank with Groq, and store top N in monsterrr_state.json.
        Returns:
            List of top N idea dicts with metadata.
        """
        self.logger.info("[IdeaGeneratorAgent] Fetching trending ideas from sources.")
        github = self.fetch_trending_github()
        hn = self.fetch_trending_hackernews()
        devto = self.fetch_trending_devto()
        producthunt = self.fetch_trending_producthunt()
        reddit_ml = self.fetch_trending_reddit("MachineLearning")
        reddit_ai = self.fetch_trending_reddit("Artificial")
        all_ideas = github + hn + devto + producthunt + reddit_ml + reddit_ai
        # Deduplicate by name
        seen = set()
        deduped = []
        for idea in all_ideas:
            name = idea.get("name", "").strip().lower()
            if name and name not in seen:
                deduped.append(idea)
                seen.add(name)
        prompt = (
            f"Given the following trending open-source project ideas, summarize, filter for uniqueness and impact, "
            f"and rank the top {top_n} ideas. For each, provide: name, description, tech stack, difficulty (easy/med/hard), "
            f"estimated dev time (weeks), and a 3-5 bullet roadmap. Output as JSON list.\n\n"
            f"Ideas: {json.dumps(deduped)[:4000]}"
        )
        try:
            self.logger.info(f"[IdeaGeneratorAgent] Groq ranking prompt: {prompt[:1000]}")
            groq_response = self.groq_client.groq_llm(prompt)
            self.logger.info(f"[IdeaGeneratorAgent] Groq raw response: {groq_response[:2000]}")
            try:
                ideas = json.loads(groq_response)
            except Exception as e:
                self.logger.error(f"[IdeaGeneratorAgent] Groq response not valid JSON: {e}. Re-prompting for concise valid JSON.")
                # Re-prompt Groq for concise valid JSON
                retry_prompt = prompt + "\n\nReturn ONLY a short valid JSON list of ideas, no extra text. If you cannot, return []."
                groq_response2 = self.groq_client.groq_llm(retry_prompt)
                self.logger.info(f"[IdeaGeneratorAgent] Groq retry raw response: {groq_response2[:2000]}")
                try:
                    ideas = json.loads(groq_response2)
                except Exception as e2:
                    self.logger.error(f"[IdeaGeneratorAgent] Groq retry response still not valid JSON: {e2}. Returning empty list.")
                    ideas = []
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
    from utils.config import Settings
    import json
    logger = setup_logger()
    settings = Settings()
    try:
        settings.validate()
    except Exception as e:
        logger.error(f"[Config] {e}")
        raise
    groq = GroqService(api_key=settings.GROQ_API_KEY, logger=logger)
    agent = IdeaGeneratorAgent(groq, logger)
    ideas = agent.fetch_and_rank_ideas()
    print(json.dumps(ideas, indent=2))
