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

        objectives = list(dict.fromkeys(current.get("business_objectives", []) + epic.get("business_objectives", [])))
        current["business_objectives"] = objectives

        acceptance = list(dict.fromkeys(current.get("acceptance_criteria", []) + epic.get("acceptance_criteria", [])))
        current["acceptance_criteria"] = acceptance

        dod = list(dict.fromkeys(current.get("definition_of_done", []) + epic.get("definition_of_done", [])))
        current["definition_of_done"] = dod

        in_scope = list(dict.fromkeys(current.get("scope", {}).get("in_scope", []) + epic.get("scope", {}).get("in_scope", [])))
        out_scope = list(dict.fromkeys(current.get("scope", {}).get("out_of_scope", []) + epic.get("scope", {}).get("out_of_scope", [])))
        current["scope"] = {
            "in_scope": in_scope,
            "out_of_scope": out_scope,
        }

        source_chunk_ids = list(dict.fromkeys(current.get("source_chunk_ids", []) + epic.get("source_chunk_ids", [])))
        current["source_chunk_ids"] = source_chunk_ids

        if len(epic.get("description", "")) > len(current.get("description", "")):
            current["description"] = epic["description"]

        if len(epic.get("summary", "")) > len(current.get("summary", "")):
            current["summary"] = epic.get("summary", "")

    return list(merged.values())
