from .db import rows,run

def search(query,limit=8):
    q=f"%{query.strip()}%"
    return rows("SELECT * FROM memories WHERE status='active' AND content LIKE ? ORDER BY confidence DESC,updated_at DESC LIMIT ?",(q,limit))

def forget(mid):
    run("UPDATE memories SET status='deleted',updated_at=CURRENT_TIMESTAMP WHERE id=?",(mid,))
    return True

def clear():
    run("UPDATE memories SET status='deleted',updated_at=CURRENT_TIMESTAMP WHERE status='active'")
    return True
