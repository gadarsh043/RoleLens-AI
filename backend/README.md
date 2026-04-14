# Backend

FastAPI service for resume upload, PDF parsing, chunking, embeddings, Chroma persistence, retrieval, and Groq-based analysis.

## Requirements

- Python `3.10+`
- A Groq API key for `/api/analysis/analyze` and `/api/analysis/chat`

## Setup

1. Create and activate a virtual environment:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create the env file:

```bash
cp .env.example .env
```

4. Set `GROQ_API_KEY` in `.env`.

Example:

```env
GROQ_API_KEY=gsk_xxxx
CHROMA_PERSIST_PATH=./chroma_store
UPLOAD_DIR=./uploads
CORS_ORIGIN=http://localhost:5173
EMBEDDING_MODEL=all-MiniLM-L6-v2
CHROMA_COLLECTION_NAME=resume_chunks
RETRIEVAL_TOP_K=5
GROQ_MODEL=llama-3.3-70b-versatile
RETRIEVAL_CONFIDENCE_FLOOR=0.35
```

## Run

```bash
cd backend
source .venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API base URL: `http://localhost:8000`

Interactive docs: `http://localhost:8000/docs`

Run from the repo root together with the frontend:

```bash
npm install
npm run rolelens
```

The root runner starts this backend with `backend/.venv/bin/python`, so the virtual environment must exist first.

## Railway Deployment

Deploy the `backend/` directory as the Railway service root.

Railway start command:

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

This repo also includes a [Procfile](/Users/adarshsonu/Desktop/Personal%20Projects/Resume%20RAG/backend/Procfile) for that command.

Recommended Railway environment variables:

```env
GROQ_API_KEY=gsk_xxxx
CHROMA_PERSIST_PATH=/data/chroma_store
UPLOAD_DIR=/data/uploads
CORS_ORIGIN=http://localhost:5173,https://your-netlify-site.netlify.app
EMBEDDING_MODEL=all-MiniLM-L6-v2
CHROMA_COLLECTION_NAME=resume_chunks
RETRIEVAL_TOP_K=5
GROQ_MODEL=llama-3.3-70b-versatile
RETRIEVAL_CONFIDENCE_FLOOR=0.35
```

Notes for Railway:

- Mount a persistent volume and point `CHROMA_PERSIST_PATH` and `UPLOAD_DIR` into that volume, for example `/data/...`.
- Without a persistent volume, Chroma data and uploaded PDFs will be lost on redeploy or restart.
- `GROQ_API_KEY` is required for both `/api/analysis/analyze` and `/api/analysis/chat`.

## Main Endpoints

- `GET /health`
- `GET /api/resume/status`
- `POST /api/resume/upload`
- `POST /api/analysis/analyze`
- `POST /api/analysis/chat`

## Notes

- The first embedding/model use may download local model files for `sentence-transformers`.
- Resume vectors persist under `CHROMA_PERSIST_PATH`.
- Uploaded PDFs persist under `UPLOAD_DIR`.
- If analysis fails, verify the Groq key and model name in `.env`.
- `/api/analysis/chat` supports follow-up Q&A against the already indexed resume. Each prompt is embedded and retrieved against Chroma before Groq answers.
