from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from services.groq_service import get_groq_service
from services.rag_service import get_rag_service
from services.session import get_session_id
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


JOB_ONLY_HINTS = (
    "sponsor",
    "sponsorship",
    "visa",
    "h-1b",
    "stem opt",
    "opt",
    "work authorization",
    "qualification",
    "qualifications",
    "responsibilities",
    "role require",
    "required",
    "job require",
    "what does this job",
    "what are the roles",
    "company",
    "company name",
    "about the company",
    "tell me about the company",
    "employer",
    "location",
    "salary",
)
COMPARISON_HINTS = (
    "fit",
    "suitable",
    "qualified",
    "match",
    "should i apply",
    "should i go for",
    "should i take",
    "my chances",
    "what are my chances",
    "chance of getting",
    "chance of getting the job",
    "will i get",
    "can i get",
    "can i land",
    "do i stand a chance",
    "worth applying",
    "worth it for me",
    "good job for me",
    "good for me",
    "is the job good",
    "is this job good",
    "best in that",
    "best thing about this job for me",
    "good for me",
    "right for me",
    "compare",
    "am i",
    "do i have",
    "gap",
    "eligible for this role",
)


@router.post("/analyze")
async def analyze_resume(
    payload: AnalyzeRequest,
    session_id: str = Depends(get_session_id),
):
    rag_service = get_rag_service()
    rag_service.prepare_session(session_id)
    rag_service.index_job_description(session_id, payload.job_description)
    if not rag_service.has_indexed_resume(session_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload and index a resume before running analysis.",
        )

    retrieved_chunks = rag_service.retrieve_relevant_chunks(
        session_id,
        payload.job_description,
        document_type="resume",
    )
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


@router.get("/context")
async def analysis_context(session_id: str = Depends(get_session_id)):
    rag_service = get_rag_service()
    rag_service.prepare_session(session_id)
    job_status = rag_service.get_job_description_status(session_id)
    return {
        "job_indexed": job_status["indexed"],
        "chunks_indexed": job_status["chunks_indexed"],
        "job_description": job_status["job_description"],
    }


@router.post("/chat")
async def chat_with_resume(
    payload: ChatRequest,
    session_id: str = Depends(get_session_id),
):
    rag_service = get_rag_service()
    rag_service.prepare_session(session_id)
    if not rag_service.has_indexed_resume(session_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload and index a resume before starting chat.",
        )

    groq_service = get_groq_service()
    intent = classify_chat_intent(payload.prompt)
    if intent is None:
        try:
            intent = groq_service.route_chat_scope(
                payload.prompt,
                [message.model_dump() for message in payload.history],
            )
        except ValueError:
            intent = "comparison"

    if intent != "resume" and not rag_service.has_indexed_job_description(session_id):
        return {
            "answer": "There is no active job description in this session yet. Paste one and run analysis first.",
            "follow_up_suggestions": [
                "Paste the target job description and click Analyze.",
                "Ask about your resume only.",
                "Re-run analysis for the current role.",
            ],
            "sources": [],
            "retrieval": [],
            "scope": intent,
        }

    resume_chunks = []
    job_chunks = []
    if intent in {"resume", "comparison"}:
        resume_chunks = rag_service.retrieve_relevant_chunks(
            session_id,
            payload.prompt,
            document_type="resume",
        )
    if intent in {"job", "comparison"}:
        job_chunks = rag_service.retrieve_relevant_chunks(
            session_id,
            payload.prompt,
            document_type="job_description",
        )

    retrieved_chunks = resume_chunks + job_chunks
    if not retrieved_chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No relevant resume or job-description content was retrieved for this prompt.",
        )

    settings = get_settings()
    average_confidence = sum(chunk["confidence"] or 0 for chunk in retrieved_chunks) / len(retrieved_chunks)
    if average_confidence < settings.retrieval_confidence_floor:
        return {
            "answer": "I could not find strong enough evidence in the stored resume or job description to answer that reliably.",
            "follow_up_suggestions": [
                "Ask about a specific skill or project.",
                "Ask about a specific job requirement or policy.",
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
            "scope": intent,
        }

    try:
        return groq_service.chat(
            payload.prompt,
            resume_chunks,
            job_chunks,
            [message.model_dump() for message in payload.history],
            intent=intent,
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


def classify_chat_intent(prompt: str) -> str | None:
    normalized = prompt.lower()
    if any(hint in normalized for hint in JOB_ONLY_HINTS):
        return "job"
    if any(hint in normalized for hint in COMPARISON_HINTS):
        return "comparison"
    if any(hint in normalized for hint in RESUME_ONLY_HINTS):
        return "resume"
    return None


RESUME_ONLY_HINTS = (
    "my resume",
    "my experience",
    "my background",
    "my project",
    "my projects",
    "my skill",
    "my skills",
    "my education",
    "my work history",
    "my profile",
)
