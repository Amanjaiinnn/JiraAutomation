

from typing import Dict, List


def _norm(value: str) -> str:
    return " ".join(value.lower().split())


def merge_and_dedupe(stories: List[Dict]) -> List[Dict]:
    deduped = {}
    for story in stories:
        key = (_norm(story.get("epic_name", "")), _norm(story.get("summary", "")))
        if not key[1]:
            continue
        if key not in deduped:
            deduped[key] = story
            continue

        existing = deduped[key]
        for f in ("acceptance_criteria", "definition_of_done"):
            merged = list(dict.fromkeys(existing.get(f, []) + story.get(f, [])))
            existing[f] = merged

    return list(deduped.values())
