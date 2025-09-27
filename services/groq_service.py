"""
Groq API wrapper for Monsterrr.
"""

import requests
import time
import os
from typing import Optional, Dict, Any, Generator
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

class GroqAuthError(Exception):
    pass

class GroqService:
    """
    Service for interacting with the Groq LLM API.
    Handles retries, logging, prompt templating, and streaming.
    """
    BASE_URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self, api_key: Optional[str] = None, logger=None, max_retries: int = 3, timeout: int = 30, fallback_models=None):
        load_dotenv()
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
        self.fallback_models = fallback_models or ["openai/gpt-oss-120b", "llama-3.1-8b-instant"]
        if not self.api_key:
            raise ValueError("Missing GROQ_API_KEY")
        if not self.model:
            raise ValueError("Missing GROQ_MODEL")
        self.logger = logger
        self.max_retries = max_retries
        self.timeout = timeout
        redacted_key = self.api_key[:6] + "..." + self.api_key[-4:]
        if self.logger:
            self.logger.info(f"[GroqService] Initialized with model: {self.model}, API key: {redacted_key}")


    def groq_llm(self, prompt: str, model: Optional[str] = None, system_prompt: Optional[str] = None, stream: bool = False, expect_json: bool = False, **kwargs) -> str:
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
        model = model or self.model
        temperature = float(os.getenv("GROQ_TEMPERATURE", 0.1))
        max_completion_tokens = int(os.getenv("GROQ_MAX_TOKENS", 2048))
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt or "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_completion_tokens": max_completion_tokens
        }
        payload.update(kwargs)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        attempt = 0
        tried_models = [model]
        while attempt < self.max_retries:
            try:
                self.logger.info(f"[GroqService] Sending request to Groq API (attempt {attempt+1})")
                self.logger.debug(f"[GroqService] Request payload: {str(payload)[:2000]}")
                if stream:
                    return self._stream_response(payload, headers)
                resp = requests.post(self.BASE_URL, json=payload, headers=headers, timeout=self.timeout)
                raw_body = resp.text[:16000]
                self.logger.debug(f"[GroqService] Raw response ({resp.status_code}): {raw_body}")
                if resp.status_code == 401:
                    self.logger.error("AUTH FAILED — check GROQ_API_KEY and model access")
                    raise GroqAuthError("Groq API 401 Unauthorized: Check your API key and model access.")
                if resp.status_code in (404, 400):
                    self.logger.error(f"Groq API {resp.status_code} error: {raw_body}")
                    try:
                        data = resp.json()
                        error_code = data.get("error", {}).get("code", "")
                        if error_code in ("model_decommissioned", "model_not_found"):
                            self.logger.warning(f"Groq model {model} decommissioned/not found. Trying fallback models.")
                            for fallback in self.fallback_models:
                                if fallback not in tried_models:
                                    payload["model"] = fallback
                                    tried_models.append(fallback)
                                    self.logger.info(f"Switching to fallback model: {fallback}")
                                    resp = requests.post(self.BASE_URL, json=payload, headers=headers, timeout=self.timeout)
                                    raw_body = resp.text[:16000]
                                    self.logger.debug(f"[GroqService] Fallback raw response ({resp.status_code}): {raw_body}")
                                    if resp.status_code == 200:
                                        data = resp.json()
                                        break
                            else:
                                raise RuntimeError("All fallback models failed or are decommissioned.")
                    except Exception:
                        pass
                if resp.status_code == 429 or resp.status_code >= 500:
                    self.logger.error(f"Groq API {resp.status_code} error: {raw_body}. Retrying...")
                    attempt += 1
                    # For rate limiting (429), wait longer based on the error message
                    if resp.status_code == 429:
                        try:
                            import json
                            error_data = resp.json()
                            # Extract wait time from error message if available
                            message = error_data.get("error", {}).get("message", "")
                            # Look for patterns like "Please try again in 12m17.962s"
                            import re
                            wait_match = re.search(r"try again in ([\d\.]+)s", message)
                            if wait_match:
                                wait_time = float(wait_match.group(1))
                                time.sleep(min(wait_time, 60))  # Cap at 60 seconds
                            else:
                                time.sleep(min(2 ** attempt, 30))  # Exponential backoff, max 30s
                        except Exception:
                            time.sleep(min(2 ** attempt, 30))  # Fallback to exponential backoff
                    else:
                        time.sleep(2 ** attempt)
                    continue
                if resp.status_code < 200 or resp.status_code >= 300:
                    self.logger.error(f"Groq API unexpected status {resp.status_code}: {raw_body}")
                    raise RuntimeError(f"Groq API error {resp.status_code}")
                try:
                    data = resp.json()
                except Exception as e:
                    self.logger.error(f"Groq API returned invalid JSON: {raw_body}")
                    # Re-prompt once with extra instruction
                    if attempt == 0:
                        payload["messages"][1]["content"] += "\n\nReturn the assistant message only. If you cannot, return {}."
                        attempt += 1
                        continue
                    raise RuntimeError("Groq API returned invalid/empty response")
                if "choices" in data and data["choices"]:
                    content = data["choices"][0]["message"].get("content", "")
                    if not content.strip():
                        self.logger.error(f"Groq API returned empty content: {data}")
                        # Re-prompt once
                        if attempt == 0:
                            payload["messages"][1]["content"] += "\n\nReturn the assistant message only. If you cannot, return {}."
                            attempt += 1
                            continue
                        raise RuntimeError("Groq API returned empty response")
                    self.logger.info("[GroqService] Groq API call successful.")
                    if expect_json:
                        try:
                            import json
                            return json.loads(content)
                        except Exception:
                            self.logger.error("Groq response was not valid JSON after retry.")
                            raise RuntimeError("Groq response was not valid JSON.")
                    return content
                else:
                    self.logger.error(f"Groq API returned no choices: {data}")
                    # Re-prompt once
                    if attempt == 0:
                        payload["messages"][1]["content"] += "\n\nReturn the assistant message only. If you cannot, return {}."
                        attempt += 1
                        continue
                    raise RuntimeError("Groq API returned no choices")
            except GroqAuthError:
                raise
            except Exception as e:
                self.logger.error(f"GroqService error: {e}")
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
