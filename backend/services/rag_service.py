from functools import lru_cache
import json
from pathlib import Path
from uuid import uuid4

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

from services.pdf_parser import chunk_resume_text, extract_text_from_pdf
from services.settings import get_settings


class RagService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = chromadb.PersistentClient(
            path=str(self.settings.chroma_persist_path),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name=self.settings.chroma_collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        self.embedding_model = SentenceTransformer(self.settings.embedding_model)

    def has_indexed_resume(self) -> bool:
        return self.collection.count() > 0

    def get_resume_status(self) -> dict:
        manifest = self._load_manifest()
        return {
            "indexed": self.has_indexed_resume(),
            "chunks_indexed": self.collection.count(),
            "resume": manifest,
        }

    def index_resume(self, filename: str, pdf_bytes: bytes) -> dict:
        pdf_path = self._store_upload(filename, pdf_bytes)
        raw_text = extract_text_from_pdf(pdf_bytes)
        if not raw_text.strip():
            raise ValueError("No readable text was found in the uploaded PDF.")

        chunks = chunk_resume_text(raw_text)
        if not chunks:
            raise ValueError("Resume text could not be split into indexable sections.")

        documents = [chunk["text"] for chunk in chunks]
        metadatas = [
            {
                "section": chunk["section"],
                "source_file": filename,
                "stored_path": str(pdf_path),
                "chunk_index": index,
            }
            for index, chunk in enumerate(chunks)
        ]
        ids = [str(uuid4()) for _ in chunks]
        embeddings = self.embedding_model.encode(documents).tolist()

        self._reset_collection()
        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )

        manifest = {
            "filename": filename,
            "stored_path": str(pdf_path),
            "sections": sorted({chunk["section"] for chunk in chunks}),
        }
        self._save_manifest(manifest)

        return {
            "indexed": True,
            "filename": filename,
            "chunks_indexed": len(chunks),
            "sections": manifest["sections"],
        }

    def retrieve_relevant_chunks(self, query_text: str, limit: int | None = None) -> list[dict]:
        top_k = limit or self.settings.retrieval_top_k
        if not self.has_indexed_resume():
            return []

        query_embedding = self.embedding_model.encode([query_text]).tolist()[0]
        result = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        retrieved_chunks: list[dict] = []
        for document, metadata, distance in zip(documents, metadatas, distances, strict=False):
            retrieved_chunks.append(
                {
                    "text": document,
                    "section": metadata.get("section", "general"),
                    "metadata": metadata,
                    "distance": distance,
                    "confidence": self._distance_to_confidence(distance),
                }
            )

        return retrieved_chunks

    def _reset_collection(self) -> None:
        existing_count = self.collection.count()
        if existing_count == 0:
            return

        ids = self.collection.get(include=[])["ids"]
        if ids:
            self.collection.delete(ids=ids)

    def _store_upload(self, filename: str, pdf_bytes: bytes) -> Path:
        sanitized_name = Path(filename).name or "resume.pdf"
        destination = self.settings.upload_dir / sanitized_name
        destination.write_bytes(pdf_bytes)
        return destination

    def _manifest_path(self) -> Path:
        return self.settings.upload_dir / "latest_resume.json"

    def _save_manifest(self, manifest: dict) -> None:
        self._manifest_path().write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    def _load_manifest(self) -> dict | None:
        manifest_path = self._manifest_path()
        if not manifest_path.exists():
            return None

        return json.loads(manifest_path.read_text(encoding="utf-8"))

    @staticmethod
    def _distance_to_confidence(distance: float | None) -> float | None:
        if distance is None:
            return None
        return round(max(0.0, min(1.0, 1 - (distance / 2))), 4)


@lru_cache
def get_rag_service() -> RagService:
    return RagService()
