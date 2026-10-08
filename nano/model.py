import json, urllib.request, urllib.error
from .config import LLAMA_URL,LLAMA_MODEL,TEMPERATURE,MAX_CONTEXT

SYSTEM='''You are Nano AI, a small local assistant powered by Qwen3 1.7B. You are offline-first and privacy-first. Do not claim to browse, execute tools, control devices, or retrain model weights. Use supplied memories as context, be honest about uncertainty, and answer concisely unless detail is requested.'''

def health():
    try:
        with urllib.request.urlopen(LLAMA_URL.rstrip('/')+'/health',timeout=2) as r: return r.status==200
    except Exception: return False

def chat(messages):
    payload={'model':LLAMA_MODEL,'messages':[{'role':'system','content':SYSTEM}]+messages,'temperature':TEMPERATURE,'stream':False}
    req=urllib.request.Request(LLAMA_URL.rstrip('/')+'/v1/chat/completions',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=180) as r:
            data=json.loads(r.read().decode()); return data['choices'][0]['message']['content'].strip()
    except urllib.error.URLError as e:
        raise RuntimeError('Local Qwen server is not reachable. Start llama-server first.') from e
