# RoleLens AI

RoleLens AI is a RAG-powered web app that helps you see how well your **resume** matches a **job description**—not just a gut feeling, but a structured breakdown you can act on.

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

The **frontend** turns that into charts and tables: fit ring, radar, skill bars, gap list, and suggested edits—so you can see *where* you’re strong, *what* you’re missing, and *what* to do next.

## How RAG is used (core flow)

For every analysis or Q&A interaction, the system follows this grounded pipeline:

1. **User asks a question** (for example: “How well does my resume fit this backend role?” or “Do I show enough Kubernetes experience?”).
2. The system **converts the question/JD into an embedding** using `sentence-transformers`.
3. It **searches ChromaDB** for the most relevant resume chunks.
4. It **retrieves top matches** (top-k chunks with metadata like section/source).
5. It sends **retrieved chunks + original question** to the Groq model.
6. The model returns an answer **grounded in retrieved resume content** (structured JSON for fit analysis, concise text for Q&A extensions).

This design reduces hallucination risk because generation is constrained by retrieved evidence from your own resume text.

## Who it’s for

People applying to roles who want a **fast, visual sanity check** before they tailor a resume or write a cover letter—especially when comparing the same resume against several postings.

## What’s *not* in scope (by design)

- It does not replace recruiters or guarantee outcomes; it’s an **assistant** based on retrieved resume text and the JD you provide.
- Embeddings run **locally**; only the **final analysis** step uses the Groq API.

## Stack (high level)

| Piece | Role |
|--------|------|
| **React + Vite** | UI: upload, JD input, results dashboard |
| **FastAPI** | APIs for upload, indexing, and analysis |
| **ChromaDB** | Vector store on disk |
| **sentence-transformers** | Local embeddings |
| **Groq** | LLM inference for structured analysis |

For file layout, endpoints, prompts, and build steps, see **[Project_Spec.md](./Project_Spec.md)**.
