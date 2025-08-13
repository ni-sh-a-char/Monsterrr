def test_groq_endpoint_success(monkeypatch):
    class DummyLogger:
        def info(self, msg): pass
        def error(self, msg): pass
    def dummy_post(url, json, headers, timeout):
        assert url == "https://api.groq.com/openai/v1/chat/completions"
        class DummyResp:
            def raise_for_status(self): pass
            def json(self): return {"choices": [{"message": {"content": "ok"}}]}
        return DummyResp()
    monkeypatch.setattr("requests.post", dummy_post)
    groq = GroqService(api_key="test", logger=DummyLogger())
    result = groq.groq_llm("Hello?")
    assert result == "ok"
"""
Unit tests for GroqService.
"""
import pytest
from unittest.mock import MagicMock, patch
from services.groq_service import GroqService

@pytest.fixture
def groq_service():
    logger = MagicMock()
    return GroqService(api_key="test-key", logger=logger)

def test_groq_llm_success(groq_service):
    with patch("services.groq_service.requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"choices": [{"message": {"content": "{}"}}]}
        result = groq_service.groq_llm("prompt")
        assert isinstance(result, str)

def test_groq_llm_retry_on_error(groq_service):
    with patch("services.groq_service.requests.post", side_effect=Exception("fail")):
        with pytest.raises(RuntimeError):
            groq_service.groq_llm("prompt")
