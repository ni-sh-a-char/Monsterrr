"""
Unit tests for GitHubService.
"""
import pytest
from unittest.mock import MagicMock, patch
from services.github_service import GitHubService, GitHubAPIError

@pytest.fixture
def github_service():
    logger = MagicMock()
    with patch("services.github_service.os.getenv", side_effect=lambda k, d=None: "test" if k in ["GITHUB_TOKEN", "GITHUB_ORG"] else d):
        return GitHubService(logger=logger)

def test_list_repositories_success(github_service):
    with patch("services.github_service.httpx.Client.request") as mock_req:
        mock_req.return_value.status_code = 200
        mock_req.return_value.json.return_value = [{"name": "repo1"}]
        mock_req.return_value.links = {}
        repos = github_service.list_repositories()
        assert isinstance(repos, list)

def test_create_repository_success(github_service):
    with patch("services.github_service.httpx.Client.request") as mock_req:
        mock_req.return_value.status_code = 200
        mock_req.return_value.json.return_value = {"name": "repo1"}
        repo = github_service.create_repository("repo1")
        assert repo["name"] == "repo1"

def test_error_handling_raises(github_service):
    with patch("services.github_service.httpx.Client.request") as mock_req:
        mock_req.return_value.status_code = 404
        mock_req.return_value.url = "http://test"
        mock_req.return_value.text = "not found"
        with pytest.raises(GitHubAPIError):
            github_service.list_repositories()
