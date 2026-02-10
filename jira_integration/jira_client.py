
# from jira import JIRA
# from app.config import JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN

# def get_jira():
#     return JIRA(server=JIRA_URL, basic_auth=(JIRA_EMAIL, JIRA_API_TOKEN))

import os
from jira import JIRA
from dotenv import load_dotenv

def get_jira():
    load_dotenv()
    return JIRA(
        server=os.getenv("JIRA_URL"),
        basic_auth=(
            os.getenv("JIRA_EMAIL"),
            os.getenv("JIRA_API_TOKEN")
        )
    )
