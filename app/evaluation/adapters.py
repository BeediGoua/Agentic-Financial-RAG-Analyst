from __future__ import annotations

import time
from typing import Protocol


class RetrieverAdapter(Protocol):
    def search(self, **kwargs): ...


def run_adapter_search(
    retriever,
    *,
    query: str,
    method: str,
    strategy: str,
    model_key: str | None,
    top_k: int,
    companies: list[str] | None,
    years: list[str] | None,
) -> tuple[list[dict], str, str | None, float]:
    started = time.perf_counter()
    kwargs = {
        "query": query,
        "strategy": strategy,
        "top_k": top_k,
        "companies": companies,
        "years": years,
    }
    if method != "bm25":
        kwargs["model_key"] = model_key
    try:
        raw = retriever.search(**kwargs)
        if hasattr(raw, "__iter__") and not isinstance(raw, (str, bytes)):
            results = [
                item.model_dump() if hasattr(item, "model_dump") else dict(item)
                for item in raw
            ]
        else:
            raise ValueError("Retriever returned an invalid result container")
        status = "success" if results else "empty"
        error = None
    except FileNotFoundError as exc:
        results = []
        status = "missing_corpus"
        error = str(exc)
    except Exception as exc:
        results = []
        message = str(exc)
        if "invalid_index" in message or "Unable to read FAISS" in message or "Rejected invalid" in message:
            status = "invalid_index"
        elif "model" in message.lower() and ("unavailable" in message.lower() or "download" in message.lower()):
            status = "model_unavailable"
        else:
            status = "error"
        error = message
    latency_ms = (time.perf_counter() - started) * 1000.0
    return results, status, error, latency_ms
