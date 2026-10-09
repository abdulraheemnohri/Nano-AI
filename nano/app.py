from pathlib import Path
from tempfile import NamedTemporaryFile
from fastapi import FastAPI,HTTPException,UploadFile,File
from fastapi.responses import HTMLResponse,FileResponse,JSONResponse
from starlette.background import BackgroundTask
from pydantic import BaseModel, Field
from . import config
from .db import init_db,rows,run
from .core import respond
from .memory import search,forget,clear
from .learning import events
from .knowledge import ingest,recent
from .skills import seed,list_all,set_enabled,proposals,accept,reject
from .settings import public,set_value,reset
from .runtime import status,installed_models,registry_models
from .model_manager import info,import_model,start_auto_setup,auto_setup_status
from .research import search_web,research_and_learn
from .web import HTML
from .voice import transcribe_wav,speak,voice_status
from .tools import list_tools, run_tool, set_enabled as set_tool_enabled

app=FastAPI(title="Nano AI",version="0.5.0")
@app.on_event("startup")
def startup(): init_db(); seed()

class ChatIn(BaseModel): conversation_id:int=1; message:str
class SettingIn(BaseModel): key:str; value:str
class KnowledgeIn(BaseModel): text:str; source:str="local"
class ConversationIn(BaseModel): title:str="New conversation"
class SkillProposalIn(BaseModel): name:str; description:str; prompt:str
class ModelImportIn(BaseModel): repo:str; filename:str; model_id:str|None=None
class ToolRunIn(BaseModel): name:str; arguments:dict

@app.get("/",response_class=HTMLResponse)
def home(): return HTML

@app.get("/api/health")
def health():
    s=status()
    return {"ok":True,"model_reachable":s["reachable"],"runtime":s,"voice":voice_status()}

@app.get("/api/ready")
def ready():
    s=status()
    ready_ok=bool(s["reachable"])
    payload={"ready":ready_ok,"model_reachable":s["reachable"],"runtime":s}
    if not ready_ok:
        return JSONResponse(payload,status_code=503)
    return payload

@app.post("/api/chat")
def chat_api(x:ChatIn):
    if not x.message.strip() or len(x.message)>config.MAX_MESSAGE_CHARS: raise HTTPException(400,"Invalid message")
    try: return {"answer":respond(x.conversation_id,x.message)}
    except ValueError as e: raise HTTPException(404,str(e))
    except Exception as e: raise HTTPException(503,str(e))

@app.get("/api/tools")
def tools_list(): return list_tools()

@app.post("/api/tools/run")
def tools_run(x:ToolRunIn):
    try: return run_tool(x.name, x.arguments)
    except ValueError as e: raise HTTPException(400, str(e))
    except PermissionError as e: raise HTTPException(403, str(e))

@app.post("/api/tools/{name}/enabled")
def tools_enabled(name:str, enabled:bool=True):
    try: return set_tool_enabled(name, enabled)
    except ValueError as e: raise HTTPException(404, str(e))

@app.get("/api/memories")
def memories(q:str=""): return search(q,50)
@app.delete("/api/memories/{mid}")
def delete_memory(mid:int): forget(mid); return {"ok":True}
@app.delete("/api/memories")
def delete_memories(): clear(); return {"ok":True}
@app.get("/api/learning/events")
def learning_events(): return events(100)

@app.get("/api/skills")
def skills(): return list_all()
@app.get("/api/skills/proposals")
def skill_proposals(): return proposals()
@app.post("/api/skills/proposals")
def skill_proposal(x:SkillProposalIn):
    if not all([x.name.strip(),x.description.strip(),x.prompt.strip()]): raise HTTPException(400,"All proposal fields are required")
    return {"id":__import__("nano.skills",fromlist=["propose"]).propose(x.name.strip(),x.description.strip(),x.prompt.strip())}
@app.post("/api/skills/proposals/{pid}/accept")
def skill_accept(pid:int): return {"ok":accept(pid)}
@app.post("/api/skills/proposals/{pid}/reject")
def skill_reject(pid:int): reject(pid); return {"ok":True}
@app.post("/api/skills/{name}/enabled")
def skill_enabled(name:str,enabled:bool=True):
    try: set_enabled(name,enabled)
    except ValueError as e: raise HTTPException(404,str(e))
    return {"ok":True}

@app.get("/api/knowledge")
def knowledge(): return recent(100)

class WebSearchIn(BaseModel):
    query: str = Field(min_length=1, max_length=300)
    limit: int = Field(default=8, ge=1, le=10)
class WebLearnIn(BaseModel):
    url: str = Field(min_length=1, max_length=2048)
    label: str | None = Field(default=None, max_length=100)

@app.post("/api/research/search")
def research_search(x:WebSearchIn):
    try: return search_web(x.query,x.limit)
    except ValueError as e: raise HTTPException(400,str(e))
    except RuntimeError as e: raise HTTPException(502,str(e))

@app.post("/api/research/learn")
def research_learn(x:WebLearnIn):
    try: return research_and_learn(x.url,x.label)
    except ValueError as e: raise HTTPException(400,str(e))
    except RuntimeError as e: raise HTTPException(502,str(e))

@app.delete("/api/knowledge")
def knowledge_clear():
    run("UPDATE memories SET status='deleted',updated_at=CURRENT_TIMESTAMP WHERE kind='knowledge' AND status='active'")
    return {"ok":True}
