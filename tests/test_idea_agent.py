def test_idea_agent_trending_fallback(monkeypatch):
    from agents.idea_agent import IdeaGeneratorAgent
    class DummyLogger:
        def info(self, msg): pass
        def error(self, msg): pass
    class DummyGroq:
        def groq_llm(self, *a, **kw): return '[{"name": "Test", "description": "desc", "tech_stack": ["Python"], "roadmap": ["step1"]}]'
    # Simulate API failure, then HTML scrape success
    def dummy_requests_get(url, timeout):
        if "github-trending-api" in url:
            raise Exception("API down")
        class DummyResp:
            text = "<article class='Box-row'><h2><a>repo1</a></h2><p>desc1</p></article>"
            def raise_for_status(self): pass
            def json(self): return []
        return DummyResp()
    monkeypatch.setattr("requests.get", dummy_requests_get)
    agent = IdeaGeneratorAgent(DummyGroq(), DummyLogger())
    trending = agent.fetch_trending_github()
    assert trending and trending[0]["name"] == "repo1"
"""
Test for IdeaGeneratorAgent.
"""

import pytest
from unittest.mock import MagicMock, patch
from agents.idea_agent import IdeaGeneratorAgent

@pytest.fixture
def agent():
    groq = MagicMock()
    logger = MagicMock()
    return IdeaGeneratorAgent(groq, logger)

def test_fetch_and_rank_ideas(agent):
    agent.fetch_trending_github = MagicMock(return_value=[{"name": "Test"}])
    agent.fetch_trending_hackernews = MagicMock(return_value=[])
    agent.fetch_trending_devto = MagicMock(return_value=[])
    agent.groq_client.groq_llm.return_value = '[{"name": "Test", "description": "desc", "tech_stack": ["Python"], "roadmap": ["step1"]}]'
    ideas = agent.fetch_and_rank_ideas(top_n=1)
    assert isinstance(ideas, list)
    assert ideas[0]["name"] == "Test"
