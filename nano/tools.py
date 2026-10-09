"""Small, local-only, allowlisted tools for Nano AI.

Tools never execute shell commands, arbitrary Python, browser actions, or network requests.
"""
import ast
import math
import operator
import re
from datetime import datetime, timezone
from .db import run
from .memory import search as search_memory
from .knowledge import recent

MAX_INPUT_CHARS = 4000
MAX_EXPR_NODES = 100
BINOPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod, ast.Pow: operator.pow,
}
UNARYOPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}

TOOL_SPECS = [
    {"name": "calculator", "description": "Evaluate basic arithmetic expressions; supports +, -, *, /, //, %, ** and parentheses.", "input": {"expression": "string"}},
    {"name": "datetime_now", "description": "Return current system date and time with timezone information.", "input": {}},
    {"name": "unit_convert", "description": "Convert common length, mass, temperature, and digital-storage units.", "input": {"value": "number", "from_unit": "string", "to_unit": "string"}},
    {"name": "text_stats", "description": "Count characters, words, lines, and sentences in supplied text.", "input": {"text": "string"}},
    {"name": "memory_search", "description": "Search saved personal memories by keyword.", "input": {"query": "string"}},
    {"name": "knowledge_search", "description": "Search imported local knowledge by keyword.", "input": {"query": "string"}},
]
CONVERSIONS = {
    "length": {"m": 1, "meter": 1, "meters": 1, "km": 1000, "kilometer": 1000, "kilometers": 1000, "cm": .01, "mm": .001, "mi": 1609.344, "mile": 1609.344, "miles": 1609.344, "ft": .3048, "feet": .3048, "in": .0254, "inch": .0254, "inches": .0254},
    "mass": {"kg": 1, "kilogram": 1, "kilograms": 1, "g": .001, "gram": .001, "grams": .001, "mg": .000001, "lb": .45359237, "lbs": .45359237, "pound": .45359237, "oz": .028349523125},
    "digital": {"b": 1, "byte": 1, "bytes": 1, "kb": 1000, "mb": 1000000, "gb": 1000000000, "tb": 1000000000000, "kib": 1024, "mib": 1048576, "gib": 1073741824},
}


def list_tools():
    from .settings import get_all
    settings = get_all()
    return [{**tool, "enabled": settings.get("tool_enabled_" + tool["name"], "true").lower() in {"true", "1", "yes", "on"}} for tool in TOOL_SPECS]


def set_enabled(name, enabled):
    from .settings import set_value
    if name not in {t["name"] for t in TOOL_SPECS}:
        raise ValueError("Unknown tool")
    set_value("tool_enabled_" + name, "true" if enabled else "false")
    return next(t for t in list_tools() if t["name"] == name)


def _number(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        value = node.value
    elif isinstance(node, ast.BinOp) and type(node.op) in BINOPS:
        left, right = _number(node.left), _number(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 100:
            raise ValueError("Exponent magnitude is limited to 100.")
        value = BINOPS[type(node.op)](left, right)
    elif isinstance(node, ast.UnaryOp) and type(node.op) in UNARYOPS:
        value = UNARYOPS[type(node.op)](_number(node.operand))
    else:
        raise ValueError("Expression contains unsupported syntax.")
    if not math.isfinite(float(value)) or abs(value) > 1e100:
        raise ValueError("Result is outside the supported numeric range.")
    return value


def calculator(expression):
    if not isinstance(expression, str) or not expression.strip() or len(expression) > 300:
        raise ValueError("Provide an arithmetic expression up to 300 characters.")
    try:
        tree = ast.parse(expression, mode="eval")
        if sum(1 for _ in ast.walk(tree)) > MAX_EXPR_NODES:
            raise ValueError("Expression is too complex.")
        result = _number(tree.body)
    except (SyntaxError, ZeroDivisionError, OverflowError) as exc:
        raise ValueError("Invalid arithmetic expression or undefined operation.") from exc
    return {"expression": expression, "result": result}


def unit_convert(value, from_unit, to_unit):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("value must be a finite number")
    source, target = from_unit.strip().lower(), to_unit.strip().lower()
    temps = {"c": "c", "°c": "c", "celsius": "c", "f": "f", "°f": "f", "fahrenheit": "f", "k": "k", "kelvin": "k"}
    if source in temps and target in temps:
        src, dst = temps[source], temps[target]
        celsius = value if src == "c" else (value - 32) * 5 / 9 if src == "f" else value - 273.15
        result = celsius if dst == "c" else celsius * 9 / 5 + 32 if dst == "f" else celsius + 273.15
        return {"value": value, "from_unit": from_unit, "to_unit": to_unit, "result": result}
    for units in CONVERSIONS.values():
        if source in units and target in units:
            result = value * units[source] / units[target]
            return {"value": value, "from_unit": from_unit, "to_unit": to_unit, "result": result}
    raise ValueError("Unsupported or incompatible units.")


def text_stats(text):
    if not isinstance(text, str) or len(text) > MAX_INPUT_CHARS:
        raise ValueError(f"text must be a string up to {MAX_INPUT_CHARS} characters")
    return {"characters": len(text), "characters_without_spaces": len(re.sub(r"\\s", "", text)), "words": len(re.findall(r"\\b\\w+\\b", text, re.UNICODE)), "lines": len(text.splitlines()) if text else 0, "sentences": len(re.findall(r"[.!?]+(?=\\s|$)", text))}


def run_tool(name, arguments):
    if not isinstance(arguments, dict):
        raise ValueError("Tool arguments must be an object.")
    spec = next((t for t in TOOL_SPECS if t["name"] == name), None)
    if spec is None:
        raise ValueError("Unknown tool")
    from .settings import get_all
    enabled = get_all().get("tool_enabled_" + name, "true").lower() in {"true", "1", "yes", "on"}
    if not enabled:
        raise PermissionError("This tool is disabled in settings.")
    if name == "calculator":
        result = calculator(arguments.get("expression", ""))
    elif name == "datetime_now":
        now = datetime.now().astimezone()
        result = {"iso": now.isoformat(), "timezone": str(now.tzinfo), "utc": datetime.now(timezone.utc).isoformat()}
    elif name == "unit_convert":
        result = unit_convert(arguments.get("value"), arguments.get("from_unit", ""), arguments.get("to_unit", ""))
    elif name == "text_stats":
        result = text_stats(arguments.get("text", ""))
    elif name == "memory_search":
        query = str(arguments.get("query", "")).strip()
        if not query or len(query) > 200:
            raise ValueError("query must contain 1-200 characters")
        result = search_memory(query, 20)
    elif name == "knowledge_search":
        query = str(arguments.get("query", "")).strip().lower()
        if not query or len(query) > 200:
            raise ValueError("query must contain 1-200 characters")
        result = [item for item in recent(200) if query in item.get("content", "").lower()][:20]
    else:
        raise ValueError("Tool not implemented")
    run("INSERT INTO learning_events(event_type,input_text,result) VALUES(?,?,?)", ("tool:" + name, str(arguments)[:MAX_INPUT_CHARS], str(result)[:MAX_INPUT_CHARS]))
    return {"tool": name, "result": result}
