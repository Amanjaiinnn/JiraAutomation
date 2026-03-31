# Run Guide

Frontend Stack: `react_vite`
Backend Stack: `python_fastapi`
Database: `postgresql`

Database:
1. Create or choose a PostgreSQL database.
2. Set `DATABASE_URL` before starting the backend.
   Example: `postgresql://postgres:password@localhost:5432/generated_story_app`

Backend:
1. `cd backend`
2. `pip install -r requirements.txt`
3. `uvicorn main:app --host 0.0.0.0 --port 8001 --reload`

Frontend:
1. `cd frontend`
2. `npm install`
3. `npm run dev`
