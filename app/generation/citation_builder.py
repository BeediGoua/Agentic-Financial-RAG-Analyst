from __future__ import annotations

from app.generation.schemas import Citation


class CitationBuilder:
    """
    Construit les citations depuis les chunks utilisés.
    """

    def build(
        self,
        reranked_results: list[dict],
    ) -> list[Citation]:
        citations = []

        seen = set()

        for item in reranked_results:
            key = (
                item.get("source_pdf"),
                item.get("page_start"),
                item.get("section"),
            )

            if key in seen:
                continue

            seen.add(key)

            citations.append(
                Citation(
                    company=item.get("company"),
                    year=item.get("year"),
                    document_type=item.get("document_type"),
                    source_pdf=item["source_pdf"],
                    page_start=item.get("page_start"),
                    page_end=item.get("page_end"),
                    section=item.get("section"),
                )
            )

        return citations