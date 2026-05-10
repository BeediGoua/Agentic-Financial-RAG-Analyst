from __future__ import annotations

import re
import time
from urllib.parse import urljoin

import requests
import urllib3
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from app.ingest.schemas import ReportDocument
from app.ingest.utils import parse_csv_filter, parse_year_filter


BRVM_LISTING_PAGES = [
    "https://www.brvm.org/fr/type-document/rapports-annuels",
    "https://www.brvm.org/fr/type-document/etats-financiers",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 Financial-RAG-Analyst/0.1 educational project"
}


class BRVMSourceAgent:
    """Discovers public BRVM report PDFs from official listing pages."""

    def __init__(
        self,
        companies: str | None = None,
        years: str | None = None,
        max_pages: int = 5,
        sleep_seconds: float = 0.5,  # Réduit de 1.0 à 0.5
    ):
        self.companies = parse_csv_filter(companies)
        self.years = parse_year_filter(years)
        self.max_pages = max_pages
        self.sleep_seconds = sleep_seconds
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.session.verify = False

    def get_html(self, url: str) -> str:
        response = self.session.get(url, timeout=30)  # Réduit de 60 à 30
        response.raise_for_status()
        return response.text

    @staticmethod
    def extract_year(text: str) -> str | None:
        match = re.search(r"(20\d{2})", text)
        return match.group(1) if match else None

    @staticmethod
    def infer_document_type(text: str) -> str:
        text = text.lower()

        if "rapport" in text and "annuel" in text:
            return "annual_report"
        if "etats financiers" in text or "états financiers" in text:
            return "financial_statements"
        if "trimestre" in text or "trimestriel" in text:
            return "quarterly_report"
        if "semestre" in text or "semestriel" in text:
            return "half_year_report"

        return "other"

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

        return "untitled"

    @staticmethod
    def find_document_pages(html: str, base_url: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        links = set()

        keywords = [
            "rapport",
            "etats financiers",
            "états financiers",
            "exercice",
            "trimestre",
            "semestre",
        ]

        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(" ", strip=True)
            candidate = f"{href} {text}".lower()

            if any(k in candidate for k in keywords):
                full_url = urljoin(base_url, href)
                if "brvm.org" in full_url and "/fr/" in full_url:
                    links.add(full_url)

        return sorted(links)

    @staticmethod
    def find_pdf_links(html: str, page_url: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        pdfs = set()

        for a in soup.find_all("a", href=True):
            full_url = urljoin(page_url, a["href"])
            if ".pdf" in full_url.lower():
                pdfs.add(full_url)

        return sorted(pdfs)

    def report_matches(self, report: ReportDocument) -> bool:
        if self.companies:
            company = (report.company or "").lower()
            title = (report.title or "").lower()
            if not any(c in company or c in title for c in self.companies):
                return False

        if self.years:
            if report.year not in self.years:
                return False

        return True

    def discover_reports(self) -> list[ReportDocument]:
        reports: list[ReportDocument] = []
        from tqdm import tqdm

        total_steps = len(BRVM_LISTING_PAGES) * self.max_pages
        with tqdm(total=total_steps, desc="Exploration BRVM", unit="page") as pbar:
            for listing_base_url in BRVM_LISTING_PAGES:
                for page in range(self.max_pages):
                    listing_url = listing_base_url if page == 0 else f"{listing_base_url}?page={page}"

                try:
                    html = self.get_html(listing_url)
                    document_pages = self.find_document_pages(html, listing_url)
                except Exception as e:
                    print(f"[WARN] Listing impossible: {listing_url} | {e}")
                    continue

                for document_page in document_pages:
                    try:
                        doc_html = self.get_html(document_page)
                        title = self.extract_title(doc_html)
                        pdf_links = self.find_pdf_links(doc_html, document_page)

                        for pdf_url in pdf_links:
                            full_text = f"{title} {pdf_url}"
                            report = ReportDocument(
                                source="BRVM",
                                title=title,
                                page_url=document_page,
                                pdf_url=pdf_url,
                                company=self.infer_company(title),
                                year=self.extract_year(full_text),
                                document_type=self.infer_document_type(full_text),
                                source_url=listing_url,
                                language="fr",
                            )

                            if self.report_matches(report):
                                reports.append(report)

                        time.sleep(self.sleep_seconds)

                    except Exception as e:
                        print(f"\n[WARN] Page document impossible: {document_page} | {e}")
                        continue  # Continue avec la page suivante

                time.sleep(self.sleep_seconds)
                pbar.update(1)

        unique: dict[str, ReportDocument] = {}
        for report in reports:
            unique[report.pdf_url] = report

        return list(unique.values())


if __name__ == "__main__":
    agent = BRVMSourceAgent(companies="CIE CI", years="2024", max_pages=2)
    docs = agent.discover_reports()
    print(f"Discovered reports: {len(docs)}")
    for doc in docs[:5]:
        print(doc.model_dump())
