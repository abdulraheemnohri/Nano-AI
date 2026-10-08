from . import config
from .db import init_db
from .learning import learn_from_text
from .memory import search as search_memory
from .model import chat
from .settings import bool_value, int_value
from .skills import active_prompts

def initialize():
    init_db()

def build_context(query):
    ms=search_memory(query, int_value("memory_limit", 6))
    mt="\n".join("- "+m["content"] for m in ms)
    sp=active_prompts()
    return "\n\n".join(x for x in ["Relevant memory:\n"+mt if mt else "", "Active skills:\n"+sp if sp else ""] if x)

def respond(conversation_id,user_text):
    from .db import rows,run
    if not rows("SELECT id FROM conversations WHERE id=?",(conversation_id,)):
        raise ValueError("Conversation not found")
    history=rows("SELECT role,content FROM messages WHERE conversation_id=? ORDER BY id DESC LIMIT ?",(conversation_id,int_value("max_history",12)))
    history.reverse()
    answer=chat(history,user_text,build_context(user_text))
    run("INSERT INTO messages(conversation_id,role,content) VALUES(?,?,?)",(conversation_id,"user",user_text))
    run("INSERT INTO messages(conversation_id,role,content) VALUES(?,?,?)",(conversation_id,"assistant",answer))
    run("UPDATE conversations SET updated_at=CURRENT_TIMESTAMP WHERE id=?",(conversation_id,))
    if bool_value("learning_enabled", config.LEARNING_ENABLED): learn_from_text(user_text)
    return answer
