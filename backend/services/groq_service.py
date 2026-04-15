from functools import lru_cache
import json
import re

from groq import Groq
from pydantic import BaseModel, Field, ValidationError, field_validator

from services.settings import get_settings


SYSTEM_PROMPT = """
You are a career analyst AI. Analyze a resume against a job description.
Return ONLY valid JSON — no markdown, no explanation:

{
  "fit_score": <0-100>,
  "grade": <"A+"|"A"|"B+"|"B"|"C"|"D">,
  "role_detected": "<string>",
  "seniority": "<Junior|Mid|Senior|Lead>",
  "matched_skills": ["skill1"],
  "missing_skills": ["skill1"],
  "radar": {
    "skills": <0-100>,
    "experience": <0-100>,
    "education": <0-100>,
    "culture": <0-100>,
    "keywords": <0-100>,
    "seniority_match": <0-100>
  },
  "gaps": [{"skill": "...", "priority": "Critical|High|Medium", "reason": "..."}],
  "recommendations": [{"title": "...", "detail": "...", "action": "..."}],
  "cover_letter_angle": "<one sentence>",
  "summary": "<2-3 sentence plain English summary>"
}
""".strip()

CHAT_SYSTEM_PROMPT = """
You are a source-grounded career assistant.
You will receive labeled resume chunks, labeled job-description chunks, a question scope, and the user's input.
Rules:
- Use resume chunks only for candidate facts.
- Use job-description chunks only for job facts.
- For comparison questions, compare both sources explicitly.
- If sponsorship, visa support, work authorization, salary, or location are not stated in the relevant source, say they are not stated.
- Do not guess or infer missing facts from the wrong source.
Return ONLY valid JSON — no markdown, no explanation:

{
  "answer": "<plain English answer>",
  "follow_up_suggestions": ["<suggestion 1>", "<suggestion 2>", "<suggestion 3>"],
  "sources": [{"source_type": "<resume|job_description>", "section": "<section name>", "evidence": "<short supporting excerpt>"}]
}
""".strip()

ROUTER_SYSTEM_PROMPT = """
You are a routing classifier for a career assistant.
Classify the user's question into exactly one scope:
- resume: answer should come from candidate/resume facts only
- job: answer should come from job-description facts only
- comparison: answer requires comparing resume facts with job-description facts

Guidance:
- Questions about sponsorship, visa policy, company, compensation, responsibilities, location, requirements, or employer facts are usually job.
- Questions about the candidate's background, projects, skills, education, or experience are usually resume.
- Questions about fit, suitability, chances, gaps, whether to apply, or comparisons are usually comparison.
- If a question mixes job facts and candidate fit, choose comparison.

Return ONLY valid JSON:
{
  "scope": "resume|job|comparison"
}
""".strip()


class GapItem(BaseModel):
    skill: str
    priority: str
    reason: str

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, value: str) -> str:
        if value not in {"Critical", "High", "Medium"}:
            raise ValueError("priority must be one of Critical, High, Medium")
        return value


class RecommendationItem(BaseModel):
    title: str
    detail: str
    action: str


class RadarScores(BaseModel):
    skills: int = Field(ge=0, le=100)
    experience: int = Field(ge=0, le=100)
    education: int = Field(ge=0, le=100)
    culture: int = Field(ge=0, le=100)
    keywords: int = Field(ge=0, le=100)
    seniority_match: int = Field(ge=0, le=100)


class AnalysisPayload(BaseModel):
    fit_score: int = Field(ge=0, le=100)
    grade: str
    role_detected: str
    seniority: str
    matched_skills: list[str]
    missing_skills: list[str]
    radar: RadarScores
    gaps: list[GapItem]
    recommendations: list[RecommendationItem]
    cover_letter_angle: str
    summary: str

    @field_validator("grade")
    @classmethod
    def validate_grade(cls, value: str) -> str:
        if value not in {"A+", "A", "B+", "B", "C", "D"}:
            raise ValueError("grade must be one of A+, A, B+, B, C, D")
        return value

    @field_validator("seniority")
    @classmethod
    def validate_seniority(cls, value: str) -> str:
        if value not in {"Junior", "Mid", "Senior", "Lead"}:
            raise ValueError("seniority must be one of Junior, Mid, Senior, Lead")
        return value


class ChatSource(BaseModel):
    source_type: str
    section: str
    evidence: str

    @field_validator("source_type")
    @classmethod
    def validate_source_type(cls, value: str) -> str:
        if value not in {"resume", "job_description"}:
            raise ValueError("source_type must be resume or job_description")
        return value


class ChatPayload(BaseModel):
    answer: str
    follow_up_suggestions: list[str]
    sources: list[ChatSource]


class RoutePayload(BaseModel):
    scope: str

    @field_validator("scope")
    @classmethod
    def validate_scope(cls, value: str) -> str:
        if value not in {"resume", "job", "comparison"}:
            raise ValueError("scope must be one of resume, job, comparison")
        return value


