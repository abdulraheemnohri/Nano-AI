"""Policy-bounded Self-X primitives for Nano AI.

This module records goals, reflections, and lessons; it does not grant new
permissions, execute generated code, or modify model weights.
"""
import json
from . import config
from .db import connect, rows, run

MAX_TITLE_CHARS = 160
MAX_TEXT_CHARS = 6000
MAX_SOURCE_CHARS = 1000
GOAL_STATUSES = {"planned", "active", "blocked", "completed", "cancelled"}


def init_selfx_db():
    """Create additive Self-X tables without modifying existing schemas."""
    with connect() as connection:
        connection.executescript("""
        CREATE TABLE IF NOT EXISTS selfx_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            priority INTEGER NOT NULL DEFAULT 3 CHECK(priority BETWEEN 1 AND 5),
            status TEXT NOT NULL DEFAULT 'planned',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_selfx_goals_status_priority
            ON selfx_goals(status, priority, updated_at);
        CREATE TABLE IF NOT EXISTS selfx_lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,
            lesson TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'experience',
            outcome TEXT NOT NULL DEFAULT 'observed',
            confidence REAL NOT NULL DEFAULT 0.5 CHECK(confidence >= 0 AND confidence <= 1),
            evidence_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_selfx_lessons_topic ON selfx_lessons(topic, created_at);
        CREATE TABLE IF NOT EXISTS selfx_reflections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scope TEXT NOT NULL,
            summary TEXT NOT NULL,
            findings_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """)


def _bounded_text(value, label, limit=MAX_TEXT_CHARS, required=True):
    if not isinstance(value, str):
        raise ValueError(f"{label} must be text.")
    value = value.strip()
    if required and not value:
        raise ValueError(f"{label} cannot be empty.")
    if len(value) > limit:
        raise ValueError(f"{label} exceeds {limit} characters.")
    return value


def create_goal(title, description="", priority=3):
    title = _bounded_text(title, "title", MAX_TITLE_CHARS)
    description = _bounded_text(description, "description", MAX_TEXT_CHARS, required=False)
    if isinstance(priority, bool) or not isinstance(priority, int) or not 1 <= priority <= 5:
        raise ValueError("priority must be an integer from 1 to 5.")
    goal_id = run(
        "INSERT INTO selfx_goals(title,description,priority) VALUES(?,?,?)",
        (title, description, priority),
    )
    return get_goal(goal_id)


def list_goals(status=None, limit=100, offset=0):
    try:
        limit = max(1, min(int(limit), 200))
        offset = max(0, int(offset))
    except (TypeError, ValueError):
        raise ValueError("limit and offset must be integers.")
    if status is not None:
        if status not in GOAL_STATUSES:
            raise ValueError("Unsupported goal status.")
        return rows(
            "SELECT * FROM selfx_goals WHERE status=? ORDER BY priority ASC, updated_at DESC, id DESC LIMIT ? OFFSET ?",
            (status, limit, offset),
        )
    return rows(
        "SELECT * FROM selfx_goals ORDER BY CASE status WHEN 'active' THEN 0 WHEN 'planned' THEN 1 ELSE 2 END, priority ASC, updated_at DESC, id DESC LIMIT ? OFFSET ?",
        (limit, offset),
    )


def get_goal(goal_id):
    found = rows("SELECT * FROM selfx_goals WHERE id=?", (goal_id,))
    return found[0] if found else None


def update_goal(goal_id, status=None, title=None, description=None, priority=None):
    if not rows("SELECT id FROM selfx_goals WHERE id=?", (goal_id,)):
        raise KeyError("Goal not found.")
    fields, values = [], []
    if status is not None:
        if status not in GOAL_STATUSES:
            raise ValueError("Unsupported goal status.")
        fields.append("status=?")
        values.append(status)
    if title is not None:
        fields.append("title=?")
        values.append(_bounded_text(title, "title", MAX_TITLE_CHARS))
    if description is not None:
        fields.append("description=?")
        values.append(_bounded_text(description, "description", MAX_TEXT_CHARS, required=False))
    if priority is not None:
        if isinstance(priority, bool) or not isinstance(priority, int) or not 1 <= priority <= 5:
            raise ValueError("priority must be an integer from 1 to 5.")
        fields.append("priority=?")
        values.append(priority)
    if fields:
        fields.append("updated_at=CURRENT_TIMESTAMP")
        values.append(goal_id)
        run("UPDATE selfx_goals SET " + ", ".join(fields) + " WHERE id=?", tuple(values))
    return get_goal(goal_id)


