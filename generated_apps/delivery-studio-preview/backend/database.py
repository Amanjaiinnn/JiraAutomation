import os
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parent / ".env")


def get_database_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/generated_story_app")


def get_connection():
    return psycopg2.connect(get_database_url(), cursor_factory=RealDictCursor)
