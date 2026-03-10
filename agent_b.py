from __future__ import annotations

import os
import re
import uuid
from typing import Any, Dict, Optional, Tuple

from a2a.server.agent_execution.agent_executor import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.apps.jsonrpc.fastapi_app import A2AFastAPI
from a2a.server.events.event_queue import EventQueue
from a2a.server.events.in_memory_queue_manager import InMemoryQueueManager
from a2a.server.request_handlers.default_request_handler import DefaultRequestHandler
from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from a2a.utils.message import new_agent_text_message
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

MCP_URL = os.getenv("MCP_URL", "http://127.0.0.1:8000/mcp")


def _extract_text_from_parts(parts: Any) -> str:
    for part in parts or []:
        if isinstance(part, dict):
            if part.get("kind") == "text" and part.get("text"):
                return part["text"]
            continue
        text = getattr(part, "text", "") or ""
        if text:
            return text
    return ""


def _extract_numbers_and_name(text: str) -> Tuple[Optional[int], Optional[int], str]:
    nums = [int(x) for x in re.findall(r"\b\d+\b", text)]
    a = nums[0] if len(nums) > 0 else None
    b = nums[1] if len(nums) > 1 else None

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
    async with streamable_http_client(MCP_URL) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            add_result = await session.call_tool("add", {"a": a, "b": b})
            total: Optional[int] = None
            for item in (add_result.content or []):
                if getattr(item, "type", None) == "text":
                    try:
                        total = int(item.text.strip())
                    except Exception:
                        pass
                if getattr(item, "type", None) == "json":
                    if isinstance(item.json, dict) and "result" in item.json:
                        total = int(item.json["result"])
            if total is None:
                total = a + b

            res = await session.read_resource(f"greeting://{name}")
            greeting_text = ""
            for item in (res.contents or []):
                if getattr(item, "text", None):
                    greeting_text = item.text
                    break

            return total, greeting_text


async def _build_reply(user_text: str, assistant_id: str) -> str:
    a, b, name = _extract_numbers_and_name(user_text)
    if a is None or b is None:
        return (
            f"[AgentB:{assistant_id}] I am MCP-enabled. "
            "Send two numbers and a name, e.g. 'compute 12 30 and greet Shashank'."
        )
    try:
        total, greet = await _call_mcp_add_and_greet(a, b, name)
        return f"[AgentB:{assistant_id}] MCP says: {a}+{b}={total}. Also: {greet}"
    except Exception as exc:
        return f"[AgentB:{assistant_id}] MCP call failed: {type(exc).__name__}: {exc}"


class ToolAgent(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        user_text = _extract_text_from_parts(getattr(context.message, "parts", None))
        reply = await _build_reply(user_text, "sdk")

        await event_queue.enqueue_event(new_agent_text_message(reply))
        await event_queue.close()

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        await event_queue.close(immediate=True)


def build_agent_card(base_url: str) -> AgentCard:
    return AgentCard(
        name="Agent B (Tool Agent)",
        description="A2A worker that calls MCP tools/resources and returns computed output.",
        url=base_url,
        version="0.2.0",
        capabilities=AgentCapabilities(streaming=True, push_notifications=False),
        default_input_modes=["text"],
        default_output_modes=["text"],
        skills=[
            AgentSkill(
                id="compute_greet",
                name="Compute And Greet",
                description="Extract numbers/name, call MCP add and greeting resource, return result.",
                tags=["demo", "mcp", "tool-agent"],
                examples=["compute 12 30 and greet Shashank", "add 5 7 and name is Alex"],
                inputModes=["text"],
                outputModes=["text"],
            )
        ],
    )


agent_executor = ToolAgent()
task_store = InMemoryTaskStore()
queue_manager = InMemoryQueueManager()

handler = DefaultRequestHandler(
    agent_executor=agent_executor,
    task_store=task_store,
    queue_manager=queue_manager,
)

a2a_app = A2AFastAPI(
    agent_card=build_agent_card("http://127.0.0.1:8002"),
    handler=handler,
)

if hasattr(a2a_app, "app"):
    app = a2a_app.app
elif hasattr(a2a_app, "asgi_app"):
    app = a2a_app.asgi_app
elif hasattr(a2a_app, "get_app"):
    app = a2a_app.get_app()
else:
    app = a2a_app


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
        message = (params.get("message") or {}) if isinstance(params, dict) else {}
        user_text = _extract_text_from_parts(message.get("parts"))
        context_id = message.get("contextId") or str(uuid.uuid4())

        reply = await _build_reply(user_text, assistant_id)

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "contextId": context_id,
                "id": str(uuid.uuid4()),
                "artifacts": [{"parts": [{"kind": "text", "text": reply}]}],
            },
        }
