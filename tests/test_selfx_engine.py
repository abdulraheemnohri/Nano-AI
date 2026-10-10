import pytest

from nano import config, db
from nano.selfx import create_goal, init_selfx_db
from nano.selfx_engine import (
    advance_plan, create_plan, get_plan, init_selfx_engine_db, list_research,
    record_research, run_review_cycle, update_plan_status, update_task,
)


@pytest.fixture
def engine_db(tmp_path, monkeypatch):
    path = tmp_path / "selfx-engine.sqlite3"
    monkeypatch.setattr(db, "DB_PATH", path)
    monkeypatch.setattr(config, "DB_PATH", path)
    db.init_db()
    init_selfx_db()
    init_selfx_engine_db()
    return path


def test_plan_tracks_task_progress_and_completes_goal(engine_db):
    goal = create_goal("Ship a tested feature")
    plan = create_plan(goal["id"], "Implementation plan", "Verify every change", [
        {"title": "Inspect existing behavior"},
        {"title": "Implement and test", "description": "Add regression coverage"},
    ])
    assert plan["status"] == "draft"
    assert plan["progress_percent"] == 0
    update_plan_status(plan["id"], "active")
    plan = get_plan(plan["id"])
    update_task(plan["tasks"][0]["id"], "completed", "Existing behavior documented")
    plan = get_plan(plan["id"])
    assert plan["progress_percent"] == 50
    plan = update_task(plan["tasks"][1]["id"], "completed", "Tests passed")
    assert plan["status"] == "completed"
    assert plan["progress_percent"] == 100
    assert db.rows("SELECT status FROM selfx_goals WHERE id=?", (goal["id"],))[0]["status"] == "completed"


def test_plan_validation_and_terminal_task_guard(engine_db):
    goal = create_goal("Safe plan")
    with pytest.raises(ValueError):
        create_plan(goal["id"], "Empty", steps=[])
    plan = create_plan(goal["id"], "One step", steps=["Review"])
    task_id = plan["tasks"][0]["id"]
    update_task(task_id, "completed", "done")
    with pytest.raises(ValueError):
        update_task(task_id, "pending", "reopen terminal task")


def test_research_preserves_source_and_unverified_credibility(engine_db):
    record = record_research(
        "How does feature X work?", "https://example.org/docs", "A source summary",
        source_title="Documentation", credibility="unassessed", confidence=0.4,
        evidence=["Source has not been independently cross-checked"],
    )
    assert record["credibility"] == "unassessed"
    assert record["evidence"] == ["Source has not been independently cross-checked"]
    assert list_research(question="feature X")[0]["source_url"] == "https://example.org/docs"
    with pytest.raises(ValueError):
        record_research("bad", "file:///etc/passwd", "invalid scheme")


def test_review_cycle_records_reflection_and_does_not_execute(engine_db):
    goal = create_goal("Track task failure")
    plan = create_plan(goal["id"], "Failure plan", steps=["Reproduce"])
    update_task(plan["tasks"][0]["id"], "failed", "Repro failed")
    result = run_review_cycle()
    assert result["auto_execution"] is False
    assert result["reflection"]["task_outcomes"]["failed"] == 1
    assert result["improvement_proposal"]["status"] == "pending"
    assert db.rows("SELECT COUNT(*) AS n FROM selfx_reflections")[0]["n"] == 1



def test_advance_plan_activates_only_next_task_without_execution(engine_db):
    goal = create_goal("Advance safely")
    plan = create_plan(goal["id"], "Sequential plan", steps=["Inspect", "Implement", "Verify"])
    update_plan_status(plan["id"], "active")

    first = advance_plan(plan["id"])
    assert first["advanced"] is True
    assert first["execution_started"] is False
    assert first["next_task"]["title"] == "Inspect"
    assert first["next_task"]["status"] == "active"

    # Repeated advance is idempotent while the caller has not reported an outcome.
    repeated = advance_plan(plan["id"])
    assert repeated["advanced"] is False
    assert repeated["next_task"]["id"] == first["next_task"]["id"]

    update_task(first["next_task"]["id"], "completed", "Inspection done")
    second = advance_plan(plan["id"])
    assert second["advanced"] is True
    assert second["next_task"]["title"] == "Implement"


