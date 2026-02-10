
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
1. pip install -r requirements.txt
2. Create .env (see README)
3. python -m streamlit run app/main.py
