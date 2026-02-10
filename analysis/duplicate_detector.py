from jira_integration.jira_client import get_jira
import os
from dotenv import load_dotenv
from difflib import SequenceMatcher


def fetch_existing_issues(limit=50):
    load_dotenv()
    jira = get_jira()
    project_key = os.getenv("JIRA_PROJECT_KEY")

    jql = f"""
    project = {project_key}
    AND issuetype IN (Story, Task, Bug)
    AND created >= -90d
    ORDER BY created DESC
    """

    issues = jira.search_issues(
        jql_str=jql,
        maxResults=limit
    )

    results = []
    for issue in issues:
        results.append({
            "key": issue.key,
            "summary": issue.fields.summary
        })

    return results


def similarity(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def detect_duplicates(story, threshold=0.75):
    """
    story: one generated story dict
    """
    existing_issues = fetch_existing_issues()

    duplicates = []
    for issue in existing_issues:
        score = similarity(story["summary"], issue["summary"])
        if score >= threshold:
            duplicates.append({
                "jira_key": issue["key"],
                "similarity": round(score, 2)
            })

    return duplicates
