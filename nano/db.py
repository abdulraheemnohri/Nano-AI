import sqlite3
from contextlib import contextmanager
from .config import DB_PATH

SCHEMA='''
CREATE TABLE IF NOT EXISTS conversations(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP,updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT,conversation_id INTEGER NOT NULL,role TEXT NOT NULL,content TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(conversation_id) REFERENCES conversations(id));
CREATE TABLE IF NOT EXISTS memories(id INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT NOT NULL,content TEXT NOT NULL,confidence REAL DEFAULT 0.5,status TEXT DEFAULT 'active',source TEXT DEFAULT 'conversation',created_at TEXT DEFAULT CURRENT_TIMESTAMP,updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS learning_events(id INTEGER PRIMARY KEY AUTOINCREMENT,event_type TEXT NOT NULL,input_text TEXT NOT NULL,result TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS skills(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT UNIQUE NOT NULL,description TEXT NOT NULL,version INTEGER DEFAULT 1,prompt TEXT NOT NULL,enabled INTEGER DEFAULT 1,created_at TEXT DEFAULT CURRENT_TIMESTAMP,updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS skill_proposals(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,description TEXT NOT NULL,prompt TEXT NOT NULL,status TEXT DEFAULT 'pending',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
'''

def connect():
    c=sqlite3.connect(DB_PATH); c.row_factory=sqlite3.Row; c.execute('PRAGMA foreign_keys=ON'); return c

def init_db():
    with connect() as c:
        c.executescript(SCHEMA)
        if not c.execute('SELECT 1 FROM conversations LIMIT 1').fetchone(): c.execute("INSERT INTO conversations(title) VALUES('Nano AI')")
        c.commit()

def rows(sql,args=()):
    with connect() as c: return [dict(x) for x in c.execute(sql,args).fetchall()]

def one(sql,args=()):
    with connect() as c:
        x=c.execute(sql,args).fetchone(); return dict(x) if x else None

def run(sql,args=()):
    with connect() as c:
        cur=c.execute(sql,args); c.commit(); return cur.lastrowid
