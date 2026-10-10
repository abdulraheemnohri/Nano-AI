import pytest

from nano import config, db
from nano.selfx import create_goal, init_selfx_db
from nano.selfx_engine import (
    create_plan, get_plan, init_selfx_engine_db, list_research,
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
