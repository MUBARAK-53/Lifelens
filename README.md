# LifeLens AI

LifeLens is a local-development FastAPI backend for three separate kinds of personal data:

- conversation history, scoped to a chat session;
- explicit saved memories, reusable across sessions;
- uploaded experiences (photos/screenshots plus user-provided metadata and optional AI analysis).

It uses synchronous SQLAlchemy 2.x with PostgreSQL and the Google Gen AI SDK. It has no authentication or user ownership model; do not expose it to a network or use it as a multi-user service.

## Setup (Windows PowerShell)

From the repository root:

```powershell
cd backend
py -3.13 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r app\requirements.txt
Copy-Item .env.example .env
```

Set `DATABASE_URL` and `GEMINI_API_KEY` in `backend/.env`. Never commit that file. Create a local PostgreSQL database first, for example `lifelens`, then use a URL such as `postgresql+psycopg://postgres:password@localhost:5432/lifelens`.

Run the database migration before starting the server. This preserves current rows; it does not reset the database.

```powershell
alembic -c alembic.ini upgrade head
python -m uvicorn app.main:app --reload
```

Swagger is at `http://127.0.0.1:8000/docs`.

## API

- `POST /chat/`, `GET /chat/{session_id}/history`
- `POST /memories/`, `GET /memories/`, `GET /memories/search`, `GET/PATCH/DELETE /memories/{memory_id}`
- `POST /experiences/upload`, `GET /experiences/`, `GET/PATCH/DELETE /experiences/{experience_id}`
- `POST /experiences/{experience_id}/analyze`, `POST /experiences/search`
- `GET /`, `GET /health`

### Upload and search example

```powershell
curl.exe -X POST http://127.0.0.1:8000/experiences/upload `
  -F "image=@C:\photos\lake-hike.jpg" `
  -F "title=Lake hike" -F "user_notes=Morning hike" -F "location_name=Pune"

curl.exe -X POST http://127.0.0.1:8000/experiences/search `
  -H "Content-Type: application/json" `
  -d '{"query":"photos from a hike near a lake","limit":10}'
```

Uploads accept JPEG, PNG, and WebP, are content-validated, capped by `MAX_UPLOAD_BYTES` (10 MB by default), and are stored under `backend/uploads/experiences` with generated names. Responses contain only relative upload paths; the application deliberately provides no unrestricted static-file route.

## AI compatibility

Chat uses `GEMMA_MODEL`. Saved memories and keyword-matched experience records are retrieved before a chat response is generated, but arbitrary chat statements are never persisted as memories automatically.

Image analysis is disabled by default. The existing configured model (`gemma-4-26b-a4b-it`) is not assumed to support image input. To enable analysis, set both `VISION_MODEL` to a model you have verified supports image parts in the Google Gen AI API and `VISION_MODEL_SUPPORTS_IMAGE_INPUT=true`. Failed or unconfigured analysis leaves the upload in `pending` or `failed` state for `POST /experiences/{id}/analyze`; it never discards the source image.

Experience search is PostgreSQL keyword retrieval over titles, notes, AI descriptions, tags, and locations. It is not semantic/vector search, and it does not ask the model to invent matches.

## Tests

Tests use SQLite and mocked chat generation; they do not require a real API key or PostgreSQL database:

```powershell
cd backend
pytest -q
```

They cover health, mocked chat plus cross-session memory retrieval, memory CRUD, image validation/size limits, experience listing/search/deletion, missing IDs, and safe deletion traversal rejection.
