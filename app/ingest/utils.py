from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import Path

import yaml


def slugify(text: str) -> str:
    """Convert text into a filesystem-safe slug."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[\s_-]+", "_", text)
    return text.strip("_") or "unknown"


def normalize_text(text: str | None) -> str:
    """Normalize text for fuzzy matching across names and aliases."""
    if text is None:
        return ""
    normalized = unicodedata.normalize("NFKD", str(text))
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    normalized = re.sub(r"\s+", " ", normalized.strip())
    return normalized.lower()


def load_yaml(path: str | Path) -> dict:
    """Load a YAML file and return a dict, defaulting to an empty dict."""
    path = Path(path)
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def extract_tickers_from_universe(universe_config: dict) -> list[str]:
    """Extract tickers from a universe config in either old or new format."""
    if not isinstance(universe_config, dict):
        return []

    companies = universe_config.get("companies")
    tickers: list[str] = []

    if isinstance(companies, list):
        for item in companies:
            if isinstance(item, dict) and item.get("ticker"):
                tickers.append(str(item["ticker"]))
            elif isinstance(item, str):
                tickers.append(item)
    elif isinstance(companies, dict):
        for item in companies.values():
            if isinstance(item, dict) and item.get("ticker"):
                tickers.append(str(item["ticker"]))

    if tickers:
        return tickers

    tickers = universe_config.get("tickers", [])
    if isinstance(tickers, dict):
        return list(tickers.keys())
    if isinstance(tickers, list):
        return [str(x) for x in tickers if x]

    return []


def extract_company_aliases_from_universe(universe_config: dict) -> list[str]:
    """Extract a list of company aliases and canonical names from universe config."""
    if not isinstance(universe_config, dict):
        return []

    aliases: list[str] = []
    companies = universe_config.get("companies")
    entries = []

    if isinstance(companies, list):
        entries = companies
    elif isinstance(companies, dict):
        entries = list(companies.values())

    for item in entries:
        if not isinstance(item, dict):
            continue

        for key in ("aliases", "canonical_name", "short_name", "ticker"):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                aliases.append(value.strip())
            elif isinstance(value, list):
                aliases.extend([str(v).strip() for v in value if isinstance(v, str) and v.strip()])

    if not aliases:
        fallback = universe_config.get("tickers", [])
        if isinstance(fallback, list):
            aliases.extend([str(x) for x in fallback if x])
        elif isinstance(fallback, dict):
            aliases.extend([str(k) for k in fallback.keys()])

    return list(dict.fromkeys(aliases))
