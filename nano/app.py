from fastapi import FastAPI,HTTPException
from pydantic import BaseModel
from fastapi.responses import HTMLResponse
from . import config
from .db import init_db,rows
from .core import respond
from .memory import search,forget,clear
from .learning import events
from .knowledge import ingest,recent
from .skills import seed,list_all,set_enabled
from .settings import public,set_value
from .runtime import status,installed_models
from .model_manager import info
from .web import HTML

app=FastAPI(title="Nano AI",version="0.2.0")
@app.on_event("startup")
def startup(): init_db(); seed()
class ChatIn(BaseModel): conversation_id:int=1; message:str
class SettingIn(BaseModel): key:str; value:str
class KnowledgeIn(BaseModel): text:str; source:str="local"

@app.get("/",response_class=HTMLResponse)
def home(): return HTML
@app.get("/api/health")
def health():
 s=status(); return {"ok":True,"model_reachable":s["reachable"],"runtime":s}
@app.post("/api/chat")
def chat_api(x:ChatIn):
 if not x.message.strip() or len(x.message)>12000: raise HTTPException(400,"Invalid message")
 try:return {"answer":respond(x.conversation_id,x.message)}
 except Exception as e:raise HTTPException(503,str(e))
@app.get("/api/memories")
def memories(q:str=""):return search(q,50)
@app.delete("/api/memories/{mid}")
def delete_memory(mid:int):forget(mid);return {"ok":True}
@app.delete("/api/memories")
def delete_memories():clear();return {"ok":True}
@app.get("/api/learning/events")
def learning_events():return events(100)
@app.get("/api/skills")
def skills():return list_all()
@app.post("/api/skills/{name}/enabled")
def skill_enabled(name:str,enabled:bool=True):set_enabled(name,enabled);return {"ok":True}
@app.get("/api/knowledge")
def knowledge():return recent(100)
@app.post("/api/knowledge")
def knowledge_add(x:KnowledgeIn):
 if not x.text.strip() or len(x.text)>500000:raise HTTPException(400,"Invalid text")
 return {"chunks":ingest(x.text,x.source)}
@app.get("/api/settings")
def settings():return public()
@app.post("/api/settings")
def setting(x:SettingIn):
 try:set_value(x.key,x.value)
 except ValueError as e:raise HTTPException(400,str(e))
 return public()
@app.get("/api/model")
def model():return info()
@app.get("/api/models")
def models():return installed_models()
@app.get("/api/system")
def system():return {"version":"0.2.0","host":config.HOST,"port":config.PORT,"runtime":status()}
@app.get("/api/conversations")
def conversations():return rows("SELECT * FROM conversations ORDER BY updated_at DESC")
@app.get("/api/conversations/{cid}/messages")
def messages(cid:int):return rows("SELECT * FROM messages WHERE conversation_id=? ORDER BY id",(cid,))
