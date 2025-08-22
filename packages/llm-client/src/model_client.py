"""
model_client.py — Minimal OpenAI Chat API client for deterministic single-label JSON output.

This module does not include the OpenAI SDK to keep dependencies light; instead
it expects the caller to provide a compatible client or we use requests.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Tuple

import requests


class OpenAIClient:
    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")

    def chat(self, model: str, messages: List[Dict[str, str]], temperature: float = 0.0, top_p: float = 0.1) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
        }
        resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
        if resp.status_code >= 300:
            raise RuntimeError(f"OpenAI API error {resp.status_code}: {resp.text}")
        data = resp.json()
        # Expect a single choice with message.content
        return data["choices"][0]["message"]["content"].strip()


def call_classifier(client: OpenAIClient, model_id: str, system: str, labels_block: str, user_payload: str) -> str:
    messages = [
        {"role": "system", "content": system},
        {"role": "system", "content": labels_block},
        {"role": "user", "content": user_payload},
    ]
    return client.chat(model=model_id, messages=messages, temperature=0.0, top_p=0.1)


