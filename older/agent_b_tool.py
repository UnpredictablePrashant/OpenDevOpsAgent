# agent_b_tool.py
import re
import uuid
from typing import Any, Dict, Optional, Tuple

from fastapi import FastAPI
from pydantic import BaseModel

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

MCP_URL = "http://127.0.0.1:8000/mcp"

app = FastAPI(title="AgentB-ToolAgent")

class A2ARequest(BaseModel):
    jsonrpc: str
    id: str
    method: str
    params: Dict[str, Any]

def _extract_text(params: Dict[str, Any]) -> str:
    msg = (params or {}).get("message", {}) or {}
    parts = msg.get("parts", []) or []
    for p in parts:
        if p.get("kind") == "text" and p.get("text"):
            return p["text"]
    return ""

def _extract_numbers_and_name(text: str) -> Tuple[Optional[int], Optional[int], str]:
    nums = [int(x) for x in re.findall(r"\b\d+\b", text)]
    a = nums[0] if len(nums) > 0 else None
    b = nums[1] if len(nums) > 1 else None

    # very simple name extraction: "greet <name>" or "name is <name>"
    name = "World"
    m = re.search(r"greet\s+([A-Za-z][A-Za-z0-9_-]*)", text, re.IGNORECASE)
    if m:
        name = m.group(1)
    else:
        m2 = re.search(r"name\s+is\s+([A-Za-z][A-Za-z0-9_-]*)", text, re.IGNORECASE)
        if m2:
            name = m2.group(1)

    return a, b, name

async def _call_mcp_add_and_greet(a: int, b: int, name: str) -> Tuple[int, str]:
    # Connect to MCP over Streamable HTTP
    async with streamable_http_client(MCP_URL) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            # Call tool: add
            add_result = await session.call_tool("add", {"a": a, "b": b})

            # The SDK returns content items; we used json_response=True, so often the value is in text/json form.
            # We'll best-effort parse it:
            total = None
            for item in (add_result.content or []):
                if getattr(item, "type", None) == "text":
                    # may be "42"
                    try:
                        total = int(item.text.strip())
                    except Exception:
                        pass
                if getattr(item, "type", None) == "json":
                    # may be {"result": 42} depending on server config
                    if isinstance(item.json, dict) and "result" in item.json:
                        total = int(item.json["result"])

            if total is None:
                # fallback: assume a+b
                total = a + b

            # Read resource: greeting://{name}
            res = await session.read_resource(f"greeting://{name}")
            greeting_text = ""
            for item in (res.contents or []):
                if getattr(item, "text", None):
                    greeting_text = item.text
                    break

            return total, greeting_text

@app.post("/a2a/{assistant_id}")
async def a2a_endpoint(assistant_id: str, req: A2ARequest):
    # Only implement message/send for the demo
    if req.method != "message/send":
        return {
            "jsonrpc": "2.0",
            "id": req.id,
            "error": {"code": -32601, "message": f"Method not supported: {req.method}"},
        }

    msg = req.params.get("message", {}) if req.params else {}
    context_id = msg.get("contextId") or str(uuid.uuid4())

    user_text = _extract_text(req.params)
    a, b, name = _extract_numbers_and_name(user_text)

    if a is None or b is None:
        answer = "Send me two numbers in the message (e.g., 'compute 12 30 and greet Prashant')."
    else:
        total, greet = await _call_mcp_add_and_greet(a, b, name)
        answer = f"[AgentB:{assistant_id}] MCP says: {a}+{b}={total}. Also: {greet}"

    return {
        "jsonrpc": "2.0",
        "id": req.id,
        "result": {
            "contextId": context_id,
            "id": str(uuid.uuid4()),  # task id (simplified)
            "artifacts": [
                {
                    "parts": [{"kind": "text", "text": answer}]
                }
            ],
        },
    }