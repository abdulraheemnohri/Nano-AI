from pathlib import Path
from fastapi import FastAPI,HTTPException,UploadFile,File,Query
from fastapi.responses import HTMLResponse,FileResponse
from pydantic import BaseModel
from .db import init_db,run,rows
from .model import chat,health
from .learning import learn_from_text,memories,delete_memory
from .skills import seed,list_skills,proposals,propose,accept
from .voice import transcribe_wav,speak
from .config import PORT,HOST,DATA_DIR

app=FastAPI(title='Nano AI',version='1.0.0')
class ChatIn(BaseModel): message:str; conversation_id:int=1
class MemoryIn(BaseModel): kind:str='fact'; content:str; confidence:float=0.8
class ProposalIn(BaseModel): name:str; description:str; prompt:str

@app.on_event('startup')
def startup(): init_db(); seed()

@app.get('/',response_class=HTMLResponse)
def home():
 return HTMLResponse(INDEX)

@app.get('/api/health')
def api_health(): return {'ok':True,'model':health()}

@app.get('/api/memories')
def api_memories(): return memories(100)
@app.post('/api/memories')
def api_memory(x:MemoryIn):
 if not x.content.strip(): raise HTTPException(400,'content required')
 i=run('INSERT INTO memories(kind,content,confidence) VALUES(?,?,?)',(x.kind,x.content.strip(),max(0,min(1,x.confidence))))
 return {'id':i}
@app.delete('/api/memories/{mid}')
def api_delete(mid:int): delete_memory(mid); return {'ok':True}

@app.get('/api/skills')
def api_skills(): return list_skills()
@app.get('/api/skills/proposals')
def api_proposals(): return proposals()
@app.post('/api/skills/proposals')
def api_propose(x:ProposalIn): return {'id':propose(x.name,x.description,x.prompt)}
@app.post('/api/skills/proposals/{pid}/accept')
def api_accept(pid:int): return {'ok':accept(pid)}

@app.get('/api/conversations/{cid}/messages')
def api_messages(cid:int): return rows('SELECT id,role,content,created_at FROM messages WHERE conversation_id=? ORDER BY id',(cid,))

@app.post('/api/chat')
def api_chat(x:ChatIn):
 msg=x.message.strip()
 if not msg: raise HTTPException(400,'message required')
 history=rows('SELECT role,content FROM messages WHERE conversation_id=? ORDER BY id DESC LIMIT 12',(x.conversation_id,))[::-1]
 mem=[{'role':'system','content':'Relevant learned memory:\n- '+m['content']} for m in memories(12)]
 answer=chat(mem+history+[{'role':'user','content':msg}])
 run('INSERT INTO messages(conversation_id,role,content) VALUES(?,?,?)',(x.conversation_id,'user',msg))
 run('INSERT INTO messages(conversation_id,role,content) VALUES(?,?,?)',(x.conversation_id,'assistant',answer))
 learned=learn_from_text(msg)
 return {'answer':answer,'learned':learned}

@app.post('/api/voice/transcribe')
async def api_transcribe(file:UploadFile=File(...)):
 p=DATA_DIR/'input.wav'; p.write_bytes(await file.read())
 try: return {'text':transcribe_wav(p)}
 except Exception as e: raise HTTPException(500,str(e))

@app.get('/api/voice/speak')
def api_speak(text: str = Query(..., min_length=1, max_length=5000)):
 out=DATA_DIR/'reply.wav'
 try: speak(text,out); return FileResponse(out,media_type='audio/wav',filename='nano-reply.wav')
 except Exception as e: raise HTTPException(500,str(e))

