from pathlib import Path
import sqlite3
from tempfile import NamedTemporaryFile
from datetime import datetime, timezone
from fastapi import FastAPI,HTTPException,UploadFile,File,Request
from fastapi.responses import HTMLResponse,FileResponse,JSONResponse
from starlette.background import BackgroundTask
from pydantic import BaseModel, Field
from . import config
from .db import init_db,rows,run
from .core import respond, generate_proactive_talk, regenerate
from .memory import search,forget,clear,find_duplicate_candidates,create_consolidation_proposals,list_consolidation_proposals,approve_consolidation,reject_consolidation
from .learning import events, save_response_feedback, feedback_summary, quality_report
from .knowledge import ingest,recent
from .skills import seed,list_all,set_enabled,proposals,accept,reject
from .settings import public,set_value,reset,schema as settings_schema,int_value,bool_value
from .runtime import status,installed_models,registry_models,model_readiness
from .model_manager import info,import_model,start_auto_setup,auto_setup_status,start_import_task,cancel_import_task
from .research import search_web,research_and_learn
from .web import HTML
from .voice import transcribe_wav,speak,voice_status
from .tools import list_tools, run_tool, set_enabled as set_tool_enabled
from .security import configured_token, is_loopback_host, max_request_bytes, request_rate_allowed
from .scheduler import start_scheduler, stop_scheduler, list_jobs, list_runs, create_job, update_job, delete_job, retry_job
from .agents import ROLES, delegate, delegate_many
from .terminal import run_command
from .browser import browser_action
from .messaging import telegram_send, webhook_send
from .mcp import handle_message
from .desktop import desktop_action
from .updates import check_update, apply_update, rollback_update

app=FastAPI(title="Nano AI",version="0.5.0")
@app.on_event("startup")
def startup():
    if not is_loopback_host(config.HOST) and not configured_token():
        raise RuntimeError("Refusing remote API startup without NANO_API_TOKEN.")
    init_db()
    seed()
    start_scheduler()

@app.on_event("shutdown")
def shutdown():
    stop_scheduler()

@app.middleware("http")
async def protect_api(request: Request, call_next):
    is_api = request.url.path.startswith("/api/") or request.url.path == "/mcp"
    if is_api:
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                path_limit = (100 * 1024 * 1024 if request.url.path == "/api/restore" else 22 * 1024 * 1024 if request.url.path == "/api/voice/stt" else max_request_bytes())
                if int(content_length) > path_limit:
                    return JSONResponse({"detail":"Request body exceeds configured size limit for this endpoint."},status_code=413)
            except ValueError:
                return JSONResponse({"detail":"Invalid Content-Length header."},status_code=400)
        peer_for_limit = request.client.host if request.client else "unknown"
        if not request_rate_allowed(peer_for_limit):
            return JSONResponse({"detail":"Request rate limit exceeded. Try again shortly."},status_code=429)
    if is_api and request.url.path != "/api/channels/telegram/webhook":
        token = configured_token()
        peer = request.client.host if request.client else ""
        remote_request = bool(peer) and peer not in {"testclient", "localhost", "::ffff:127.0.0.1"} and not is_loopback_host(peer)
        required = bool(token) or remote_request or not is_loopback_host(config.HOST)
        supplied = request.headers.get("authorization", "")
        if supplied.lower().startswith("bearer "):
            supplied = supplied[7:].strip()
        else:
            supplied = request.headers.get("x-nano-token", "")
        if required and not token:
            return JSONResponse({"detail":"Remote API access is disabled until NANO_API_TOKEN is configured."},status_code=503)
        if token and (not supplied or not __import__("hmac").compare_digest(supplied,token)):
            return JSONResponse({"detail":"Missing or invalid API token. Use Authorization: Bearer <token>."},status_code=401)
    return await call_next(request)

class ChatIn(BaseModel): conversation_id:int=1; message:str
class MemoryConsolidationIn(BaseModel): merged_content:str|None=Field(default=None,max_length=12000)
class FeedbackIn(BaseModel):
    conversation_id:int = Field(ge=1)
    user_text:str = Field(min_length=1,max_length=12000)
    assistant_text:str = Field(min_length=1,max_length=20000)
    rating:int
    correction:str = Field(default="",max_length=2000)