@app.post("/api/knowledge")
def knowledge_add(x:KnowledgeIn):
    if not x.text.strip() or len(x.text)>500000: raise HTTPException(400,"Invalid text")
    return {"chunks":ingest(x.text,x.source)}

@app.get("/api/settings")
def settings(): return public()
@app.post("/api/settings")
def setting(x:SettingIn):
    try: set_value(x.key,x.value)
    except ValueError as e: raise HTTPException(400,str(e))
    return public()
@app.post("/api/settings/reset")
def settings_reset(): return reset()

@app.get("/api/export")
def export_data():
    return JSONResponse({
        "version":"0.5.0",
        "conversations": rows("SELECT * FROM conversations ORDER BY id"),
        "messages": rows("SELECT * FROM messages ORDER BY id"),
        "memories": rows("SELECT * FROM memories ORDER BY id"),
        "learning_events": rows("SELECT * FROM learning_events ORDER BY id"),
        "skills": rows("SELECT * FROM skills ORDER BY id"),
        "skill_proposals": rows("SELECT * FROM skill_proposals ORDER BY id"),
        "settings": public(),
    })

@app.get("/api/model")
def model(): return info()
@app.get("/api/models")
def models(): return installed_models()
@app.get("/api/models/registry")
def model_registry(): return registry_models()

@app.post("/api/models/auto-setup")
def model_auto_setup():
    state=start_auto_setup()
    if state["status"] == "error": raise HTTPException(503,state["message"])
    return state

@app.get("/api/models/auto-setup")
def model_auto_setup_status(): return auto_setup_status()
@app.post("/api/models/import")
def model_import(x:ModelImportIn):
    try:
        return {"model_id": import_model(x.repo, x.filename, x.model_id)}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(503, str(e))

@app.get("/api/system")
def system(): return {"version":"0.5.0","host":config.HOST,"port":config.PORT,"runtime":status(),"voice":voice_status(),"paths":{"data":str(config.DATA_DIR),"models":str(config.MODEL_DIR),"skills":str(config.SKILLS_DIR),"database":str(config.DB_PATH)}}

@app.get("/api/conversations")
def conversations(): return rows("SELECT * FROM conversations ORDER BY updated_at DESC,id DESC")
@app.post("/api/conversations")
def conversation_create(x:ConversationIn):
    title=x.title.strip()[:120] or "New conversation"; cid=run("INSERT INTO conversations(title) VALUES(?)",(title,))
    return {"id":cid,"title":title}
@app.patch("/api/conversations/{cid}")
def conversation_rename(cid:int,x:ConversationIn):
    title=x.title.strip()[:120]
    if not title: raise HTTPException(400,"Title cannot be empty")
    if not rows("SELECT id FROM conversations WHERE id=?",(cid,)): raise HTTPException(404,"Conversation not found")
    run("UPDATE conversations SET title=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",(title,cid)); return {"ok":True,"title":title}
@app.delete("/api/conversations/{cid}")
def conversation_delete(cid:int):
    if not rows("SELECT id FROM conversations WHERE id=?",(cid,)): raise HTTPException(404,"Conversation not found")
    run("DELETE FROM messages WHERE conversation_id=?",(cid,)); run("DELETE FROM conversations WHERE id=?",(cid,))
    if not rows("SELECT id FROM conversations LIMIT 1"): run("INSERT INTO conversations(title) VALUES('Nano AI')")
    return {"ok":True}
@app.get("/api/conversations/{cid}/messages")
def messages(cid:int):
    if not rows("SELECT id FROM conversations WHERE id=?",(cid,)): raise HTTPException(404,"Conversation not found")
    return rows("SELECT * FROM messages WHERE conversation_id=? ORDER BY id",(cid,))

@app.get("/api/voice/status")
def voice_api_status(): return voice_status()
@app.post("/api/voice/stt")
async def voice_stt(file:UploadFile=File(...)):
    if file.content_type not in {"audio/wav","audio/x-wav","audio/wave","application/octet-stream"}: raise HTTPException(415,"Upload a mono 16-bit WAV file.")
    with NamedTemporaryFile(prefix="nano-stt-",suffix=".wav",delete=False) as tmp:
        temp=Path(tmp.name); data=await file.read()
        if len(data)>20*1024*1024: temp.unlink(missing_ok=True); raise HTTPException(413,"Audio file too large.")
        temp.write_bytes(data)
    try: return {"text":transcribe_wav(temp)}
    except (ValueError,RuntimeError) as e: raise HTTPException(422,str(e))
    finally: temp.unlink(missing_ok=True)
@app.get("/api/voice/tts")
def voice_tts(text:str):
    if not text.strip() or len(text)>config.MAX_MESSAGE_CHARS: raise HTTPException(400,"Invalid TTS text.")
    with NamedTemporaryFile(prefix="nano-tts-",suffix=".wav",delete=False) as tmp: output=Path(tmp.name)
    try:
        speak(text,output)
        return FileResponse(output,media_type="audio/wav",filename="nano-response.wav",background=BackgroundTask(output.unlink,missing_ok=True))
    except (ValueError,RuntimeError) as e:
        output.unlink(missing_ok=True); raise HTTPException(503,str(e))
