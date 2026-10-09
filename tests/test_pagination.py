from nano import config, db, knowledge, learning


def _setup(tmp_path, monkeypatch):
    path = tmp_path / "pages.sqlite3"
    monkeypatch.setattr(config, "DB_PATH", path)
    monkeypatch.setattr(db, "DB_PATH", path)
    db.init_db()
    return path


def test_learning_events_support_offset_paging(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    for i in range(5):
        db.run(
            "INSERT INTO learning_events(event_type,input_text,result) VALUES(?,?,?)",
            ("conversation", "event-%d" % i, ""),
        )
    page1 = learning.events(3, 0)
    page2 = learning.events(3, 3)
    assert len(page1) == 3
    assert len(page2) == 2
    assert {e["id"] for e in page1}.isdisjoint({e["id"] for e in page2})
    negative = learning.events(100, -5)
    assert len(negative) == 5


def test_knowledge_recent_support_offset_paging(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    for i in range(5):
        db.run(
            "INSERT INTO memories(kind,content,confidence,status,source) VALUES(?,?,?,?,?)",
            ("knowledge", "knowledge chunk number %d" % i, 0.65, "active", "test"),
        )
    page1 = knowledge.recent(3, 0)
    page2 = knowledge.recent(3, 3)
    assert len(page1) == 3
    assert len(page2) == 2
    assert {e["id"] for e in page1}.isdisjoint({e["id"] for e in page2})
