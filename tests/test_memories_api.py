from fastapi.testclient import TestClient

from nano import app as app_module, config, db


def _setup(tmp_path, monkeypatch):
    path = tmp_path / "mem.sqlite3"
    monkeypatch.setattr(config, "DB_PATH", path)
    monkeypatch.setattr(db, "DB_PATH", path)
    db.init_db()
    # Keep pagination tests independent of any seeded memory rows.
    db.run("UPDATE memories SET status='deleted'")
    return TestClient(app_module.app)


def _add(content, confidence):
    return db.run(
        "INSERT INTO memories(kind,content,confidence,source) VALUES('fact',?,?,'test')",
        (content, confidence),
    )


def test_memories_list_is_paginated(tmp_path, monkeypatch):
    client = _setup(tmp_path, monkeypatch)
    for i in range(7):
        _add("alpha memory %d" % i, 0.1 * (i + 1))

    page1 = client.get("/api/memories", params={"limit": 3}).json()
    page2 = client.get("/api/memories", params={"limit": 3, "offset": 3}).json()
    page3 = client.get("/api/memories", params={"limit": 3, "offset": 6}).json()
    assert len(page1) == 3 and len(page2) == 3 and len(page3) == 1
    ids = [m["id"] for m in page1 + page2 + page3]
    assert len(set(ids)) == 7
    # Highest confidence first.
    assert page1[0]["content"] == "alpha memory 7"
    assert page3[0]["content"] == "alpha memory 1"

    negative = client.get("/api/memories", params={"offset": -5}).json()
    assert len(negative) == 7

    beyond = client.get("/api/memories", params={"limit": 3, "offset": 60}).json()
    assert beyond == []


def test_memories_search_supports_offset_paging(tmp_path, monkeypatch):
    client = _setup(tmp_path, monkeypatch)
    for i in range(5):
        _add("needle item %d" % i, 0.1 * (i + 1))
    _add("unrelated", 0.99)

    page1 = client.get("/api/memories", params={"q": "needle", "limit": 3}).json()
    page2 = client.get("/api/memories", params={"q": "needle", "limit": 3, "offset": 3}).json()
    assert len(page1) == 3 and len(page2) == 2
    assert all("needle" in m["content"] for m in page1 + page2)
    assert not ({m["id"] for m in page1} & {m["id"] for m in page2})
