# RoleLens AI — Project Spec v1.0

Technical specification for RoleLens AI: a RAG-based resume and job-fit analysis application.

## Quick stats

| | |
|---|---|
| **Build time** | ~2 hours |
| **Cost** | Free (local embeddings + Chroma; LLM via [Groq](https://groq.com) usage/free tier as applicable) |
| **Stack** | React + Vite · FastAPI · ChromaDB · **Groq API** |

---

## 1. Tech stack

| Layer | Technology | Why |
|-------|------------|-----|
| Frontend | React + Vite | Fast iteration; widely used for SPAs |
| Styling | Tailwind CSS | Rapid UI without large custom CSS surface |
| Charts | Recharts | Radar, bar, ring — native to React |
| Backend | FastAPI (Python) | Async-friendly API layer; strong typing and docs |
| Embeddings | sentence-transformers | Local, free, no API key |
| Vector store | ChromaDB | Zero-config, persists to disk |
| LLM | **[Groq](https://console.groq.com)** | Fast inference via official **`groq`** Python SDK (OpenAI-compatible chat API) — no Anthropic/Claude |
| PDF parser | PyMuPDF (`fitz`) | Extract text from resume PDFs |

---

## 2. Folder structure

```
resume-fit/
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── ResumeUpload.jsx
│       │   ├── JobDescInput.jsx
│       │   ├── FitScoreRing.jsx
│       │   ├── SkillMatchChart.jsx
│       │   ├── RadarChart.jsx
│       │   └── GapAnalysis.jsx
│       ├── pages/
│       │   ├── Home.jsx
│       │   └── Results.jsx
│       └── api/client.js
└── backend/
    ├── main.py
    ├── routers/
    │   ├── resume.py
    │   └── analysis.py
    ├── services/
    │   ├── rag_service.py
    │   ├── groq_service.py      # Groq chat completions → structured JSON from JD + chunks
    │   └── pdf_parser.py
    ├── requirements.txt
    └── .env
```

---

## 3. API endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/resume/upload` | Upload PDF → chunk → embed into ChromaDB |
| `GET` | `/api/resume/status` | Check if resume is indexed |
| `POST` | `/api/analysis/analyze` | Submit JD → fit score + gaps |
| `GET` | `/api/analysis/history` | Past analyses |
| `POST` | `/api/analysis/report` | Generate PDF summary |

---

## 4. RAG pipeline (6 steps)

1. **Ingest** — PyMuPDF extracts text from uploaded PDF.
2. **Chunk** — Split by resume sections (Summary, Experience, Skills, Education, Projects), not arbitrary token splits.
3. **Embed** — `all-MiniLM-L6-v2` (~80 MB, downloads once, fully local).
4. **Store** — ChromaDB saves vectors + raw text + section metadata under `chroma_store/`.
5. **Retrieve** — JD is embedded; top-5 resume chunks by cosine similarity.
6. **Generate** — Chunks + JD → **Groq** chat completion → structured JSON response.

---

## 4.1 Grounded question-answer flow (must-have behavior)

RoleLens AI is explicitly Retrieval-Augmented Generation (RAG), not plain prompting.
Each end-user interaction follows this pattern:

1. The **end user submits a question** (job-fit, skill-gap, or resume-targeting query).
2. The backend **creates an embedding** from the question or job-description text.
3. The backend **queries ChromaDB** for the nearest resume chunks by cosine similarity.
4. The backend **retrieves top-k chunks** with section metadata.
5. The backend sends **the question plus retrieved chunks** to the Groq model.
6. The model returns an answer **grounded in retrieved data** (JSON for analysis endpoints).

Implementation notes:

- Retrieval logic lives in `rag_service.py`; generation (Groq calls) lives in `groq_service.py`.
- Chunk metadata (section, similarity or confidence score) is included in the prompt context.
- A fixed `k` (for example 5) is used initially, then tuned against token budget and quality.
- When retrieval confidence is low, the system returns a guarded or fallback response instead of a falsely confident answer.

---

## 5. LLM prompt (template for `groq_service.py`)

The same JSON contract applies regardless of model. The system prompt instructs the model to return **only** valid JSON; optional post-parse validation catches malformed output.

The quoted prompt blocks below are **payload text sent to the Groq API**. Second-person wording inside those blocks (for example “You are a career analyst AI”) addresses the model role, not the reader of this specification.

**System:**

```text
You are a career analyst AI. Analyze a resume against a job description.
Return ONLY valid JSON — no markdown, no explanation:

{
  "fit_score": <0-100>,
  "grade": <"A+"|"A"|"B+"|"B"|"C"|"D">,
  "role_detected": "<string>",
  "seniority": "<Junior|Mid|Senior|Lead>",
  "matched_skills": ["skill1", ...],
  "missing_skills": ["skill1", ...],
  "radar": {
    "skills": <0-100>, "experience": <0-100>,
    "education": <0-100>, "culture": <0-100>,
    "keywords": <0-100>, "seniority_match": <0-100>
  },
  "gaps": [{ "skill": "...", "priority": "Critical|High|Medium", "reason": "..." }],
  "recommendations": [{ "title": "...", "detail": "...", "action": "..." }],
  "cover_letter_angle": "<one sentence>",
  "summary": "<2-3 sentence plain English summary>"
}
```

**User:**

```text
--- RESUME CHUNKS ---
{retrieved_chunks}

--- JOB DESCRIPTION ---
{job_description}
```

Integration notes:

- The official **`groq`** package is used: `from groq import Groq` and `client.chat.completions.create(...)` with `GROQ_API_KEY` ([Groq docs](https://console.groq.com/docs/quickstart)).
- `model` is set to a Groq-supported model ID (for example `llama-3.3-70b-versatile` or another ID listed in the console) and centralized in a single configuration constant.
- If the model wraps JSON in markdown fences, `groq_service.py` strips fences before `json.loads`.

---

## 6. UI screens

### Home

Two-panel layout: drag-and-drop resume upload (left) + JD textarea with auto-detected role badge (right). Large **Analyze** button with step-by-step loading: “Indexing… Retrieving… Analyzing…”

### Results dashboard

- **Fit score ring** — animated circular progress, score + grade + role label.
- **Radar chart** — six axes (Skills, Experience, Education, Culture, Keywords, Seniority): profile vs ideal.
- **Skill match bars** — horizontal bars; green = matched, red = missing; sorted by importance.
- **Gap heatmap** — table of missing skills with Critical / High / Medium badges.
- **AI recs panel** — three cards: what to add, how to reframe experience, what to learn.
- **Export** — PDF download of full analysis.

---

## 7. Two-hour build plan

Example prompts for Cursor-style tooling (illustrative; not addressed to a specific individual):

| Phase | Time | What to build | Cursor prompt (summary) |
|-------|------|---------------|-------------------------|
| 0 | 10 min | Init both repos, install deps | “Create FastAPI + React Vite with the folder structure above.” |
| 1 | 20 min | PDF parser + RAG indexing | “Build `/upload-resume` using PyMuPDF + ChromaDB + sentence-transformers.” |
| 2 | 20 min | Analysis endpoint + Groq | “Build `/analyze`: top-5 Chroma chunks + **Groq** `chat.completions` with the JSON prompt template.” |
| 3 | 30 min | React home page | “Two-panel home: upload + JD, call upload then analyze, loading steps.” |
| 4 | 30 min | Results dashboard | “FitScoreRing (SVG), RadarChart, SkillMatchChart (Recharts), gap table.” |
| 5 | 10 min | Polish | “Spinners, error toasts, empty states, CORS.” |

---

## 8. Environment (`.env`)

```env
# Groq — keys issued at https://console.groq.com/keys
GROQ_API_KEY=gsk_xxxx

CHROMA_PERSIST_PATH=./chroma_store
UPLOAD_DIR=./uploads
CORS_ORIGIN=http://localhost:5173
```

Additional LLM vendor keys (for example `ANTHROPIC_API_KEY`, `XAI_API_KEY`) are out of scope unless multi-provider support is explicitly added to the project.

---

## 9. Backend installs

```bash
pip install fastapi uvicorn chromadb sentence-transformers pymupdf groq python-dotenv python-multipart
```

(Python 3.10+ recommended for `groq`.)

---

## 10. Brainstorm & deployment notes (Groq-only)

- **Single LLM surface** — All generative steps (fit analysis, optional report copy, future “rewrite bullet” features) go through `groq_service.py` so nothing in the repo assumes Claude artifacts or Anthropic message formats.
- **RAG-first product behavior** — Responses must always be evidence-backed: retrieval happens before generation, and prompts should include retrieved text + section metadata so outputs stay grounded.
- **Deploy “fully”** — Frontend: static host (Vercel, Netlify, Cloudflare Pages) or same origin behind nginx; backend: container or PaaS with `GROQ_API_KEY` as a secret; Chroma data must use a **persistent volume** (not ephemeral disk) if analyses must survive process restarts.
- **Model choice** — Initially, a single Groq model covers all generative tasks; additional models for latency versus quality may be introduced if quotas or latency require it.
- **Safety & limits** — The `/analyze` endpoint should be rate-limited; job-description and chunk payload sizes should be capped; Groq errors should be logged without echoing API keys.

---

*Spec version: 1.0 — LLM provider: Groq only.*
