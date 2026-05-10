from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import Path

import yaml


def slugify(text: str | None) -> str:
    """
    Convertit un texte en nom de dossier/fichier propre.

    Exemple :
    "Orange Côte d'Ivoire" -> "orange_cote_divoire"
    """
    if not text:
        return "unknown"

    text = normalize_text(text)
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[\s_-]+", "_", text)

    return text.strip("_") or "unknown"


def normalize_text(text: str | None) -> str:
    """
    Normalise un texte pour comparer les noms d'entreprises.

    Exemple :
    "Côte d’Ivoire" -> "cote divoire"
    """
    if text is None:
        return ""

    normalized = unicodedata.normalize("NFKD", str(text))
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    normalized = normalized.replace("’", "'")
    normalized = re.sub(r"\s+", " ", normalized.strip())

    return normalized.lower()


def sha256_file(path: str | Path) -> str:
    """
    Calcule le hash SHA256 d'un fichier.
    Sert à détecter les doublons.
    """
    path = Path(path)
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)

    return h.hexdigest()


def parse_csv_filter(value: str | list[str] | None) -> list[str] | None:
    """
    Transforme :
    "ORAC,SNTS,CIEC"

    en :
    ["ORAC", "SNTS", "CIEC"]
    """
    if value is None:
        return None

    if isinstance(value, list):
        cleaned = [str(x).strip() for x in value if str(x).strip()]
        return cleaned or None

    value = str(value).strip()

    if not value:
        return None

    return [x.strip() for x in value.split(",") if x.strip()]


def parse_year_filter(value: str | list[str] | None) -> list[str] | None:
    """
    Transforme :
    "2023,2024"

    en :
    ["2023", "2024"]
    """
    if value is None:
        return None

    value = value.strip()

    if "-" in value and "," not in value:
        start_str, end_str = value.split("-", 1)
        start_year = int(start_str.strip())
        end_year = int(end_str.strip())
        if start_year > end_year:
            start_year, end_year = end_year, start_year
            
        years = [str(y) for y in range(start_year, end_year + 1)]
        return years

    

    return [x.strip() for x in value.split(",") if x.strip()]


def load_yaml(path: str | Path) -> dict:
    """
    Charge un fichier YAML.
    """
    path = Path(path)

    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def extract_tickers_from_universe(universe_config: dict) -> list[str]:
    """
    Extrait les tickers depuis config/universe.yaml.
    Compatible avec :
    - tickers: [...]
    - companies: [...]
    """
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
        return list(dict.fromkeys(tickers))

    fallback = universe_config.get("tickers", [])

    if isinstance(fallback, dict):
        return list(fallback.keys())

    if isinstance(fallback, list):
        return [str(x) for x in fallback if x]

    return []


def extract_company_aliases_from_universe(universe_config: dict) -> list[str]:
    """
    Extrait tous les noms utiles pour matcher une société :
    - ticker
    - canonical_name
    - short_name
    - aliases
    """
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

        for key in ("ticker", "canonical_name", "short_name"):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                aliases.append(value.strip())

        item_aliases = item.get("aliases", [])
        if isinstance(item_aliases, list):
            aliases.extend(
                [str(v).strip() for v in item_aliases if str(v).strip()]
            )

    if not aliases:
        tickers = universe_config.get("tickers", [])

        if isinstance(tickers, list):
            aliases.extend([str(x).strip() for x in tickers if str(x).strip()])

        elif isinstance(tickers, dict):
            aliases.extend([str(k).strip() for k in tickers.keys()])

    return list(dict.fromkeys(aliases))