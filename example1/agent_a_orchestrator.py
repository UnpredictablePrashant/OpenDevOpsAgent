from __future__ import annotations

import asyncio
import uuid
from typing import Any, Dict

import aiohttp
from fastapi import FastAPI
from pydantic import BaseModel

AGENT_B_URL = "http://127.0.0.1:9102/a2a/finance"
AGENT_C_URL = "http://127.0.0.1:9103/a2a/support"

app = FastAPI(title="Example1-AgentA-Orchestrator")


class A2ARequest(BaseModel):
    jsonrpc: str
    id: str
    method: str
    params: Dict[str, Any]


def _extract_text(resp_json: Dict[str, Any]) -> str:
    result = (resp_json or {}).get("result", {}) or {}
    for art in (result.get("artifacts", []) or []):
        for part in (art.get("parts", []) or []):
            if part.get("kind") == "text" and part.get("text"):
                return part["text"]
    return "(no text)"


async def _call_agent(session: aiohttp.ClientSession, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "message/send",
        "params": params,
    }
    async with session.post(url, json=payload, timeout=20) as r:
        body_text = await r.text()
        if r.status != 200:
            return {"error": {"code": r.status, "message": body_text[:300]}}
        return await r.json()


@app.post("/a2a/orchestrator")
async def a2a_orchestrator(req: A2ARequest):
    if req.method != "message/send":
        return {"jsonrpc": "2.0", "id": req.id, "error": {"code": -32601, "message": "Method not supported"}}

    async with aiohttp.ClientSession() as session:
        b_resp, c_resp = await asyncio.gather(
            _call_agent(session, AGENT_B_URL, req.params),
            _call_agent(session, AGENT_C_URL, req.params),
        )

    b_text = _extract_text(b_resp) if "error" not in b_resp else f"[AgentB error] {b_resp['error']}"
    c_text = _extract_text(c_resp) if "error" not in c_resp else f"[AgentC error] {c_resp['error']}"

    final = (
        "[AgentA-Orchestrator] Customer Ops Automation Plan\n"
        "automation_steps:\n"
        "1) Run billing computation and draft invoice\n"
        "2) Run support triage and escalation policy\n"
        "3) Produce unified account action summary\n\n"
        f"billing_output: {b_text}\n"
        f"support_output: {c_text}"
    )

    msg = req.params.get("message", {}) if req.params else {}
    context_id = msg.get("contextId") or str(uuid.uuid4())
    return {
        "jsonrpc": "2.0",
        "id": req.id,
        "result": {
            "contextId": context_id,
            "id": str(uuid.uuid4()),
            "artifacts": [{"parts": [{"kind": "text", "text": final}]}],
        },
    }
