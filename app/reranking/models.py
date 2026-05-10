from __future__ import annotations


RERANKING_MODELS = {
    "mini_cross_encoder": {
        "model_name": "cross-encoder/ms-marco-MiniLM-L-6-v2",
        "description": "Lightweight cross-encoder reranker baseline.",
    },
    "tiny_cross_encoder": {
        "model_name": "cross-encoder/ms-marco-TinyBERT-L-2-v2",
        "description": "Very lightweight reranker, faster but usually less accurate.",
    },
}


def get_reranking_model_config(model_key: str) -> dict:
    if model_key not in RERANKING_MODELS:
        raise ValueError(
            f"Unknown reranking model: {model_key}. "
            f"Available: {list(RERANKING_MODELS)}"
        )

    return RERANKING_MODELS[model_key]