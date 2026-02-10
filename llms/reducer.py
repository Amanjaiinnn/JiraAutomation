def merge_and_dedupe(stories):
    seen = set()
    final = []

    for s in stories:
        key = s["summary"].lower()
        if key not in seen:
            seen.add(key)
            final.append(s)

    return final
