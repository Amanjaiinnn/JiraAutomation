from jira import JIRA
import os
from dotenv import load_dotenv

load_dotenv()

print("JIRA_URL:", os.getenv("JIRA_URL"))
print("JIRA_EMAIL:", os.getenv("JIRA_EMAIL"))
print("JIRA_API_TOKEN loaded:", bool(os.getenv("JIRA_API_TOKEN")))

jira = JIRA(
    server=os.getenv("JIRA_URL"),
    basic_auth=(os.getenv("JIRA_EMAIL"), os.getenv("JIRA_API_TOKEN"))
)

print("✅ Connected to Jira")
print("Server info:", jira.server_info())

projects = jira.projects()
print("Projects available:", [p.key for p in projects])

issue = jira.create_issue(
    project={"key": "SCRUM"},
    summary="TEST ISSUE – JIRA API CHECK",
    description="If you see this issue, Jira API integration is working.",
    issuetype={"name": "Task"}
)

print("🎉 Issue created:", issue.key)
