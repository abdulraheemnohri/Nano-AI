import sqlite3
from contextlib import contextmanager
from .config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP,updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT,conversation_id INTEGER NOT NULL,role TEXT NOT NULL,content TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(conversation_id) REFERENCES conversations(id));
CREATE TABLE IF NOT EXISTS memories(id INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT NOT NULL,content TEXT NOT NULL,confidence REAL DEFAULT 0.5,status TEXT DEFAULT 'active',source TEXT DEFAULT 'conversation',created_at TEXT DEFAULT CURRENT_TIMESTAMP,updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS learning_events(id INTEGER PRIMARY KEY AUTOINCREMENT,event_type TEXT NOT NULL,input_text TEXT NOT NULL,result TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS skills(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT UNIQUE NOT NULL,description TEXT NOT NULL,version INTEGER DEFAULT 1,prompt TEXT NOT NULL,enabled INTEGER DEFAULT 1,created_at TEXT DEFAULT CURRENT_TIMESTAMP,updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS skill_proposals(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,description TEXT NOT NULL,prompt TEXT NOT NULL,status TEXT DEFAULT 'pending',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS response_feedback(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 conversation_id INTEGER NOT NULL,
 user_text TEXT NOT NULL,
 assistant_text TEXT NOT NULL,
 rating INTEGER NOT NULL CHECK(rating IN (-1,1)),
 correction TEXT NOT NULL DEFAULT '',
 created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_feedback_recent ON response_feedback(id DESC);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id,id);
CREATE INDEX IF NOT EXISTS idx_memories_active ON memories(status,confidence,updated_at);
CREATE INDEX IF NOT EXISTS idx_learning_events_created ON learning_events(id);
CREATE INDEX IF NOT EXISTS idx_skills_enabled ON skills(enabled,name);
"""

@contextmanager
def connect():
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA busy_timeout=10000")
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()

def init_db():
    with connect() as c:
        c.executescript(SCHEMA)
        if not c.execute("SELECT 1 FROM conversations LIMIT 1").fetchone():
            c.execute("INSERT INTO conversations(title) VALUES('Nano AI')")

def rows(sql, args=()):
    with connect() as c:
        return [dict(row) for row in c.execute(sql, args).fetchall()]

def one(sql, args=()):
    with connect() as c:
        row = c.execute(sql, args).fetchone()
        return dict(row) if row else None

def run(sql, args=()):
    with connect() as c:
        cursor = c.execute(sql, args)
        return cursor.lastrowid
