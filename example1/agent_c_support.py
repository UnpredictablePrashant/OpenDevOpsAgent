from __future__ import annotations

import re
import uuid
from typing import Any, Dict

from fastapi import FastAPI
from pydantic import BaseModel

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

MCP_URL = "http://127.0.0.1:8000/mcp"

app = FastAPI(title="Example1-AgentC-Support")


class A2ARequest(BaseModel):
    jsonrpc: str
    id: str
    method: str
    params: Dict[str, Any]


def _extract_text(params: Dict[str, Any]) -> str:
    msg = (params or {}).get("message", {}) or {}
    for p in (msg.get("parts", []) or []):
        if p.get("kind") == "text" and p.get("text"):
            return p["text"]
    return ""


def _pick_str(text: str, key: str, default: str) -> str:
    m = re.search(rf"{key}\s*=\s*([A-Za-z][A-Za-z0-9_-]*)", text, re.IGNORECASE)
    return m.group(1) if m else default


def _pick_int(text: str, key: str, default: int) -> int:
    m = re.search(rf"{key}\s*=\s*(-?\d+)", text, re.IGNORECASE)
    return int(m.group(1)) if m else default


def _extract_json_content(result: Any) -> Dict[str, Any]:
    for item in (getattr(result, "content", None) or []):
        if getattr(item, "type", None) == "json" and isinstance(getattr(item, "json", None), dict):
            return item.json
    return {}


def _extract_resource_text(resource_result: Any) -> str:
    for item in (getattr(resource_result, "contents", None) or []):
        text = getattr(item, "text", None)
        if text:
            return text
    return ""


@app.post("/a2a/support")
async def a2a_support(req: A2ARequest):
    if req.method != "message/send":
        return {"jsonrpc": "2.0", "id": req.id, "error": {"code": -32601, "message": "Method not supported"}}

    text = _extract_text(req.params)
    customer = _pick_str(text, "customer", "Unknown")
    open_tickets = _pick_int(text, "tickets", -1)
    sla_breaches = _pick_int(text, "breaches", -1)

    if open_tickets < 0 or sla_breaches < 0:
        answer = (
            "[AgentC-Support] Missing support inputs. "
            "Provide: customer=<name> tickets=<int> breaches=<int>."
        )
    else:
        async with streamable_http_client(MCP_URL) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                risk_raw = await session.call_tool(
                    "assess_support_priority",
                    {"open_tickets": open_tickets, "sla_breaches": sla_breaches},
                )
                risk = _extract_json_content(risk_raw)
                priority = str(risk.get("priority", "P3"))
                score = risk.get("risk_score", 0)

                playbook_raw = await session.read_resource(f"playbook://{priority}")
                playbook = _extract_resource_text(playbook_raw)
                customer_raw = await session.read_resource(f"customer://{customer}")
                customer_profile = _extract_resource_text(customer_raw)

        answer = (
            f"[AgentC-Support] Support triage for {customer}: priority={priority}, risk_score={score}. "
            f"profile={customer_profile}. playbook={playbook}"
        )

    msg = req.params.get("message", {}) or {}
    context_id = msg.get("contextId") or str(uuid.uuid4())
    return {
        "jsonrpc": "2.0",
        "id": req.id,
        "result": {
            "contextId": context_id,
            "id": str(uuid.uuid4()),
            "artifacts": [{"parts": [{"kind": "text", "text": answer}]}],
        },
    }
