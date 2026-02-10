
import os
from dotenv import load_dotenv
load_dotenv()

GROQ_MODEL = os.getenv("GROQ_MODEL", "mixtral-8x7b-32768")
JIRA_URL = os.getenv("JIRA_URL")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY")
