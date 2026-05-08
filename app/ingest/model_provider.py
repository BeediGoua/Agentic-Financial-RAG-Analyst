import os
from smolagents import LiteLLMModel


def test_ollama_connection(api_base: str = "http://localhost:11434") -> bool:
    """Test if Ollama server is running and accessible."""
    try:
        import httpx
        client = httpx.Client(timeout=2)
        response = client.get(f"{api_base}/api/tags")
        return response.status_code == 200
    except Exception:
        return False


def test_huggingface_token() -> bool:
    """Test if HuggingFace API token is configured."""
    token = os.getenv("HUGGINGFACE_API_KEY", "").strip()
    return len(token) > 10


def build_model(provider: str = "auto", model_id: str | None = None):
    """
    Build LLM model with automatic fallback.
    
    provider options:
    - "ollama": Use local Ollama server
    - "huggingface": Use HuggingFace API
    - "auto": Try Ollama first, then HuggingFace, then fail with helpful message
    """
    api_base = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")

    # Auto mode: try multiple providers
    if provider == "auto":
        print("🔍 Auto-detecting LLM provider...")
        
        # Try Ollama first
        if test_ollama_connection(api_base):
            print("✅ Ollama found! Using local Ollama server")
            return LiteLLMModel(
                model_id=model_id or "ollama/qwen2.5-coder:7b",
                api_base=api_base,
                temperature=0.1,
            )
        
        # Try HuggingFace
        if test_huggingface_token():
            print("✅ HuggingFace token found! Using HuggingFace API")
            return LiteLLMModel(
                model_id=model_id or "Qwen/Qwen2.5-Coder-32B-Instruct",
                temperature=0.1,
            )
        
        # No providers available
        print("\n❌ No LLM provider available!")
        print("\nOptions:")
        print("  1. Start Ollama: ollama serve")
        print("  2. Set HuggingFace token: export HUGGINGFACE_API_KEY='hf_...'")
        print("  3. Use simple_ingest.py instead: python simple_ingest.py")
        raise RuntimeError(
            "No LLM provider found. Please configure Ollama or HuggingFace token."
        )

    # Explicit provider selection
    if provider == "ollama":
        return LiteLLMModel(
            model_id=model_id or "ollama/qwen2.5-coder:7b",
            api_base=api_base,
            temperature=0.1,
        )
    
    if provider == "huggingface":
        return LiteLLMModel(
            model_id=model_id or "Qwen/Qwen2.5-Coder-32B-Instruct",
            temperature=0.1,
        )
    
    raise ValueError(f"Unknown provider: {provider}. Use 'ollama', 'huggingface', or 'auto'.")
