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
            merged[key].setdefault("source_chunk_ids", epic.get("source_chunk_ids", []))
            continue

        current = merged[key]
        covered = list(dict.fromkeys(current.get("covered_requirements", []) + epic.get("covered_requirements", [])))
        current["covered_requirements"] = covered

        source_chunk_ids = list(dict.fromkeys(current.get("source_chunk_ids", []) + epic.get("source_chunk_ids", [])))
        current["source_chunk_ids"] = source_chunk_ids

        if len(epic.get("description", "")) > len(current.get("description", "")):
            current["description"] = epic["description"]

    return list(merged.values())
