"""
Test for CreatorAgent.
"""

import pytest
from unittest.mock import MagicMock
from agents.creator_agent import CreatorAgent

@pytest.fixture
def agent():
    github = MagicMock()
    logger = MagicMock()
    return CreatorAgent(github, logger)

def test_create_repository(agent):
    idea = {"name": "TestRepo", "description": "desc", "tech_stack": ["Python"], "roadmap": ["step1"]}
    agent.github_service.create_repository.return_value = {"html_url": "http://github.com/test"}
    agent.github_service.create_or_update_file.return_value = {}
    agent.github_service.create_issue.return_value = {}
    agent.create_repository(idea)
    agent.github_service.create_repository.assert_called_once()
