from functools import lru_cache
import json
import re

from groq import Groq

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
You are a resume-grounded career assistant.
Answer using only the retrieved resume chunks and the user's current input.
If the evidence is weak or missing, say so clearly instead of guessing.
Return ONLY valid JSON — no markdown, no explanation:

{
  "answer": "<plain English answer>",
  "follow_up_suggestions": ["<suggestion 1>", "<suggestion 2>", "<suggestion 3>"],
  "sources": [{"section": "<section name>", "evidence": "<short supporting excerpt>"}]
}
""".strip()


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

        content = response.choices[0].message.content or ""
        cleaned_content = self._strip_json_fences(content)
        parsed = json.loads(cleaned_content)
        parsed["sources"] = [
            {
                "section": chunk["section"],
                "confidence": chunk["confidence"],
                "distance": chunk["distance"],
            }
            for chunk in retrieved_chunks
        ]
        return parsed

    def chat(self, prompt: str, retrieved_chunks: list[dict], history: list[dict] | None = None) -> dict:
        response = self.client.chat.completions.create(
            model=self.settings.groq_model,
            temperature=0.2,
            messages=[
                {"role": "system", "content": CHAT_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": self._build_chat_prompt(prompt, retrieved_chunks, history or []),
                },
            ],
        )

        content = response.choices[0].message.content or ""
        cleaned_content = self._strip_json_fences(content)
        parsed = json.loads(cleaned_content)
        parsed["retrieval"] = [
            {
                "section": chunk["section"],
                "confidence": chunk["confidence"],
                "distance": chunk["distance"],
            }
            for chunk in retrieved_chunks
        ]
        return parsed

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

    def _build_chat_prompt(self, prompt: str, retrieved_chunks: list[dict], history: list[dict]) -> str:
        history_block = "\n".join(
            [
                f"{item.get('role', 'user').upper()}: {item.get('content', '')}"
                for item in history[-6:]
                if item.get("content")
            ]
        )
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
        return f"""--- CONVERSATION HISTORY ---
{history_block or "No prior conversation."}

--- RESUME CHUNKS ---
{chunk_block}

--- USER INPUT ---
{prompt}"""

    @staticmethod
    def _strip_json_fences(content: str) -> str:
        stripped = content.strip()
        return re.sub(r"^```(?:json)?\s*|\s*```$", "", stripped)


@lru_cache
def get_groq_service() -> GroqService:
    return GroqService()
