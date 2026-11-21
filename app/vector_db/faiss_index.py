from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path

import faiss
import numpy as np
from tqdm import tqdm

from app.core.artifact_cache import (
    build_fingerprint,
    sha256_file,
    validate_faiss_artifact,
    write_artifact_manifest,
)
from app.core.atomic import atomic_text_writer
from app.embeddings.models import get_model_config
from app.vector_db.schemas import VectorMetadata


def validate_embedding_vector(
    embedding,
    *,
    expected_dimension: int,
) -> np.ndarray:
    try:
        vector = np.asarray(embedding, dtype=np.float32)
    except (TypeError, ValueError) as exc:
        raise ValueError("Embedding contains invalid numeric values") from exc
    if vector.ndim != 1:
        raise ValueError("Embedding must be one-dimensional")
    if vector.shape[0] != expected_dimension:
        raise ValueError(
            f"Invalid dimension: expected {expected_dimension}, got {vector.shape[0]}"
        )
    if not np.isfinite(vector).all():
        raise ValueError("Embedding contains NaN or infinite values")
    norm = float(np.linalg.norm(vector))
    if not np.isfinite(norm) or norm <= 0:
        raise ValueError("Embedding has zero or invalid norm")
    return vector


def write_faiss_safely(index, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
        faiss.write_index(index, str(temporary_path))
        candidate = faiss.read_index(str(temporary_path))
        if candidate.ntotal != index.ntotal:
            raise ValueError("Temporary FAISS index lost vectors")
        if candidate.d != index.d:
            raise ValueError("Temporary FAISS dimension mismatch")
        os.replace(temporary_path, destination)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


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
        relative = embedding_file.relative_to(
            self.embeddings_dir / strategy / model
        )
        expected_suffix = ".embeddings.jsonl"
        if not relative.name.endswith(expected_suffix):
            raise ValueError(f"Unexpected embedding filename: {relative.name}")
        stem = relative.name[:-len(expected_suffix)]
        if not stem:
            raise ValueError("Empty embedding file identity")
        output_root = (
            self.output_dir
            / strategy
            / model
            / relative.parent
            / stem
        )
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
        fingerprint = build_fingerprint(
            source_path=embedding_file,
            stage="faiss_index",
            params={
                "strategy": strategy,
                "model": model,
                "model_revision": get_model_config(model)["revision"],
            },
        )
        fingerprint["model_revision"] = get_model_config(model)["revision"]

        try:
            if not force:
                manifest_path = Path(str(index_path) + ".build.json")
                if index_path.exists() and metadata_path.exists() and manifest_path.exists():
                    config = get_model_config(model)
                    valid, vectors_count, vector_dimension = validate_faiss_artifact(
                        index_path,
                        metadata_path,
                        expected_fingerprint=fingerprint,
                        expected_dimension=int(config["dimension"]),
                        expected_strategy=strategy,
                        expected_model=model,
                        expected_revision=str(config["revision"]),
                    )
                    if valid:
                        return {
                            "status": "already_exists",
                            "strategy": strategy,
                            "model": model,
                            "input_path": str(embedding_file),
                            "index_path": str(index_path),
                            "metadata_path": str(metadata_path),
                            "vectors_count": vectors_count,
                            "vector_dimension": vector_dimension,
                        }

            rows = self.load_jsonl(embedding_file)

            if not rows:
                return {
                    "status": "empty",
                    "strategy": strategy,
                    "model": model,
                    "input_path": str(embedding_file),
                    "vectors_count": 0,
                }

            config = get_model_config(model)
            expected_dimension = int(config["dimension"])
            vectors = []
            metadata_rows: list[VectorMetadata] = []
            seen_chunk_ids: set[str] = set()

            for row in rows:
                if row.get("chunking_strategy") != strategy:
                    raise ValueError("Embedding chunking strategy mismatch")
                if row.get("embedding_model") != model:
                    raise ValueError("Embedding model mismatch")

                chunk_id = str(row.get("chunk_id") or "")
                if not chunk_id:
                    raise ValueError("Missing chunk identifier")
                if chunk_id in seen_chunk_ids:
                    raise ValueError(f"Duplicate chunk_id: {chunk_id}")
                seen_chunk_ids.add(chunk_id)

                vector = validate_embedding_vector(
                    row.get("embedding"),
                    expected_dimension=expected_dimension,
                )
                vector_id = len(vectors)
                vectors.append(vector)

                metadata_rows.append(
                    VectorMetadata(
                        vector_id=vector_id,
                        chunk_id=chunk_id,
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

                if not row.get("source_pdf"):
                    raise ValueError("Missing document provenance")
                if not str(row.get("text") or "").strip():
                    raise ValueError("Missing chunk text")
                page_start = row.get("page_start")
                page_end = row.get("page_end")
                if page_start is not None and int(page_start) < 1:
                    raise ValueError("Invalid page_start")
                if page_end is not None:
                    if page_start is not None and int(page_end) < int(page_start):
                        raise ValueError("Invalid page range")

            if not vectors:
                raise ValueError("No valid embeddings")

            matrix = np.stack(vectors).astype(np.float32)
            if len(metadata_rows) != matrix.shape[0]:
                raise ValueError("Metadata/vector cardinality mismatch")
            if [item.vector_id for item in metadata_rows] != list(range(matrix.shape[0])):
                raise ValueError("Non-contiguous vector identifiers")
            vector_dimension = matrix.shape[1]
            norms = np.linalg.norm(matrix, axis=1, keepdims=True)
            matrix = matrix / norms
            index = faiss.IndexFlatIP(vector_dimension)
            index.add(matrix)

            backup_dir = index_path.parent / ".g2-faiss-backup"
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
            backup_dir.mkdir(parents=True, exist_ok=True)
            index_backup = backup_dir / "index.faiss"
            metadata_backup = backup_dir / "metadata.jsonl"
            manifest_backup = backup_dir / "index.faiss.build.json"
            if index_path.exists():
                shutil.copy2(index_path, index_backup)
            if metadata_path.exists():
                shutil.copy2(metadata_path, metadata_backup)
            manifest_path = Path(str(index_path) + ".build.json")
            if manifest_path.exists():
                shutil.copy2(manifest_path, manifest_backup)
            try:
                write_faiss_safely(index, index_path)
                with atomic_text_writer(metadata_path) as f:
                    for item in metadata_rows:
                        f.write(item.model_dump_json() + "\n")
                manifest_path = write_artifact_manifest(index_path, fingerprint)
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest["metadata_sha256"] = sha256_file(metadata_path)
                manifest["metadata_size"] = metadata_path.stat().st_size
                with atomic_text_writer(manifest_path) as manifest_output:
                    json.dump(
                        manifest,
                        manifest_output,
                        ensure_ascii=False,
                        indent=2,
                        sort_keys=True,
                    )
            except Exception:
                if index_backup.exists():
                    os.replace(index_backup, index_path)
                else:
                    index_path.unlink(missing_ok=True)
                if metadata_backup.exists():
                    os.replace(metadata_backup, metadata_path)
                else:
                    metadata_path.unlink(missing_ok=True)
                if manifest_backup.exists():
                    os.replace(manifest_backup, manifest_path)
                else:
                    manifest_path.unlink(missing_ok=True)
                raise
            finally:
                shutil.rmtree(backup_dir, ignore_errors=True)

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