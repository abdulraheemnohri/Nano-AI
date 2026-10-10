def test_conversation_delete_removes_feedback_and_feedback_learning_event(tmp_path, monkeypatch):
    import nano.config as config
    import nano.db as db
    from nano import app as app_module
    path = tmp_path / "delete-feedback.sqlite3"
    monkeypatch.setattr(config, "DB_PATH", path)
    monkeypatch.setattr(db, "DB_PATH", path)
    db.init_db()
    cid = db.run("INSERT INTO conversations(title) VALUES(?)", ("Delete me",))
    fid = db.run("INSERT INTO response_feedback(conversation_id,user_text,assistant_text,rating,correction) VALUES(?,?,?,?,?)",
                 (cid, "my private prompt", "private answer", -1, "private correction"))
    db.run("INSERT INTO learning_events(event_type,input_text,result) VALUES(?,?,?)",
           ("response_feedback", "my private prompt", str({"feedback_id": fid, "rating": -1, "correction": "private correction"})))
    app_module.conversation_delete(cid)
    assert db.rows("SELECT id FROM response_feedback WHERE conversation_id=?", (cid,)) == []
    assert db.rows("SELECT id FROM learning_events WHERE event_type='response_feedback' AND result LIKE ?", (f"%feedback_id': {fid}%",)) == []
    assert db.rows("SELECT id FROM conversations WHERE id=?", (cid,)) == []
