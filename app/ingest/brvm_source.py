from __future__ import annotations

import re
import time
from urllib.parse import urljoin

import requests
import urllib3
from bs4 import BeautifulSoup
from tqdm import tqdm

from app.core.universe import UniverseManager
from app.ingest.schemas import ReportDocument
from app.ingest.utils import normalize_text, parse_csv_filter, parse_year_filter

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


BRVM_LISTING_PAGES = [
    "https://www.brvm.org/fr/type-document/rapports-annuels",
    "https://www.brvm.org/fr/type-document/etats-financiers",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 Financial-RAG-Analyst/0.1 educational project"
}


class BRVMSourceAgent:
    """
    Agent déterministe.
    Rôle :
    - découvrir les rapports PDF BRVM ;
    - gérer les filtres ticker / nom société via universe.yaml ;
    - scanner les pages générales BRVM ;
    - scanner aussi les pages société dédiées.
    """

    def __init__(
        self,
        companies: list[str] | str | None = None,
        years: list[str] | str | None = None,
        max_pages: int = 5,
        sleep_seconds: float = 0.5,
        universe_path: str = "config/universe.yaml",
    ):
        self.universe = UniverseManager(config_path=universe_path)

        if isinstance(companies, str):
            companies = parse_csv_filter(companies)

        expanded_companies = self.universe.expand_company_filters(companies)

        self.companies = (
            [normalize_text(c) for c in expanded_companies]
            if expanded_companies
            else None
        )

        self.years = parse_year_filter(years)
        self.max_pages = max_pages
        self.sleep_seconds = sleep_seconds

        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.session.verify = False

    def get_html(self, url: str) -> str:
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        return response.text

    @staticmethod
    def extract_year(text: str) -> str | None:
        match = re.search(r"(20\d{2})", text)
        return match.group(1) if match else None

    @staticmethod
    def infer_document_type(text: str) -> str:
        text = normalize_text(text)

        if "rapport" in text and "annuel" in text:
            return "annual_report"

        if "etats financiers" in text or "etat financier" in text:
            return "financial_statements"

        if "trimestre" in text or "trimestriel" in text:
            return "quarterly_report"

        if "semestre" in text or "semestriel" in text:
            return "half_year_report"

        return "other_report"

    @staticmethod
    def infer_company(title: str) -> str | None:
        if ":" in title:
            return title.split(":")[0].strip()

        if "-" in title:
            return title.split("-")[0].strip()

        return None

    @staticmethod
    def extract_title(html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")

        h1 = soup.find("h1")
        if h1:
            return h1.get_text(" ", strip=True)

        title = soup.find("title")
        if title:
            return title.get_text(" ", strip=True)

        return "untitled_report"

    @staticmethod
    def find_document_pages(html: str, base_url: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        links: set[str] = set()

        keywords = [
            "rapport",
            "etats financiers",
            "états financiers",
            "etat financier",
            "exercice",
            "trimestre",
            "semestre",
        ]

        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(" ", strip=True)
            candidate = normalize_text(f"{href} {text}")

            if any(normalize_text(k) in candidate for k in keywords):
                full_url = urljoin(base_url, href)

                if "brvm.org" in full_url and "/fr/" in full_url:
                    links.add(full_url)

        return sorted(links)

    @staticmethod
    def find_pdf_links(html: str, page_url: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        pdfs: set[str] = set()

        for a in soup.find_all("a", href=True):
            full_url = urljoin(page_url, a["href"])

            if ".pdf" in full_url.lower():
                pdfs.add(full_url)

        return sorted(pdfs)

    def get_company_report_pages(self) -> list[str]:
        """
        Retourne les pages BRVM dédiées aux sociétés.

        Exemple :
        ORAC -> https://www.brvm.org/fr/rapports-societe-cotes/orange-ci
        """

        pages: list[str] = []

        if not self.companies:
            for company in self.universe.companies():
                page = company.get("brvm_company_page")
                if page:
                    pages.append(page)

            return list(dict.fromkeys(pages))

        for company_filter in self.companies:
            company = self.universe.get_company_by_filter(company_filter)

            if company and company.get("brvm_company_page"):
                pages.append(company["brvm_company_page"])

        return list(dict.fromkeys(pages))

    def report_matches(self, report: ReportDocument) -> bool:
        if self.companies:
            searchable_text = " ".join(
                [
                    report.company or "",
                    report.title or "",
                    report.document_type or "",
                    report.pdf_url or "",
                    report.page_url or "",
                    report.source_url or "",
                ]
            )

            normalized = normalize_text(searchable_text)

            if not any(company_filter in normalized for company_filter in self.companies):
                return False

        if self.years:
            if report.year not in self.years:
                return False

        return True

    def build_report(
        self,
        title: str,
        page_url: str,
        pdf_url: str,
        forced_company: str | None = None,
    ) -> ReportDocument:
        full_text = f"{title} {page_url} {pdf_url}"

        return ReportDocument(
            source="BRVM",
            title=title,
            page_url=page_url,
            pdf_url=pdf_url,
            company=forced_company or self.infer_company(title),
            year=self.extract_year(full_text),
            document_type=self.infer_document_type(full_text),
            source_url=page_url,
            language="fr",
        )

    def discover_from_listing_pages(self) -> list[ReportDocument]:
        reports: list[ReportDocument] = []

        total_steps = len(BRVM_LISTING_PAGES) * self.max_pages

        with tqdm(total=total_steps, desc="Exploration BRVM listings", unit="page") as pbar:
            for listing_base_url in BRVM_LISTING_PAGES:
                for page in range(self.max_pages):
                    listing_url = (
                        listing_base_url
                        if page == 0
                        else f"{listing_base_url}?page={page}"
                    )

                    try:
                        html = self.get_html(listing_url)
                        document_pages = self.find_document_pages(html, listing_url)

                    except Exception as e:
                        tqdm.write(f"[WARN] Listing impossible: {listing_url} | {e}")
                        pbar.update(1)
                        continue

                    for document_page in document_pages:
                        try:
                            doc_html = self.get_html(document_page)
                            title = self.extract_title(doc_html)
                            pdf_links = self.find_pdf_links(doc_html, document_page)

                            for pdf_url in pdf_links:
                                report = self.build_report(
                                    title=title,
                                    page_url=document_page,
                                    pdf_url=pdf_url,
                                )

                                if self.report_matches(report):
                                    reports.append(report)

                            time.sleep(self.sleep_seconds)

                        except Exception as e:
                            tqdm.write(
                                f"[WARN] Page document impossible: {document_page} | {e}"
                            )

                    time.sleep(self.sleep_seconds)
                    pbar.update(1)

        return reports

    def discover_from_company_pages(self) -> list[ReportDocument]:
        reports: list[ReportDocument] = []
        company_pages = self.get_company_report_pages()

        with tqdm(
            total=len(company_pages),
            desc="Exploration BRVM pages sociétés",
            unit="company",
        ) as pbar:
            for company_page in company_pages:
                try:
                    html = self.get_html(company_page)
                    title = self.extract_title(html)

                    company_meta = self.universe.get_company_by_filter(company_page)
                    forced_company = None

                    if company_meta:
                        forced_company = (
                            company_meta.get("short_name")
                            or company_meta.get("canonical_name")
                            or company_meta.get("ticker")
                        )

                    document_pages = self.find_document_pages(html, company_page)

                    # Cas 1 : la page société contient directement des PDF.
                    direct_pdf_links = self.find_pdf_links(html, company_page)

                    for pdf_url in direct_pdf_links:
                        report = self.build_report(
                            title=title,
                            page_url=company_page,
                            pdf_url=pdf_url,
                            forced_company=forced_company,
                        )

                        if self.report_matches(report):
                            reports.append(report)

                    # Cas 2 : la page société liste des pages détail.
                    for document_page in document_pages:
                        try:
                            doc_html = self.get_html(document_page)
                            doc_title = self.extract_title(doc_html)
                            pdf_links = self.find_pdf_links(doc_html, document_page)

                            for pdf_url in pdf_links:
                                report = self.build_report(
                                    title=doc_title,
                                    page_url=document_page,
                                    pdf_url=pdf_url,
                                    forced_company=forced_company,
                                )

                                if self.report_matches(report):
                                    reports.append(report)

                            time.sleep(self.sleep_seconds)

                        except Exception as e:
                            tqdm.write(
                                f"[WARN] Page document société impossible: {document_page} | {e}"
                            )

                except Exception as e:
                    tqdm.write(f"[WARN] Page société impossible: {company_page} | {e}")

                time.sleep(self.sleep_seconds)
                pbar.update(1)

        return reports

    def discover_reports(self) -> list[ReportDocument]:
        """
        Point d’entrée principal.
        Combine :
        - pages générales BRVM ;
        - pages dédiées aux sociétés ;
        - déduplication par pdf_url.
        """

        reports: list[ReportDocument] = []

        reports.extend(self.discover_from_listing_pages())
        reports.extend(self.discover_from_company_pages())

        unique: dict[str, ReportDocument] = {}

        for report in reports:
            unique[report.pdf_url] = report

        return list(unique.values())


if __name__ == "__main__":
    agent = BRVMSourceAgent(
        companies="ORAC",
        years="2025",
        max_pages=2,
    )

    docs = agent.discover_reports()

    print(f"Discovered reports: {len(docs)}")

    for doc in docs[:10]:
        print(doc.model_dump())