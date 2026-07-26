import hashlib
import json
import secrets
import time

import httpx

BASE_URL = "http://localhost:8000/"
REGISTERED_EMAIL = "24f2004647@ds.study.iitm.ac.in".strip().lower()

COMMON_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


def send(client, session_id, payload, extra_headers=None):
    headers = dict(COMMON_HEADERS)
    if session_id:
        headers["mcp-session-id"] = session_id
    if extra_headers:
        headers.update(extra_headers)
    resp = client.post(BASE_URL, headers=headers, content=json.dumps(payload))
    return resp


def expected_answer(challenge):
    combined = f"{challenge}:{REGISTERED_EMAIL}"
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()[:16]


def main():
    with httpx.Client(timeout=10) as client:
        # 1. initialize
        init_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "grader-sim", "version": "1.0"},
            },
        }
        resp = send(client, None, init_payload)
        print("initialize status:", resp.status_code)
        session_id = resp.headers.get("mcp-session-id")
        print("session id:", session_id)
        body = resp.text
        print("initialize body:", body[:300])

        # 2. notifications/initialized (no id -> notification)
        notif_payload = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {},
        }
        resp2 = send(client, session_id, notif_payload)
        print("notifications/initialized status:", resp2.status_code)

        # 3. tools/list
        list_payload = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        resp3 = send(client, session_id, list_payload)
        print("tools/list status:", resp3.status_code)
        print("tools/list body:", resp3.text[:500])
        tools = json.loads(resp3.text)
        tool_names = [t["name"] for t in tools["result"]["tools"]]
        assert "solve_challenge" in tool_names, f"solve_challenge missing! got {tool_names}"
        print("Found solve_challenge tool. Required props on schema:",
              tools["result"]["tools"][0].get("inputSchema", {}).get("required"))

        # 4. five tools/call with FRESH per-call headers
        all_ok = True
        for i in range(5):
            challenge = secrets.token_hex(16)  # 32 lowercase hex chars
            timestamp = str(int(time.time() * 1000))
            call_payload = {
                "jsonrpc": "2.0",
                "id": 100 + i,
                "method": "tools/call",
                "params": {"name": "solve_challenge", "arguments": {}},
            }
            extra = {
                "X-Exam-Challenge": challenge,
                "X-Exam-Timestamp": timestamp,
                "X-Exam-Signature": "deadbeef",  # unscored, doesn't need to be valid
            }
            resp = send(client, session_id, call_payload, extra_headers=extra)
            data = json.loads(resp.text)
            result_text = data["result"]["content"][0]["text"]
            expected = expected_answer(challenge)
            ok = result_text == expected
            all_ok &= ok
            print(f"call {i}: challenge={challenge} got={result_text} expected={expected} {'OK' if ok else 'MISMATCH'}")

        print("\nALL CALLS CORRECT:", bool(all_ok))


if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
