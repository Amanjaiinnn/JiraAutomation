
# Jira Groq AI Automation (RAG-based)

## Features
- React UI for clearer workflows and expansion-ready API integrations.
- Epic + story generation from requirements (CSV / PDF / TXT).
- Dedicated duplicate-story checker tab.
- Story-level build packs inside Planning: app code, unit tests, manual tests, automated tests.
- Cumulative project workspace that keeps previous generated files in context for later stories.
- Inline application preview derived from the generated project structure.
- Jira Cloud auto-configuration endpoints and connectivity check.
- Direct Jira issue creation from selected generated stories.

## Architecture
- **Backend API (FastAPI)**: `app/backend/api.py`
- **Use-case functions/services**: `app/backend/services.py`
- **React UI**: `frontend/`

Use cases are exposed as API functions and consumed by React UI. Planning now drives code generation, test generation, and project preview from the same story cards while preserving accumulated project context.

## Requirements
- Python 3.11+ recommended
- Node.js 18+ recommended
- npm

## Setup
1. Install Python dependencies:
   - `pip install -r requirements.txt`
2. Install frontend dependencies:
   - `cd frontend && npm install`
3. Configure environment variables in `.env`:
   - Required for AI generation:
     - `GROQ_API_KEY`
   - Optional Groq model overrides:
     - `GROQ_MODEL`
     - `CODEGEN_MODEL`
   - Optional Jira configuration if not configuring via API/UI:
     - `JIRA_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, `JIRA_PROJECT_KEY`
   - Optional story notification email delivery:
     - `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`, `SMTP_USE_TLS`
4. Run backend API:
   - `uvicorn app.backend.api:app --host 0.0.0.0 --port 8000 --reload`
5. Run React frontend:
   - `cd frontend && npm run dev`

Example `.env`:
```env
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=mixtral-8x7b-32768
CODEGEN_MODEL=llama-3.3-70b-versatile
JIRA_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your_jira_api_token
JIRA_PROJECT_KEY=ABC
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=your-smtp-username
SMTP_PASSWORD=your-smtp-password
SMTP_FROM_EMAIL=no-reply@example.com
SMTP_USE_TLS=true
```

## Frontend API Configuration
- By default, frontend uses Vite dev-server proxy (`vite.config.js`) and calls relative API paths.
- Optional: set `VITE_API_BASE_URL` to point at a remote backend.

## White Screen Troubleshooting
If `http://localhost:5173/` opens as a blank page:
1. Open browser devtools console first.
2. A React error boundary now renders an explicit error card instead of a silent blank screen.
3. Ensure backend is running on `http://localhost:8000` for API routes.
4. If backend is remote, set `VITE_API_BASE_URL` in frontend environment.

## Main API Endpoints
- `POST /requirements/parse`
- `POST /epics/generate`
- `POST /stories/generate`
- `POST /stories/check-duplicates`
- `POST /stories/generate-code`
- `POST /stories/generate-deliverables`
- `POST /stories/generate-tests`
- `POST /stories/send-notification`
- `POST /jira/create-stories`
- `GET /jira/config`
- `POST /jira/configure`
- `GET /jira/health`

## Running Tests
- Backend tests:
  - `pytest`
