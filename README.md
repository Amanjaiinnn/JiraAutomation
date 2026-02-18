
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

If `JIRA_AUTOMATION_API_BASE_URL` is not set, UI uses local API service fallback with the same contracts.
