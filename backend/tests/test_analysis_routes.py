from fastapi.testclient import TestClient

import routers.analysis as analysis_router
from main import app


class FakeRagService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []
        self.job_description = None

    def prepare_session(self, session_id: str) -> None:
        self.calls.append(("prepare_session", session_id, ""))

    def index_job_description(self, session_id: str, job_description: str) -> dict:
        self.calls.append(("index_job_description", session_id, job_description))
        self.job_description = job_description
        return {"indexed": True, "chunks_indexed": 2, "sections": ["requirements"], "preview": job_description[:20]}

    def has_indexed_resume(self, session_id: str) -> bool:
        self.calls.append(("has_indexed_resume", session_id, ""))
        return True

    def has_indexed_job_description(self, session_id: str) -> bool:
        self.calls.append(("has_indexed_job_description", session_id, ""))
        return self.job_description is not None

    def retrieve_relevant_chunks(self, session_id: str, query_text: str, document_type: str = "resume", limit=None):
        self.calls.append(("retrieve", session_id, document_type))
        if document_type == "resume":
            return [
                {
                    "text": "Built React and Python systems.",
                    "section": "experience",
                    "document_type": "resume",
                    "confidence": 0.9,
                    "distance": 0.2,
                }
            ]
        if self.job_description:
            return [
                {
                    "text": "Visa sponsorship is not provided.",
                    "section": "sponsorship",
                    "document_type": "job_description",
                    "confidence": 0.92,
                    "distance": 0.16,
                }
            ]
        return []

    def get_job_description_status(self, session_id: str) -> dict:
        return {
            "indexed": self.job_description is not None,
            "chunks_indexed": 1 if self.job_description else 0,
            "job_description": {"text": self.job_description} if self.job_description else None,
        }


class FakeGroqService:
    def __init__(self) -> None:
        self.last_chat = None
        self.route_scope = "comparison"
        self.raise_route_error = False

    def analyze(self, job_description: str, retrieved_chunks: list[dict]) -> dict:
        return {
            "fit_score": 80,
            "grade": "B+",
            "role_detected": "Software Engineer",
            "seniority": "Mid",
            "matched_skills": ["Python"],
            "missing_skills": ["SAP"],
            "radar": {
                "skills": 80,
                "experience": 75,
                "education": 70,
                "culture": 65,
                "keywords": 78,
                "seniority_match": 74,
            },
            "gaps": [{"skill": "SAP", "priority": "High", "reason": "Not shown in resume"}],
            "recommendations": [{"title": "Add ERP context", "detail": "Show adjacent experience", "action": "Rewrite bullets"}],
            "cover_letter_angle": "Bridge strong engineering skills into ERP tooling.",
            "summary": "Solid engineering match with an ERP gap.",
            "sources": [{"section": "experience", "confidence": 0.9, "distance": 0.2}],
        }

    def chat(self, prompt: str, resume_chunks: list[dict], job_chunks: list[dict], history=None, intent: str = "resume") -> dict:
        self.last_chat = {
            "prompt": prompt,
            "resume_chunks": resume_chunks,
            "job_chunks": job_chunks,
            "intent": intent,
        }
        return {
            "answer": "This answer is grounded correctly.",
            "follow_up_suggestions": ["Ask about fit", "Ask about sponsorship", "Ask about SAP"],
            "sources": [
                {
                    "source_type": "job_description" if job_chunks else "resume",
                    "section": "sponsorship" if job_chunks else "experience",
                    "evidence": "Grounded evidence.",
                }
            ],
            "scope": intent,
            "retrieval": [],
        }

    def route_chat_scope(self, prompt: str, history=None) -> str:
        if self.raise_route_error:
            raise ValueError("route failed")
        return self.route_scope


