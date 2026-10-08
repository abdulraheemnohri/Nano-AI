import re
from .db import run,rows

PATTERNS=[(r'\bremember that\s+(.+)', 'fact',0.9),(r'\bmy name is\s+(.+)', 'preference',0.95),(r'\bi prefer\s+(.+)', 'preference',0.9),(r'\bi like\s+(.+)', 'preference',0.85),(r'\blearn that\s+(.+)', 'fact',0.9),(r'\bremember\s+(.+)', 'fact',0.8)]

def learn_from_text(text):
    found=[]
    for pat,kind,confidence in PATTERNS:
        m=re.search(pat,text,re.I)
        if m:
            content=m.group(1).strip().rstrip('.!?')
            if content:
                mid=run('INSERT INTO memories(kind,content,confidence,status,source) VALUES(?,?,?,?,?)',(kind,content,confidence,'active','conversation'))
                found.append({'id':mid,'kind':kind,'content':content,'confidence':confidence})
    run('INSERT INTO learning_events(event_type,input_text,result) VALUES(?,?,?)',('conversation',text,str(found)))
    return found

def memories(limit=20): return rows('SELECT * FROM memories WHERE status="active" ORDER BY confidence DESC,updated_at DESC LIMIT ?',(limit,))
def delete_memory(mid): run('UPDATE memories SET status="deleted",updated_at=CURRENT_TIMESTAMP WHERE id=?',(mid,))
