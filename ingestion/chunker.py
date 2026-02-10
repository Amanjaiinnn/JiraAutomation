
# def chunk_requirements(text, n=5):
#     lines = [l for l in text.split("\n") if l.strip()]
#     return ["\n".join(lines[i:i+n]) for i in range(0, len(lines), n)]

def chunk_requirements(text, max_lines=5):
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    chunks = []

    for i in range(0, len(lines), max_lines):
        chunk = "\n".join(lines[i:i + max_lines])
        chunks.append(chunk)

    return chunks
