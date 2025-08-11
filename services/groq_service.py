"""
Groq API wrapper for Monsterrr.
"""

import requests
import time
from typing import Optional, Dict, Any, Generator

class GroqService:
    """
    Service for interacting with the Groq LLM API.
    Handles retries, logging, prompt templating, and streaming.
    """
    BASE_URL = "https://api.groq.com/v1/chat/completions"

    def __init__(self, api_key: str, logger, max_retries: int = 3, timeout: int = 30):
        """
        Args:
            api_key (str): Groq API key
            logger: Logger instance
            max_retries (int): Number of retries for failed requests
            timeout (int): Timeout for API requests in seconds
        """
        self.api_key = api_key
        self.logger = logger
        self.max_retries = max_retries
        self.timeout = timeout

    def groq_llm(self, prompt: str, model: str = "mixtral-8x7b", system_prompt: Optional[str] = None, stream: bool = False, **kwargs) -> str:
        """
        Send a prompt to Groq LLM and return the response.

        Args:
            prompt (str): User prompt
            model (str): Model name
            system_prompt (Optional[str]): System prompt for context injection
            stream (bool): If True, yields streaming responses
            **kwargs: Additional Groq API parameters

        Returns:
            str: LLM response (or generator if stream=True)
        """
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt or "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            **kwargs
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        attempt = 0
        while attempt < self.max_retries:
            try:
                self.logger.info(f"[GroqService] Sending prompt to Groq API (attempt {attempt+1})")
                if stream:
                    return self._stream_response(payload, headers)
                resp = requests.post(self.BASE_URL, json=payload, headers=headers, timeout=self.timeout)
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                self.logger.info("[GroqService] Groq API call successful.")
                return content
            except Exception as e:
                self.logger.error(f"[GroqService] Groq API error: {e}")
                attempt += 1
                time.sleep(2 ** attempt)
        raise RuntimeError("Groq API call failed after retries.")

    def _stream_response(self, payload: Dict[str, Any], headers: Dict[str, str]) -> Generator[str, None, None]:
        """
        Stream Groq API responses (for large outputs or chat UIs).
        Yields:
            str: Partial response chunks
        """
        payload["stream"] = True
        with requests.post(self.BASE_URL, json=payload, headers=headers, stream=True, timeout=self.timeout) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if line:
                    try:
                        chunk = line.decode("utf-8")
                        self.logger.debug(f"[GroqService] Stream chunk: {chunk}")
                        yield chunk
                    except Exception as e:
                        self.logger.error(f"[GroqService] Stream decode error: {e}")