class GroqService:
    def __init__(self) -> None:
        self.settings = get_settings()
        if not self.settings.groq_api_key:
            raise ValueError("GROQ_API_KEY is missing.")
        self.client = Groq(api_key=self.settings.groq_api_key)

    def analyze(self, job_description: str, retrieved_chunks: list[dict]) -> dict:
        response = self.client.chat.completions.create(
            model=self.settings.groq_model,
            temperature=0.2,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": self._build_user_prompt(job_description, retrieved_chunks),
                },
            ],
        )

        parsed = self._parse_analysis_response(response.choices[0].message.content or "")
        parsed["sources"] = [
            {
                "section": chunk["section"],
                "confidence": chunk["confidence"],
                "distance": chunk["distance"],
            }
            for chunk in retrieved_chunks
        ]
        return parsed

    def chat(
        self,
        prompt: str,
        resume_chunks: list[dict],
        job_chunks: list[dict],
        history: list[dict] | None = None,
        intent: str = "resume",
    ) -> dict:
        response = self.client.chat.completions.create(
            model=self.settings.groq_model,
            temperature=0.2,
            messages=[
                {"role": "system", "content": CHAT_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": self._build_chat_prompt(
                        prompt,
                        resume_chunks,
                        job_chunks,
                        history or [],
                        intent=intent,
                    ),
                },
            ],
        )

        parsed = self._parse_chat_response(response.choices[0].message.content or "")
        parsed["retrieval"] = [
            {
                "source_type": chunk["document_type"],
                "section": chunk["section"],
                "confidence": chunk["confidence"],
                "distance": chunk["distance"],
            }
            for chunk in [*resume_chunks, *job_chunks]
        ]
        parsed["scope"] = intent
        return parsed

    def route_chat_scope(self, prompt: str, history: list[dict] | None = None) -> str:
        response = self.client.chat.completions.create(
            model=self.settings.groq_model,
            temperature=0,
            messages=[
                {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": self._build_route_prompt(prompt, history or []),
                },
            ],
        )

        try:
            payload = json.loads(self._strip_json_fences(response.choices[0].message.content or ""))
            return RoutePayload.model_validate(payload).scope
        except (json.JSONDecodeError, ValidationError) as exc:
            raise ValueError(f"Groq route response failed validation: {exc}") from exc

    def _parse_analysis_response(self, content: str) -> dict:
        try:
            payload = json.loads(self._strip_json_fences(content))
            return AnalysisPayload.model_validate(payload).model_dump()
        except (json.JSONDecodeError, ValidationError) as exc:
            raise ValueError(f"Groq analysis response failed validation: {exc}") from exc

    def _parse_chat_response(self, content: str) -> dict:
        try:
            payload = json.loads(self._strip_json_fences(content))
            return ChatPayload.model_validate(payload).model_dump()
        except (json.JSONDecodeError, ValidationError) as exc:
            raise ValueError(f"Groq chat response failed validation: {exc}") from exc

    def _build_user_prompt(self, job_description: str, retrieved_chunks: list[dict]) -> str:
        chunk_block = "\n\n".join(
            [
                "\n".join(
                    [
                        f"[Chunk {index + 1}]",
                        f"Section: {chunk['section']}",
                        f"Confidence: {chunk['confidence']}",
                        chunk["text"],
                    ]
                )
                for index, chunk in enumerate(retrieved_chunks)
            ]
        )
        return f"""--- RESUME CHUNKS ---
{chunk_block}

--- JOB DESCRIPTION ---
{job_description}"""

    def _build_chat_prompt(
        self,
        prompt: str,
        resume_chunks: list[dict],
        job_chunks: list[dict],
        history: list[dict],
        intent: str,
    ) -> str:
        history_block = "\n".join(
            [
                f"{item.get('role', 'user').upper()}: {item.get('content', '')}"
                for item in history[-6:]
                if item.get("content")
            ]
        )
        resume_block = self._format_chunk_block(resume_chunks)
        job_block = self._format_chunk_block(job_chunks)
        return f"""--- CONVERSATION HISTORY ---
{history_block or "No prior conversation."}

--- QUESTION SCOPE ---
{intent}

--- RESUME CHUNKS ---
{resume_block or "No resume chunks retrieved."}

--- JOB DESCRIPTION CHUNKS ---
{job_block or "No job-description chunks retrieved."}

--- USER INPUT ---
{prompt}"""

    @staticmethod
    def _build_route_prompt(prompt: str, history: list[dict]) -> str:
        history_block = "\n".join(
            [
                f"{item.get('role', 'user').upper()}: {item.get('content', '')}"
                for item in history[-4:]
                if item.get("content")
            ]
        )
        return f"""--- RECENT HISTORY ---
{history_block or "No prior conversation."}

--- USER INPUT ---
{prompt}"""

    @staticmethod
    def _format_chunk_block(chunks: list[dict]) -> str:
        return "\n\n".join(
            [
                "\n".join(
                    [
                        f"[Chunk {index + 1}]",
                        f"Source: {chunk.get('document_type', 'unknown')}",
                        f"Section: {chunk['section']}",
                        f"Confidence: {chunk['confidence']}",
                        chunk["text"],
                    ]
                )
                for index, chunk in enumerate(chunks)
            ]
        )

    @staticmethod
    def _strip_json_fences(content: str) -> str:
        stripped = content.strip()
        return re.sub(r"^```(?:json)?\s*|\s*```$", "", stripped)


@lru_cache
def get_groq_service() -> GroqService:
    return GroqService()
