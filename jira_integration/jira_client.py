

# import os
# from jira import JIRA
# from dotenv import load_dotenv

# def get_jira():
#     load_dotenv()
#     return JIRA(
#         server=os.getenv("JIRA_URL"),
#         basic_auth=(
#             os.getenv("JIRA_EMAIL"),
#             os.getenv("JIRA_API_TOKEN")
#         )
#     )



from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from jira import JIRA

load_dotenv()

_RUNTIME_JIRA_CONFIG: dict[str, str | None] = {}


def _resolved_config(overrides: dict[str, Any] | None = None) -> dict[str, str | None]:
    config = {
        "jira_url": os.getenv("JIRA_URL"),
        "jira_email": os.getenv("JIRA_EMAIL"),
        "jira_api_token": os.getenv("JIRA_API_TOKEN"),
        "jira_project_key": os.getenv("JIRA_PROJECT_KEY"),
    }
    config.update(_RUNTIME_JIRA_CONFIG)
    if overrides:
        config.update({k: v for k, v in overrides.items() if v is not None})
    return config


def configure_jira(config: dict[str, Any]) -> dict[str, Any]:
    _RUNTIME_JIRA_CONFIG.update({k: v for k, v in config.items() if k in {"jira_url", "jira_email", "jira_api_token", "jira_project_key"}})
    return get_current_jira_config()


def get_current_jira_config() -> dict[str, Any]:
    config = _resolved_config()
    return {
        "jira_url": config.get("jira_url"),
        "jira_email": config.get("jira_email"),
        "jira_project_key": config.get("jira_project_key"),
        "configured": all(
            [
                config.get("jira_url"),
                config.get("jira_email"),
                config.get("jira_api_token"),
                config.get("jira_project_key"),
            ]
        ),
        "token_configured": bool(config.get("jira_api_token")),
    }


def get_jira(overrides: dict[str, Any] | None = None) -> JIRA:
    config = _resolved_config(overrides)
    missing = [
        key
        for key in ["jira_url", "jira_email", "jira_api_token"]
        if not config.get(key)
    ]
    if missing:
        raise ValueError(f"Missing Jira configuration values: {', '.join(missing)}")

    return JIRA(
        server=config["jira_url"],
        basic_auth=(
            config["jira_email"],
            config["jira_api_token"],
        ),
    )


def test_jira_connection() -> dict[str, Any]:
    try:
        jira = get_jira()
        myself = jira.myself()
        return {"ok": True, "user": myself.get("displayName") or myself.get("name")}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}