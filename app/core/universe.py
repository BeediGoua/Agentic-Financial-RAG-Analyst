from __future__ import annotations

from pathlib import Path
import unicodedata
import yaml


def normalize_company_text(text: str | None) -> str:
    if not text:
        return ""

    text = unicodedata.normalize("NFKD", str(text))
    text = text.encode("ascii", "ignore").decode("ascii")
    return " ".join(text.lower().replace("’", "'").split())


class UniverseManager:
    def __init__(self, config_path: str = "config/universe.yaml"):
        self.config_path = Path(config_path)

        if not self.config_path.exists():
            self.data = {"companies": []}
            return

        with self.config_path.open("r", encoding="utf-8") as f:
            self.data = yaml.safe_load(f) or {"companies": []}

    def companies(self) -> list[dict]:
        companies = self.data.get("companies", [])
        return companies if isinstance(companies, list) else []

    def expand_company_filters(self, filters: list[str] | None) -> list[str] | None:
        if not filters:
            return None

        expanded: list[str] = []

        for query in filters:
            query_norm = normalize_company_text(query)
            matched = False

            for company in self.companies():
                candidates = [
                    company.get("ticker"),
                    company.get("canonical_name"),
                    company.get("short_name"),
                    *(company.get("aliases") or []),
                ]

                candidates_norm = [normalize_company_text(x) for x in candidates if x]

                if query_norm in candidates_norm:
                    expanded.extend([x for x in candidates if x])
                    matched = True
                    break

            if not matched:
                expanded.append(query)

        return list(dict.fromkeys(expanded))

    def get_company_by_filter(self, value: str) -> dict | None:
        value_norm = normalize_company_text(value)

        for company in self.companies():
            candidates = [
                company.get("ticker"),
                company.get("canonical_name"),
                company.get("short_name"),
                *(company.get("aliases") or []),
            ]

            if value_norm in [normalize_company_text(x) for x in candidates if x]:
                return company

        return None