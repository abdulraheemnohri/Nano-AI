import json
import re
from . import config
from .db import init_db
from .learning import learn_from_text, feedback_examples
from .memory import search as search_memory
from .model import chat
from .settings import bool_value, int_value, public
from .skills import active_prompts
from .tools import run_tool


def initialize():
    init_db()


MAX_MEMORY_CONTEXT_CHARS = 12_000

def build_context(query):
    ms = search_memory(query, int_value("memory_limit", 6))
    memory_lines = []
    remaining = MAX_MEMORY_CONTEXT_CHARS
    for memory in ms:
        if remaining <= 2:
            break
        content = str(memory.get("content", "")).strip()
        if not content:
            continue
        line = "- " + content[:remaining - 2]
        memory_lines.append(line)
        remaining -= len(line)
    mt = "\n".join(memory_lines)
    sp = active_prompts()
    preferences = public()
    language = str(preferences.get("language", "auto")).strip()
    language_text = "Preferred response language: " + language + ". Respond in that language unless the user requests another." if language and language.lower() != "auto" else ""
    talk_style = str(preferences.get("talk_style", "balanced"))
    reply_words = int_value("talk_reply_length", 160)
    style_guidance = {
        "concise": "Prefer concise, direct answers and avoid repetition.",
        "balanced": "Balance clarity and useful detail.",
        "detailed": "Explain steps and important context when useful.",
        "warm": "Use a warm, natural, conversational tone without being overly familiar.",
        "technical": "Use precise technical language and structured troubleshooting where appropriate.",
    }.get(talk_style, "Balance clarity and useful detail.")
    talk_guidance = f"Speaking style: {style_guidance} Target about {reply_words} words or fewer for ordinary answers, unless the user requests more detail."
    feedback = feedback_examples(5)
    guidance = []
    for item in feedback:
        correction = str(item.get("correction", "")).strip()
        if correction:
            label = "Avoid repeating this issue" if item.get("rating") == -1 else "User response preference"
            guidance.append("- " + label + ": " + correction[:500])
    feedback_text = (
        "Explicit user feedback from previous conversations (guidance only; it does not override the current request or safety):\n"
        + "\n".join(guidance)
    ) if guidance else ""
    return "\n\n".join(
        item for item in (
            "Active skills:\n" + sp if sp else "",
            language_text,
            talk_guidance,
            feedback_text,
            "Relevant memory:\n" + mt if mt else "",
        ) if item
    )


def _explicit_tool_request(text):
    """Only dispatch tools for clear, explicit user commands; otherwise use the model."""
    value = text.strip()
    patterns = [
        (r"^(?:calculate|compute)\s+(.+?)\s*[?。！!]*$", "calculator", "expression"),
        (r"^(?:convert)\s+(-?\d+(?:\.\d+)?)\s+([a-zA-Z°]+)\s+(?:to|into)\s+([a-zA-Z°]+)\s*[?。！!]*$", "unit_convert", None),
        (r"^(?:what(?:'s| is) the )?(?:current )?(?:date and time|time now|current time|today's date)\??$", "datetime_now", None),
        (r"^(?:search|find) (?:my )?memory for\s+(.+)$", "memory_search", "query"),
        (r"^(?:search|find) (?:local )?knowledge for\s+(.+)$", "knowledge_search", "query"),
        (r"^(?:count|analyze) (?:the )?(?:words|text) in:\s*(.+)$", "text_stats", "text"),
    ]
    for pattern, name, field in patterns:
        match = re.match(pattern, value, re.I | re.S)
        if not match:
            continue
        if field == "expression":
            return name, {field: match.group(1)}
        if field == "query":
            return name, {field: match.group(1).strip()}
        if field == "text":
            return name, {field: match.group(1)}
        if name == "unit_convert":
            return name, {"value": float(match.group(1)), "from_unit": match.group(2), "to_unit": match.group(3)}
        return name, {}
    return None