class ProactiveTalkIn(BaseModel):
    prompt:str|None = Field(default=None,max_length=1000)
class UpdateApplyIn(BaseModel):
    approved:bool = False
class UpdateRollbackIn(BaseModel):
    approved:bool = False
    restore_database:bool = False
class SettingIn(BaseModel): key:str; value:str
class KnowledgeIn(BaseModel): text:str; source:str="local"
class ConversationIn(BaseModel): title:str="New conversation"
class RegenerateIn(BaseModel): conversation_id:int=Field(ge=1)
class SkillProposalIn(BaseModel): name:str; description:str; prompt:str
class ModelImportIn(BaseModel): repo:str; filename:str; model_id:str|None=None
class ToolRunIn(BaseModel): name:str; arguments:dict
class ScheduleIn(BaseModel):
    name:str = Field(min_length=1,max_length=100)
    job_type:str = "assistant_prompt"
    prompt:str = Field(min_length=1,max_length=8000)
    interval_seconds:int = Field(ge=60,le=31536000)
    enabled:bool = True
    max_attempts:int = Field(default=3,ge=1,le=10)
    retry_delay_seconds:int = Field(default=60,ge=5,le=3600)
    timeout_seconds:int = Field(default=300,ge=5,le=86400)
class AgentTaskIn(BaseModel):
    role:str
    task:str = Field(min_length=1,max_length=8000)
    timeout_seconds:int = Field(default=180,ge=5,le=300)
class AgentBatchIn(BaseModel):
    tasks:list[AgentTaskIn] = Field(min_length=1,max_length=4)
    timeout_seconds:int = Field(default=180,ge=5,le=300)
class TerminalIn(BaseModel):
    command:str
    args:list[str] = Field(default_factory=list,max_length=10)
    timeout:int = Field(default=15,ge=1,le=30)
    approved:bool = False
class BrowserIn(BaseModel):
    action:str
    url:str = Field(min_length=1,max_length=2048)
    selector:str|None = None
    value:str|None = None
    approved:bool = False
class DesktopIn(BaseModel):
    action:str
    x:int|None=None
    y:int|None=None
    text:str|None=None
    key:str|None=None
    approved:bool=False
class TelegramSendIn(BaseModel):
    chat_id:str = Field(min_length=1,max_length=100)
    text:str = Field(min_length=1,max_length=4000)
class WebhookSendIn(BaseModel):
    url:str = Field(min_length=1,max_length=2048)
    text:str = Field(min_length=1,max_length=12000)

@app.get("/",response_class=HTMLResponse)
def home(): return HTML

@app.post("/api/talk/proactive")
def proactive_talk(x:ProactiveTalkIn):
    if not bool_value("autonomous_talk_enabled", False):
        raise HTTPException(403,"Enable autonomous talking in Settings first.")
    if not bool_value("voice_enabled", True) or not bool_value("auto_tts", True):
        raise HTTPException(403,"Enable voice and auto-TTS in Settings first.")
    prompt = (x.prompt or public().get("autonomous_talk_prompt", "")).strip()
    if not prompt or len(prompt) > 1000:
        raise HTTPException(400,"A valid proactive-talk prompt is required.")
    try:
        return {"answer": generate_proactive_talk(prompt), "mode":"local-proactive-check-in"}
    except Exception as e:
        raise HTTPException(503,str(e))

@app.get("/api/system/update/check")
def system_update_check():
    try: return check_update()
    except RuntimeError as e: raise HTTPException(503,str(e))
@app.post("/api/system/update/apply")
def system_update_apply(x:UpdateApplyIn):
    try: return apply_update(x.approved)
    except PermissionError as e: raise HTTPException(403,str(e))
    except RuntimeError as e: raise HTTPException(409,str(e))

@app.post("/api/system/update/rollback")
def system_update_rollback(x:UpdateRollbackIn):
    try: return rollback_update(x.approved, x.restore_database)
    except PermissionError as e: raise HTTPException(403,str(e))
    except RuntimeError as e: raise HTTPException(409,str(e))

@app.get("/api/health")
def health():
    s=status()
    readiness=model_readiness(s)
    return {"ok":True,"model_reachable":s["reachable"],"model_ready":readiness["status"]=="ok","model_readiness":readiness,"runtime":s,"voice":voice_status()}

