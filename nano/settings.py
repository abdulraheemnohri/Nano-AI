from .db import one,run

DEFAULTS={"language":"auto","voice_enabled":"true","learning_enabled":"true","theme":"dark","temperature":"0.7"}

def get_all():
    return {k:(one("SELECT value FROM settings WHERE key=?",(k,)) or {"value":v})["value"] for k,v in DEFAULTS.items()}

def set_value(key,value):
    if key not in DEFAULTS: raise ValueError("unknown setting")
    run("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(key,str(value)))
    return str(value)
