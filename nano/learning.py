import re
from .db import rows, run

PATTERNS = [
    (r"\\bremember that\\s+(.+)", "fact", 0.9),
    (r"\\bmy name is\\s+(.+)", "preference", 0.95),
    (r"\\bi prefer\\s+(.+)", "preference", 0.9),
    (r"\\bi like\\s+(.+)", "preference", 0.85),
    (r"\\blearn that\\s+(.+)", "fact", 0.9),
    (r"\\bremember\\s+(.+)", "fact", 0.8),
]
MAX_LEARNED_CHARS = 1000


def _clean(value):
    value = re.sub(r"\\s+", " ", value).strip().rstrip(".!?")
    return value[:MAX_LEARNED_CHARS].strip()


def learn_from_text(text):
    found = []
    if not isinstance(text, str):
        return found
    for pattern, kind, confidence in PATTERNS:
        match = re.search(pattern, text, re.I)
        if not match:
            continue
        content = _clean(match.group(1))
        if not content:
            continue
        existing = rows("SELECT id,kind,confidence FROM memories WHERE status='active' AND content=? LIMIT 1", (content,))
        if existing:
            found.append({"id": existing[0]["id"], "kind": existing[0]["kind"], "content": content, "confidence": existing[0]["confidence"]})
            continue
        mid = run("INSERT INTO memories(kind,content,confidence,status,source) VALUES(?,?,?,?,?)", (kind, content, confidence, "active", "conversation"))
        found.append({"id": mid, "kind": kind, "content": content, "confidence": confidence})
    run("INSERT INTO learning_events(event_type,input_text,result) VALUES(?,?,?)", ("conversation", text[:12000], str(found)))
    return found


def memories(limit=20):
    limit = max(1, min(int(limit), 500))
    return rows("SELECT * FROM memories WHERE status='active' ORDER BY confidence DESC,updated_at DESC LIMIT ?", (limit,))


def events(limit=100):
    limit = max(1, min(int(limit), 500))
    return rows("SELECT * FROM learning_events ORDER BY id DESC LIMIT ?", (limit,))


def delete_memory(mid):
    run("UPDATE memories SET status='deleted',updated_at=CURRENT_TIMESTAMP WHERE id=?", (mid,))