INDEX='''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Nano AI</title><style>*{box-sizing:border-box}body{margin:0;background:#070b12;color:#e9f0ff;font:15px system-ui}header{padding:18px 24px;border-bottom:1px solid #1b2638;background:#0b111c;display:flex;justify-content:space-between}.brand{font-size:22px;font-weight:800}.pill{padding:5px 10px;border:1px solid #273650;border-radius:99px}main{max-width:1050px;margin:auto;padding:20px;display:grid;grid-template-columns:1fr 300px;gap:18px}.card{background:#0c1320;border:1px solid #1b2a40;border-radius:18px;padding:16px;box-shadow:0 10px 40px #0005}.chat{height:60vh;overflow:auto;display:flex;flex-direction:column;gap:10px}.msg{padding:11px 14px;border-radius:14px;max-width:85%;white-space:pre-wrap}.user{align-self:flex-end;background:#17345c}.assistant{align-self:flex-start;background:#121d2d}form{display:flex;gap:8px;margin-top:10px}input,textarea,button{background:#0a101b;color:#e9f0ff;border:1px solid #263750;border-radius:11px;padding:11px}input{flex:1}button{cursor:pointer}button:hover{filter:brightness(1.25)}aside section{margin-bottom:16px}.stat{font-size:28px;font-weight:800}.list{max-height:190px;overflow:auto}small{color:#8fa2bf}@media(max-width:800px){main{grid-template-columns:1fr}.chat{height:55vh}}</style></head><body><header><div class="brand">◉ Nano AI <small>Qwen3 1.7B · Local</small></div><div id="status" class="pill">checking…</div></header><main><section class="card"><div id="chat" class="chat"></div><form id="form"><input id="input" autocomplete="off" placeholder="Talk to Nano…"><button>Send</button><button type="button" id="mic">🎙️</button><button type="button" id="speak">🔊</button></form></section><aside><section class="card"><h3>Memory</h3><div id="mem" class="list"></div><button onclick="load()">Refresh</button></section><section class="card"><h3>Skills</h3><div id="skills" class="list"></div></section><section class="card"><h3>Learning</h3><div class="stat">∞</div><small>Explicit conversation learning, durable memory and versioned skill evolution. No weight rewriting.</small></section></aside></main><script>const chat=document.querySelector('#chat');function add(role,text){const d=document.createElement('div');d.className='msg '+role;d.textContent=text;chat.appendChild(d);chat.scrollTop=chat.scrollHeight}async function load(){let a=await fetch('/api/memories').then(r=>r.json());document.querySelector('#mem').innerHTML=a.map(x=>'<div>• '+esc(x.content)+'</div>').join('')||'<small>No memories yet.</small>';let s=await fetch('/api/skills').then(r=>r.json());document.querySelector('#skills').innerHTML=s.map(x=>'<div>• '+esc(x.name)+' v'+x.version+'</div>').join('')}function esc(s){return s.replaceAll('&','&amp;').replaceAll('<','&lt;')}document.querySelector('#form').onsubmit=async e=>{e.preventDefault();let i=document.querySelector('#input'),m=i.value.trim();if(!m)return;add('user',m);i.value='';try{let r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:m})}),x=await r.json();if(!r.ok)throw Error(x.detail);add('assistant',x.answer);load()}catch(e){add('assistant','Error: '+e.message)}};let recognition=null;if('webkitSpeechRecognition' in window||'SpeechRecognition' in window){const R=window.SpeechRecognition||window.webkitSpeechRecognition;recognition=new R();recognition.lang=navigator.language||'en-US';recognition.continuous=false;recognition.onresult=e=>{document.querySelector('#input').value=e.results[0][0].transcript;document.querySelector('#form').requestSubmit()}}document.querySelector('#mic').onclick=()=>{if(recognition)recognition.start();else add('assistant','Browser speech recognition is unavailable; install Vosk server-side for offline STT.')};document.querySelector('#speak').onclick=()=>{let last=[...document.querySelectorAll('.assistant')].pop();if(last)new Audio('/api/voice/speak?text='+encodeURIComponent(last.textContent)+'&x='+Date.now()).play().catch(()=>{});};document.addEventListener('keydown',e=>{if(e.code==='Space'&&e.ctrlKey){e.preventDefault();document.querySelector('#mic').click()}});fetch('/api/health').then(r=>r.json()).then(x=>document.querySelector('#status').textContent=x.model?'Qwen online':'Qwen offline');load();add('assistant','Hello. I am Nano AI. Ask me anything, or explicitly say “remember that …” to teach me.')</script></body></html>'''
