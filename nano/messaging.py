"""Optional outbound messaging adapters; credentials are environment-only."""
import json
import os
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

def _post_json(url, payload, headers=None, timeout=15):
    data=json.dumps(payload).encode("utf-8")
    req=Request(url,data=data,headers={"Content-Type":"application/json",**(headers or {})},method="POST")
    try:
        with urlopen(req,timeout=timeout) as response:
            raw=response.read(65536).decode("utf-8","replace")
            return {"ok":200 <= response.status < 300,"status_code":response.status,"response":raw[:4000]}
    except (URLError,HTTPError,TimeoutError) as exc:
        raise RuntimeError("Messaging request failed: "+str(exc)[:500]) from exc

def telegram_send(chat_id, text):
    token=os.getenv("NANO_TELEGRAM_BOT_TOKEN","").strip()
    if not token: raise RuntimeError("Set NANO_TELEGRAM_BOT_TOKEN to enable Telegram.")
    if not str(text).strip() or len(str(text))>4000: raise ValueError("Message must contain 1 to 4000 characters.")
    return _post_json(f"https://api.telegram.org/bot{token}/sendMessage",{"chat_id":str(chat_id),"text":str(text)})

def webhook_send(url, text):
    if not str(url).startswith("https://"): raise ValueError("Webhook URL must use HTTPS.")
    if not str(text).strip() or len(str(text))>12000: raise ValueError("Message must contain 1 to 12000 characters.")
    return _post_json(url,{"text":str(text)})
