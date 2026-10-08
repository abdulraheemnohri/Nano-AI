from nano.db import init_db
from nano.learning import learn_from_text,memories
from nano.skills import seed,list_skills

def test_learning_and_skills(tmp_path,monkeypatch):
    import nano.config as cfg
    db=tmp_path/'t.sqlite3'; monkeypatch.setattr(cfg,'DB_PATH',db)
    import nano.db as dbm; monkeypatch.setattr(dbm,'DB_PATH',db)
    init_db(); seed(); found=learn_from_text('Remember that I prefer Urdu.')
    assert found and memories(10)
    assert any(x['name']=='urdu' for x in list_skills())
