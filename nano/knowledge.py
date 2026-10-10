import re
from .db import run, rows

MAX_INGEST_CHARS = 200_000
MAX_CHUNK_CHARS = 2_000
MAX_CHUNKS = 200

def _split_long_text(text, max_chars=MAX_CHUNK_CHARS):
    """Split text at whitespace boundaries without oversized chunks."""
    words = text.split()
    chunks = []
    current = []
    current_length = 0
    for word in words:
        if len(word) > max_chars:
            if current:
                chunks.append(" ".join(current))
                current, current_length = [], 0
            chunks.extend(word[i:i + max_chars] for i in range(0, len(word), max_chars))
            continue
        extra = len(word) + (1 if current else 0)
        if current and current_length + extra > max_chars:
            chunks.append(" ".join(current))
            current, current_length = [word], len(word)
        else:
            current.append(word)
            current_length += extra
    if current:
        chunks.append(" ".join(current))
    return chunks

def _chunks(clean):
    chunks = []
    for sentence in re.split(r"(?<=[.!?])\s+", clean):
        sentence = sentence.strip()
        if len(sentence) <= MAX_CHUNK_CHARS:
            if len(sentence) > 20:
                chunks.append(sentence)
        else:
            chunks.extend(part for part in _split_long_text(sentence) if len(part) > 20)
    if len(chunks) > MAX_CHUNKS:
        raise ValueError(f"Knowledge text produces {len(chunks)} chunks; limit is {MAX_CHUNKS}. Split the source into smaller imports.")
    return chunks

def ingest(text, source="local"):
    if not isinstance(text, str):
        raise ValueError("Knowledge text must be a string.")
    clean = re.sub(r"\s+", " ", text).strip()
    if not clean:
        return 0
    if len(clean) > MAX_INGEST_CHARS:
        raise ValueError(f"Knowledge import is limited to {MAX_INGEST_CHARS} characters.")
    chunks = _chunks(clean)
    count = 0
    for chunk in chunks:
        run("INSERT INTO memories(kind,content,confidence,status,source) VALUES(?,?,?,?,?)",
            ("knowledge", chunk, 0.65, "active", source))
        count += 1
    run("INSERT INTO learning_events(event_type,input_text,result) VALUES(?,?,?)",
        ("knowledge_import", clean, str(count)))
    return count

def recent(limit=50, offset=0):
    limit = max(1, min(int(limit), 500))
    safe_offset = max(0, int(offset))
    return rows("SELECT * FROM memories WHERE kind='knowledge' AND status='active' ORDER BY id DESC LIMIT ? OFFSET ?",
                (limit, safe_offset))