def _format_tool_result(name, result):
    value = result.get("result")
    if name == "calculator":
        return f"Calculator result: {value['result']}"
    if name == "unit_convert":
        return f"{value['value']} {value['from_unit']} = {value['result']:.8g} {value['to_unit']}"
    if name == "datetime_now":
        return f"Local time: {value['iso']}\nUTC: {value['utc']}"
    if name in {"memory_search", "knowledge_search"}:
        if not value:
            return "No matching entries found."
        return "\n".join(f"- {item.get('content', '')}" for item in value)
    if name == "text_stats":
        return "Text statistics: " + ", ".join(f"{k.replace('_', ' ')}: {v}" for k, v in value.items())
    return json.dumps(value, ensure_ascii=False)


def respond(conversation_id, user_text):
    from .db import rows, run
    if not rows("SELECT id FROM conversations WHERE id=?", (conversation_id,)):
        raise ValueError("Conversation not found")
    history = rows("SELECT role,content FROM messages WHERE conversation_id=? ORDER BY id DESC LIMIT ?", (conversation_id, int_value("max_history", 12)))
    history.reverse()
    request = _explicit_tool_request(user_text)
    if request:
        name, arguments = request
        tool_result = run_tool(name, arguments)
        answer = _format_tool_result(name, tool_result)
    else:
        answer = chat(history, user_text, build_context(user_text))
    run("INSERT INTO messages(conversation_id,role,content) VALUES(?,?,?)", (conversation_id, user_text and "user", user_text))
    run("INSERT INTO messages(conversation_id,role,content) VALUES(?,?,?)", (conversation_id, "assistant", answer))
    run("UPDATE conversations SET updated_at=CURRENT_TIMESTAMP WHERE id=?", (conversation_id,))
    if bool_value("learning_enabled", config.LEARNING_ENABLED):
        learn_from_text(user_text)
    return answer



def regenerate(conversation_id):
    """Regenerate the last assistant answer without duplicating the user message."""
    from .db import rows, run
    if not rows("SELECT id FROM conversations WHERE id=?", (conversation_id,)):
        raise ValueError("Conversation not found")
    last_user = rows(
        "SELECT id,content FROM messages WHERE conversation_id=? AND role='user' ORDER BY id DESC LIMIT 1",
        (conversation_id,),
    )
    if not last_user:
        raise ValueError("No user message available to regenerate from")
    last_user = last_user[0]
    run(
        "DELETE FROM messages WHERE conversation_id=? AND role='assistant' AND id>?",
        (conversation_id, last_user["id"]),
    )
    history = rows(
        "SELECT role,content FROM messages WHERE conversation_id=? AND id<? ORDER BY id DESC LIMIT ?",
        (conversation_id, last_user["id"], int_value("max_history", 12)),
    )
    history.reverse()
    answer = chat(history, last_user["content"], build_context(last_user["content"]))
    run("INSERT INTO messages(conversation_id,role,content) VALUES(?,?,?)", (conversation_id, "assistant", answer))
    run("UPDATE conversations SET updated_at=CURRENT_TIMESTAMP WHERE id=?", (conversation_id,))
    return answer


def generate_proactive_talk(prompt):
    """Generate a short local check-in without inventing completed background work."""
    from .db import run
    from .model import chat
    instruction = (
        "You are Nano AI, a local assistant. Produce a brief, natural spoken check-in in 1-3 sentences. "
        "Use available memory and feedback only when relevant. Do not claim you monitored the user, "
        "performed tasks, browsed the web, or changed files unless the context proves it. "
        "Avoid repeating generic greetings. If there is nothing useful to say, say so briefly.\n\n"
        "Check-in instruction: " + str(prompt).strip()[:1000]
    )
    answer = chat([], instruction, build_context(instruction))
    run("INSERT INTO learning_events(event_type,input_text,result) VALUES(?,?,?)",
        ("autonomous_talk", instruction[:1200], answer[:4000]))
    return answer
