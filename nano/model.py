import json
import urllib.error
import urllib.request
from .config import LITERT_URL, LITERT_MODEL, TEMPERATURE, MAX_CONTEXT

SYSTEM = """You are Nano AI, a small local assistant powered by Qwen3 1.7B through the LiteRT-LM CLI runtime. You are offline-first and privacy-first. Do not claim to browse, execute tools, control devices, or retrain model weights. Use supplied memories as context, be honest about uncertainty, and answer concisely unless detail is requested."""

def health():
    try:
        with urllib.request.urlopen(LITERT_URL.rstrip("/") + "/v1/models", timeout=2) as response:
            return response.status == 200
    except Exception:
        return False

def chat(messages, user_text=None, context=""):
    history = list(messages)
    if user_text is not None:
        history.append({"role": "user", "content": user_text})
    system = SYSTEM
    if context:
        system += "\n\nUse this local context when relevant:\n" + context
    payload = {
        "model": LITERT_MODEL,
        "messages": [{"role": "system", "content": system}] + history[-12:],
        "temperature": TEMPERATURE,
        "stream": False,
        "max_tokens": max(256, min(2048, MAX_CONTEXT // 2)),
    }
    request = urllib.request.Request(
        LITERT_URL.rstrip("/") + "/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"LiteRT-LM server returned HTTP {exc.code}: {detail[:300]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError("LiteRT-LM server is not reachable. Start litert-lm serve first.") from exc
    except (KeyError, IndexError, json.JSONDecodeError) as exc:
        raise RuntimeError("LiteRT-LM server returned an invalid chat response.") from exc
