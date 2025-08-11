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
