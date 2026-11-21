from __future__ import annotations

from pathlib import Path

import yaml

from app.core.universe import canonical_company, normalize_company_text


def normalize_company(value: str | None) -> str:
    return normalize_company_text(value)


def company_aliases(value: str) -> set[str]:
    canonical = canonical_company(value, _load_universe())
    if canonical:
        return {canonical}
    return {normalize_company(value)}


def _load_universe() -> dict:
    universe_path = Path("config/universe.yaml")
    if not universe_path.is_file():
        return {"companies": []}
    try:
        data = yaml.safe_load(universe_path.read_text(encoding="utf-8")) or {}
        return data if isinstance(data, dict) else {"companies": []}
    except (OSError, yaml.YAMLError):
        return {"companies": []}


def matches_retrieval_filters(
    record: dict,
    *,
    companies: list[str] | None = None,
    years: list[str] | None = None,
) -> bool:
    company = normalize_company(record.get("company"))
    year = str(record.get("year") or "")

    if companies:
        universe = _load_universe()
        accepted: set[str] = set()
        for value in companies:
            accepted.add(canonical_company(value, universe) or f"unknown:{normalize_company(value)}")
        document_identity = canonical_company(record.get("company"), universe) or f"unknown:{company}"
        if document_identity not in accepted:
            return False
    if years:
        accepted_years = {str(value) for value in years}
        if year not in accepted_years:
            return False
    return True
