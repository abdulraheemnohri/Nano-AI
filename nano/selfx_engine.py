"""Goal planning, task tracking and provenance-aware research for Self-X.

Plans are proposals. This module never executes shell commands, generated code,
or recommendations; task completion must be reported by an explicit caller.
"""
import json
from .db import connect, rows, run

PLAN_STATES = {"draft", "active", "blocked", "completed", "cancelled"}
TASK_STATES = {"pending", "active", "blocked", "completed", "failed", "cancelled"}
MAX_STEPS = 30


def init_selfx_engine_db():
    with connect() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS selfx_plans (
          id INTEGER PRIMARY KEY AUTOINCREMENT, goal_id INTEGER NOT NULL,
          title TEXT NOT NULL, rationale TEXT NOT NULL DEFAULT '',
          status TEXT NOT NULL DEFAULT 'draft', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_selfx_plans_goal ON selfx_plans(goal_id,status,id);
        CREATE TABLE IF NOT EXISTS selfx_tasks (
          id INTEGER PRIMARY KEY AUTOINCREMENT, plan_id INTEGER NOT NULL,
          title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
          status TEXT NOT NULL DEFAULT 'pending', position INTEGER NOT NULL,
          result TEXT NOT NULL DEFAULT '', attempts INTEGER NOT NULL DEFAULT 0,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_selfx_tasks_plan ON selfx_tasks(plan_id,position,id);
        CREATE TABLE IF NOT EXISTS selfx_research (
          id INTEGER PRIMARY KEY AUTOINCREMENT, question TEXT NOT NULL,
          source_url TEXT NOT NULL, source_title TEXT NOT NULL DEFAULT '',
          summary TEXT NOT NULL, credibility TEXT NOT NULL DEFAULT 'unassessed',
          confidence REAL NOT NULL DEFAULT 0.5, checked_at TEXT,
          evidence_json TEXT NOT NULL DEFAULT '[]',
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_selfx_research_question ON selfx_research(question,created_at);
        """)


def _text(value, label, limit=4000, required=True):
    if not isinstance(value, str):
        raise ValueError(f"{label} must be text.")
    value = value.strip()
    if required and not value:
        raise ValueError(f"{label} cannot be empty.")
    if len(value) > limit:
        raise ValueError(f"{label} exceeds {limit} characters.")
    return value


def create_plan(goal_id, title, rationale="", steps=None):
    goal = rows("SELECT id,status FROM selfx_goals WHERE id=?", (goal_id,))
    if not goal:
        raise KeyError("Goal not found.")
    if goal[0]["status"] in {"completed", "cancelled"}:
        raise ValueError("Cannot create a plan for a completed or cancelled goal.")
    title = _text(title, "title", 160)
    rationale = _text(rationale, "rationale", 4000, required=False)
    if not isinstance(steps, list) or not 1 <= len(steps) <= MAX_STEPS:
        raise ValueError(f"steps must contain 1-{MAX_STEPS} items.")
    normalized = []
    for item in steps:
        if isinstance(item, str):
            task_title, description = item, ""
        elif isinstance(item, dict):
            task_title, description = item.get("title"), item.get("description", "")
        else:
            raise ValueError("Each step must be text or an object.")
        normalized.append((_text(task_title, "step title", 160), _text(description, "step description", 2000, required=False)))
    with connect() as c:
        cursor = c.execute("INSERT INTO selfx_plans(goal_id,title,rationale) VALUES(?,?,?)", (goal_id,title,rationale))
        plan_id = cursor.lastrowid
        for position, (task_title, description) in enumerate(normalized, 1):
            c.execute("INSERT INTO selfx_tasks(plan_id,title,description,position) VALUES(?,?,?,?)", (plan_id,task_title,description,position))
    return get_plan(plan_id)


def get_plan(plan_id):
    found = rows("SELECT * FROM selfx_plans WHERE id=?", (plan_id,))
    if not found:
        return None
    plan = found[0]
    plan["tasks"] = rows("SELECT * FROM selfx_tasks WHERE plan_id=? ORDER BY position,id", (plan_id,))
    total = len(plan["tasks"])
    plan["progress_percent"] = round(sum(t["status"] == "completed" for t in plan["tasks"]) * 100 / total) if total else 0
    return plan


def list_plans(goal_id=None, status=None, limit=100, offset=0):
    limit = max(1, min(int(limit), 200))
    offset = max(0, int(offset))
    clauses, args = [], []
    if goal_id is not None:
        clauses.append("goal_id=?"); args.append(goal_id)
    if status is not None:
        if status not in PLAN_STATES:
            raise ValueError("Unsupported plan status.")
        clauses.append("status=?"); args.append(status)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    found = rows("SELECT * FROM selfx_plans" + where + " ORDER BY id DESC LIMIT ? OFFSET ?", tuple(args + [limit, offset]))
    result = []
    for item in found:
        result.append(get_plan(item["id"]))
    return result


def update_plan_status(plan_id, status):
    if status not in PLAN_STATES:
        raise ValueError("Unsupported plan status.")
    if not rows("SELECT id FROM selfx_plans WHERE id=?", (plan_id,)):
        raise KeyError("Plan not found.")
    run("UPDATE selfx_plans SET status=?,updated_at=CURRENT_TIMESTAMP WHERE id=?", (status, plan_id))
    if status == "active":
        run("UPDATE selfx_goals SET status='active',updated_at=CURRENT_TIMESTAMP WHERE id=(SELECT goal_id FROM selfx_plans WHERE id=?) AND status='planned'", (plan_id,))
    return get_plan(plan_id)


def update_task(task_id, status, result=""):
    if status not in TASK_STATES:
        raise ValueError("Unsupported task status.")
    result = _text(result, "result", 4000, required=False)
    found = rows("SELECT * FROM selfx_tasks WHERE id=?", (task_id,))
    if not found:
        raise KeyError("Task not found.")
    current = found[0]
    if current["status"] in {"completed", "cancelled"} and status != current["status"]:
        raise ValueError("Completed or cancelled tasks are terminal; create a new plan to retry.")
    attempts = current["attempts"] + (1 if status in {"active", "failed"} and status != current["status"] else 0)
    run("UPDATE selfx_tasks SET status=?,result=?,attempts=?,updated_at=CURRENT_TIMESTAMP WHERE id=?", (status,result,attempts,task_id))
    plan = get_plan(current["plan_id"])
    if plan and all(t["status"] == "completed" for t in plan["tasks"]):
        run("UPDATE selfx_plans SET status='completed',updated_at=CURRENT_TIMESTAMP WHERE id=?", (plan["id"],))
        run("UPDATE selfx_goals SET status='completed',updated_at=CURRENT_TIMESTAMP WHERE id=? AND status IN ('planned','active')", (plan["goal_id"],))
    elif status == "blocked":
        run("UPDATE selfx_plans SET status='blocked',updated_at=CURRENT_TIMESTAMP WHERE id=?", (current["plan_id"],))
    return get_plan(current["plan_id"])


def record_research(question, source_url, summary, source_title="", credibility="unassessed", confidence=0.5, checked_at=None, evidence=None):
    question = _text(question, "question", 1000)
    source_url = _text(source_url, "source_url", 2000)
    if not source_url.startswith(("https://", "http://")):
        raise ValueError("source_url must use HTTP or HTTPS.")
    summary = _text(summary, "summary", 6000)
    source_title = _text(source_title, "source_title", 300, required=False)
    if credibility not in {"unassessed", "low", "medium", "high", "contradicted", "stale"}:
        raise ValueError("Unsupported credibility label.")
    if isinstance(confidence, bool) or not isinstance(confidence, (int,float)) or not 0 <= confidence <= 1:
        raise ValueError("confidence must be between 0 and 1.")
    evidence = [] if evidence is None else evidence
    if not isinstance(evidence, list) or len(evidence) > 20:
        raise ValueError("evidence must contain at most 20 items.")
    evidence = [_text(str(item), "evidence item", 1000) for item in evidence]
    rid = run("INSERT INTO selfx_research(question,source_url,source_title,summary,credibility,confidence,checked_at,evidence_json) VALUES(?,?,?,?,?,?,?,?)",
              (question,source_url,source_title,summary,credibility,float(confidence),checked_at,json.dumps(evidence,ensure_ascii=False)))
    return get_research(rid)


def get_research(research_id):
    found = rows("SELECT * FROM selfx_research WHERE id=?", (research_id,))
    if not found:
        return None
    item = found[0]
    item["evidence"] = json.loads(item.pop("evidence_json"))
    return item


def list_research(question=None, limit=100, offset=0):
    limit = max(1, min(int(limit), 200)); offset = max(0, int(offset))
    if question:
        return [get_research(item["id"]) for item in rows("SELECT id FROM selfx_research WHERE question LIKE ? ORDER BY id DESC LIMIT ? OFFSET ?", ("%"+question[:1000]+"%",limit,offset))]
    return [get_research(item["id"]) for item in rows("SELECT id FROM selfx_research ORDER BY id DESC LIMIT ? OFFSET ?", (limit,offset))]


def run_review_cycle():
    """Summarize persisted execution/feedback signals and create a reviewable proposal."""
    from .learning import feedback_summary, quality_report
    summary = feedback_summary()
    failed = rows("SELECT COUNT(*) AS n FROM selfx_tasks WHERE status='failed'")[0]["n"]
    blocked = rows("SELECT COUNT(*) AS n FROM selfx_tasks WHERE status='blocked'")[0]["n"]
    completed = rows("SELECT COUNT(*) AS n FROM selfx_tasks WHERE status='completed'")[0]["n"]
    reflection = {
        "feedback": summary,
        "task_outcomes": {"completed": completed, "failed": failed, "blocked": blocked},
        "limitations": ["Signals are descriptive and may be sparse or biased.", "No model weights or permissions are changed."],
    }
    from .selfx import reflect, propose_improvement
    reflect("scheduled_self_review", "Review cycle computed from local feedback and task outcomes.", [
        f"Completed tasks: {completed}", f"Failed tasks: {failed}", f"Blocked tasks: {blocked}",
        f"Feedback records: {summary['total']}",
    ])
    proposal = None
    if failed or blocked or summary["unhelpful"]:
        proposal = propose_improvement(
            "Review recurring task failures and negative feedback",
            "Inspect the linked evidence, identify a reproducible cause, and add a regression test before changing behavior. This proposal does not authorize automatic code changes.",
            evidence=[
                {"source":"selfx_tasks", "note":f"failed={failed}, blocked={blocked}, completed={completed}"},
                {"source":"response_feedback", "note":f"helpful={summary['helpful']}, unhelpful={summary['unhelpful']}, corrections={summary['corrections']}"},
            ],
        )
    return {"reflection": reflection, "quality": quality_report(), "improvement_proposal": proposal, "auto_execution": False}
