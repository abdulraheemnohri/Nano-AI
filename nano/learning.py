import re
from .db import rows, run

PATTERNS = [
    (r"\bremember that\s+(.+)", "fact", 0.9),
    (r"\bmy name is\s+(.+)", "preference", 0.95),
    (r"\bi prefer\s+(.+)", "preference", 0.9),
    (r"\bi like\s+(.+)", "preference", 0.85),
    (r"\blearn that\s+(.+)", "fact", 0.9),
    (r"\bremember\s+(.+)", "fact", 0.8),
]
MAX_LEARNED_CHARS = 1000
MAX_EVENT_CHARS = 12000


def _clean(value):
    value = re.sub(r"\s+", " ", value).strip().rstrip(".!?")
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
        existing = rows(
            "SELECT id,kind,confidence FROM memories WHERE status='active' AND content=? LIMIT 1",
            (content,),
        )
        if existing:
            found.append({
                "id": existing[0]["id"],
                "kind": existing[0]["kind"],
                "content": content,
                "confidence": existing[0]["confidence"],
            })
            continue
        mid = run(
            "INSERT INTO memories(kind,content,confidence,status,source) VALUES(?,?,?,?,?)",
            (kind, content, confidence, "active", "conversation"),
        )
        found.append({"id": mid, "kind": kind, "content": content, "confidence": confidence})
    run(
        "INSERT INTO learning_events(event_type,input_text,result) VALUES(?,?,?)",
        ("conversation", text[:MAX_EVENT_CHARS], str(found)),
    )
    return found


def memories(limit=20):
    limit = max(1, min(int(limit), 500))
    return rows(
        "SELECT * FROM memories WHERE status='active' ORDER BY confidence DESC,updated_at DESC LIMIT ?",
        (limit,),
    )


def events(limit=100):
    limit = max(1, min(int(limit), 500))
    return rows("SELECT * FROM learning_events ORDER BY id DESC LIMIT ?", (limit,))


def delete_memory(mid):
    run("UPDATE memories SET status='deleted',updated_at=CURRENT_TIMESTAMP WHERE id=?", (mid,))



def save_response_feedback(conversation_id, user_text, assistant_text, rating, correction=""):
    """Persist explicit user feedback; never silently train model weights."""
    if isinstance(conversation_id, bool) or not isinstance(conversation_id, int) or conversation_id < 1:
        raise ValueError("Invalid conversation id.")
    if isinstance(rating, bool) or rating not in (-1, 1):
        raise ValueError("rating must be 1 (helpful) or -1 (not helpful).")
    user_text = str(user_text or "").strip()
    assistant_text = str(assistant_text or "").strip()
    correction = re.sub(r"\s+", " ", str(correction or "")).strip()
    if not user_text or len(user_text) > 12000:
        raise ValueError("User message must contain 1-12000 characters.")
    if not assistant_text or len(assistant_text) > 20000:
        raise ValueError("Assistant response must contain 1-20000 characters.")
    if len(correction) > 2000:
        raise ValueError("Correction is limited to 2000 characters.")
    fid = run(
        "INSERT INTO response_feedback(conversation_id,user_text,assistant_text,rating,correction) VALUES(?,?,?,?,?)",
        (conversation_id, user_text, assistant_text, rating, correction),
    )
    run(
        "INSERT INTO learning_events(event_type,input_text,result) VALUES(?,?,?)",
        ("response_feedback", user_text[:MAX_EVENT_CHARS],
         str({"feedback_id": fid, "rating": rating, "correction": correction[:500]})),
    )
    return {"id": fid, "rating": rating, "correction_saved": bool(correction)}


def feedback_examples(limit=5):
    limit = max(1, min(int(limit), 10))
    return rows(
        "SELECT rating,correction FROM response_feedback WHERE correction<>'' ORDER BY id DESC LIMIT ?",
        (limit,),
    )


def feedback_summary():
    row = rows(
        "SELECT COUNT(*) AS total, "
        "SUM(CASE WHEN rating=1 THEN 1 ELSE 0 END) AS helpful, "
        "SUM(CASE WHEN rating=-1 THEN 1 ELSE 0 END) AS unhelpful, "
        "SUM(CASE WHEN correction<>'' THEN 1 ELSE 0 END) AS corrections "
        "FROM response_feedback"
    )
    return {key: int(value or 0) for key, value in row[0].items()} if row else {
        "total": 0, "helpful": 0, "unhelpful": 0, "corrections": 0
    }



def quality_report():
    """Return descriptive local feedback metrics; never claim causal model improvement."""
    summary = feedback_summary()
    total = summary["total"]
    rated = summary["helpful"] + summary["unhelpful"]
    summary["helpful_rate_percent"] = round(summary["helpful"] * 100 / rated, 1) if rated else None
    summary["correction_rate_percent"] = round(summary["corrections"] * 100 / total, 1) if total else None
    windows = rows(
        "SELECT "
        "SUM(CASE WHEN created_at >= datetime('now','-7 days') THEN 1 ELSE 0 END) AS recent_total, "
        "SUM(CASE WHEN created_at >= datetime('now','-7 days') AND rating=1 THEN 1 ELSE 0 END) AS recent_helpful, "
        "SUM(CASE WHEN created_at >= datetime('now','-7 days') AND rating=-1 THEN 1 ELSE 0 END) AS recent_unhelpful, "
        "SUM(CASE WHEN created_at < datetime('now','-7 days') AND created_at >= datetime('now','-14 days') THEN 1 ELSE 0 END) AS previous_total, "
        "SUM(CASE WHEN created_at < datetime('now','-7 days') AND created_at >= datetime('now','-14 days') AND rating=1 THEN 1 ELSE 0 END) AS previous_helpful, "
        "SUM(CASE WHEN created_at < datetime('now','-7 days') AND created_at >= datetime('now','-14 days') AND rating=-1 THEN 1 ELSE 0 END) AS previous_unhelpful "
        "FROM response_feedback"
    )
    window = {key: int(value or 0) for key, value in (windows[0] if windows else {}).items()}
    recent_rated = window["recent_helpful"] + window["recent_unhelpful"]
    previous_rated = window["previous_helpful"] + window["previous_unhelpful"]
    recent_rate = round(window["recent_helpful"] * 100 / recent_rated, 1) if recent_rated else None
    previous_rate = round(window["previous_helpful"] * 100 / previous_rated, 1) if previous_rated else None
    summary.update({
        "last_7_days": window["recent_total"],
        "previous_7_days": window["previous_total"],
        "last_7_days_helpful_rate_percent": recent_rate,
        "previous_7_days_helpful_rate_percent": previous_rate,
        "helpful_rate_change_percentage_points": round(recent_rate - previous_rate, 1) if recent_rate is not None and previous_rate is not None else None,
    })
    summary["daily"] = rows(
        "SELECT date(created_at) AS day, COUNT(*) AS total, "
        "SUM(CASE WHEN rating=1 THEN 1 ELSE 0 END) AS helpful, "
        "SUM(CASE WHEN rating=-1 THEN 1 ELSE 0 END) AS unhelpful, "
        "SUM(CASE WHEN correction<>'' THEN 1 ELSE 0 END) AS corrections "
        "FROM response_feedback WHERE created_at >= datetime('now','-13 days') "
        "GROUP BY date(created_at) ORDER BY day"
    )
    summary["daily"] = [{key: (int(value or 0) if key in {"total", "helpful", "unhelpful", "corrections"} else value) for key, value in item.items()} for item in summary["daily"]]
    summary["last_feedback_at"] = rows("SELECT MAX(created_at) AS value FROM response_feedback")[0]["value"] if total else None
    return summary
