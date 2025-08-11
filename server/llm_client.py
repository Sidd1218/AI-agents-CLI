# server/llm_client.py
import os
import requests

API_URL = "https://router.huggingface.co/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {os.environ['HF_API_TOKEN']}",
}

MODEL = os.getenv("HF_MODEL_ID", "Qwen/Qwen3-0.6B:fireworks-ai")

def ask_model(prompt: str) -> str:
    payload = {
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "model": MODEL
    }
    response = requests.post(API_URL, headers=headers, json=payload)
    data = response.json()
    return data["choices"][0]["message"]["content"]
