from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    groq_api_key: str | None = Field(default=None, alias="GROQ_API_KEY")
    chroma_persist_path: Path = Field(default=Path("./chroma_store"), alias="CHROMA_PERSIST_PATH")
    upload_dir: Path = Field(default=Path("./uploads"), alias="UPLOAD_DIR")
    cors_origin: str = Field(default="http://localhost:5173", alias="CORS_ORIGIN")
    embedding_model: str = Field(default="all-MiniLM-L6-v2", alias="EMBEDDING_MODEL")
    chroma_collection_name: str = Field(default="resume_chunks", alias="CHROMA_COLLECTION_NAME")
    retrieval_top_k: int = Field(default=5, alias="RETRIEVAL_TOP_K")
    groq_model: str = Field(default="llama-3.3-70b-versatile", alias="GROQ_MODEL")
    retrieval_confidence_floor: float = Field(default=0.35, alias="RETRIEVAL_CONFIDENCE_FLOOR")
    session_ttl_hours: int = Field(default=24, alias="SESSION_TTL_HOURS")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def ensure_directories(self) -> None:
        self.chroma_persist_path = self._resolve_path(self.chroma_persist_path)
        self.upload_dir = self._resolve_path(self.upload_dir)
        self.chroma_persist_path.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origin.split(",") if origin.strip()]

    @staticmethod
    def _resolve_path(path: Path) -> Path:
        return path if path.is_absolute() else BASE_DIR / path


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings
