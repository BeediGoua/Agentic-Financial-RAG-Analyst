import os
from smolagents import HfApiModel, LiteLLMModel


def build_model(provider: str = "ollama", model_id: str | None = None):
    if provider == "ollama":
        return LiteLLMModel(
            model_id=model_id or "ollama/qwen2.5-coder:7b",
            api_base=os.getenv("OLLAMA_API_BASE", "http://localhost:11434"),
            temperature=0.1,
        )
    if provider == "huggingface":
        return HfApiModel(
            model_id=model_id or "Qwen/Qwen2.5-Coder-32B-Instruct",
            temperature=0.1,
            max_tokens=4096,
        )
    raise ValueError(f"Unknown provider: {provider}")
