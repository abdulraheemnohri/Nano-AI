"""Minimal MCP-style JSON-RPC dispatcher exposing only Nano's allowlisted tools."""
import json
from .tools import list_tools, run_tool

def handle_message(message):
    if not isinstance(message,dict): return {"jsonrpc":"2.0","id":None,"error":{"code":-32600,"message":"Invalid Request"}}
    request_id=message.get("id")
    if message.get("jsonrpc")!="2.0" or not isinstance(message.get("method"),str):
        return {"jsonrpc":"2.0","id":request_id,"error":{"code":-32600,"message":"Invalid Request"}}
    method=message["method"]
    if method=="initialize":
        result={"protocolVersion":message.get("params",{}).get("protocolVersion","2024-11-05"),
                "capabilities":{"tools":{}},"serverInfo":{"name":"nano-ai","version":"0.6.0"}}
    elif method=="notifications/initialized":
        return None
    elif method=="ping": result={}
    elif method=="tools/list":
        result={"tools":[{"name":t["name"],"description":t["description"],"inputSchema":{"type":"object","properties":{k:{"type":"string" if v=="string" else "number"} for k,v in t["input"].items()},"additionalProperties":False}} for t in list_tools() if t["enabled"]]}
    elif method=="tools/call":
        params=message.get("params") or {}
        name=params.get("name")
        arguments=params.get("arguments",{})
        try:
            outcome=run_tool(name,arguments)
            result={"content":[{"type":"text","text":json.dumps(outcome,ensure_ascii=False)}],"isError":False}
        except Exception as exc:
            result={"content":[{"type":"text","text":str(exc)[:1000]}],"isError":True}
    else:
        return {"jsonrpc":"2.0","id":request_id,"error":{"code":-32601,"message":"Method not found"}}
    return {"jsonrpc":"2.0","id":request_id,"result":result}
