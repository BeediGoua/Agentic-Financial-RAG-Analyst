from __future__ import annotations


EMBEDDING_MODELS = {
    "mini_lm_multilingual": {
        "model_name": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        "query_prefix": "",
        "passage_prefix": "",
    },
    "e5_small": {
        "model_name": "intfloat/multilingual-e5-small",
        "query_prefix": "query: ",
        "passage_prefix": "passage: ",
    },
}


def get_model_config(model_key: str) -> dict:
    if model_key not in EMBEDDING_MODELS:
        raise ValueError(
            f"Unknown model_key={model_key}. Available: {list(EMBEDDING_MODELS)}"
        )

    return EMBEDDING_MODELS[model_key]