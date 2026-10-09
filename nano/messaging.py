"""Optional outbound messaging adapters; credentials are environment-only."""
import json
import os
import ipaddress
from urllib.parse import urlparse
from urllib.request import Request, urlopen, build_opener, HTTPRedirectHandler
from urllib.error import URLError, HTTPError

def _post_json(url, payload, headers=None, timeout=15):
    data=json.dumps(payload).encode("utf-8")
    req=Request(url,data=data,headers={"Content-Type":"application/json",**(headers or {})},method="POST")
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    try:
        with build_opener(NoRedirect).open(req,timeout=timeout) as response:
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
    parsed=urlparse(str(url))
    allowed={"hooks.slack.com","discord.com","discordapp.com"}
    allowed.update(x.strip().lower() for x in os.getenv("NANO_WEBHOOK_ALLOWED_HOSTS","").split(",") if x.strip())
    if parsed.scheme!="https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Webhook URL must be HTTPS and cannot include embedded credentials.")
    host=parsed.hostname.lower()
    try:
        ipaddress.ip_address(host)
        raise ValueError("IP-literal webhook hosts are not allowed.")
    except ValueError as exc:
        if str(exc)=="IP-literal webhook hosts are not allowed.": raise
    if host not in allowed:
        raise ValueError("Webhook host is not allowlisted. Use Slack/Discord or add it to NANO_WEBHOOK_ALLOWED_HOSTS.")
    if not str(text).strip() or len(str(text))>12000: raise ValueError("Message must contain 1 to 12000 characters.")
    payload={"content":str(text)} if host in {"discord.com","discordapp.com"} else {"text":str(text)}
    return _post_json(url,payload)
