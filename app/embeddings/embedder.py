from __future__ import annotations

import json
from pathlib import Path

from sentence_transformers import SentenceTransformer
from tqdm import tqdm

from app.embeddings.models import get_model_config
from app.embeddings.schemas import EmbeddingRecord


class ChunkEmbedder:
    """
    Rôle :
    - lire les chunks JSONL ;
    - calculer les embeddings ;
    - stocker les vecteurs en JSONL ;
    - conserver les métadonnées utiles pour FAISS, retrieval et citations.
    """

    def __init__(
        self,
        chunks_dir: str = "data/chunks",
        embeddings_dir: str = "data/embeddings",
        batch_size: int = 32,
    ):
        self.chunks_dir = Path(chunks_dir)
        self.embeddings_dir = Path(embeddings_dir)
        self.batch_size = batch_size
        self.embeddings_dir.mkdir(parents=True, exist_ok=True)

    def load_chunks(self, path: Path) -> list[dict]:
        rows = []

        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rows.append(json.loads(line))

        return rows

    def build_output_path(self, chunk_file: Path, model_key: str) -> Path:
        relative = chunk_file.relative_to(self.chunks_dir)
        strategy = relative.parts[0]
        
        # On retire le premier dossier (la stratégie) du chemin relatif pour éviter la duplication
        relative_no_strategy = Path(*relative.parts[1:])

        output_path = (
            self.embeddings_dir
            / strategy
            / model_key
            / relative_no_strategy.with_suffix(".embeddings.jsonl")
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        return output_path

    def matches_filter(
        self,
        chunk: dict,
        companies: list[str] | None,
        years: list[str] | None,
    ) -> bool:
        company = str(chunk.get("company") or "").lower()
        year = str(chunk.get("year") or "")

        if companies:
            if not any(c.lower() in company for c in companies):
                return False

        if years:
            if year not in years:
                return False

        return True

    def embed_file(
        self,
        chunk_file: Path,
        model_key: str,
        companies: list[str] | None = None,
        years: list[str] | None = None,
        force: bool = False,
    ) -> dict:
        output_path = self.build_output_path(chunk_file, model_key)

        if output_path.exists() and not force:
            # On compte les lignes pour garder un rapport précis même si on skip
            count = 0
            try:
                with output_path.open("r", encoding="utf-8") as f:
                    for _ in f:
                        count += 1
            except Exception:
                count = 0

            config = get_model_config(model_key)
            return {
                "status": "already_exists",
                "model": model_key,
                "input_path": str(chunk_file),
                "output_path": str(output_path),
                "records_count": count,
                "vector_dimension": config.get("dimension", 0),
            }

        config = get_model_config(model_key)
        model = SentenceTransformer(config["model_name"])
        passage_prefix = config["passage_prefix"]

        chunks = [
            chunk
            for chunk in self.load_chunks(chunk_file)
            if self.matches_filter(chunk, companies, years)
        ]

        if not chunks:
            return {
                "status": "empty",
                "model": model_key,
                "input_path": str(chunk_file),
                "output_path": str(output_path),
                "records_count": 0,
            }

        texts = [passage_prefix + str(chunk.get("text") or "") for chunk in chunks]

        embeddings = model.encode(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=True,
            normalize_embeddings=True,
        )

        records = []

        for chunk, vector in zip(chunks, embeddings):
            record = EmbeddingRecord(
                chunk_id=chunk["chunk_id"],
                chunking_strategy=chunk["chunking_strategy"],
                embedding_model=model_key,
                vector_dimension=len(vector),
                embedding=[float(x) for x in vector],

                source_pdf=chunk["source_pdf"],
                source_url=chunk.get("source_url"),
                company=chunk.get("company"),
                year=chunk.get("year"),
                document_type=chunk.get("document_type"),
                language=chunk.get("language"),

                page_start=chunk.get("page_start"),
                page_end=chunk.get("page_end"),
                section=chunk.get("section"),
                parent_id=chunk.get("parent_id"),
                content_type=chunk.get("content_type"),

                char_count=chunk.get("char_count"),
                word_count=chunk.get("word_count"),

                text=chunk.get("text") or "",
            )

            records.append(record)

        with output_path.open("w", encoding="utf-8") as f:
            for record in records:
                f.write(record.model_dump_json() + "\n")

        return {
            "status": "success",
            "model": model_key,
            "input_path": str(chunk_file),
            "output_path": str(output_path),
            "records_count": len(records),
            "vector_dimension": len(embeddings[0]) if len(embeddings) else 0,
        }

    def run(
        self,
        model_key: str,
        strategies: list[str],
        companies: list[str] | None = None,
        years: list[str] | None = None,
        force: bool = False,
    ) -> list[dict]:
        results = []

        for strategy in strategies:
            strategy_dir = self.chunks_dir / strategy

            if not strategy_dir.exists():
                continue

            chunk_files = list(strategy_dir.rglob("*.chunks.jsonl"))

            for chunk_file in tqdm(
                chunk_files,
                desc=f"Embedding {strategy}/{model_key}",
            ):
                results.append(
                    self.embed_file(
                        chunk_file=chunk_file,
                        model_key=model_key,
                        companies=companies,
                        years=years,
                        force=force,
                    )
                )

        return results