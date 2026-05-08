from __future__ import annotations
import json
import re
import time
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from smolagents import tool
from app.ingest.schemas import ReportDocument

BRVM_LISTING_PAGES = [
    "https://www.brvm.org/fr/type-document/rapports-annuels",
    "https://www.brvm.org/fr/type-document/etats-financiers",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 Financial-RAG-Analyst/0.1 educational project"
}


def extract_year(text: str) -> str | None:
    match = re.search(r"(20\d{2})", text)
    return match.group(1) if match else None


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


def infer_company(title: str) -> str | None:
    if ":" in title:
        return title.split(":")[0].strip()
    if "-" in title:
        return title.split("-")[0].strip()
    return None


def extract_title(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(" ", strip=True)
    title = soup.find("title")
    if title:
        return title.get_text(" ", strip=True)
    return "untitled"


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


def find_pdf_links(html: str, page_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    pdfs = set()
    for a in soup.find_all("a", href=True):
        full_url = urljoin(page_url, a["href"])
        if ".pdf" in full_url.lower():
            pdfs.add(full_url)
    return sorted(pdfs)


def normalize_list(value: str | None) -> list[str] | None:
    if not value:
        return None
    return [x.strip().lower() for x in value.split(",") if x.strip()]


def report_matches(
    report: ReportDocument,
    companies: list[str] | None,
    years: list[str] | None,
) -> bool:
    if companies:
        company = (report.company or "").lower()
        title = (report.title or "").lower()
        if not any(c in company or c in title for c in companies):
            return False
    if years:
        if report.year not in years:
            return False
    return True


@tool
def discover_brvm_reports(
    companies: str = "",
    years: str = "",
    max_pages: int = 5,
) -> str:
    """
    Discover BRVM public financial reports and return matching reports as JSON.
    Args:
        companies: Comma-separated company names. Example: "CIE CI,SONATEL". Empty means all companies.
        years: Comma-separated years. Example: "2023,2024". Empty means all years.
        max_pages: Number of BRVM listing pages to scan.
    Returns:
        JSON string containing discovered report metadata.
    """
    session = requests.Session()
    session.headers.update(HEADERS)
    selected_companies = normalize_list(companies)
    selected_years = normalize_list(years)
    reports: list[ReportDocument] = []
    for listing_base_url in BRVM_LISTING_PAGES:
        for page in range(max_pages):
            listing_url = listing_base_url if page == 0 else f"{listing_base_url}?page={page}"
            try:
                response = session.get(listing_url, timeout=60)
                response.raise_for_status()
                document_pages = find_document_pages(response.text, listing_url)
            except Exception:
                continue
            for document_page in document_pages:
                try:
                    response = session.get(document_page, timeout=60)
                    response.raise_for_status()
                    title = extract_title(response.text)
                    pdf_links = find_pdf_links(response.text, document_page)
                    for pdf_url in pdf_links:
                        full_text = f"{title} {pdf_url}"
                        report = ReportDocument(
                            source="BRVM",
                            title=title,
                            page_url=document_page,
                            pdf_url=pdf_url,
                            company=infer_company(title),
                            year=extract_year(full_text),
                            document_type=infer_document_type(full_text),
                        )
                        if report_matches(report, selected_companies, selected_years):
                            reports.append(report)
                    time.sleep(1)
                except Exception:
                    continue
            time.sleep(1)
    unique = {}
    for report in reports:
        unique[report.pdf_url] = report
    return json.dumps(
        [r.model_dump() for r in unique.values()],
        indent=2,
        ensure_ascii=False,
    )
