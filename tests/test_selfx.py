import pytest

from nano import config, db
from nano.selfx import (
    create_goal,
    init_selfx_db,
    list_goals,
    list_lessons,
    record_lesson,
    run_self_check,
    update_goal,
)


@pytest.fixture
def selfx_db(tmp_path, monkeypatch):
    path = tmp_path / "nano-test.sqlite3"
    monkeypatch.setattr(db, "DB_PATH", path)
    monkeypatch.setattr(config, "DB_PATH", path)
    db.init_db()
    init_selfx_db()
    return path


def test_goal_create_list_and_update(selfx_db):
    goal = create_goal("Improve answer quality", "Use feedback and verify results", 1)

    assert goal["title"] == "Improve answer quality"
    assert goal["priority"] == 1
    assert goal["status"] == "planned"

    updated = update_goal(goal["id"], status="active", priority=2)
    assert updated["status"] == "active"
    assert updated["priority"] == 2
    assert list_goals(status="active")[0]["id"] == goal["id"]


def test_goal_rejects_invalid_priority_and_status(selfx_db):
    with pytest.raises(ValueError):
        create_goal("Bad priority", priority=0)
    goal = create_goal("Safe goal")
    with pytest.raises(ValueError):
        update_goal(goal["id"], status="self_authorized")


def test_lessons_keep_provenance_and_validate_confidence(selfx_db):
    lesson = record_lesson(
        "testing",
        "Verify behavior with a regression test.",
        source="pytest run",
        outcome="passed",
        confidence=0.9,
        evidence=[{"source": "tests/test_selfx.py", "note": "Regression test"}],
    )

    assert lesson["confidence"] == 0.9
    assert lesson["evidence"][0]["source"] == "tests/test_selfx.py"
    assert list_lessons(topic="testing")[0]["lesson"] == lesson["lesson"]

    with pytest.raises(ValueError):
        record_lesson("testing", "Invalid confidence", confidence=1.5)


def test_self_check_is_read_only_and_reports_recommendations(selfx_db):
    result = run_self_check()

    assert result["mode"] == "read_only"
    assert result["autonomous_execution"] is False
    assert result["model_weight_updates"] is False
    assert "selfx_goals" in result["counts"]
    assert any(item["kind"] == "planning" for item in result["recommendations"])
