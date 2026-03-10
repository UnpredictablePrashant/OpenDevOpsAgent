# run_demo.py
import asyncio
import uuid
import aiohttp

AGENT_A_URL = "http://127.0.0.1:9001/a2a/orchestrator"

def extract_text(resp: dict) -> str:
    res = resp.get("result", {}) or {}
    for art in res.get("artifacts", []) or []:
        for part in art.get("parts", []) or []:
            if part.get("kind") == "text" and part.get("text"):
                return part["text"]
    return "(no text)"

async def main():
    message = {
        "role": "user",
        "parts": [{"kind": "text", "text": "compute 12 30 and greet Shashank"}],
        "messageId": str(uuid.uuid4()),
    }

    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "message/send",
        "params": {"message": message},
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(AGENT_A_URL, json=payload) as r:
            resp = await r.json()

    print(extract_text(resp))

if __name__ == "__main__":
    asyncio.run(main())