from fastapi.testclient import TestClient

from nano import app as app_module, config, core, db


def _setup(tmp_path, monkeypatch):
    path = tmp_path / "conv.sqlite3"
    monkeypatch.setattr(config, "DB_PATH", path)
    monkeypatch.setattr(db, "DB_PATH", path)
    db.init_db()
    # init_db seeds a default conversation; isolate API pagination tests from it.
    db.run("DELETE FROM messages")
    db.run("DELETE FROM conversations")
    calls = {"n": 0}
    def fake_chat(history, user_text=None, context=""):
        calls["n"] += 1
        return "reply-%d" % calls["n"]
    monkeypatch.setattr(core, "chat", fake_chat)
    client = TestClient(app_module.app)
    return client


def test_regenerate_replaces_last_assistant_answer(tmp_path, monkeypatch):
    client = _setup(tmp_path, monkeypatch)
    cid = client.post("/api/conversations", json={"title": "Regen"}).json()["id"]
    client.post("/api/chat", json={"conversation_id": cid, "message": "first question"})
    client.post("/api/chat", json={"conversation_id": cid, "message": "second question"})

    response = client.post("/api/chat/regenerate", json={"conversation_id": cid})
    assert response.status_code == 200
    assert response.json()["answer"].startswith("reply-")

    messages = client.get(f"/api/conversations/{cid}/messages").json()
    assert len(messages) == 4
    assert messages[-1]["role"] == "assistant"
    assert messages[-1]["content"].startswith("reply-3")
    assert messages[-2]["content"] == "second question"


def test_regenerate_requires_a_user_message(tmp_path, monkeypatch):
    client = _setup(tmp_path, monkeypatch)
    cid = client.post("/api/conversations", json={"title": "Empty"}).json()["id"]
    response = client.post("/api/chat/regenerate", json={"conversation_id": cid})
    assert response.status_code == 404


def test_regenerate_unknown_conversation(tmp_path, monkeypatch):
    client = _setup(tmp_path, monkeypatch)
    response = client.post("/api/chat/regenerate", json={"conversation_id": 9999})
    assert response.status_code == 404


def test_conversation_search_finds_matching_messages(tmp_path, monkeypatch):
    client = _setup(tmp_path, monkeypatch)
    cid = client.post("/api/conversations", json={"title": "Search target"}).json()["id"]
    client.post("/api/chat", json={"conversation_id": cid, "message": "the needle is here"})
    client.post("/api/chat", json={"conversation_id": cid, "message": "unrelated message"})

    results = client.get("/api/conversations/search", params={"q": "needle"}).json()
    assert len(results) == 1
    assert results[0]["conversation_id"] == cid
    assert "needle" in results[0]["content"]

    empty = client.get("/api/conversations/search", params={"q": ""}).json()
    assert empty == []


def test_conversation_export_returns_full_history(tmp_path, monkeypatch):
    client = _setup(tmp_path, monkeypatch)
    cid = client.post("/api/conversations", json={"title": "Export me"}).json()["id"]
    client.post("/api/chat", json={"conversation_id": cid, "message": "hello"})

    exported = client.get(f"/api/conversations/{cid}/export")
    assert exported.status_code == 200
    body = exported.json()
    assert body["conversation"]["title"] == "Export me"
    assert [m["role"] for m in body["messages"]] == ["user", "assistant"]

    missing = client.get("/api/conversations/9999/export")
    assert missing.status_code == 404


def test_conversation_list_is_bounded(tmp_path, monkeypatch):
    client = _setup(tmp_path, monkeypatch)
    for i in range(5):
        client.post("/api/conversations", json={"title": "conv-%d" % i})

    limited = client.get("/api/conversations", params={"limit": 3}).json()
    assert len(limited) == 3

    oversized = client.get("/api/conversations", params={"limit": 99999}).json()
    assert len(oversized) == 5


def test_conversation_list_supports_offset_paging(tmp_path, monkeypatch):
    client = _setup(tmp_path, monkeypatch)
    for i in range(5):
        client.post("/api/conversations", json={"title": "page-%d" % i})

    page1 = client.get("/api/conversations", params={"limit": 3}).json()
    page2 = client.get("/api/conversations", params={"limit": 3, "offset": 3}).json()
    assert len(page1) == 3
    assert len(page2) == 2
    ids1 = {c["id"] for c in page1}
    ids2 = {c["id"] for c in page2}
    assert not (ids1 & ids2)
    negative = client.get("/api/conversations", params={"offset": -5}).json()
    assert len(negative) == 5


def test_conversation_messages_paginated_newest_window(tmp_path, monkeypatch):
    client = _setup(tmp_path, monkeypatch)
    cid = client.post("/api/conversations", json={"title": "Long"}).json()["id"]
    for i in range(7):
        db.run(
            "INSERT INTO messages(conversation_id,role,content) VALUES(?,?,?)",
            (cid, "user", "m-%d" % i),
        )

    latest = client.get("/api/conversations/%d/messages" % cid, params={"limit": 3}).json()
    assert [m["content"] for m in latest] == ["m-4", "m-5", "m-6"]

    earlier = client.get("/api/conversations/%d/messages" % cid, params={"limit": 3, "offset": 3}).json()
    assert [m["content"] for m in earlier] == ["m-1", "m-2", "m-3"]

    oldest = client.get("/api/conversations/%d/messages" % cid, params={"limit": 3, "offset": 6}).json()
    assert [m["content"] for m in oldest] == ["m-0"]

    assert client.get("/api/conversations/9999/messages").status_code == 404
