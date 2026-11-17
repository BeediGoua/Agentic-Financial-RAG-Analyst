from __future__ import annotations


EMBEDDING_MODELS = {
    "mini_lm_multilingual": {
        "model_name": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        "revision": "e8f8c211226b894fcb81acc59f3b34ba3efd5f42",
        "query_prefix": "",
        "passage_prefix": "",
        "dimension": 384,
    },
    "e5_small": {
        "model_name": "intfloat/multilingual-e5-small",
        "revision": "614241f622f53c4eeff9890bdc4f31cfecc418b3",
        "query_prefix": "query: ",
        "passage_prefix": "passage: ",
        "dimension": 384,
    },
}


def get_model_config(model_key: str) -> dict:
    if model_key not in EMBEDDING_MODELS:
        raise ValueError(
            f"Unknown model_key={model_key}. Available: {list(EMBEDDING_MODELS)}"
        )

    return EMBEDDING_MODELS[model_key]