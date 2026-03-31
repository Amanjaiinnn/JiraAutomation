import os
import sys
from pathlib import Path

os.environ.setdefault("GROQ_API_KEY", "test-key")
sys.path.append(str(Path(__file__).resolve().parents[1]))

from jira_integration.story_creator import JIRA_SUMMARY_LIMIT, _normalize_summary


def test_normalize_summary_trims_whitespace_and_collapses_lines():
    summary = _normalize_summary("  Epic\nname\twith   spaces  ")
    assert summary == "Epic name with spaces"


def test_normalize_summary_truncates_to_jira_limit():
    raw = "AI generated epic for enterprise customer onboarding and approval workflow with policy validation and multi-step review across operations teams " * 3
    summary = _normalize_summary(raw)

    assert len(summary) <= JIRA_SUMMARY_LIMIT
    assert "..." not in summary
    assert "onboarding" in summary.lower()


def test_normalize_summary_rejects_blank_values():
    try:
        _normalize_summary("   \n\t  ")
        assert False, "Expected ValueError for blank summary"
    except ValueError as exc:
        assert "cannot be empty" in str(exc)
