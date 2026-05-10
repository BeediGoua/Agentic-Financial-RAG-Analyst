from __future__ import annotations

import re


SECTION_PATTERNS = {
    "risk": [
        r"\brisques?\b",
        r"\brisk factors?\b",
        r"\brisk management\b",
        r"\bliquidity risk\b",
        r"\brisque de liquidite\b",
    ],
    "debt": [
        r"\bdette\b",
        r"\bendettement\b",
        r"\bdebt\b",
        r"\bborrowings?\b",
        r"\bfinancial liabilities\b",
    ],
    "revenue": [
        r"\bchiffre d'affaires\b",
        r"\brevenus?\b",
        r"\brevenue\b",
        r"\bsales\b",
        r"\bturnover\b",
    ],
    "performance": [
        r"\bperformance\b",
        r"\bresultat\b",
        r"\bprofit\b",
        r"\bnet income\b",
        r"\bebitda\b",
        r"\bebit\b",
    ],
    "cash_flow": [
        r"\bcash flow\b",
        r"\bflux de tresorerie\b",
        r"\btresorerie\b",
    ],
    "strategy": [
        r"\bstrategie\b",
        r"\bstrategy\b",
        r"\boutlook\b",
        r"\bperspectives\b",
    ],
    "governance": [
        r"\bgouvernance\b",
        r"\bgovernance\b",
        r"\bboard\b",
        r"\bconseil d'administration\b",
    ],
    "dividend": [
        r"\bdividendes?\b",
        r"\bdividend\b",
        r"\bpayout\b",
    ],
}


class SectionDetection:
    """
    Détection simple de sections métier.
    Version déterministe, sans LLM.
    """

    def detect_section(self, text: str) -> str | None:
        normalized = text.lower()

        for section, patterns in SECTION_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, normalized, flags=re.IGNORECASE):
                    return section

        return None

    def detect_page_section(self, page: dict) -> str | None:
        text = str(page.get("cleaned_text") or page.get("text") or "")
        return self.detect_section(text[:1500])