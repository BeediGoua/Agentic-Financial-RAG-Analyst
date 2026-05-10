from __future__ import annotations

import json
from pathlib import Path

import faiss
import numpy as np
from tqdm import tqdm

from app.vector_db.schemas import VectorMetadata


class FaissIndexBuilder:
    """
    Rôle :
    - lire les embeddings JSONL ;
    - construire un index FAISS ;
    - sauvegarder index.faiss ;
    - sauvegarder metadata.jsonl aligné avec les vecteurs ;
    - conserver les métadonnées nécessaires au retrieval, aux citations et à l'évaluation.
    """

    def __init__(
        self,
        embeddings_dir: str = "data/embeddings",
        output_dir: str = "data/vector_db/faiss",
    ):
        self.embeddings_dir = Path(embeddings_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def load_jsonl(self, path: Path) -> list[dict]:
        rows = []

        if not path.exists():
            return rows

        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rows.append(json.loads(line))

        return rows

    def discover_embedding_files(
        self,
        strategies: list[str] | None = None,
        models: list[str] | None = None,
    ) -> list[Path]:
        """
        Découvre automatiquement tous les fichiers embeddings disponibles.

        Structure attendue :
        data/embeddings/{strategy}/{model}/.../*.embeddings.jsonl
        """

        files = list(self.embeddings_dir.rglob("*.embeddings.jsonl"))
        selected = []

        for file in files:
            relative = file.relative_to(self.embeddings_dir)
            parts = relative.parts

            if len(parts) < 3:
                continue

            strategy = parts[0]
            model = parts[1]

            if strategies and strategy not in strategies:
                continue

            if models and model not in models:
                continue

            selected.append(file)

        return selected

    def infer_strategy_model(self, embedding_file: Path) -> tuple[str, str]:
        relative = embedding_file.relative_to(self.embeddings_dir)
        parts = relative.parts

        if len(parts) < 3:
            raise ValueError(
                f"Chemin embeddings invalide: {embedding_file}. "
                "Structure attendue: data/embeddings/{strategy}/{model}/..."
            )

        return parts[0], parts[1]

    def build_output_paths(self, embedding_file: Path) -> tuple[Path, Path]:
        strategy, model = self.infer_strategy_model(embedding_file)

        relative_parent = embedding_file.relative_to(
            self.embeddings_dir / strategy / model
        ).parent

        output_root = self.output_dir / strategy / model / relative_parent
        output_root.mkdir(parents=True, exist_ok=True)

        index_path = output_root / "index.faiss"
        metadata_path = output_root / "metadata.jsonl"

        return index_path, metadata_path

    def build_index_for_file(
        self,
        embedding_file: Path,
        force: bool = False,
    ) -> dict:
        strategy, model = self.infer_strategy_model(embedding_file)
        index_path, metadata_path = self.build_output_paths(embedding_file)

        if index_path.exists() and metadata_path.exists() and not force:
            return {
                "status": "already_exists",
                "strategy": strategy,
                "model": model,
                "input_path": str(embedding_file),
                "index_path": str(index_path),
                "metadata_path": str(metadata_path),
            }

        try:
            rows = self.load_jsonl(embedding_file)

            if not rows:
                return {
                    "status": "empty",
                    "strategy": strategy,
                    "model": model,
                    "input_path": str(embedding_file),
                    "vectors_count": 0,
                }

            vectors = []
            metadata_rows: list[VectorMetadata] = []

            for vector_id, row in enumerate(rows):
                embedding = row.get("embedding")

                if not embedding:
                    continue

                vectors.append(embedding)

                metadata_rows.append(
                    VectorMetadata(
                        vector_id=vector_id,
                        chunk_id=row["chunk_id"],
                        chunking_strategy=row["chunking_strategy"],
                        embedding_model=row["embedding_model"],

                        source_pdf=row["source_pdf"],
                        source_url=row.get("source_url"),
                        company=row.get("company"),
                        year=row.get("year"),
                        document_type=row.get("document_type"),
                        language=row.get("language"),

                        page_start=row.get("page_start"),
                        page_end=row.get("page_end"),
                        section=row.get("section"),
                        parent_id=row.get("parent_id"),
                        content_type=row.get("content_type"),

                        char_count=row.get("char_count"),
                        word_count=row.get("word_count"),

                        text=row.get("text") or "",
                    )
                )

            if not vectors:
                return {
                    "status": "empty",
                    "strategy": strategy,
                    "model": model,
                    "input_path": str(embedding_file),
                    "vectors_count": 0,
                }

            matrix = np.array(vectors, dtype="float32")

            if len(matrix.shape) != 2:
                raise ValueError("Embedding matrix must be 2D")

            vector_dimension = matrix.shape[1]

            # Les embeddings sont déjà normalisés en phase 5.
            # IndexFlatIP donne une similarité de type cosine si les vecteurs sont normalisés.
            index = faiss.IndexFlatIP(vector_dimension)
            index.add(matrix)

            faiss.write_index(index, str(index_path))

            with metadata_path.open("w", encoding="utf-8") as f:
                for item in metadata_rows:
                    f.write(item.model_dump_json() + "\n")

            return {
                "status": "success",
                "strategy": strategy,
                "model": model,
                "input_path": str(embedding_file),
                "index_path": str(index_path),
                "metadata_path": str(metadata_path),
                "vectors_count": len(metadata_rows),
                "vector_dimension": vector_dimension,
            }

        except Exception as e:
            return {
                "status": "error",
                "strategy": strategy,
                "model": model,
                "input_path": str(embedding_file),
                "error": str(e),
            }

    def run(
        self,
        strategies: list[str] | None = None,
        models: list[str] | None = None,
        force: bool = False,
    ) -> list[dict]:
        embedding_files = self.discover_embedding_files(
            strategies=strategies,
            models=models,
        )

        results = []

        for embedding_file in tqdm(embedding_files, desc="Building FAISS indexes"):
            results.append(
                self.build_index_for_file(
                    embedding_file=embedding_file,
                    force=force,
                )
            )

        return results