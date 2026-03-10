from __future__ import annotations

import asyncio
import os
import uuid
from typing import Any, Dict

import aiohttp

AGENT_A_URL = os.getenv("AGENT_A_URL", "http://127.0.0.1:8001/a2a/orchestrator")
DEMO_TEXT = os.getenv("DEMO_TEXT", "compute 12 30 and greet Shashank")


def extract_text(resp: Dict[str, Any]) -> str:
    result = (resp or {}).get("result", {}) or {}
    for art in (result.get("artifacts", []) or []):
        for part in (art.get("parts", []) or []):
            if part.get("kind") == "text" and part.get("text"):
                return part["text"]
    return "(no text)"


async def main() -> None:
    message = {
        "role": "user",
        "parts": [{"kind": "text", "text": DEMO_TEXT}],
        "messageId": str(uuid.uuid4()),
    }
    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "message/send",
        "params": {"message": message},
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(AGENT_A_URL, json=payload, timeout=20) as r:
            raw = await r.text()
            if r.status != 200:
                raise RuntimeError(f"Agent A call failed ({r.status}): {raw[:400]}")
            try:
                resp = await r.json()
            except Exception:
                raise RuntimeError(f"Agent A returned non-JSON response: {raw[:400]}")

    if "error" in resp:
        raise RuntimeError(f"Agent A JSON-RPC error: {resp['error']}")

    print(extract_text(resp))


if __name__ == "__main__":
    asyncio.run(main())
