from datetime import datetime, timedelta, timezone
from functools import lru_cache
import json
from pathlib import Path
import re
import shutil
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
        self._legacy_storage_cleaned = False
        self._legacy_chunk_cleanup_done = False

    def prepare_session(self, session_id: str) -> None:
        self.cleanup_legacy_global_storage()
        self.cleanup_legacy_global_chunks()
        self.cleanup_expired_sessions()
        self.touch_session(session_id)

    def has_indexed_resume(self, session_id: str) -> bool:
        return self._session_chunk_count(session_id, document_type="resume") > 0

    def has_indexed_job_description(self, session_id: str) -> bool:
        return self._session_chunk_count(session_id, document_type="job_description") > 0

    def get_resume_status(self, session_id: str) -> dict:
        manifest = self._load_manifest(session_id, document_type="resume")
        chunks_indexed = self._session_chunk_count(session_id, document_type="resume")
        return {
            "indexed": chunks_indexed > 0,
            "chunks_indexed": chunks_indexed,
            "resume": (
                {
                    **manifest,
                    "chunks_indexed": chunks_indexed,
                }
                if manifest
                else None
            ),
        }

    def get_job_description_status(self, session_id: str) -> dict:
        manifest = self._load_manifest(session_id, document_type="job_description")
        chunks_indexed = self._session_chunk_count(session_id, document_type="job_description")
        return {
            "indexed": chunks_indexed > 0,
            "chunks_indexed": chunks_indexed,
            "job_description": (
                {
                    **manifest,
                    "chunks_indexed": chunks_indexed,
                }
                if manifest
                else None
            ),
        }

    def index_resume(self, session_id: str, filename: str, pdf_bytes: bytes) -> dict:
        raw_text = extract_text_from_pdf(pdf_bytes)
        if not raw_text.strip():
            raise ValueError("No readable text was found in the uploaded PDF.")

        chunks = chunk_resume_text(raw_text)
        if not chunks:
            raise ValueError("Resume text could not be split into indexable sections.")

        documents = [chunk["text"] for chunk in chunks]
        metadatas = [
            {
                "session_id": session_id,
                "document_type": "resume",
                "section": chunk["section"],
                "source_file": filename,
                "chunk_index": index,
            }
            for index, chunk in enumerate(chunks)
        ]
        ids = [str(uuid4()) for _ in chunks]
        embeddings = self.embedding_model.encode(documents).tolist()

        previous_manifest = self._load_manifest(session_id, document_type="resume")
        self._delete_session_documents(session_id, document_type="resume")
        self._delete_stored_resume(previous_manifest)
        pdf_path = self._store_upload(session_id, filename, pdf_bytes)
        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )

        manifest = {
            "session_id": session_id,
            "filename": filename,
            "stored_path": str(pdf_path),
            "sections": sorted({chunk["section"] for chunk in chunks}),
        }
        self._save_manifest(session_id, document_type="resume", manifest=manifest)

        return {
            "indexed": True,
            "filename": filename,
            "chunks_indexed": len(chunks),
            "sections": manifest["sections"],
        }

    def index_job_description(self, session_id: str, job_description: str) -> dict:
        normalized_text = job_description.strip()
        if not normalized_text:
            raise ValueError("Job description text is required.")

        chunks = chunk_job_description_text(normalized_text)
        if not chunks:
            raise ValueError("Job description could not be split into indexable sections.")

        documents = [chunk["text"] for chunk in chunks]
        metadatas = [
            {
                "session_id": session_id,
                "document_type": "job_description",
                "section": chunk["section"],
                "chunk_index": index,
            }
            for index, chunk in enumerate(chunks)
        ]
        ids = [str(uuid4()) for _ in chunks]
        embeddings = self.embedding_model.encode(documents).tolist()

        self._delete_session_documents(session_id, document_type="job_description")
        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )

        manifest = {
            "session_id": session_id,
            "text": normalized_text,
            "preview": normalized_text[:240],
            "sections": sorted({chunk["section"] for chunk in chunks}),
        }
        self._save_manifest(session_id, document_type="job_description", manifest=manifest)

        return {
            "indexed": True,
            "chunks_indexed": len(chunks),
            "sections": manifest["sections"],
            "preview": manifest["preview"],
        }

    def retrieve_relevant_chunks(
        self,
        session_id: str,
        query_text: str,
        document_type: str = "resume",
        limit: int | None = None,
    ) -> list[dict]:
        top_k = limit or self.settings.retrieval_top_k
        if self._session_chunk_count(session_id, document_type=document_type) == 0:
            return []

        query_embedding = self.embedding_model.encode([query_text]).tolist()[0]
        result = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=self._document_filter(session_id, document_type),
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
                    "document_type": metadata.get("document_type", document_type),
                    "metadata": metadata,
                    "distance": distance,
                    "confidence": self._distance_to_confidence(distance),
                }
            )

        return retrieved_chunks

    def cleanup_expired_sessions(self) -> None:
        sessions_root = self.settings.upload_dir / "sessions"
        if not sessions_root.exists():
            return

        cutoff = self._utc_now() - timedelta(hours=self.settings.session_ttl_hours)
        for session_dir in sessions_root.iterdir():
            if not session_dir.is_dir():
                continue

            session_meta = self._load_session_meta(session_dir)
            last_accessed_at = self._parse_timestamp(
                session_meta.get("last_accessed_at") if session_meta else None
            )
            if last_accessed_at is None:
                last_accessed_at = self._directory_timestamp(session_dir)

            if last_accessed_at and last_accessed_at < cutoff:
                self._delete_session_data(session_dir.name)

    def cleanup_legacy_global_storage(self) -> None:
        if self._legacy_storage_cleaned:
            return

        legacy_paths = (
            self.settings.upload_dir / "latest_resume.json",
            self.settings.upload_dir / "resume.pdf",
        )
        for legacy_path in legacy_paths:
            if legacy_path.exists() and legacy_path.is_file():
                legacy_path.unlink()

        self._legacy_storage_cleaned = True

    def cleanup_legacy_global_chunks(self) -> None:
        if self._legacy_chunk_cleanup_done:
            return

        collection_data = self.collection.get(include=["metadatas"])
        ids = collection_data.get("ids", [])
        metadatas = collection_data.get("metadatas", [])
        stale_ids = [
            chunk_id
            for chunk_id, metadata in zip(ids, metadatas, strict=False)
            if not metadata or not metadata.get("session_id")
        ]
        if stale_ids:
            self.collection.delete(ids=stale_ids)

        self._legacy_chunk_cleanup_done = True

    def touch_session(self, session_id: str) -> None:
        session_dir = self._session_dir(session_id)
        session_dir.mkdir(parents=True, exist_ok=True)
        session_meta = self._load_session_meta(session_dir) or {"session_id": session_id}
        session_meta["session_id"] = session_id
        session_meta["last_accessed_at"] = self._utc_now().isoformat()
        self._session_meta_path(session_id).write_text(
            json.dumps(session_meta, indent=2),
            encoding="utf-8",
        )

    def _store_upload(self, session_id: str, filename: str, pdf_bytes: bytes) -> Path:
        destination_dir = self._session_resume_dir(session_id)
        destination_dir.mkdir(parents=True, exist_ok=True)
        sanitized_name = Path(filename).name or "resume.pdf"
        destination = destination_dir / sanitized_name
        destination.write_bytes(pdf_bytes)
        return destination

    def _session_chunk_count(self, session_id: str, document_type: str) -> int:
        result = self.collection.get(
            where=self._document_filter(session_id, document_type),
            include=[],
        )
        return len(result.get("ids", []))

    def _delete_session_documents(self, session_id: str, document_type: str) -> None:
        result = self.collection.get(
            where=self._document_filter(session_id, document_type),
            include=[],
        )
        if not result.get("ids"):
            return
        self.collection.delete(where=self._document_filter(session_id, document_type))

    def _session_dir(self, session_id: str) -> Path:
        return self.settings.upload_dir / "sessions" / self._safe_session_fragment(session_id)

    def _session_resume_dir(self, session_id: str) -> Path:
        return self._session_dir(session_id) / "resume"

    def _session_meta_path(self, session_id: str) -> Path:
        return self._session_dir(session_id) / "session_meta.json"

    def _manifest_path(self, session_id: str, document_type: str) -> Path:
        if document_type == "resume":
            return self._session_dir(session_id) / "latest_resume.json"
        if document_type == "job_description":
            return self._session_dir(session_id) / "latest_job_description.json"
        raise ValueError(f"Unsupported document type: {document_type}")

    def _save_manifest(self, session_id: str, document_type: str, manifest: dict) -> None:
        manifest_path = self._manifest_path(session_id, document_type)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    def _load_manifest(self, session_id: str, document_type: str) -> dict | None:
        manifest_path = self._manifest_path(session_id, document_type)
        if not manifest_path.exists():
            return None

        return json.loads(manifest_path.read_text(encoding="utf-8"))

    def _delete_stored_resume(self, manifest: dict | None) -> None:
        if not manifest:
            return

        stored_path = manifest.get("stored_path")
        if not stored_path:
            return

        path = Path(stored_path)
        if path.exists():
            path.unlink()

    def _delete_session_data(self, session_fragment: str) -> None:
        self._delete_session_documents(session_fragment, document_type="resume")
        self._delete_session_documents(session_fragment, document_type="job_description")
        session_dir = self.settings.upload_dir / "sessions" / session_fragment
        if session_dir.exists():
            shutil.rmtree(session_dir, ignore_errors=True)

    def _load_session_meta(self, session_dir: Path) -> dict | None:
        meta_path = session_dir / "session_meta.json"
        if not meta_path.exists():
            return None

        return json.loads(meta_path.read_text(encoding="utf-8"))

    def _directory_timestamp(self, session_dir: Path) -> datetime | None:
        try:
            return datetime.fromtimestamp(session_dir.stat().st_mtime, tz=timezone.utc)
        except FileNotFoundError:
            return None

    @staticmethod
    def _parse_timestamp(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _safe_session_fragment(session_id: str) -> str:
        return re.sub(r"[^A-Za-z0-9_-]+", "_", session_id).strip("_") or "anonymous"

    @staticmethod
    def _document_filter(session_id: str, document_type: str) -> dict:
        return {
            "$and": [
                {"session_id": {"$eq": session_id}},
                {"document_type": {"$eq": document_type}},
            ]
        }

    @staticmethod
    def _distance_to_confidence(distance: float | None) -> float | None:
        if distance is None:
            return None
        return round(max(0.0, min(1.0, 1 - (distance / 2))), 4)


@lru_cache
def get_rag_service() -> RagService:
    return RagService()


JD_SECTION_PATTERNS = {
    "title": re.compile(r"^(job title|title|role)$", re.IGNORECASE),
    "summary": re.compile(r"^(summary|overview|about the role|about this role|position summary)$", re.IGNORECASE),
    "responsibilities": re.compile(
        r"^(responsibilities|key responsibilities|what you'll do|what you will do|duties)$",
        re.IGNORECASE,
    ),
    "requirements": re.compile(
        r"^(requirements|qualifications|required qualifications|minimum qualifications|must have)$",
        re.IGNORECASE,
    ),
    "preferred": re.compile(
        r"^(preferred qualifications|nice to have|preferred skills|bonus qualifications)$",
        re.IGNORECASE,
    ),
    "benefits": re.compile(r"^(benefits|perks|what we offer)$", re.IGNORECASE),
    "location": re.compile(r"^(location|work location|work model)$", re.IGNORECASE),
    "sponsorship": re.compile(
        r"^(work authorization|sponsorship|visa sponsorship|immigration support)$",
        re.IGNORECASE,
    ),
}


def chunk_job_description_text(raw_text: str, max_chars: int = 1200) -> list[dict]:
    sections: list[dict] = []
    current_name = "general"
    current_lines: list[str] = []

    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        matched_name = _match_jd_section_name(stripped)
        if matched_name:
            if current_lines:
                sections.append({"section": current_name, "text": "\n".join(current_lines).strip()})
            current_name = matched_name
            current_lines = [stripped]
            continue

        current_lines.append(stripped)

    if current_lines:
        sections.append({"section": current_name, "text": "\n".join(current_lines).strip()})

    if not sections:
        sections = [{"section": "general", "text": raw_text.strip()}]

    expanded_chunks: list[dict] = []
    for section in sections:
        expanded_chunks.extend(_split_text_chunk(section["section"], section["text"], max_chars=max_chars))

    return [chunk for chunk in expanded_chunks if chunk["text"]]


def _match_jd_section_name(line: str) -> str | None:
    normalized = re.sub(r"[:\s]+$", "", line).strip()
    for section_name, pattern in JD_SECTION_PATTERNS.items():
        if pattern.match(normalized):
            return section_name
    return None


def _split_text_chunk(section: str, text: str, max_chars: int = 1200) -> list[dict]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(text) <= max_chars:
        return [{"section": section, "text": text}]

    chunks: list[dict] = []
    current_lines: list[str] = []
    current_length = 0

    for line in lines:
        projected_length = current_length + len(line) + 1
        if current_lines and projected_length > max_chars:
            chunks.append({"section": section, "text": "\n".join(current_lines)})
            current_lines = []
            current_length = 0

        current_lines.append(line)
        current_length += len(line) + 1

    if current_lines:
        chunks.append({"section": section, "text": "\n".join(current_lines)})

    return chunks
