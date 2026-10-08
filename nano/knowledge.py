import re
from .db import run,rows

def ingest(text,source="local"):
    clean=re.sub(r"\s+"," ",text).strip()
    if not clean:return 0
    chunks=[x.strip() for x in re.split(r"(?<=[.!?])\s+",clean) if len(x.strip())>20]
    count=0
    for chunk in chunks[:100]:
        run("INSERT INTO memories(kind,content,confidence,status,source) VALUES(?,?,?,?,?)",("knowledge",chunk,0.65,"active",source)); count+=1
    run("INSERT INTO learning_events(event_type,input_text,result) VALUES(?,?,?)",("knowledge_import",clean,str(count)))
    return count

def recent(limit=50):
    return rows("SELECT * FROM memories WHERE kind='knowledge' AND status='active' ORDER BY id DESC LIMIT ?",(limit,))
