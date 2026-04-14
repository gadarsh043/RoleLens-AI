# Frontend

React + Vite client for uploading a resume, submitting a job description, and viewing the analysis dashboard.

## Requirements

- Node.js `18+`
- npm

## Setup

1. Install dependencies:

```bash
cd frontend
npm install
```

2. Create the env file:

```bash
cp .env.example .env
```

3. Set the backend base URL if needed:

```env
VITE_API_BASE_URL=http://localhost:8000
```

## Run

```bash
cd frontend
npm run dev
```

App URL: `http://localhost:5173`

Run from the repo root together with the backend:

```bash
npm install
npm run rolelens
```

## Build

```bash
cd frontend
npm run build
```

Preview production build:

```bash
npm run preview
```

## Notes

- The frontend expects the backend CORS origin to allow `http://localhost:5173`.
- Upload and analysis errors returned by the backend are shown directly in the UI.
- Results are also cached in `sessionStorage` so refreshes on `/results` can still render the last analysis.
- The `/results` page includes a chat panel for follow-up resume questions and for testing a different JD against the already indexed resume.
