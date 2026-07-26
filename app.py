import contextvars
import hashlib
import os

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
REGISTERED_EMAIL = "24f2004647@ds.study.iitm.ac.in".strip().lower()

# Per-request header storage. This is a plain ASGI middleware (not
# Starlette's BaseHTTPMiddleware, which spawns a separate task and would
# break contextvar propagation for streaming responses). Because it runs
# in-line in the same asyncio task that later handles the JSON-RPC message,
# the contextvar set here is visible to the tool function invoked for that
# same HTTP request.
current_headers: contextvars.ContextVar[dict] = contextvars.ContextVar(
    "current_headers", default={}
)


class HeaderCaptureMiddleware:
    """Raw ASGI middleware that stashes the incoming request's headers into
    a contextvar so tool functions (which have no direct access to the HTTP
    request) can read them for the request currently being handled."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = {
                k.decode("latin-1").lower(): v.decode("latin-1")
                for k, v in scope.get("headers", [])
            }
            current_headers.set(headers)
        await self.app(scope, receive, send)


# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------
mcp = FastMCP(
    "exam-solver",
    stateless_http=True,
    json_response=True,
    host="0.0.0.0",
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False
    ),
)


@mcp.tool()
def solve_challenge() -> str:
    """Solve the exam challenge for the current request.

    Reads the fresh, single-use challenge from the X-Exam-Challenge HTTP
    header of *this* tool call (never from the JSON arguments) and returns
    the first 16 lowercase hex characters of
    SHA-256(f"{challenge}:{registered_email}").
    """
    headers = current_headers.get()
    challenge = headers.get("x-exam-challenge", "")
    combined = f"{challenge}:{REGISTERED_EMAIL}"
    digest = hashlib.sha256(combined.encode("utf-8")).hexdigest()
    return digest[:16]


# Build the ASGI app and wrap it with the header-capture middleware.
app = mcp.streamable_http_app()
app.add_middleware(HeaderCaptureMiddleware)


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
