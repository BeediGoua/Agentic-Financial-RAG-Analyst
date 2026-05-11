from __future__ import annotations

import requests

from app.generation.prompts import (
    SYSTEM_PROMPT,
    build_user_prompt,
)


class OllamaGenerator:
    """
    Génération locale via Ollama.
    """

    def __init__(
        self,
        model_name: str = "qwen2.5:7b",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.0,
    ):
        self.model_name = model_name
        self.base_url = base_url
        self.temperature = temperature

    def generate(
        self,
        query: str,
        contexts: list[str],
    ) -> str:
        prompt = build_user_prompt(
            query=query,
            contexts=contexts,
        )

        response = requests.post(
            f"{self.base_url}/api/chat",
            json={
                "model": self.model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                "stream": False,
                "options": {
                    "temperature": self.temperature,
                },
            },
            timeout=300,
        )

        response.raise_for_status()

        data = response.json()

        return (
            data.get("message", {})
            .get("content", "")
            .strip()
        )