def record_lesson(topic, lesson, source="experience", outcome="observed", confidence=0.5, evidence=None):
    topic = _bounded_text(topic, "topic", MAX_TITLE_CHARS)
    lesson = _bounded_text(lesson, "lesson", MAX_TEXT_CHARS)
    source = _bounded_text(source, "source", MAX_SOURCE_CHARS)
    outcome = _bounded_text(outcome, "outcome", 80)
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        raise ValueError("confidence must be between 0 and 1.")
    if evidence is None:
        evidence = []
    if not isinstance(evidence, list) or len(evidence) > 20:
        raise ValueError("evidence must be a list of at most 20 items.")
    safe_evidence = []
    for item in evidence:
        if not isinstance(item, dict):
            raise ValueError("Each evidence item must be an object.")
        safe_evidence.append({
            "source": _bounded_text(str(item.get("source", "")), "evidence source", 1000),
            "note": _bounded_text(str(item.get("note", "")), "evidence note", 1000, required=False),
        })
    evidence_json = json.dumps(safe_evidence, ensure_ascii=False)
    lesson_id = run(
        "INSERT INTO selfx_lessons(topic,lesson,source,outcome,confidence,evidence_json) VALUES(?,?,?,?,?,?)",
        (topic, lesson, source, outcome, float(confidence), evidence_json),
    )
    result = rows("SELECT * FROM selfx_lessons WHERE id=?", (lesson_id,))[0]
    result["evidence"] = json.loads(result.pop("evidence_json"))
    return result


def list_lessons(topic=None, limit=100, offset=0):
    try:
        limit = max(1, min(int(limit), 200))
        offset = max(0, int(offset))
    except (TypeError, ValueError):
        raise ValueError("limit and offset must be integers.")
    if topic is not None:
        topic = _bounded_text(topic, "topic", MAX_TITLE_CHARS)
        found = rows(
            "SELECT * FROM selfx_lessons WHERE topic=? ORDER BY id DESC LIMIT ? OFFSET ?",
            (topic, limit, offset),
        )
    else:
        found = rows("SELECT * FROM selfx_lessons ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset))
    for item in found:
        item["evidence"] = json.loads(item.pop("evidence_json"))
    return found


def reflect(scope, summary, findings=None):
    scope = _bounded_text(scope, "scope", MAX_TITLE_CHARS)
    summary = _bounded_text(summary, "summary", MAX_TEXT_CHARS)
    findings = [] if findings is None else findings
    if not isinstance(findings, list) or len(findings) > 50:
        raise ValueError("findings must be a list of at most 50 items.")
    normalized = [_bounded_text(str(item), "finding", 1000) for item in findings]
    reflection_id = run(
        "INSERT INTO selfx_reflections(scope,summary,findings_json) VALUES(?,?,?)",
        (scope, summary, json.dumps(normalized, ensure_ascii=False)),
    )
    return rows("SELECT id,scope,summary,findings_json,created_at FROM selfx_reflections WHERE id=?", (reflection_id,))[0]


def run_self_check():
    """Collect a bounded, read-only snapshot and actionable recommendations."""
    counts = {}
    for table in ("conversations", "messages", "memories", "learning_events", "skills", "skill_proposals"):
        try:
            result = rows(f"SELECT COUNT(*) AS count FROM {table}")
            counts[table] = int(result[0]["count"]) if result else 0
        except Exception:
            counts[table] = None
    for table in ("selfx_goals", "selfx_lessons", "selfx_reflections"):
        try:
            result = rows(f"SELECT COUNT(*) AS count FROM {table}")
            counts[table] = int(result[0]["count"]) if result else 0
        except Exception:
            counts[table] = 0
    recommendations = []
    if not config.DB_PATH.exists():
        recommendations.append({"kind": "storage", "priority": "high", "action": "Initialize the local database and check its configured path."})
    if counts.get("learning_events") == 0:
        recommendations.append({"kind": "learning", "priority": "low", "action": "Record explicit feedback on answers to build a useful evaluation history."})
    if counts.get("selfx_goals") == 0:
        recommendations.append({"kind": "planning", "priority": "low", "action": "Create a goal to begin tracking objectives and progress."})
    return {
        "mode": "read_only",
        "autonomous_execution": False,
        "model_weight_updates": False,
        "permission_changes": "approval_required",
        "database_exists": config.DB_PATH.exists(),
        "counts": counts,
        "recommendations": recommendations,
    }