@app.get("/api/system/health")
def system_health_api():
    from .system_health import system_health
    return system_health()

@app.get("/api/ready")
def ready():
    s=status()
    readiness=model_readiness(s)
    ready_ok=readiness["status"]=="ok"
    payload={"ready":ready_ok,"model_reachable":s["reachable"],"model_ready":ready_ok,"model_readiness":readiness,"runtime":s}
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

@app.get("/api/memories/duplicates")
def memory_duplicates():
    return find_duplicate_candidates()

@app.get("/api/memories/consolidation")
def memory_consolidation_queue():
    return list_consolidation_proposals()

@app.post("/api/memories/consolidation/scan")
def memory_consolidation_scan():
    return create_consolidation_proposals()

@app.post("/api/memories/consolidation/{proposal_id}/approve")
def memory_consolidation_approve(proposal_id:int, x:MemoryConsolidationIn):
    try:
        return approve_consolidation(proposal_id, x.merged_content)
    except ValueError as e:
        raise HTTPException(409,str(e))

@app.post("/api/memories/consolidation/{proposal_id}/reject")
def memory_consolidation_reject(proposal_id:int):
    try:
        return reject_consolidation(proposal_id)
    except ValueError as e:
        raise HTTPException(404,str(e))
@app.get("/api/learning/events")
def learning_events(): return events(100)
@app.get("/api/learning/feedback-summary")
def learning_feedback_summary(): return feedback_summary()
@app.get("/api/learning/quality")
def learning_quality_report(): return quality_report()
@app.post("/api/feedback")
def response_feedback(x:FeedbackIn):
    if x.rating not in (-1,1): raise HTTPException(400,"rating must be 1 or -1")
    if not rows("SELECT id FROM conversations WHERE id=?", (x.conversation_id,)):
        raise HTTPException(404,"Conversation not found")
    try:
        return save_response_feedback(x.conversation_id,x.user_text,x.assistant_text,x.rating,x.correction)
    except ValueError as e:
        raise HTTPException(400,str(e))

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
def knowledge(): return recent(int_value("knowledge_limit", 100))

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
@app.get("/api/settings/schema")
def settings_schema_api(): return settings_schema()
@app.post("/api/settings")
def setting(x:SettingIn):
    try: set_value(x.key,x.value)
    except ValueError as e: raise HTTPException(400,str(e))
    return public()
@app.post("/api/settings/reset")
def settings_reset(): return reset()

@app.get("/api/backup")
def backup_database():
    """Return a consistent SQLite snapshot without copying a live WAL file."""
    if not config.DB_PATH.exists():
        raise HTTPException(404, "Database file does not exist yet.")
    with NamedTemporaryFile(prefix="nano-backup-", suffix=".sqlite3", delete=False) as tmp:
        backup_path = Path(tmp.name)
    source = None
    destination = None
    try:
        source = sqlite3.connect(str(config.DB_PATH), timeout=10)
        destination = sqlite3.connect(str(backup_path), timeout=10)
        source.backup(destination)
        destination.close()
        destination = None
        source.close()
        source = None
        return FileResponse(backup_path, media_type="application/vnd.sqlite3", filename="nano-ai-backup.sqlite3", background=BackgroundTask(backup_path.unlink, missing_ok=True))
    except sqlite3.Error as exc:
        if destination is not None:
            destination.close()
        if source is not None:
            source.close()
        backup_path.unlink(missing_ok=True)
        raise HTTPException(500, "Could not create a consistent database backup.") from exc



_RECOVERY_SNAPSHOT_KEEP = 10


def _prune_recovery_snapshots(recovery_dir):
    """Keep only the newest pre-restore snapshots so restores cannot fill the disk."""
    try:
        snapshots = sorted(recovery_dir.glob("pre-restore-*.sqlite3"), key=lambda p: p.stat().st_mtime, reverse=True)
        for stale in snapshots[_RECOVERY_SNAPSHOT_KEEP:]:
            stale.unlink(missing_ok=True)
    except OSError:
        pass


