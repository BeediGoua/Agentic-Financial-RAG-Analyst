from __future__ import annotations

import unicodedata
from pathlib import Path

import yaml

from app.ingest.utils import normalize_text


def normalize_company(value: str | None) -> str:
    text = normalize_text(str(value or "")).lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    return text


def company_aliases(value: str) -> set[str]:
    normalized = normalize_company(value)
    universe_path = Path("config/universe.yaml")
    if not universe_path.is_file():
        return {normalized}
    try:
        data = yaml.safe_load(universe_path.read_text(encoding="utf-8")) or {}
        for company in data.get("companies", []):
            aliases = [
                company.get("canonical_name"),
                company.get("short_name"),
                *company.get("aliases", []),
            ]
            normalized_aliases = {
                normalize_company(alias)
                for alias in aliases
                if alias
            }
            if normalized in normalized_aliases:
                return normalized_aliases
    except (OSError, yaml.YAMLError):
        pass
    return {normalized}


def matches_retrieval_filters(
    record: dict,
    *,
    companies: list[str] | None = None,
    years: list[str] | None = None,
) -> bool:
    company = normalize_company(record.get("company"))
    year = str(record.get("year") or "")

    if companies:
        accepted_aliases: set[str] = set()
        for value in companies:
            accepted_aliases.update(company_aliases(value))
        if not any(
            name and name in company
            for name in accepted_aliases
        ):
            return False
    if years:
        accepted_years = {str(value) for value in years}
        if year not in accepted_years:
            return False
    return True
