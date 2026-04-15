# RoleLens AI

RoleLens AI is a RAG-powered web app that helps you compare your **resume** with a **job description** using grounded analysis and follow-up chat.

## Project name

**Recommended name: `RoleLens AI`**

Why it works:
- `Role` maps directly to hiring and job-fit context.
- `Lens` communicates analysis and clarity.
- `AI` keeps it clear this is an AI-native assistant.

## What it does

1. **You upload** your resume as a PDF and **paste** the job description (or posting text).
2. The backend **reads** the PDF, **chunks** it by resume sections, and **embeds** those chunks locally (no embedding API calls).
3. It **stores** vectors in ChromaDB and **retrieves** the few chunks that best match the job description.
4. A **Groq**-hosted language model reads those chunks plus the job description and returns a **single JSON report**: fit score, grade, matched vs missing skills, a six-axis “radar” view, prioritized gaps, and short recommendations.
5. On the **results page**, you can keep asking follow-up questions about your resume, the active job description, or your fit between them. You can also paste a new job description against the already indexed resume. Each message runs retrieval again before generation.

The **frontend** turns that into charts and tables: fit ring, radar, skill bars, gap list, and suggested edits—so you can see *where* you’re strong, *what* you’re missing, and *what* to do next.

## How RAG is used (core flow)

For every analysis or Q&A interaction, the system follows this grounded pipeline:

1. **User asks a question** (for example: “How well does my resume fit this backend role?” or “Do I show enough Kubernetes experience?”).
2. The system **converts the question/JD into an embedding** using `sentence-transformers`.
3. It **searches ChromaDB** for the most relevant resume chunks.
4. It **retrieves top matches** (top-k chunks with metadata like section/source).
5. It sends **retrieved chunks + original question** to the Groq model.
6. The model returns an answer **grounded in retrieved resume content, job-description content, or both** depending on the question.

This design reduces hallucination risk because generation is constrained by retrieved evidence from your own resume text.

## Who it’s for

People applying to roles who want a **fast, visual sanity check** before they tailor a resume or write a cover letter—especially when comparing the same resume against several postings.

## What’s *not* in scope (by design)

- It does not replace recruiters or guarantee outcomes; it’s an **assistant** based on retrieved resume text, retrieved job-description text, and explicit comparison between them.
- Embeddings run **locally**; only the **final analysis** step uses the Groq API.

## Stack (high level)

| Piece | Role |
|--------|------|
| **React + Vite** | UI: upload, JD input, results dashboard |
| **FastAPI** | APIs for upload, indexing, and analysis |
| **ChromaDB** | Vector store on disk |
| **sentence-transformers** | Local embeddings |
| **Groq** | LLM inference for structured analysis |

## Product behavior

- Upload the resume once and keep it indexed in Chroma.
- Run an initial JD analysis from the home page.
- Continue on `/results` with follow-up questions about resume facts, job facts, or fit, or run a different JD against the same indexed resume.
- Every new question or JD triggers retrieval again, so the response stays grounded in resume evidence.

## Quick start
1. Set up the backend once:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

2. Set up the frontend once:

```bash
cd frontend
npm install
cp .env.example .env
```

3. Install the root runner and start both services:

```bash
npm install
npm run rolelens
```

`npm run rolelens` starts:
- FastAPI on `http://localhost:8000`
- Vite on `http://localhost:5173`

Detailed setup docs:
- Backend: **[backend/README.md](./backend/README.md)**
- Frontend: **[frontend/README.md](./frontend/README.md)**

## Deployment

- Frontend can be deployed to Netlify from `frontend/`.
- Backend can be deployed to Railway from `backend/`.
- For Railway, mount a persistent volume and set:
  - `CHROMA_PERSIST_PATH=/data/chroma_store`
  - `UPLOAD_DIR=/data/uploads`
- Session data is stored under `UPLOAD_DIR/sessions/<session_id>/...`, and inactive sessions are cleaned up based on `SESSION_TTL_HOURS`.
- Add `SESSION_TTL_HOURS=24` or another retention value that fits your deployment.
- Set `CORS_ORIGIN` on Railway to include both local development and your Netlify URL, for example:

```env
CORS_ORIGIN=http://localhost:5173,https://your-netlify-site.netlify.app
```

For file layout, endpoints, prompts, and build details, see **[Project_Spec.md](./Project_Spec.md)**.
