from __future__ import annotations

import re
import uuid
from typing import Any, Dict

from fastapi import FastAPI
from pydantic import BaseModel

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

MCP_URL = "http://127.0.0.1:8000/mcp"

app = FastAPI(title="Example1-AgentB-Finance")


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


def _pick_float(text: str, key: str, default: float) -> float:
    m = re.search(rf"{key}\s*=\s*(-?\d+(?:\.\d+)?)", text, re.IGNORECASE)
    return float(m.group(1)) if m else default


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


@app.post("/a2a/finance")
async def a2a_finance(req: A2ARequest):
    if req.method != "message/send":
        return {"jsonrpc": "2.0", "id": req.id, "error": {"code": -32601, "message": "Method not supported"}}

    text = _extract_text(req.params)
    customer = _pick_str(text, "customer", "Unknown")
    usage_units = _pick_int(text, "usage", 0)
    unit_price = _pick_float(text, "unit_price", 0.0)
    discount_pct = _pick_float(text, "discount", 0.0)

    if usage_units <= 0 or unit_price <= 0:
        answer = (
            "[AgentB-Finance] Missing billing inputs. "
            "Provide: customer=<name> usage=<int> unit_price=<float> discount=<float>."
        )
    else:
        async with streamable_http_client(MCP_URL) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                invoice_raw = await session.call_tool(
                    "calculate_invoice",
                    {
                        "usage_units": usage_units,
                        "unit_price": unit_price,
                        "discount_pct": discount_pct,
                    },
                )
                invoice = _extract_json_content(invoice_raw)
                customer_raw = await session.read_resource(f"customer://{customer}")
                customer_profile = _extract_resource_text(customer_raw)

        total = invoice.get("total")
        discount_amount = invoice.get("discount_amount")
        answer = (
            f"[AgentB-Finance] Invoice ready for {customer}: total={total}, discount_amount={discount_amount}. "
            f"profile={customer_profile}. action=Create invoice draft + send for finance approval."
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
