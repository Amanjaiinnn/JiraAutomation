

from typing import Dict, List


def _norm(v: str) -> str:
    return " ".join(v.lower().split())


def merge_and_dedupe_epics(epics: List[Dict]) -> List[Dict]:
    merged = {}
    for epic in epics:
        key = _norm(epic.get("epic_name", ""))
        if not key:
            continue
        if key not in merged:
            merged[key] = epic
            continue

        current = merged[key]
        covered = list(dict.fromkeys(current.get("covered_requirements", []) + epic.get("covered_requirements", [])))
        current["covered_requirements"] = covered
        if len(epic.get("description", "")) > len(current.get("description", "")):
            current["description"] = epic["description"]

    return list(merged.values())
