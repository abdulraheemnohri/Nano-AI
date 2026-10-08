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

def test_conversation_api(tmp_path,monkeypatch):
    import nano.config as cfg
    db=tmp_path/'api.sqlite3'; monkeypatch.setattr(cfg,'DB_PATH',db)
    import nano.db as dbm; monkeypatch.setattr(dbm,'DB_PATH',db)
    from fastapi.testclient import TestClient
    from nano.app import app
    with TestClient(app) as client:
        r=client.get('/api/conversations'); assert r.status_code==200 and r.json()
        r=client.post('/api/conversations',json={'title':'Test chat'}); assert r.status_code==200
        cid=r.json()['id']
        assert client.get(f'/api/conversations/{cid}/messages').status_code==200
        assert client.patch(f'/api/conversations/{cid}',json={'title':'Renamed'}).json()['ok']
        assert client.delete(f'/api/conversations/{cid}').json()['ok']

def test_voice_status_api(tmp_path,monkeypatch):
    import nano.config as cfg
    db=tmp_path/'voice.sqlite3'; monkeypatch.setattr(cfg,'DB_PATH',db)
    import nano.db as dbm; monkeypatch.setattr(dbm,'DB_PATH',db)
    from fastapi.testclient import TestClient
    from nano.app import app
    with TestClient(app) as client:
        r=client.get('/api/voice/status')
        assert r.status_code==200
        assert r.json()['stt']['offline'] is True
        assert r.json()['tts']['offline'] is True


def test_settings_validation_and_runtime_values(tmp_path,monkeypatch):
    import nano.config as cfg
    db=tmp_path/'settings.sqlite3'; monkeypatch.setattr(cfg,'DB_PATH',db)
    import nano.db as dbm; monkeypatch.setattr(dbm,'DB_PATH',db)
    from nano.settings import set_value, public
    init_db()
    set_value('temperature','0.4')
    set_value('max_tokens','512')
    assert public()['temperature']=='0.4'
    assert public()['max_tokens']=='512'

def test_skill_proposal_lifecycle(tmp_path,monkeypatch):
    import nano.config as cfg
    db=tmp_path/'skills.sqlite3'; monkeypatch.setattr(cfg,'DB_PATH',db)
    import nano.db as dbm; monkeypatch.setattr(dbm,'DB_PATH',db)
    from nano.skills import seed, propose, proposals, accept, list_all
    init_db(); seed()
    pid=propose('test-skill','Test skill','Be concise.')
    assert proposals()
    assert accept(pid)
    assert any(x['name']=='test-skill' for x in list_all())
