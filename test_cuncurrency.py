import asyncio
import hashlib
import json
import secrets

import httpx

BASE_URL = "http://localhost:8000/"
REGISTERED_EMAIL = "24f2004647@ds.study.iitm.ac.in".strip().lower()
HEADERS_BASE = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


def expected_answer(challenge):
    combined = f"{challenge}:{REGISTERED_EMAIL}"
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()[:16]


async def one_call(client, i):
    challenge = secrets.token_hex(16)
    payload = {
        "jsonrpc": "2.0",
        "id": 1000 + i,
        "method": "tools/call",
        "params": {"name": "solve_challenge", "arguments": {}},
    }
    headers = dict(HEADERS_BASE)
    headers["X-Exam-Challenge"] = challenge
    resp = await client.post(BASE_URL, headers=headers, content=json.dumps(payload))
    data = json.loads(resp.text)
    got = data["result"]["content"][0]["text"]
    expected = expected_answer(challenge)
    return i, challenge, got, expected, got == expected


async def main():
    async with httpx.AsyncClient(timeout=10) as client:
        results = await asyncio.gather(*[one_call(client, i) for i in range(20)])
        ok = all(r[4] for r in results)
        for r in results:
            print(r)
        print("\nALL CONCURRENT CALLS ISOLATED CORRECTLY:", ok)


asyncio.run(main())


asyncio.run(main())
