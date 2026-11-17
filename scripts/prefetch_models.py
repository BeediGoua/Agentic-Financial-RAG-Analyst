"""Explicit, opt-in model downloads; never run during unit tests or CI.

Models in app.embeddings.models / app.reranking.models can change. This
script reads the registries to avoid duplicating model IDs in setup code.
"""
from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Download Hugging Face models explicitly")
    parser.add_argument("--all", action="store_true", help="Download every configured model")
    args = parser.parse_args()
    from app.embeddings.models import EMBEDDING_MODELS
    from app.reranking.models import RERANKING_MODELS
    from sentence_transformers import CrossEncoder, SentenceTransformer

    embedding_names = (
        [cfg["model_name"] for cfg in EMBEDDING_MODELS.values()]
        if args.all
        else [EMBEDDING_MODELS["mini_lm_multilingual"]["model_name"]]
    )
    ranking_names = (
        [cfg["model_name"] for cfg in RERANKING_MODELS.values()]
        if args.all
        else [RERANKING_MODELS["tiny_cross_encoder"]["model_name"]]
    )
    for name in dict.fromkeys(embedding_names):
        print(f"Downloading embedding model: {name}", flush=True)
        SentenceTransformer(name)
    for name in dict.fromkeys(ranking_names):
        print(f"Downloading reranker: {name}", flush=True)
        CrossEncoder(name)
    print("Model downloads completed. Check hashes/revisions before production.")


if __name__ == "__main__":
    main()
