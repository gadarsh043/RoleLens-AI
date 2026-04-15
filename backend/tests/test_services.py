from services.groq_service import GroqService
from services.rag_service import RagService


class FakeCollection:
    def __init__(self) -> None:
        self.deleted_ids = None

    def get(self, include=None):
        return {
            "ids": ["old-1", "active-1", "old-2"],
            "metadatas": [
                None,
                {"session_id": "sess_live", "document_type": "resume"},
                {"document_type": "resume"},
            ],
        }

    def delete(self, ids=None, where=None):
        self.deleted_ids = ids


def test_groq_chat_response_validation_rejects_invalid_source_type():
    service = GroqService.__new__(GroqService)

    try:
        service._parse_chat_response(
            '{"answer":"x","follow_up_suggestions":["a"],"sources":[{"source_type":"other","section":"s","evidence":"e"}]}'
        )
        assert False, "Expected ValueError for invalid source_type"
    except ValueError as exc:
        assert "failed validation" in str(exc)


def test_groq_analysis_response_validation_rejects_invalid_grade():
    service = GroqService.__new__(GroqService)

    try:
        service._parse_analysis_response(
            '{"fit_score":80,"grade":"Z","role_detected":"Engineer","seniority":"Mid","matched_skills":[],"missing_skills":[],"radar":{"skills":80,"experience":70,"education":60,"culture":50,"keywords":90,"seniority_match":75},"gaps":[],"recommendations":[],"cover_letter_angle":"x","summary":"y"}'
        )
        assert False, "Expected ValueError for invalid grade"
    except ValueError as exc:
        assert "failed validation" in str(exc)


def test_legacy_global_chunk_cleanup_deletes_rows_without_session_id():
    service = RagService.__new__(RagService)
    service.collection = FakeCollection()
    service._legacy_chunk_cleanup_done = False

    service.cleanup_legacy_global_chunks()

    assert service.collection.deleted_ids == ["old-1", "old-2"]
    assert service._legacy_chunk_cleanup_done is True


def test_document_filter_uses_valid_chroma_and_expression():
    assert RagService._document_filter("sess_123", "resume") == {
        "$and": [
            {"session_id": {"$eq": "sess_123"}},
            {"document_type": {"$eq": "resume"}},
        ]
    }
