# groq_api_tester.py
import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL")  # Default model

if not GROQ_API_KEY:
    raise ValueError("Missing GROQ_API_KEY in environment variables.")

def test_groq_api(prompt: str):
    """
    Send a test request to the Groq API and print the response.
    """
    url = "https://api.groq.com/openai/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": GROQ_MODEL,
        "temperature": 0.2,
        "max_tokens": 256,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
    }
    
    print("Sending request to Groq API...")
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code != 200:
        print(f"Error {response.status_code}: {response.text}")
        return
    
    data = response.json()
    print("\nGroq API Response:\n")
    print(data["choices"][0]["message"]["content"])

if __name__ == "__main__":
    test_prompt = "Give me 3 creative project ideas in AI and NLP."
    test_groq_api(test_prompt)
