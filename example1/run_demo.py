import asyncio
import uuid

import aiohttp

AGENT_A_URL = "http://127.0.0.1:9101/a2a/orchestrator"


def extract_text(resp: dict) -> str:
    result = (resp or {}).get("result", {}) or {}
    for art in (result.get("artifacts", []) or []):
        for part in (art.get("parts", []) or []):
            if part.get("kind") == "text" and part.get("text"):
                return part["text"]
    return "(no text)"


async def main():
    user_text = "customer=Acme usage=120 unit_price=2.5 discount=10 tickets=4 breaches=1"
    message = {
        "role": "user",
        "parts": [{"kind": "text", "text": user_text}],
        "messageId": str(uuid.uuid4()),
    }
    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "message/send",
        "params": {"message": message},
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(AGENT_A_URL, json=payload, timeout=30) as r:
            body = await r.json()
    print(extract_text(body))


if __name__ == "__main__":
    asyncio.run(main())
