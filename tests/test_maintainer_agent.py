"""
Test for MaintainerAgent.
"""

import pytest
from unittest.mock import MagicMock
from agents.maintainer_agent import MaintainerAgent

@pytest.fixture
def agent():
    github = MagicMock()
    groq = MagicMock()
    logger = MagicMock()
    return MaintainerAgent(github, groq, logger)

def test_perform_maintenance(agent):
    agent.github_service.list_repositories.return_value = ["repo1"]
    agent.github_service.list_issues.return_value = [{"number": 1, "title": "Test", "state": "open"}]
    agent.groq_client.groq_llm.return_value = "This is a suggestion."
    agent.github_service.close_issue.return_value = {}
    agent.perform_maintenance()
    agent.github_service.list_repositories.assert_called_once()
