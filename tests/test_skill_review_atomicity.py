import pytest

from nano import config, db
from nano import skills


@pytest.fixture
def skills_db(tmp_path, monkeypatch):
    path = tmp_path / "skills-review.sqlite3"
    monkeypatch.setattr(db, "DB_PATH", path)
    monkeypatch.setattr(config, "DB_PATH", path)
    db.init_db()
    skills.seed()
    return path


def test_accepting_proposal_is_idempotent_and_activates_once(skills_db):
    proposal_id = skills.propose(
        "safe-review",
        "Suggest test review steps.",
        "Suggest regression tests and explain their purpose.",
    )

    assert skills.accept(proposal_id) is True
    assert skills.accept(proposal_id) is False

    proposal = db.rows("SELECT status FROM skill_proposals WHERE id=?", (proposal_id,))[0]
    skill = db.rows("SELECT version,enabled,prompt FROM skills WHERE name='safe-review'")[0]
    assert proposal["status"] == "accepted"
    assert skill["version"] == 1
    assert skill["enabled"] == 1
    assert skill["prompt"] == "Suggest regression tests and explain their purpose."


def test_rejected_proposal_cannot_later_be_accepted(skills_db):
    proposal_id = skills.propose(
        "rejected-review",
        "A proposal for testing.",
        "Recommend tests; do not run commands.",
    )

    assert skills.reject(proposal_id) is True
    assert skills.reject(proposal_id) is False
    assert skills.accept(proposal_id) is False
    assert db.rows("SELECT id FROM skills WHERE name='rejected-review'") == []
    assert db.rows("SELECT status FROM skill_proposals WHERE id=?", (proposal_id,))[0]["status"] == "rejected"


def test_accepting_unknown_proposal_is_a_noop(skills_db):
    assert skills.accept(999999) is False
    assert skills.reject(999999) is False
