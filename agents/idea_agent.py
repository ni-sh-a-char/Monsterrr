from typing import List, Dict, Any
import os
import json
import time
import requests
import re
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
            resp = requests.get(url, headers=headers, timeout=15)  # Increased timeout
            # Check if response is valid JSON
            if resp.status_code == 200:
                try:
                    # Add additional validation for empty or invalid responses
                    content = resp.text.strip()
                    if not content:
                        self.logger.warning(f"[IdeaGeneratorAgent] Reddit API returned empty response for {subreddit}")
                        return []
                    if content.startswith('<'):  # HTML response instead of JSON
                        self.logger.warning(f"[IdeaGeneratorAgent] Reddit API returned HTML instead of JSON for {subreddit}")
                        return []
                    data = resp.json()
                    if "data" in data and "children" in data["data"]:
                        posts = data["data"]["children"]
                        return [{
                            "name": post["data"]["title"],
                            "description": post["data"].get("selftext", "")[:500] if post["data"].get("selftext") else ""
                        } for post in posts]
                    else:
                        self.logger.warning(f"[IdeaGeneratorAgent] Reddit API returned unexpected structure for {subreddit}")
                        return []
                except ValueError as e:
                    self.logger.error(f"[IdeaGeneratorAgent] Reddit API returned invalid JSON for {subreddit}: {e}")
                    self.logger.debug(f"[IdeaGeneratorAgent] Reddit response content: {resp.text[:500]}")
                    return []
            else:
                self.logger.error(f"[IdeaGeneratorAgent] Reddit API returned status {resp.status_code} for {subreddit}")
                if resp.status_code == 429:  # Rate limiting
                    self.logger.warning("[IdeaGeneratorAgent] Reddit rate limiting detected, skipping Reddit fetch")
                    return []
                return []
        except requests.exceptions.RequestException as e:
            self.logger.error(f"[IdeaGeneratorAgent] Reddit network error: {e}")
            return []
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
                "DevOps automation", "container orchestration", "data privacy tools",
                "real-time analytics", "predictive maintenance", "digital twins",
                "cybersecurity automation", "API gateway management", "data visualization",
                "natural language processing", "computer vision applications"
            ]
            
            # Select random trends to simulate web search results
            selected_trends = random.sample(tech_trends, min(5, len(tech_trends)))
            
            web_ideas = []
            for trend in selected_trends:
                # Generate more meaningful project names based on the trend
                name_parts = trend.lower().replace(" ", "-").replace("/", "-").split("-")
                # Create a more descriptive name
                if len(name_parts) > 1:
                    name = f"{name_parts[0]}-{name_parts[-1]}-tool"
                else:
                    name = f"{name_parts[0]}-utility"
                    
                web_ideas.append({
                    "name": name,
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

    def _sanitize_repo_name(self, name: str) -> str:
        """Sanitize repository name to prevent weird names and ensure meaningful names."""
        if not name:
            return "monsterrr-project"
        
        # Convert to lowercase
        name = name.lower().strip()
        
        # Replace spaces and underscores with hyphens
        name = name.replace(" ", "-").replace("_", "-")
        
        # Remove special characters except hyphens
        name = re.sub(r"[^a-z0-9\-]", "", name)
        
        # Remove multiple consecutive hyphens
        name = re.sub(r"-+", "-", name)
        
        # Remove leading/trailing hyphens
        name = name.strip("-")
        
        # Additional validation to ensure meaningful names
        # Check if name contains only numbers or is too short
        if not name or name.isdigit() or len(name) < 3:
            name = "monsterrr-project"
        # Check if name is too generic
        elif name in ["project", "app", "application", "software", "tool", "program", "demo", "test", "example"]:
            name = f"monsterrr-{name}"
        # Ensure name is descriptive enough
        elif len(name) < 6 and "-" not in name:
            name = f"monsterrr-{name}-tool"
        # Check for meaningless combinations
        elif re.match(r"^[a-z]{3,6}-[a-z]{3,6}$", name) and not any(keyword in name for keyword in [
            "api", "bot", "cli", "web", "data", "code", "dev", "auto", "smart", "ml", "ai", "cloud", "iot", "sec", "util"
        ]):
            # If it's a generic two-word combination, make it more specific
            name = f"{name}-utility"
        
        # Ensure name is not empty and not too long
        if not name:
            name = "monsterrr-project"
        elif len(name) > 50:
            name = name[:50].rstrip("-")
            
        return name

    def fetch_and_rank_ideas(self, top_n: int = 5) -> List[Dict[str, Any]]:
        """
        Fetch trending ideas from multiple sources, deduplicate, summarize and rank with Groq, and store top N in monsterrr_state.json.
        Returns:
            List of top N idea dicts with metadata.
        """
        self.logger.info("[IdeaGeneratorAgent] Fetching trending ideas from sources.")
        
        # Add rate limiting delay between API calls to prevent rate limiting
        def rate_limited_call(func, *args, **kwargs):
            try:
                result = func(*args, **kwargs)
                # Add a small delay between calls to prevent rate limiting
                time.sleep(1)
                return result
            except Exception as e:
                self.logger.error(f"[IdeaGeneratorAgent] Error in {func.__name__}: {e}")
                # Add a longer delay on error to prevent further rate limiting
                time.sleep(2)
                return []
        
        # Temporarily disable Reddit calls due to rate limiting issues
        github = rate_limited_call(self.fetch_trending_github)
        hn = rate_limited_call(self.fetch_trending_hackernews)
        devto = rate_limited_call(self.fetch_trending_devto)
        producthunt = rate_limited_call(self.fetch_trending_producthunt)
        
        # Only fetch from Reddit if we have a valid Reddit API setup
        # For now, let's skip Reddit to avoid errors
        reddit_ml = []  # Disabled due to rate limiting
        reddit_ai = []  # Disabled due to rate limiting
        reddit_programming = []  # Disabled due to rate limiting
        reddit_webdev = []  # Disabled due to rate limiting
        reddit_python = []  # Disabled due to rate limiting
        reddit_javascript = []  # Disabled due to rate limiting
        
        github_topics = rate_limited_call(self.fetch_trending_github_topics)
        devto_week = rate_limited_call(self.fetch_trending_devto_week)
        hn_month = rate_limited_call(self.fetch_trending_hackernews_month)
        stackoverflow = rate_limited_call(self.fetch_trending_stackoverflow)
        
        # Web trends for enhanced idea generation
        web_trends = rate_limited_call(self.fetch_web_trends)
        
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
        
        # If we have no ideas, return early
        if not deduped:
            self.logger.info("[IdeaGeneratorAgent] No ideas fetched from sources.")
            state = self._load_state()
            state['ideas'] = {
                'generated_at': datetime.utcnow().isoformat(),
                'top_ideas': []
            }
            self._save_state(state)
            return []
        
        # Limit the number of ideas to prevent overwhelming the LLM
        deduped = deduped[:20]  # Limit to 20 ideas max
        
        prompt = (
            f"Given the following trending open-source project ideas, summarize, filter for uniqueness and impact, "
            f"and rank the top {top_n} ideas. For each, provide: name, description, detailed_description, tech stack, difficulty (easy/med/hard), "
            f"estimated dev time (weeks), features (as a list), and a 5-7 step detailed roadmap. "
            f"Make the ideas as specific and actionable as possible with complete technical details. "
            f"The detailed_description should be 2-3 sentences explaining the problem the project solves. "
            f"The features should be specific functionalities the project will have. "
            f"Each roadmap step should be a concrete implementation task."
            f"\n\nIMPORTANT: Return ONLY a valid JSON array. No extra text, no markdown formatting, no explanations. "
            f"Example format: [{{\"name\": \"project-name\", \"description\": \"description\", \"detailed_description\": \"detailed description\", \"tech_stack\": [\"tech1\", \"tech2\"], \"difficulty\": \"med\", \"estimated_dev_time\": 4, \"features\": [\"feature1\", \"feature2\"], \"roadmap\": [\"step1\", \"step2\"]}}]"
            f"\n\nIMPORTANT: The name should be a sensible, professional project name that follows standard naming conventions (lowercase, hyphens for spaces, no special characters). Examples: 'api-documentation-generator', 'machine-learning-dashboard', 'code-review-automation'."
            f"\n\nIMPORTANT: The name should clearly indicate what the project does and should be descriptive. Avoid generic names like 'project' or 'app'. The name should be between 6-30 characters and should clearly communicate the project's purpose."
            f"\n\nIdeas: {json.dumps(deduped)[:4000]}"
        )
        try:
            self.logger.info(f"[IdeaGeneratorAgent] Groq ranking prompt: {prompt[:1000]}...")
            groq_response = self.groq_client.groq_llm(prompt)
            self.logger.info(f"[IdeaGeneratorAgent] Groq raw response: {groq_response[:2000]}")
            
            # Try to parse the response as JSON
            try:
                # First, try to extract JSON from the response
                import re
                # Look for JSON array pattern
                json_match = re.search(r'\[.*\]', groq_response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    ideas = json.loads(json_str)
                else:
                    # If no JSON array found, try parsing the whole response
                    ideas = json.loads(groq_response)
            except Exception as e:
                self.logger.error(f"[IdeaGeneratorAgent] Groq response not valid JSON: {e}. Re-prompting for concise valid JSON.")
                # Re-prompt Groq for concise valid JSON
                retry_prompt = prompt + "\n\nReturn ONLY a short valid JSON array, no extra text. If you cannot, return []."
                groq_response2 = self.groq_client.groq_llm(retry_prompt)
                self.logger.info(f"[IdeaGeneratorAgent] Groq retry raw response: {groq_response2[:2000]}")
                try:
                    # Try to extract JSON from retry response
                    json_match = re.search(r'\[.*\]', groq_response2, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                        ideas = json.loads(json_str)
                    else:
                        ideas = json.loads(groq_response2)
                except Exception as e2:
                    self.logger.error(f"[IdeaGeneratorAgent] Groq retry response still not valid JSON: {e2}. Returning empty list.")
                    ideas = []
            self.logger.info(f"[IdeaGeneratorAgent] Got {len(ideas)} ranked ideas from Groq.")
        except Exception as e:
            self.logger.error(f"[IdeaGeneratorAgent] Groq summarization error: {e}")
            ideas = []
        
        # Sanitize repository names to prevent weird names
        for idea in ideas:
            if "name" in idea:
                idea["name"] = self._sanitize_repo_name(idea["name"])
        
        # Store in monsterrr_state.json
        state = self._load_state()
        state['ideas'] = {
            'generated_at': datetime.utcnow().isoformat(),
            'top_ideas': ideas[:top_n]
        }
        self._save_state(state)
        return ideas[:top_n]
