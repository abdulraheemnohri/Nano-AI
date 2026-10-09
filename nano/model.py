import json
import urllib.error
import urllib.request
from . import config
from .settings import bool_value, float_value, int_value

SYSTEM = """You are Nano AI, a small local assistant powered by Qwen3 1.7B through the LiteRT-LM CLI runtime. You are offline-first and privacy-first. Nano may use a small allowlisted set of local tools when the application supplies actual tool results. Never claim a tool ran unless its result is supplied. Nano cannot browse the internet, run terminal commands, control devices, or retrain model weights. Use supplied memories as context, be honest about uncertainty, and answer concisely unless detail is requested."""

def health():
    try:
        with urllib.request.urlopen(config.LITERT_URL.rstrip("/") + "/v1/models", timeout=2) as response:
            return response.status == 200
    except Exception:
        return False

def _settings():
    return {
        "temperature": float_value("temperature", config.TEMPERATURE),
        "max_tokens": int_value("max_tokens", max(256, min(2048, config.MAX_CONTEXT // 2))),
        "max_history": int_value("max_history", 12),
        "language": __import__("nano.settings", fromlist=["get_all"]).get_all().get("language", "auto"),
    }

def chat(messages, user_text=None, context=""):
    history = list(messages)
    if user_text is not None:
        history.append({"role": "user", "content": user_text})
    s = _settings()
    system = SYSTEM
    if s["language"] != "auto":
        system += f"\nPreferred response language: {s['language']}."
    if context:
        system += "\n\nUse this local context when relevant:\n" + context
    payload = {
        "model": config.LITERT_MODEL,
        "messages": [{"role": "system", "content": system}] + history[-s["max_history"]:],
        "temperature": s["temperature"],
        "stream": False,
        "max_tokens": max(1, min(4096, s["max_tokens"])),
    }
    request = urllib.request.Request(
        config.LITERT_URL.rstrip("/") + "/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=config.LITERT_TIMEOUT) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"LiteRT-LM server returned HTTP {exc.code}: {detail[:300]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError("LiteRT-LM server is not reachable. Start litert-lm serve first.") from exc
    except (KeyError, IndexError, json.JSONDecodeError) as exc:
        raise RuntimeError("LiteRT-LM server returned an invalid chat response.") from exc
