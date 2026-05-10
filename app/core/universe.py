from __future__ import annotations

from pathlib import Path
import unicodedata
import yaml


def normalize_company_text(text: str | None) -> str:
    if not text:
        return ""

    text = unicodedata.normalize("NFKD", str(text))
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.replace("’", "'")
    text = text.replace("-", " ")
    text = text.replace("_", " ")

    return " ".join(text.lower().split())


class UniverseManager:
    """
    Référentiel métier des sociétés BRVM.

    Rôle :
    - convertir ticker -> aliases ;
    - retrouver une société depuis un nom ;
    - retrouver une société depuis une URL BRVM ;
    - fournir canonical_name / short_name / slug.
    """

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

    def company_candidates(self, company: dict) -> list[str]:
        candidates: list[str] = []

        for key in (
            "ticker",
            "canonical_name",
            "short_name",
            "brvm_report_slug",
            "brvm_company_page",
        ):
            value = company.get(key)
            if value:
                candidates.append(str(value))

        aliases = company.get("aliases") or []
        if isinstance(aliases, list):
            candidates.extend([str(x) for x in aliases if x])

        return list(dict.fromkeys(candidates))

    def expand_company_filters(self, filters: list[str] | None) -> list[str] | None:
        if not filters:
            return None

        expanded: list[str] = []

        for query in filters:
            query_norm = normalize_company_text(query)
            matched = False

            for company in self.companies():
                candidates = self.company_candidates(company)
                candidates_norm = [normalize_company_text(x) for x in candidates]

                if query_norm in candidates_norm:
                    expanded.extend(candidates)
                    matched = True
                    break

            if not matched:
                expanded.append(query)

        return list(dict.fromkeys(expanded))

    def get_company_by_filter(self, value: str) -> dict | None:
        value_norm = normalize_company_text(value)

        for company in self.companies():
            candidates = self.company_candidates(company)
            candidates_norm = [normalize_company_text(x) for x in candidates]

            if value_norm in candidates_norm:
                return company

        return None

    def get_company_by_page_url(self, page_url: str) -> dict | None:
        page_url_norm = normalize_company_text(page_url)

        for company in self.companies():
            slug = company.get("brvm_report_slug")
            company_page = company.get("brvm_company_page")

            candidates = []

            if slug:
                candidates.append(slug)

            if company_page:
                candidates.append(company_page)

            for candidate in candidates:
                candidate_norm = normalize_company_text(candidate)

                if candidate_norm and candidate_norm in page_url_norm:
                    return company

        return None

    def get_display_name(self, company: dict | None) -> str | None:
        if not company:
            return None

        return (
            company.get("short_name")
            or company.get("canonical_name")
            or company.get("ticker")
        )