def test_chat_routes_job_questions_to_job_chunks(monkeypatch):
    rag = FakeRagService()
    groq = FakeGroqService()
    rag.job_description = "Visa sponsorship is not provided."
    monkeypatch.setattr(analysis_router, "get_rag_service", lambda: rag)
    monkeypatch.setattr(analysis_router, "get_groq_service", lambda: groq)

    client = TestClient(app)
    response = client.post(
        "/api/analysis/chat",
        headers={"X-Session-Id": "sess_test_user"},
        json={"prompt": "Does it sponsor H-1B?", "history": []},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["scope"] == "job"
    assert groq.last_chat["intent"] == "job"
    assert groq.last_chat["resume_chunks"] == []
    assert len(groq.last_chat["job_chunks"]) == 1


def test_chat_requires_active_job_description_for_job_scope(monkeypatch):
    rag = FakeRagService()
    groq = FakeGroqService()
    monkeypatch.setattr(analysis_router, "get_rag_service", lambda: rag)
    monkeypatch.setattr(analysis_router, "get_groq_service", lambda: groq)

    client = TestClient(app)
    response = client.post(
        "/api/analysis/chat",
        headers={"X-Session-Id": "sess_test_user"},
        json={"prompt": "What are the job responsibilities?", "history": []},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["scope"] == "job"
    assert "no active job description" in payload["answer"].lower()


def test_analyze_persists_job_description_before_analysis(monkeypatch):
    rag = FakeRagService()
    groq = FakeGroqService()
    monkeypatch.setattr(analysis_router, "get_rag_service", lambda: rag)
    monkeypatch.setattr(analysis_router, "get_groq_service", lambda: groq)

    client = TestClient(app)
    response = client.post(
        "/api/analysis/analyze",
        headers={"X-Session-Id": "sess_test_user"},
        json={"job_description": "Responsibilities: Build backend systems.\nRequirements: Python."},
    )

    assert response.status_code == 200
    assert ("index_job_description", "sess_test_user", "Responsibilities: Build backend systems.\nRequirements: Python.") in rag.calls


def test_chat_routes_apply_chances_question_to_comparison(monkeypatch):
    rag = FakeRagService()
    groq = FakeGroqService()
    rag.job_description = "This role requires strong statistics and research."
    monkeypatch.setattr(analysis_router, "get_rag_service", lambda: rag)
    monkeypatch.setattr(analysis_router, "get_groq_service", lambda: groq)

    client = TestClient(app)
    response = client.post(
        "/api/analysis/chat",
        headers={"X-Session-Id": "sess_test_user"},
        json={"prompt": "Should I apply, what are my chances?", "history": []},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["scope"] == "comparison"
    assert groq.last_chat["intent"] == "comparison"
    assert len(groq.last_chat["resume_chunks"]) == 1
    assert len(groq.last_chat["job_chunks"]) == 1


def test_chat_routes_company_question_to_job_chunks(monkeypatch):
    rag = FakeRagService()
    groq = FakeGroqService()
    rag.job_description = "Two Sigma is looking for a Quantitative Researcher."
    monkeypatch.setattr(analysis_router, "get_rag_service", lambda: rag)
    monkeypatch.setattr(analysis_router, "get_groq_service", lambda: groq)

    client = TestClient(app)
    response = client.post(
        "/api/analysis/chat",
        headers={"X-Session-Id": "sess_test_user"},
        json={"prompt": "Tell me about the company", "history": []},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["scope"] == "job"
    assert groq.last_chat["intent"] == "job"
    assert groq.last_chat["resume_chunks"] == []
    assert len(groq.last_chat["job_chunks"]) == 1


def test_chat_uses_llm_router_for_ambiguous_prompt(monkeypatch):
    rag = FakeRagService()
    groq = FakeGroqService()
    rag.job_description = "Two Sigma is looking for a Quantitative Researcher."
    groq.route_scope = "job"
    monkeypatch.setattr(analysis_router, "get_rag_service", lambda: rag)
    monkeypatch.setattr(analysis_router, "get_groq_service", lambda: groq)

    client = TestClient(app)
    response = client.post(
        "/api/analysis/chat",
        headers={"X-Session-Id": "sess_test_user"},
        json={"prompt": "check jd and tell me the company", "history": []},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["scope"] == "job"
    assert groq.last_chat["intent"] == "job"
    assert groq.last_chat["resume_chunks"] == []
    assert len(groq.last_chat["job_chunks"]) == 1


def test_chat_falls_back_to_comparison_when_llm_router_fails(monkeypatch):
    rag = FakeRagService()
    groq = FakeGroqService()
    rag.job_description = "This role requires strong statistics and research."
    groq.raise_route_error = True
    monkeypatch.setattr(analysis_router, "get_rag_service", lambda: rag)
    monkeypatch.setattr(analysis_router, "get_groq_service", lambda: groq)

    client = TestClient(app)
    response = client.post(
        "/api/analysis/chat",
        headers={"X-Session-Id": "sess_test_user"},
        json={"prompt": "comp fit?", "history": []},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["scope"] == "comparison"
    assert groq.last_chat["intent"] == "comparison"
    assert len(groq.last_chat["resume_chunks"]) == 1
    assert len(groq.last_chat["job_chunks"]) == 1
