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
}

BOOL_KEYS = {"voice_enabled", "learning_enabled", "auto_tts"}
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
        maximum = 4096 if key in {"max_tokens", "max_history"} else 5000
        if not minimum <= number <= maximum:
            raise ValueError(f"{key} must be between {minimum} and {maximum}")
        return str(number)
    if key == "language":
        if len(value) > 32:
            raise ValueError("language is too long")
        return value or "auto"
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
