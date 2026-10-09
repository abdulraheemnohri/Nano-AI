import json
import re
from itertools import combinations
from .db import rows, run, connect

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



def _normalize(content):
    return re.sub(r"\s+", " ", str(content or "").strip().casefold())


def find_duplicate_candidates(limit=100):
    """Suggest exact or highly similar active memories; never change memory records."""
    limit = max(1, min(int(limit), 300))
    items = rows("SELECT id,kind,content,source,confidence,created_at FROM memories WHERE status='active' ORDER BY updated_at DESC LIMIT 500")
    candidates = []
    normalized = [(item, _normalize(item["content"])) for item in items]
    for (left, left_text), (right, right_text) in combinations(normalized, 2):
        if not left_text or not right_text:
            continue
        score = 1.0 if left_text == right_text else 0.0
        if score == 0:
            left_words = set(re.findall(r"\w+", left_text))
            right_words = set(re.findall(r"\w+", right_text))
            if left_words and right_words:
                union = left_words | right_words
                overlap = len(left_words & right_words) / len(union)
                if overlap >= 0.82 and min(len(left_text), len(right_text)) / max(len(left_text), len(right_text)) >= 0.65:
                    score = overlap
        if score:
            candidates.append({
                "source_ids": [left["id"], right["id"]],
                "kind": left["kind"] if left["kind"] == right["kind"] else "consolidated",
                "source": "memory-review",
                "score": round(score, 3),
                "memories": [
                    {"id": left["id"], "kind": left["kind"], "content": left["content"], "source": left["source"]},
                    {"id": right["id"], "kind": right["kind"], "content": right["content"], "source": right["source"]},
                ],
                "suggested_content": left["content"] if left_text == right_text else left["content"].strip() + "\n\n" + right["content"].strip(),
            })
    candidates.sort(key=lambda item: (-item["score"], item["source_ids"]))
    return candidates[:limit]


def create_consolidation_proposals(limit=50):
    """Queue deduplicated suggestions for user review. Does not merge or delete anything."""
    existing = rows("SELECT source_ids FROM memory_consolidation_proposals")
    known = {tuple(sorted(json.loads(item["source_ids"]))) for item in existing}
    created = 0
    for candidate in find_duplicate_candidates(limit=300):
        ids = tuple(sorted(candidate["source_ids"]))
        if ids in known:
            continue
        run(
            "INSERT INTO memory_consolidation_proposals(source_ids,merged_content,kind,source) VALUES(?,?,?,?)",
            (json.dumps(ids), candidate["suggested_content"], candidate["kind"], candidate["source"]),
        )
        known.add(ids)
        created += 1
        if created >= max(1, min(int(limit), 100)):
            break
    return {"created": created, "proposals": list_consolidation_proposals()}


def list_consolidation_proposals():
    proposals = rows("SELECT * FROM memory_consolidation_proposals WHERE status='pending' ORDER BY id DESC LIMIT 100")
    active = {item["id"]: item for item in rows("SELECT id,kind,content,source FROM memories WHERE status='active'")}
    result = []
    for proposal in proposals:
        ids = json.loads(proposal["source_ids"])
        source_memories = [active[mid] for mid in ids if mid in active]
        result.append({**proposal, "source_ids": ids, "memories": source_memories})
    return result


def approve_consolidation(proposal_id, merged_content=None):
    """Atomically add the reviewed memory and mark its source memories as merged."""
    with connect() as connection:
        proposal = connection.execute(
            "SELECT * FROM memory_consolidation_proposals WHERE id=? AND status='pending'",
            (proposal_id,),
        ).fetchone()
        if not proposal:
            raise ValueError("Pending consolidation proposal not found")
        source_ids = json.loads(proposal["source_ids"])
        if len(source_ids) < 2 or len(source_ids) > 20:
            raise ValueError("Invalid consolidation source list")
        content = str(merged_content if merged_content is not None else proposal["merged_content"]).strip()
        if not content or len(content) > 12000:
            raise ValueError("Merged memory must contain 1 to 12000 characters")
        placeholders = ",".join("?" for _ in source_ids)
        source_rows = connection.execute(
            f"SELECT id,kind,source FROM memories WHERE status='active' AND id IN ({placeholders})",
            tuple(source_ids),
        ).fetchall()
        if len(source_rows) != len(set(source_ids)):
            raise ValueError("One or more source memories are no longer active; refresh the review queue")
        kinds = {item["kind"] for item in source_rows}
        kind = next(iter(kinds)) if len(kinds) == 1 else "consolidated"
        source = "consolidated:" + ",".join(str(mid) for mid in source_ids)
        cursor = connection.execute(
            "INSERT INTO memories(kind,content,confidence,status,source) VALUES(?,?,0.7,'active',?)",
            (kind, content, source),
        )
        connection.execute(
            f"UPDATE memories SET status='merged',updated_at=CURRENT_TIMESTAMP WHERE status='active' AND id IN ({placeholders})",
            tuple(source_ids),
        )
        connection.execute(
            "UPDATE memory_consolidation_proposals SET status='accepted',reviewed_at=CURRENT_TIMESTAMP WHERE id=?",
            (proposal_id,),
        )
        return {"ok": True, "memory_id": cursor.lastrowid, "source_ids": source_ids}


def reject_consolidation(proposal_id):
    with connect() as connection:
        cursor = connection.execute(
            "UPDATE memory_consolidation_proposals SET status='rejected',reviewed_at=CURRENT_TIMESTAMP WHERE id=? AND status='pending'",
            (proposal_id,),
        )
        if cursor.rowcount != 1:
            raise ValueError("Pending consolidation proposal not found")
    return {"ok": True}
