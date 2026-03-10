# agent_a.py
from __future__ import annotations

import json
import os
import uuid
from typing import Any, Dict, List

import aiohttp

from a2a.server.apps.jsonrpc.fastapi_app import A2AFastAPI
from a2a.server.request_handlers.default_request_handler import DefaultRequestHandler
from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore
from a2a.server.events.in_memory_queue_manager import InMemoryQueueManager
from a2a.server.agent_execution.agent_executor import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue

from a2a.types import AgentCard, AgentCapabilities, AgentSkill
from a2a.utils.message import new_agent_text_message


# -------------------------
# Config
# -------------------------
AGENT_B_BASE_URL = os.getenv("AGENT_B_BASE_URL", "http://127.0.0.1:8002").rstrip("/")
AGENT_B_RPC_PATH = os.getenv("AGENT_B_RPC_PATH", "").strip()


def _extract_text_from_response(resp_json: Dict[str, Any]) -> str:
    result = (resp_json or {}).get("result", {}) or {}
    for art in (result.get("artifacts", []) or []):
        for part in (art.get("parts", []) or []):
            if part.get("kind") == "text" and part.get("text"):
                return part["text"]
    return ""


def _extract_user_text_from_params(params: Dict[str, Any]) -> str:
    msg = (params or {}).get("message", {}) or {}
    for part in (msg.get("parts", []) or []):
        if part.get("kind") == "text" and part.get("text"):
            return part["text"]
    return ""


def _candidate_b_rpc_urls() -> List[str]:
    paths: List[str] = []
    if AGENT_B_RPC_PATH:
        path = AGENT_B_RPC_PATH if AGENT_B_RPC_PATH.startswith("/") else f"/{AGENT_B_RPC_PATH}"
        paths.append(path)
    paths.extend(["/", "/a2a", "/a2a/tool-agent"])

    urls: List[str] = []
    seen = set()
    for path in paths:
        url = f"{AGENT_B_BASE_URL}{path}" if path != "/" else f"{AGENT_B_BASE_URL}/"
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


# -------------------------
# Agent A (Orchestrator)
# -------------------------
class OrchestratorAgent(AgentExecutor):
    def __init__(self) -> None:
        self._resolved_b_url: str | None = None

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        user_text = ""
        if context.message and context.message.parts:
            first = context.message.parts[0]
            user_text = getattr(first, "text", "") or ""

        try:
            b_reply_text = await self._call_agent_b(user_text)
            reply = f"Agent A orchestrated → Agent B replied: {b_reply_text}"
        except Exception as e:
            reply = f"Agent A error while calling Agent B: {type(e).__name__}: {e}"

        await event_queue.enqueue_event(new_agent_text_message(reply))
        await event_queue.close()

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        await event_queue.close(immediate=True)

    async def _call_agent_b(self, user_text: str) -> str:
        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "message/send",
            "params": {
                "message": {
                    "role": "user",
                    "parts": [{"kind": "text", "text": user_text}],
                }
            },
        }

        urls = _candidate_b_rpc_urls()
        if self._resolved_b_url and self._resolved_b_url in urls:
            urls = [self._resolved_b_url] + [u for u in urls if u != self._resolved_b_url]

        errors = []
        async with aiohttp.ClientSession() as session:
            for url in urls:
                try:
                    async with session.post(url, json=payload, timeout=10) as r:
                        body_text = await r.text()
                        if r.status != 200:
                            errors.append(f"{url} -> HTTP {r.status}: {body_text[:120]}")
                            continue
                        try:
                            data = json.loads(body_text)
                        except json.JSONDecodeError:
                            data = await r.json()

                    if "error" in data:
                        errors.append(f"{url} -> JSON-RPC error: {data['error']}")
                        continue

                    text = _extract_text_from_response(data)
                    if text:
                        self._resolved_b_url = url
                        return text
                    errors.append(f"{url} -> no text artifact in response")
                except Exception as exc:
                    errors.append(f"{url} -> {type(exc).__name__}: {exc}")

        raise RuntimeError(" | ".join(errors) if errors else "No Agent B endpoint responded")


def build_agent_card(base_url: str) -> AgentCard:
    return AgentCard(
        name="Agent A (Orchestrator)",
        description="Delegates requests to Agent B via A2A; Agent B can call MCP tools/resources.",
        url=base_url,
        version="0.1.0",
        capabilities=AgentCapabilities(streaming=True, push_notifications=False),
        default_input_modes=["text"],
        default_output_modes=["text"],
        skills=[
            AgentSkill(
                id="delegate",
                name="Delegate",
                description="Delegates the message to Agent B and returns its response.",
                tags=["demo", "orchestrator", "a2a"],
                examples=["hello", "compute 12 30 and greet Shashank"],
                inputModes=["text"],
                outputModes=["text"],
            )
        ],
    )


# --- wire everything (same pattern as Agent B) ---
agent_executor = OrchestratorAgent()
task_store = InMemoryTaskStore()
queue_manager = InMemoryQueueManager()

handler = DefaultRequestHandler(
    agent_executor=agent_executor,
    task_store=task_store,
    queue_manager=queue_manager,
)

a2a_app = A2AFastAPI(
    agent_card=build_agent_card("http://127.0.0.1:8001"),
    handler=handler,
)

# Export ASGI app (same version-safe pattern as your Agent B)
if hasattr(a2a_app, "app"):
    app = a2a_app.app
elif hasattr(a2a_app, "asgi_app"):
    app = a2a_app.asgi_app
elif hasattr(a2a_app, "get_app"):
    app = a2a_app.get_app()
else:
    app = a2a_app


# Compatibility route for the older demo client that calls /a2a/{assistant_id}.
if hasattr(app, "post"):
    @app.post("/a2a/{assistant_id}")
    async def compat_a2a_endpoint(assistant_id: str, req: Dict[str, Any]):
        req_id = req.get("id")
        if req.get("method") != "message/send":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Method not supported: {req.get('method')}"},
            }

        params = (req.get("params") or {}) if isinstance(req, dict) else {}
        user_text = _extract_user_text_from_params(params)

        try:
            b_reply = await agent_executor._call_agent_b(user_text)
            out_text = f"[AgentA:{assistant_id}] Delegated to AgentB. Result: {b_reply}"
        except Exception as exc:
            out_text = f"[AgentA:{assistant_id}] Failed to call AgentB: {type(exc).__name__}: {exc}"

        msg = (params.get("message") or {}) if isinstance(params, dict) else {}
        context_id = msg.get("contextId") or str(uuid.uuid4())
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "contextId": context_id,
                "id": str(uuid.uuid4()),
                "artifacts": [{"parts": [{"kind": "text", "text": out_text}]}],
            },
        }
