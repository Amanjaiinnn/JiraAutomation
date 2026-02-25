<!-- 
# Jira Groq AI Automation (RAG-based)

## Features
- Create Epics & User Stories from requirements (CSV / PDF / TXT)
- UI review before Jira creation
- Enhance existing stories (AC, DoD)
- Code generation, UTs, test cases
- Impact analysis & duplicate detection (RAG)
- Direct Jira Cloud integration
- Uses Groq + local embeddings (no OpenAI)

## Setup
1. `pip install -r requirements.txt`
2. Create `.env` (see project env vars)
3. Run backend API (optional, for remote execution):
   - `uvicorn app.backend.api:app --host 0.0.0.0 --port 8000`
4. Run Streamlit UI:
   - `streamlit run app/main.py`
5. Optional: point UI to backend API:
   - `export JIRA_AUTOMATION_API_BASE_URL=http://localhost:8000`

If `JIRA_AUTOMATION_API_BASE_URL` is not set, UI uses local API service fallback with the same contracts. -->

# Jira Groq AI Automation (RAG-based)

## Features
- React UI for clearer workflows and expansion-ready API integrations.
- Epic + story generation from requirements (CSV / PDF / TXT).
- Dedicated duplicate-story checker tab.
- Dedicated story code generator tab.
- Jira Cloud auto-configuration endpoints and connectivity check.
- Direct Jira issue creation from selected generated stories.

## Architecture
- **Backend API (FastAPI)**: `app/backend/api.py`
- **Use-case functions/services**: `app/backend/services.py`
- **React UI**: `frontend/`

Use cases are exposed as API functions and consumed by React UI so each workflow remains separate and extensible.

## Setup
1. Install Python dependencies:
   - `pip install -r requirements.txt`
2. Install frontend dependencies:
   - `cd frontend && npm install`
3. Configure environment variables in `.env` (optional if configuring via API/UI):
   - `JIRA_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, `JIRA_PROJECT_KEY`
4. Run backend API:
   - `uvicorn app.backend.api:app --host 0.0.0.0 --port 8000 --reload`
5. Run React frontend:
   - `cd frontend && npm run dev`

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
- `POST /jira/create-stories`
- `GET /jira/config`
- `POST /jira/configure`
- `GET /jira/health`