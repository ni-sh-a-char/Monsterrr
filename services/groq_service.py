"""
Groq API wrapper for Monsterrr.
"""

import requests
import time
import os
from typing import Optional, Dict, Any, Generator, List
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

    # Define model groups for different tasks
    HIGH_PERFORMANCE_MODELS = [
        "openai/gpt-oss-120b",  # Flagship model for complex tasks
        "llama-3.3-70b-versatile"  # High-performance alternative
    ]
    
    BALANCED_MODELS = [
        "llama-3.1-8b-instant",  # Fast and efficient for general tasks
        "openai/gpt-oss-20b"     # Good balance of speed and capability
    ]
    
    FAST_MODELS = [
        "llama-3.1-8b-instant",  # Fastest model for simple tasks
        "llama-3.3-70b-versatile"  # Fallback for when 8b is rate limited
    ]
    
    FALLBACK_MODELS = [
        "llama-3.1-8b-instant",   # Primary fallback
        "llama-3.3-70b-versatile", # Secondary fallback
        "openai/gpt-oss-20b"      # Tertiary fallback
    ]

    def __init__(self, api_key: Optional[str] = None, logger=None, max_retries: int = 3, timeout: int = 30):
        load_dotenv()
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
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

    def get_model_for_task(self, task_type: str) -> str:
        """
        Get the appropriate model for a specific task type.
        
        Args:
            task_type (str): Type of task ('complex', 'balanced', 'fast')
            
        Returns:
            str: Model name
        """
        if task_type == "complex":
            return self.HIGH_PERFORMANCE_MODELS[0]
        elif task_type == "balanced":
            return self.BALANCED_MODELS[0]
        elif task_type == "fast":
            return self.FAST_MODELS[0]
        else:
            return self.model  # Default model

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
                if self.logger:
                    self.logger.info(f"[GroqService] Sending request to Groq API (attempt {attempt+1}) with model {model}")
                    self.logger.debug(f"[GroqService] Request payload: {str(payload)[:2000]}")
                if stream:
                    return self._stream_response(payload, headers)
                resp = requests.post(self.BASE_URL, json=payload, headers=headers, timeout=self.timeout)
                raw_body = resp.text[:16000]
                if self.logger:
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
                            # Try fallback models
                            for fallback in self.FALLBACK_MODELS:
                                if fallback not in tried_models:
                                    payload["model"] = fallback
                                    tried_models.append(fallback)
                                    if self.logger:
                                        self.logger.info(f"Switching to fallback model: {fallback}")
                                    resp = requests.post(self.BASE_URL, json=payload, headers=headers, timeout=self.timeout)
                                    raw_body = resp.text[:16000]
                                    if self.logger:
                                        self.logger.debug(f"[GroqService] Fallback raw response ({resp.status_code}): {raw_body}")
                                    if resp.status_code == 200:
                                        data = resp.json()
                                        break
                            else:
                                raise RuntimeError("All fallback models failed or are decommissioned.")
                    except Exception:
                        pass
                if resp.status_code == 429 or resp.status_code >= 500:
                    if self.logger:
                        self.logger.error(f"Groq API {resp.status_code} error: {raw_body}. Retrying...")
                    attempt += 1
                    # For rate limiting (429), check headers for rate limit information
                    if resp.status_code == 429:
                        # Check rate limit headers
                        retry_after = resp.headers.get("retry-after")
                        reset_requests = resp.headers.get("x-ratelimit-reset-requests")
                        reset_tokens = resp.headers.get("x-ratelimit-reset-tokens")
                        
                        wait_time = 5  # Default wait time
                        
                        # Use retry-after header if available
                        if retry_after:
                            try:
                                wait_time = int(retry_after) + 2  # Add buffer
                            except:
                                pass
                        
                        # Use reset time headers if available
                        elif reset_requests or reset_tokens:
                            # Parse time format like "2m59.56s" or "7.66s"
                            reset_time = reset_requests or reset_tokens
                            try:
                                if "m" in reset_time:
                                    # Format like "2m59.56s"
                                    minutes_part, seconds_part = reset_time.split("m")
                                    minutes = int(minutes_part)
                                    seconds = float(seconds_part.replace("s", ""))
                                    wait_time = minutes * 60 + seconds + 2
                                else:
                                    # Format like "7.66s"
                                    wait_time = float(reset_time.replace("s", "")) + 2
                            except:
                                pass
                        
                        # Cap wait time to reasonable maximum
                        wait_time = min(wait_time, 300)  # Max 5 minutes
                        
                        if self.logger:
                            self.logger.info(f"[GroqService] Rate limited. Waiting {wait_time} seconds before retry.")
                        time.sleep(wait_time)
                    else:
                        # For server errors, use exponential backoff
                        wait_time = min(2 ** attempt * 5, 120)  # Max 2 minutes
                        if self.logger:
                            self.logger.info(f"[GroqService] Server error. Waiting {wait_time} seconds before retry.")
                        time.sleep(wait_time)
                    continue
                if resp.status_code < 200 or resp.status_code >= 300:
                    if self.logger:
                        self.logger.error(f"Groq API unexpected status {resp.status_code}: {raw_body}")
                    raise RuntimeError(f"Groq API error {resp.status_code}")
                try:
                    data = resp.json()
                except Exception as e:
                    if self.logger:
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
                        if self.logger:
                            self.logger.error(f"Groq API returned empty content: {data}")
                        # Re-prompt once
                        if attempt == 0:
                            payload["messages"][1]["content"] += "\n\nReturn the assistant message only. If you cannot, return {}."
                            attempt += 1
                            continue
                        raise RuntimeError("Groq API returned empty response")
                    if self.logger:
                        self.logger.info("[GroqService] Groq API call successful.")
                    if expect_json:
                        try:
                            import json
                            # Try to extract JSON from the response if it contains extra text
                            import re
                            # Look for JSON object or array pattern
                            json_match = re.search(r'(\{.*\}|\[.*\])', content, re.DOTALL)
                            if json_match:
                                json_str = json_match.group(1)
                                return json.loads(json_str)
                            else:
                                # If no JSON pattern found, try to parse the whole content
                                return json.loads(content)
                        except Exception as e:
                            if self.logger:
                                self.logger.error(f"Groq response was not valid JSON: {e}")
                                self.logger.debug(f"Groq response content: {content}")
                            # Try to fix common JSON issues
                            try:
                                # Fix common issues like single quotes, trailing commas
                                fixed_content = content.replace("'", '"')
                                fixed_content = re.sub(r',(\s*[}\]])', r'\1', fixed_content)  # Remove trailing commas
                                return json.loads(fixed_content)
                            except Exception as e2:
                                if self.logger:
                                    self.logger.error(f"Groq response still not valid JSON after fixes: {e2}")
                                raise RuntimeError("Groq response was not valid JSON.")
                    return content
                else:
                    if self.logger:
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
                if self.logger:
                    self.logger.error(f"GroqService error: {e}")
                attempt += 1
                if attempt < self.max_retries:
                    wait_time = min(2 ** attempt * 2, 60)  # Max 1 minute
                    if self.logger:
                        self.logger.info(f"[GroqService] Error occurred. Waiting {wait_time} seconds before retry.")
                    time.sleep(wait_time)
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
                        if self.logger:
                            self.logger.debug(f"[GroqService] Stream chunk: {chunk}")
                        yield chunk
                    except Exception as e:
                        if self.logger:
                            self.logger.error(f"[GroqService] Stream decode error: {e}")

    def _make_request_with_backoff(self, prompt: str, max_tokens: int = None, temperature: float = None) -> str:
        """
        Make a request to the Groq API with exponential backoff for rate limiting.
        """
        max_retries = 4
        base_delay = 10  # Start with 10 seconds
        
        for attempt in range(max_retries):
            try:
                self.logger.info(f"[GroqService] Sending request to Groq API (attempt {attempt + 1}) with model {self.model}")
                
                # Use tenacity for retries
                @retry(
                    stop=stop_after_attempt(3),
                    wait=wait_exponential(multiplier=1, min=4, max=10),
                    retry=retry_if_exception_type((RateLimitError, TimeoutError)),
                    reraise=True
                )
                def _make_api_call():
                    chat_completion = self.client.chat.completions.create(
                        messages=[
                            {
                                "role": "user",
                                "content": prompt,
                            }
                        ],
                        model=self.model,
                        max_tokens=max_tokens or self.max_tokens,
                        temperature=temperature or self.temperature,
                    )
                    return chat_completion.choices[0].message.content
                
                response = _make_api_call()
                return response
                
            except RateLimitError as e:
                self.logger.error(f"Groq API rate limit error: {e}")
                if attempt < max_retries - 1:
                    # Calculate delay with exponential backoff
                    delay = base_delay * (2 ** attempt)
                    # Add some randomness to prevent thundering herd
                    delay += random.uniform(0, 10)
                    self.logger.info(f"[GroqService] Rate limited. Waiting {delay:.0f} seconds before retry.")
                    time.sleep(delay)
                else:
                    raise
            except Exception as e:
                self.logger.error(f"Groq API error: {e}")
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    self.logger.info(f"[GroqService] Error occurred. Waiting {delay:.0f} seconds before retry.")
                    time.sleep(delay)
                else:
                    raise
