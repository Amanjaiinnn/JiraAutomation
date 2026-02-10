def merge_and_dedupe_epics(epics: list) -> list:
    seen = {}
    for epic in epics:
        key = epic["epic_name"].lower()
        if key not in seen:
            seen[key] = epic
    return list(seen.values())
