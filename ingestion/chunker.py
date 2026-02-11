import hashlib
import re
from typing import Dict, List


def _normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip())


def _line_key(line: str) -> str:
    """Stable identifier component for a requirement line."""
    digest = hashlib.sha1(line.encode("utf-8")).hexdigest()[:10]
    return digest


def chunk_requirements(text: str, max_lines: int = 5) -> List[Dict[str, str]]:
    """
    Build small semantic chunks with stable ids.

    Returns:
        [{"chunk_id": "C-<hash>", "text": "..."}, ...]
    """
    lines = [_normalize_line(l) for l in text.splitlines() if l.strip()]
    if not lines:
        return []

    chunks: List[Dict[str, str]] = []
    bucket: List[str] = []

    for line in lines:
        bucket.append(line)
        semantic_break = line.endswith(":") or line.lower().startswith(("epic", "module", "feature"))
        if len(bucket) >= max_lines or semantic_break:
            chunk_text = "\n".join(bucket)
            chunk_id = f"C-{_line_key(chunk_text)}"
            chunks.append({"chunk_id": chunk_id, "text": chunk_text})
            bucket = []

    if bucket:
        chunk_text = "\n".join(bucket)
        chunk_id = f"C-{_line_key(chunk_text)}"
        chunks.append({"chunk_id": chunk_id, "text": chunk_text})

    return chunks
