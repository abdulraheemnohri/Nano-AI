from .db import one, run

DEFAULTS = {
    "language": "auto",
    "voice_enabled": "true",
    "learning_enabled": "true",
    "theme": "dark",
    "temperature": "0.7",
}

def get_all():
    result = {}
    for key, default in DEFAULTS.items():
        row = one("SELECT value FROM settings WHERE key=?", (key,))
        result[key] = row["value"] if row else default
    return result

def public():
    return get_all()

def set_value(key, value):
    if key not in DEFAULTS:
        raise ValueError("unknown setting")
    value = str(value)
    if key == "temperature":
        try:
            temperature = float(value)
        except ValueError as exc:
            raise ValueError("temperature must be a number") from exc
        if not 0 <= temperature <= 2:
            raise ValueError("temperature must be between 0 and 2")
    if key in {"voice_enabled", "learning_enabled"} and value.lower() not in {"true", "false", "1", "0", "yes", "no"}:
        raise ValueError(f"{key} must be true or false")
    run("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
    return value
