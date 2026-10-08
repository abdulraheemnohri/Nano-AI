from .db import rows, run

BUILTINS = [
    ("conversation", "Conversation", "Natural conversation, clarification and tone.", "Be a helpful conversational partner. Ask a brief clarifying question when needed."),
    ("learning", "Learning", "Extract and organize durable knowledge.", "When the user explicitly teaches something, identify the durable fact and avoid inventing details."),
    ("reasoning", "Reasoning", "Step-by-step reasoning with concise conclusions.", "Reason carefully, state assumptions, and check calculations."),
    ("urdu", "Urdu", "Urdu and Roman Urdu conversation.", "Reply in the language requested by the user; support Urdu and Roman Urdu naturally."),
    ("writing", "Writing", "Draft and improve text.", "Produce clear, polished writing while preserving the user intent."),
    ("summary", "Summarization", "Compact summaries of supplied text.", "Summarize supplied material faithfully without adding unsupported facts."),
]

def seed():
    for name, title, description, prompt in BUILTINS:
        run("INSERT OR IGNORE INTO skills(name,description,version,prompt) VALUES(?,?,1,?)", (name, description, prompt))

def list_all():
    return rows("SELECT * FROM skills ORDER BY name")

def list_skills():
    return list_all()

def active_prompts():
    return "\\n".join("- " + item["prompt"] for item in rows("SELECT * FROM skills WHERE enabled=1 ORDER BY name"))

def set_enabled(name, enabled):
    if not rows("SELECT id FROM skills WHERE name=?", (name,)):
        raise ValueError("Skill not found")
    run("UPDATE skills SET enabled=?,updated_at=CURRENT_TIMESTAMP WHERE name=?", (1 if enabled else 0, name))

def propose(name, description, prompt):
    return run("INSERT INTO skill_proposals(name,description,prompt) VALUES(?,?,?)", (name, description, prompt))

def proposals():
    return rows("SELECT * FROM skill_proposals WHERE status='pending' ORDER BY id DESC")

def accept(pid):
    proposal = rows("SELECT * FROM skill_proposals WHERE id=? AND status='pending'", (pid,))
    if not proposal:
        return False
    item = proposal[0]
    run("INSERT INTO skills(name,description,version,prompt) VALUES(?,?,1,?) ON CONFLICT(name) DO UPDATE SET version=version+1,description=excluded.description,prompt=excluded.prompt,updated_at=CURRENT_TIMESTAMP", (item["name"], item["description"], item["prompt"]))
    run("UPDATE skill_proposals SET status='accepted' WHERE id=?", (pid,))
    return True

def reject(pid):
    run("UPDATE skill_proposals SET status='rejected' WHERE id=? AND status='pending'", (pid,))
