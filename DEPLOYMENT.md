# VoiceOps — Deployment (Render / Railway)

## Backend

- **Start command** (run from `voiceops/backend`):
  ```bash
  uvicorn app.main:app --host 0.0.0.0 --port 8000
  ```
- **Environment variables**: Set in the host dashboard.
  - **Required**: `OPENAI_API_KEY`
  - **Optional**: `UPLOAD_DIR`, `DATA_DIR` (defaults: `backend/uploads`, `backend/data` relative to app root)
- **Root directory**: Configure the service so the working directory is `voiceops/backend` (or set `UPLOAD_DIR` and `DATA_DIR` to absolute paths).

## Frontend (static)

- **Build** (from `voiceops/frontend`): `npm install && npm run build`
- **Output**: `voiceops/frontend/dist/`
- **API URL**: Set `VITE_API_BASE_URL` at build time to the backend URL (e.g. `https://your-backend.onrender.com`).

## Local development

1. Copy `.env.example` to `.env` and set `OPENAI_API_KEY` and optionally `VITE_API_BASE_URL`.
2. Backend: `cd voiceops/backend && source venv/bin/activate && uvicorn app.main:app --reload --port 8000`
3. Frontend: `cd voiceops/frontend && npm run dev`
