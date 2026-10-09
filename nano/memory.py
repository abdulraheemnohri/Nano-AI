from .db import rows, run

MAX_LIMIT = 500


def _limit(value, default=8):
    try:
        return max(1, min(int(value), MAX_LIMIT))
    except (TypeError, ValueError):
        return default


def search(query, limit=8):
    query = str(query or "").strip()
    limit = _limit(limit)
    if not query:
        return rows("SELECT * FROM memories WHERE status='active' ORDER BY confidence DESC,updated_at DESC LIMIT ?", (limit,))
    escaped = query.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
    pattern = f"%{escaped}%"
    return rows("SELECT * FROM memories WHERE status='active' AND content LIKE ? ESCAPE '\\' ORDER BY confidence DESC,updated_at DESC LIMIT ?", (pattern, limit))


def forget(mid):
    run("UPDATE memories SET status='deleted',updated_at=CURRENT_TIMESTAMP WHERE id=? AND status='active'", (mid,))
    return True


def clear():
    run("UPDATE memories SET status='deleted',updated_at=CURRENT_TIMESTAMP WHERE status='active'")
    return True
