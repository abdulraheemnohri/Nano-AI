import re
from .db import one, run

DEFAULTS = {
    "language": "auto",
    "voice_enabled": "true",
    "learning_enabled": "true",
    "auto_tts": "true",
    "theme": "dark",
    "temperature": "0.7",
    "max_tokens": "1024",
    "max_history": "12",
    "memory_limit": "6",
    "knowledge_limit": "100",
    "tool_enabled_calculator": "true",
    "tool_enabled_datetime_now": "true",
    "tool_enabled_unit_convert": "true",
    "tool_enabled_text_stats": "true",
    "tool_enabled_memory_search": "true",
    "tool_enabled_knowledge_search": "true",
}

BOOL_KEYS = {key for key in DEFAULTS if key.startswith("tool_enabled_")} | {"voice_enabled", "learning_enabled", "auto_tts"}
INT_KEYS = {"max_tokens", "max_history", "memory_limit", "knowledge_limit"}


def _normalize(key, value):
    value = str(value).strip()
    if key not in DEFAULTS:
        raise ValueError("unknown setting")
    if key in BOOL_KEYS:
        if value.lower() not in {"true", "false", "1", "0", "yes", "no", "on", "off"}:
            raise ValueError(f"{key} must be true or false")
        return "true" if value.lower() in {"true", "1", "yes", "on"} else "false"
    if key == "temperature":
        try:
            number = float(value)
        except ValueError as exc:
            raise ValueError("temperature must be a number") from exc
        if not 0 <= number <= 2:
            raise ValueError("temperature must be between 0 and 2")
        return str(number)
    if key in INT_KEYS:
        try:
            number = int(value)
        except ValueError as exc:
            raise ValueError(f"{key} must be an integer") from exc
        minimum = 1
        maximum = {"max_tokens": 4096, "max_history": 128, "memory_limit": 100, "knowledge_limit": 5000}[key]
        if not minimum <= number <= maximum:
            raise ValueError(f"{key} must be between {minimum} and {maximum}")
        return str(number)
    if key == "language":
        if not value:
            return "auto"
        if len(value) > 32 or not re.fullmatch(r"[A-Za-z][A-Za-z0-9 _-]{0,31}", value):
            raise ValueError("language must be 'auto' or a short language name/code without punctuation.")
        return value
    if key == "theme":
        if value not in {"dark", "light", "system"}:
            raise ValueError("theme must be dark, light, or system")
        return value
    return value


def get_all():
    result = {}
    for key, default in DEFAULTS.items():
        row = one("SELECT value FROM settings WHERE key=?", (key,))
        result[key] = row["value"] if row else default
    return result


def public():
    return get_all()


def set_value(key, value):
    value = _normalize(key, value)
    run("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
    return value


def bool_value(key, fallback=True):
    value = get_all().get(key, str(fallback)).lower()
    return value in {"true", "1", "yes", "on"}


def int_value(key, fallback):
    try:
        return int(get_all().get(key, str(fallback)))
    except ValueError:
        return fallback


def float_value(key, fallback):
    try:
        return float(get_all().get(key, str(fallback)))
    except ValueError:
        return fallback


def reset():
    run("DELETE FROM settings")
    return get_all()


DESCRIPTIONS = {
    "language": "Preferred response language; use auto to let Nano follow the conversation.",
    "voice_enabled": "Enable local Vosk speech recognition and Piper text-to-speech endpoints.",
    "learning_enabled": "Allow explicit conversation-derived memory/learning events to be recorded.",
    "auto_tts": "Automatically play local Piper speech after assistant replies.",
    "theme": "Web interface color theme.",
    "temperature": "Model response randomness, from 0 (more deterministic) to 2.",
    "max_tokens": "Maximum generated tokens per model response.",
    "max_history": "Maximum recent conversation messages included in model context.",
    "memory_limit": "Maximum relevant memories included in prompt context.",
    "knowledge_limit": "Maximum knowledge entries shown in the knowledge UI.",
    "tool_enabled_calculator": "Allow the local calculator tool.",
    "tool_enabled_datetime_now": "Allow the local date/time tool.",
    "tool_enabled_unit_convert": "Allow the local unit conversion tool.",
    "tool_enabled_text_stats": "Allow local text statistics.",
    "tool_enabled_memory_search": "Allow memory search through built-in tools.",
    "tool_enabled_knowledge_search": "Allow local knowledge search through built-in tools.",
}


def schema():
    result = []
    for key, default in DEFAULTS.items():
        kind = "boolean" if key in BOOL_KEYS else "number" if key in INT_KEYS or key == "temperature" else "choice" if key == "theme" else "text"
        item = {"key": key, "default": default, "description": DESCRIPTIONS.get(key, "Nano AI setting."), "type": kind}
        if key == "theme":
            item["choices"] = ["dark", "light", "system"]
        elif key == "temperature":
            item.update(minimum=0, maximum=2, step=0.1)
        elif key == "max_tokens":
            item.update(minimum=1, maximum=4096, step=1)
        elif key == "max_history":
            item.update(minimum=1, maximum=128, step=1)
        elif key == "memory_limit":
            item.update(minimum=1, maximum=100, step=1)
        elif key == "knowledge_limit":
            item.update(minimum=1, maximum=5000, step=1)
        result.append(item)
    return result