@app.post("/api/restore")
async def restore_database(file: UploadFile = File(...)):
    """Validate an uploaded SQLite backup, preserve a recovery snapshot, then restore via SQLite backup."""
    max_bytes = 100 * 1024 * 1024
    filename = (file.filename or "").lower()
    if not filename.endswith((".sqlite", ".sqlite3", ".db")):
        raise HTTPException(400, "Upload a .sqlite, .sqlite3, or .db backup file.")
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(prefix="nano-restore-candidate-", suffix=".sqlite3", delete=False) as tmp:
        candidate = Path(tmp.name)
    size = 0
    try:
        with candidate.open("wb") as output:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > max_bytes:
                    raise HTTPException(413, "Backup exceeds the 100 MB restore limit.")
                output.write(chunk)
        if size == 0:
            raise HTTPException(400, "Uploaded backup is empty.")
        try:
            check = sqlite3.connect(f"file:{candidate.as_posix()}?mode=ro", uri=True, timeout=10)
            try:
                integrity = check.execute("PRAGMA integrity_check").fetchone()
                if not integrity or integrity[0] != "ok":
                    raise HTTPException(400, "Backup failed SQLite integrity_check.")
                tables = {row[0] for row in check.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                required = {"conversations", "messages", "memories", "learning_events", "settings", "skills", "skill_proposals"}
                if not required.issubset(tables):
                    raise HTTPException(400, "Backup is not a compatible Nano AI database.")
            finally:
                check.close()
        except sqlite3.DatabaseError as exc:
            raise HTTPException(400, "Uploaded file is not a valid SQLite database.") from exc

        recovery_dir = config.DB_PATH.parent / "recovery"
        recovery_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        recovery_path = recovery_dir / f"pre-restore-{stamp}.sqlite3"
        current = None
        try:
            if config.DB_PATH.exists():
                current = sqlite3.connect(str(config.DB_PATH), timeout=10)
                recovery = sqlite3.connect(str(recovery_path), timeout=10)
                try:
                    current.backup(recovery)
                finally:
                    recovery.close()
                    current.close()
                    current = None
            source = sqlite3.connect(f"file:{candidate.as_posix()}?mode=ro", uri=True, timeout=10)
            destination = sqlite3.connect(str(config.DB_PATH), timeout=10)
            try:
                source.backup(destination)
                # Migrate optional tables when restoring backups created by older Nano versions.
                destination.execute("CREATE TABLE IF NOT EXISTS response_feedback(id INTEGER PRIMARY KEY AUTOINCREMENT, conversation_id INTEGER NOT NULL, user_text TEXT NOT NULL, assistant_text TEXT NOT NULL, rating INTEGER NOT NULL CHECK(rating IN (-1,1)), correction TEXT NOT NULL DEFAULT '', created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
                destination.execute("CREATE INDEX IF NOT EXISTS idx_feedback_recent ON response_feedback(id DESC)")
                result = destination.execute("PRAGMA integrity_check").fetchone()
                if not result or result[0] != "ok":
                    raise sqlite3.DatabaseError("Restored database failed integrity_check.")
            finally:
                source.close()
                destination.close()
        except Exception as exc:
            if current is not None:
                current.close()
            if recovery_path.exists():
                try:
                    recovery = sqlite3.connect(f"file:{recovery_path.as_posix()}?mode=ro", uri=True, timeout=10)
                    rollback = sqlite3.connect(str(config.DB_PATH), timeout=10)
                    try:
                        recovery.backup(rollback)
                    finally:
                        recovery.close()
                        rollback.close()
                except sqlite3.Error:
                    pass
            if isinstance(exc, HTTPException):
                raise
            raise HTTPException(500, "Restore failed; Nano attempted rollback using the recovery snapshot.") from exc
        _prune_recovery_snapshots(recovery_dir)
        return {"ok": True, "restored_bytes": size,
                "recovery_backup": recovery_path.name if recovery_path.exists() else None,
                "message": "Restore completed and passed SQLite integrity_check."}
    finally:
        await file.close()
        candidate.unlink(missing_ok=True)

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

@app.post("/api/models/auto-setup/cancel")
@app.post("/api/models/import-task/cancel")
def model_import_cancel(): return cancel_import_task()
@app.post("/api/models/import-task")
def model_import_task(x:ModelImportIn):
    try:
        return start_import_task(x.repo, x.filename, x.model_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(409, str(e))

@app.post("/api/models/import")
def model_import(x:ModelImportIn):
    try:
        return {"model_id": import_model(x.repo, x.filename, x.model_id)}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(503, str(e))

@app.get("/api/scheduler/jobs")
def scheduler_jobs(): return list_jobs()

@app.post("/api/scheduler/jobs")
def scheduler_create(x:ScheduleIn):
    try: return create_job(x.name,x.job_type,{"prompt":x.prompt},x.interval_seconds,x.enabled,x.max_attempts,x.retry_delay_seconds,x.timeout_seconds)
    except ValueError as e: raise HTTPException(400,str(e))

@app.patch("/api/scheduler/jobs/{job_id}")
def scheduler_enable(job_id:int, enabled:bool=True):
    try: return update_job(job_id,enabled)
    except KeyError as e: raise HTTPException(404,str(e))

@app.delete("/api/scheduler/jobs/{job_id}")
def scheduler_delete(job_id:int): return delete_job(job_id)

@app.post("/api/scheduler/jobs/{job_id}/retry")
def scheduler_retry(job_id:int):
    try: return retry_job(job_id)
    except KeyError as e: raise HTTPException(404,str(e))
    except ValueError as e: raise HTTPException(409,str(e))

@app.get("/api/scheduler/runs")
def scheduler_runs(job_id:int|None=None,limit:int=100): return list_runs(job_id,limit)

@app.get("/api/agents")
def agents_list(): return [{"role":name,"description":prompt} for name,prompt in ROLES.items()]

@app.post("/api/agents/delegate")
def agents_delegate(x:AgentTaskIn):
    try: return delegate(x.role,x.task,x.timeout_seconds)
    except ValueError as e: raise HTTPException(400,str(e))

@app.post("/api/agents/delegate-batch")
def agents_delegate_batch(x:AgentBatchIn):
    try: return delegate_many([t.model_dump() for t in x.tasks],x.timeout_seconds)
    except ValueError as e: raise HTTPException(400,str(e))

@app.post("/api/terminal/run")
def terminal_run(x:TerminalIn):
    if not x.approved: raise HTTPException(403,"Explicit approval is required to run a terminal command.")
    try: return run_command(x.command,x.args,x.timeout)
    except ValueError as e: raise HTTPException(400,str(e))

@app.post("/api/browser/action")
def browser_control(x:BrowserIn):
    try: return browser_action(x.action,x.url,x.selector,x.value,x.approved)
    except ValueError as e: raise HTTPException(400,str(e))
    except PermissionError as e: raise HTTPException(403,str(e))
    except RuntimeError as e: raise HTTPException(503,str(e))

@app.post("/api/computer/action")
def computer_control(x:DesktopIn):
    try: return desktop_action(x.action,x.x,x.y,x.text,x.key,x.approved)
    except ValueError as e: raise HTTPException(400,str(e))
    except PermissionError as e: raise HTTPException(403,str(e))
    except RuntimeError as e: raise HTTPException(503,str(e))

@app.post("/api/channels/telegram/webhook")
def telegram_webhook(request: Request, update:dict):
    import os, hmac
    expected = os.getenv("NANO_TELEGRAM_WEBHOOK_SECRET", "").strip()
    supplied = request.headers.get("x-telegram-bot-api-secret-token", "")
    if not expected or not supplied or not hmac.compare_digest(expected,supplied):
        raise HTTPException(401,"Telegram webhook secret is missing or invalid.")
    message = update.get("message") or update.get("edited_message") or {}
    chat = message.get("chat") or {}
    text = message.get("text")
    chat_id = chat.get("id")
    if not chat_id or not isinstance(text,str) or not text.strip():
        return {"ok":True,"ignored":True}
    if len(text)>config.MAX_MESSAGE_CHARS:
        raise HTTPException(413,"Telegram message is too long.")
    try:
        conv = rows("SELECT id FROM conversations ORDER BY id LIMIT 1")
        cid = conv[0]["id"] if conv else run("INSERT INTO conversations(title) VALUES('Telegram')")
        answer = respond(cid,text)
        return telegram_send(chat_id,answer)
    except Exception as e:
        raise HTTPException(502,"Could not process Telegram update: "+str(e)[:300])

@app.post("/api/channels/telegram/send")
def telegram_send_api(x:TelegramSendIn):
    try: return telegram_send(x.chat_id,x.text)
    except ValueError as e: raise HTTPException(400,str(e))
    except RuntimeError as e: raise HTTPException(502,str(e))

@app.post("/api/channels/webhook/send")
def webhook_send_api(x:WebhookSendIn):
    try: return webhook_send(x.url,x.text)
    except ValueError as e: raise HTTPException(400,str(e))
    except RuntimeError as e: raise HTTPException(502,str(e))

@app.post("/mcp")
def mcp_endpoint(message:dict):
    response = handle_message(message)
    if response is None: return JSONResponse({},status_code=202)
    return response

@app.get("/api/system")
def system(): return {"version":"0.5.0","host":config.HOST,"port":config.PORT,"runtime":status(),"voice":voice_status(),"paths":{"data":str(config.DATA_DIR),"models":str(config.MODEL_DIR),"skills":str(config.SKILLS_DIR),"database":str(config.DB_PATH)}}

@app.get("/api/conversations")
def conversations(limit:int=200):
    bounded=max(1,min(500,limit))
    return rows("SELECT * FROM conversations ORDER BY updated_at DESC,id DESC LIMIT ?",(bounded,))
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

@app.post("/api/chat/regenerate")
def chat_regenerate(x:RegenerateIn):
    try: return {"answer":regenerate(x.conversation_id)}
    except ValueError as e: raise HTTPException(404,str(e))
    except Exception as e: raise HTTPException(503,str(e))

@app.get("/api/conversations/search")
def conversations_search(q:str="",limit:int=50):
    query=q.strip()
    if not query: return []
    limit=max(1,min(100,limit))
    like="%"+query.replace("\\","\\\\").replace("%","\\%").replace("_","\\_")+"%"
    return rows("SELECT m.conversation_id,c.title,m.role,m.content,m.created_at FROM messages m JOIN conversations c ON c.id=m.conversation_id WHERE m.content LIKE ? ESCAPE '\\' ORDER BY m.id DESC LIMIT ?",(like,limit))

@app.get("/api/conversations/{cid}/export")
def conversation_export(cid:int):
    conversation=rows("SELECT id,title,created_at,updated_at FROM conversations WHERE id=?",(cid,))
    if not conversation: raise HTTPException(404,"Conversation not found")
    return JSONResponse({"conversation":conversation[0],"messages":rows("SELECT id,role,content,created_at FROM messages WHERE conversation_id=? ORDER BY id",(cid,))})

@app.get("/api/voice/status")
def voice_api_status(): return voice_status()
@app.post("/api/voice/stt")
async def voice_stt(file:UploadFile=File(...)):
    if not bool_value("voice_enabled", True): raise HTTPException(403,"Voice is disabled in Settings.")
    if file.content_type not in {"audio/wav","audio/x-wav","audio/wave","application/octet-stream"}: raise HTTPException(415,"Upload a mono 16-bit WAV file.")
    max_bytes = 20 * 1024 * 1024
    with NamedTemporaryFile(prefix="nano-stt-",suffix=".wav",delete=False) as tmp:
        temp=Path(tmp.name)
    size=0
    try:
        with temp.open("wb") as output:
            while True:
                chunk=await file.read(1024*1024)
                if not chunk: break
                size += len(chunk)
                if size > max_bytes: raise HTTPException(413,"Audio file too large.")
                output.write(chunk)
        return {"text":transcribe_wav(temp)}
    except (ValueError,RuntimeError) as e:
        raise HTTPException(422,str(e))
    finally:
        await file.close()
        temp.unlink(missing_ok=True)
@app.get("/api/voice/tts")
def voice_tts(text:str):
    if not bool_value("voice_enabled", True): raise HTTPException(403,"Voice is disabled in Settings.")
    if not text.strip() or len(text)>config.MAX_MESSAGE_CHARS: raise HTTPException(400,"Invalid TTS text.")
    with NamedTemporaryFile(prefix="nano-tts-",suffix=".wav",delete=False) as tmp: output=Path(tmp.name)
    try:
        speak(text,output)
        return FileResponse(output,media_type="audio/wav",filename="nano-response.wav",background=BackgroundTask(output.unlink,missing_ok=True))
    except (ValueError,RuntimeError) as e:
        output.unlink(missing_ok=True); raise HTTPException(503,str(e))
