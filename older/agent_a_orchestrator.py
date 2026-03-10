# agent_a_orchestrator.py
import uuid
from typing import Any, Dict

import aiohttp
from fastapi import FastAPI
from pydantic import BaseModel

AGENT_B_URL = "http://127.0.0.1:9002/a2a/tool-agent"

app = FastAPI(title="AgentA-Orchestrator")

class A2ARequest(BaseModel):
    jsonrpc: str
    id: str
    method: str
    params: Dict[str, Any]

def _extract_text_from_result(resp_json: Dict[str, Any]) -> str:
    # Best-effort extraction similar to common A2A patterns
    result = (resp_json or {}).get("result", {}) or {}
    for art in (result.get("artifacts", []) or []):
        for part in (art.get("parts", []) or []):
            if part.get("kind") == "text" and part.get("text"):
                return part["text"]
    return "(no text)"

@app.post("/a2a/{assistant_id}")
async def a2a_endpoint(assistant_id: str, req: A2ARequest):
    if req.method != "message/send":
        return {
            "jsonrpc": "2.0",
            "id": req.id,
            "error": {"code": -32601, "message": f"Method not supported: {req.method}"},
        }

    # Forward the exact message to Agent B (A2A → A2A)
    payload_to_b = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "message/send",
        "params": req.params,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(AGENT_B_URL, json=payload_to_b) as r:
            b_resp = await r.json()

    text = _extract_text_from_result(b_resp)

    # Respond back to caller
    return {
        "jsonrpc": "2.0",
        "id": req.id,
        "result": {
            "contextId": (b_resp.get("result", {}) or {}).get("contextId"),
            "id": str(uuid.uuid4()),
            "artifacts": [{"parts": [{"kind": "text", "text": f"[AgentA:{assistant_id}] Delegated to AgentB. Result: {text}"}]}],
        },
    }