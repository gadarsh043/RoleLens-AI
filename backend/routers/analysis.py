from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from services.groq_service import get_groq_service
from services.rag_service import get_rag_service
from services.settings import get_settings

router = APIRouter()


class AnalyzeRequest(BaseModel):
    job_description: str = Field(..., min_length=20)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=5)
    history: list[ChatMessage] = Field(default_factory=list)


@router.post("/analyze")
async def analyze_resume(payload: AnalyzeRequest):
    rag_service = get_rag_service()
    if not rag_service.has_indexed_resume():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload and index a resume before running analysis.",
        )

    retrieved_chunks = rag_service.retrieve_relevant_chunks(payload.job_description)
    if not retrieved_chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No resume content was retrieved for this job description.",
        )

    settings = get_settings()
    average_confidence = sum(chunk["confidence"] or 0 for chunk in retrieved_chunks) / len(retrieved_chunks)
    if average_confidence < settings.retrieval_confidence_floor:
        return {
            "fit_score": 0,
            "grade": "D",
            "role_detected": "Unknown",
            "seniority": "Mid",
            "matched_skills": [],
            "missing_skills": [],
            "radar": {
                "skills": 0,
                "experience": 0,
                "education": 0,
                "culture": 0,
                "keywords": 0,
                "seniority_match": 0,
            },
            "gaps": [],
            "recommendations": [
                {
                    "title": "Low-confidence retrieval",
                    "detail": "The indexed resume content did not strongly match this job description.",
                    "action": "Upload a clearer resume PDF or try a more specific job description.",
                }
            ],
            "cover_letter_angle": "Insufficient grounded evidence to suggest a strong angle.",
            "summary": "The system could not retrieve enough relevant resume evidence to produce a reliable analysis.",
            "sources": [
                {
                    "section": chunk["section"],
                    "confidence": chunk["confidence"],
                    "distance": chunk["distance"],
                }
                for chunk in retrieved_chunks
            ],
        }

    try:
        groq_service = get_groq_service()
        return groq_service.analyze(payload.job_description, retrieved_chunks)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Groq analysis failed: {exc}",
        ) from exc


@router.post("/chat")
async def chat_with_resume(payload: ChatRequest):
    rag_service = get_rag_service()
    if not rag_service.has_indexed_resume():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload and index a resume before starting chat.",
        )

    retrieved_chunks = rag_service.retrieve_relevant_chunks(payload.prompt)
    if not retrieved_chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No resume content was retrieved for this prompt.",
        )

    settings = get_settings()
    average_confidence = sum(chunk["confidence"] or 0 for chunk in retrieved_chunks) / len(retrieved_chunks)
    if average_confidence < settings.retrieval_confidence_floor:
        return {
            "answer": "I could not find strong enough evidence in the indexed resume to answer that reliably.",
            "follow_up_suggestions": [
                "Ask about a specific skill or project.",
                "Paste a more targeted job description.",
                "Upload a clearer resume PDF if extraction was incomplete.",
            ],
            "sources": [],
            "retrieval": [
                {
                    "section": chunk["section"],
                    "confidence": chunk["confidence"],
                    "distance": chunk["distance"],
                }
                for chunk in retrieved_chunks
            ],
        }

    try:
        groq_service = get_groq_service()
        return groq_service.chat(
            payload.prompt,
            retrieved_chunks,
            [message.model_dump() for message in payload.history],
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Groq chat failed: {exc}",
        ) from exc


@router.get("/history")
async def analysis_history():
    return {"items": []}


@router.post("/report")
async def analysis_report():
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Report generation is not implemented yet.",
    )