def test_advance_plan_requires_active_plan_and_stops_on_failed_task(engine_db):
    goal = create_goal("Do not skip failure")
    plan = create_plan(goal["id"], "Guarded plan", steps=["First", "Second"])
    with pytest.raises(ValueError, match="must be active"):
        advance_plan(plan["id"])

    update_plan_status(plan["id"], "active")
    update_task(plan["tasks"][0]["id"], "failed", "Needs investigation")
    with pytest.raises(ValueError, match="failed, blocked, or cancelled"):
        advance_plan(plan["id"])

def test_replan_creates_draft_for_only_failed_and_blocked_tasks(engine_db):
    goal = create_goal("Finish a safe task")
    original = create_plan(goal["id"], "Original plan", steps=["Investigate", "Implement", "Verify"])
    update_task(original["tasks"][0]["id"], "failed", "Missing prerequisite")
    update_task(original["tasks"][1]["id"], "blocked", "Waiting for approved access")
    result = __import__("nano.selfx_engine", fromlist=["replan_failed_tasks"]).replan_failed_tasks(original["id"])
    assert result["execution_started"] is False
    assert result["replanned_task_count"] == 2
    assert result["new_plan"]["status"] == "draft"
    assert len(result["new_plan"]["tasks"]) == 2
    assert all(task["status"] == "pending" for task in result["new_plan"]["tasks"])


def test_research_comparison_reports_source_diversity_without_claiming_truth(engine_db):
    from nano.selfx_engine import compare_research

    record_research("Compare local model runtimes", "https://example.org/guide", "Runtime A supports CPU inference and local execution.")
    record_research("Compare local model runtimes", "https://docs.python.org/guide", "Runtime B uses a different execution and packaging model.", credibility="high", confidence=0.8)
    report = compare_research("Compare local model runtimes")
    assert report["record_count"] == 2
    assert report["distinct_source_count"] == 2
    assert report["needs_independent_review"] is True
    assert "cannot establish truth" in report["interpretation"]


def test_task_outcome_can_create_evidence_linked_lesson(engine_db):
    from nano.selfx_engine import learn_from_task

    goal = create_goal("Learn from task evidence")
    plan = create_plan(goal["id"], "Evidence plan", steps=["Run verification"])
    task_id = plan["tasks"][0]["id"]
    with pytest.raises(ValueError):
        learn_from_task(task_id, "verification", "Pending tasks are not outcomes.")
    update_task(task_id, "completed", "The regression suite passed.")
    lesson = learn_from_task(task_id, "verification", "Run the regression suite before accepting this class of change.")
    assert lesson["source"] == f"task:{task_id}"
    assert lesson["outcome"] == "completed"
    assert lesson["evidence"][0]["source"] == "selfx_tasks"
    assert "regression suite passed" in lesson["evidence"][0]["note"]


def test_lesson_can_seed_pending_skill_proposal_without_enabling_it(engine_db):
    from nano.selfx import record_lesson
    from nano.selfx_engine import propose_skill_from_lesson

    lesson = record_lesson("testing", "Always add a regression test for this failure mode.")
    result = propose_skill_from_lesson(
        lesson["id"], "regression-helper", "Suggest focused regression tests.",
        "When a reproducible bug is identified, propose a focused regression test and explain what it protects.",
    )
    assert result["status"] == "pending"
    assert result["source_lesson_id"] == lesson["id"]
    assert result["auto_enabled"] is False
    proposal = db.rows("SELECT status FROM skill_proposals WHERE id=?", (result["proposal_id"],))[0]
    assert proposal["status"] == "pending"
