from typing import List, Dict, Any
import os
import json
import time
import requests
from datetime import datetime, timezone, timedelta
IST = timezone(timedelta(hours=5, minutes=30))


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
    
    def fetch_trending_github_topics(self) -> list:
        """Fetch trending topics from GitHub."""
        try:
            import requests
            from bs4 import BeautifulSoup
            resp = requests.get("https://github.com/topics", timeout=10)
            bs = BeautifulSoup(resp.text, "html.parser")
            topics = []
            for topic in bs.select("div[data-topic-name]"):
                name = topic.select_one("a[href*='/topics/']")
                desc = topic.select_one("p")
                if name:
                    topic_name = name.text.strip()
                    topic_desc = desc.text.strip() if desc else ""
                    topics.append({
                        "name": topic_name,
                        "description": topic_desc
                    })
            return topics
        except Exception as e:
            self.logger.error(f"[IdeaGeneratorAgent] GitHub topics fetch error: {e}")
            return []
    
    def fetch_trending_devto_week(self) -> list:
        """Fetch top articles from Dev.to for the week."""
        try:
            import requests
            resp = requests.get("https://dev.to/api/articles?top=1&per_page=15&tag=week", timeout=10)
            resp.raise_for_status()
            articles = resp.json()
            return [{
                "name": article["title"],
                "description": article.get("description", article.get("body_markdown", ""))[:200]
            } for article in articles]
        except Exception as e:
            self.logger.error(f"[IdeaGeneratorAgent] Dev.to week fetch error: {e}")
            return []
    
    def fetch_trending_hackernews_month(self) -> list:
        """Fetch top stories from Hacker News for the month."""
        try:
            import requests
            # Get more stories for better variety
            top_ids = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=10).json()[:30]
            stories = []
            for sid in top_ids:
                try:
                    item = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json", timeout=5).json()
                    if item and 'title' in item:
                        stories.append({
                            "name": item["title"],
                            "description": item.get("text", "")[:200] if item.get("text") else ""
                        })
                except:
                    continue
            return stories
        except Exception as e:
            self.logger.error(f"[IdeaGeneratorAgent] HackerNews month fetch error: {e}")
            return []
    
    def fetch_trending_stackoverflow(self) -> list:
        """Fetch trending tags from Stack Overflow."""
        try:
            import requests
            resp = requests.get("https://api.stackexchange.com/2.3/tags?order=desc&sort=popular&site=stackoverflow&pagesize=20", timeout=10)
            resp.raise_for_status()
            tags = resp.json()["items"]
            return [{
                "name": f"{tag['name']} Development Tool",
                "description": f"A tool or library for {tag['name']} development"
            } for tag in tags[:10]]  # Limit to top 10
        except Exception as e:
            self.logger.error(f"[IdeaGeneratorAgent] Stack Overflow fetch error: {e}")
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
                repos.append({
                    "name": item["name"], 
                    "description": item.get("description", ""),
                    "language": item.get("language", ""),
                    "stars": item.get("stargazers_count", 0),
                    "forks": item.get("forks_count", 0)
                })
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
                lang_tag = repo_tag.select_one("[itemprop='programmingLanguage']")
                name = name_tag.text.strip().replace("\n", "").replace(" ", "") if name_tag else ""
                desc = desc_tag.text.strip() if desc_tag else ""
                lang = lang_tag.text.strip() if lang_tag else ""
                if name:
                    repos.append({
                        "name": name, 
                        "description": desc,
                        "language": lang
                    })
            if repos:
                return repos
        except Exception as e:
            self.logger.error(f"[IdeaGeneratorAgent] GitHub trending HTML scrape error: {e}")
        return []

    def fetch_web_trends(self) -> List[Dict[str, Any]]:
        """Fetch trending topics from web searches to enhance idea generation."""
        try:
            # This would integrate with a web search API like Google Custom Search or similar
            # For now, we'll return a placeholder that can be expanded
            import random
            tech_trends = [
                "AI code generation", "low-code platforms", "serverless computing", 
                "edge computing", "quantum computing", "blockchain applications",
                "IoT security", "cloud-native development", "microservices architecture",
                "DevOps automation", "container orchestration", "data privacy tools"
            ]
            
            # Select random trends to simulate web search results
            selected_trends = random.sample(tech_trends, min(5, len(tech_trends)))
            
            web_ideas = []
            for trend in selected_trends:
                web_ideas.append({
                    "name": f"{trend.replace(' ', '-')}",
                    "description": f"A project focused on {trend}",
                    "source": "web_trends"
                })
            
            return web_ideas
        except Exception as e:
            self.logger.error(f"[IdeaGeneratorAgent] Web trends fetch error: {e}")
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

    def _load_state(self):
        """Load the monsterrr state from file."""
        if os.path.exists(self.IDEA_FILE):
            try:
                with open(self.IDEA_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"[IdeaGeneratorAgent] Error loading state: {e}")
                return {}
        return {}

    def _save_state(self, state):
        """Save the monsterrr state to file."""
        try:
            with open(self.IDEA_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"[IdeaGeneratorAgent] Error saving state: {e}")

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
        github_topics = self.fetch_trending_github_topics()
        devto_week = self.fetch_trending_devto_week()
        hn_month = self.fetch_trending_hackernews_month()
        stackoverflow = self.fetch_trending_stackoverflow()
        
        # Additional sources for more diverse ideas
        reddit_programming = self.fetch_trending_reddit("programming")
        reddit_webdev = self.fetch_trending_reddit("webdev")
        reddit_python = self.fetch_trending_reddit("Python")
        reddit_javascript = self.fetch_trending_reddit("javascript")
        
        # Web trends for enhanced idea generation
        web_trends = self.fetch_web_trends()
        
        # Combine all ideas
        all_ideas = github + hn + devto + producthunt + reddit_ml + reddit_ai + github_topics + devto_week + hn_month + stackoverflow + reddit_programming + reddit_webdev + reddit_python + reddit_javascript + web_trends
        
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
            f"and rank the top {top_n} ideas. For each, provide: name, description, detailed_description, tech stack, difficulty (easy/med/hard), "
            f"estimated dev time (weeks), features (as a list), and a 5-7 step detailed roadmap. "
            f"Make the ideas as specific and actionable as possible with complete technical details. "
            f"The detailed_description should be 2-3 sentences explaining the problem the project solves. "
            f"The features should be specific functionalities the project will have. "
            f"Each roadmap step should be a concrete implementation task."
            f"\n\nIMPORTANT: Do NOT use tables in your answer. Instead, present all lists and structured data as professional, visually clear bullet points. Each idea should be a separate bullet with its details as sub-bullets."
            f"\n\nIMPORTANT: The name should be a sensible, professional project name that follows standard naming conventions (lowercase, hyphens for spaces, no special characters). Examples: 'api-documentation-generator', 'machine-learning-dashboard', 'code-review-automation'."
            f"\n\nIdeas: {json.dumps(deduped)[:4000]}"
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