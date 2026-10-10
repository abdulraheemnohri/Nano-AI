"""Minimal MCP-style JSON-RPC dispatcher exposing only Nano's allowlisted tools."""
import json

from .tools import list_tools, run_tool


def _error(request_id, code, message):
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def handle_message(message):
    if not isinstance(message, dict):
        return _error(None, -32600, "Invalid Request")

    request_id = message.get("id")
    if message.get("jsonrpc") != "2.0" or not isinstance(message.get("method"), str):
        return _error(request_id, -32600, "Invalid Request")

    # This dispatcher implements named MCP parameters, which must be objects.
    # Reject malformed values explicitly instead of letting .get() raise a 500.
    params = message.get("params", {})
    if not isinstance(params, dict):
        return _error(request_id, -32602, "Invalid params")

    method = message["method"]
    if method == "initialize":
        protocol_version = params.get("protocolVersion", "2024-11-05")
        if not isinstance(protocol_version, str):
            return _error(request_id, -32602, "protocolVersion must be a string")
        result = {
            "protocolVersion": protocol_version,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "nano-ai", "version": "0.5.0"},
        }
    elif method == "notifications/initialized":
        return None
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {
            "tools": [
                {
                    "name": tool["name"],
                    "description": tool["description"],
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            key: {"type": "string" if value == "string" else "number"}
                            for key, value in tool["input"].items()
                        },
                        "additionalProperties": False,
                    },
                }
                for tool in list_tools()
                if tool["enabled"]
            ]
        }
    elif method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments", {})
        if not isinstance(name, str) or not name.strip():
            return _error(request_id, -32602, "tools/call requires a non-empty string name")
        if not isinstance(arguments, dict):
            return _error(request_id, -32602, "tools/call arguments must be an object")
        try:
            outcome = run_tool(name, arguments)
            result = {
                "content": [{"type": "text", "text": json.dumps(outcome, ensure_ascii=False)}],
                "isError": False,
            }
        except Exception as exc:
            result = {
                "content": [{"type": "text", "text": str(exc)[:1000]}],
                "isError": True,
            }
    else:
        return _error(request_id, -32601, "Method not found")

    return {"jsonrpc": "2.0", "id": request_id, "result": result}
