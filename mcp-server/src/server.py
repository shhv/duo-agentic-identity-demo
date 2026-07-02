"""FastAPI app implementing MCP protocol over Streamable HTTP + SSE transport.

No auth validation — agentgateway handles all authorization.
This server trusts internal Docker network traffic.
"""

import asyncio
import json
import uuid

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from .tools import TOOL_DEFINITIONS, dispatch_tool

app = FastAPI(title="Duo Agentic Identity - MCP Server")

_sessions: dict[str, asyncio.Queue] = {}

MCP_PROTOCOL_VERSION = "2024-11-05"


@app.get("/health")
async def health():
    return {"status": "ok", "tools": len(TOOL_DEFINITIONS)}


@app.get("/sse")
async def sse_endpoint(request: Request):
    """SSE endpoint — establishes a session and streams responses."""
    session_id = str(uuid.uuid4())
    queue: asyncio.Queue = asyncio.Queue()
    _sessions[session_id] = queue

    async def event_generator():
        base = str(request.base_url).rstrip("/")
        post_url = f"{base}/messages/{session_id}"
        yield {"event": "endpoint", "data": post_url}

        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield {"event": "message", "data": json.dumps(message)}
                except asyncio.TimeoutError:
                    yield {"comment": "keepalive"}
        finally:
            _sessions.pop(session_id, None)

    return EventSourceResponse(event_generator())


@app.post("/sse")
async def streamable_http_endpoint(request: Request):
    """Streamable HTTP endpoint — handles JSON-RPC POST requests directly.

    agentgateway 0.12+ uses this transport: POST to the MCP endpoint,
    get a JSON-RPC response back (or SSE stream for streaming responses).
    """
    try:
        message = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content=_make_error_response(None, -32700, "Parse error"),
        )

    response = await _handle_message(message)

    session_id = request.headers.get("mcp-session-id", str(uuid.uuid4()))
    resp = JSONResponse(content=response)
    resp.headers["mcp-session-id"] = session_id
    return resp


@app.post("/messages/{session_id}")
async def messages_endpoint(session_id: str, request: Request):
    """Receives MCP JSON-RPC messages for SSE sessions."""
    queue = _sessions.get(session_id)
    if queue is None:
        return JSONResponse(status_code=404, content={"error": "Session not found"})

    try:
        message = await request.json()
    except Exception:
        error_resp = _make_error_response(None, -32700, "Parse error")
        await queue.put(error_resp)
        return Response(status_code=202)

    response = await _handle_message(message)
    await queue.put(response)
    return Response(status_code=202)


async def _handle_message(message: dict) -> dict:
    """Route an MCP JSON-RPC message to the appropriate handler."""
    method = message.get("method", "")
    msg_id = message.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {
                    "name": "duo-agentic-identity-mcp",
                    "version": "1.0.0",
                },
            },
        }

    elif method == "notifications/initialized":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}

    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {"tools": TOOL_DEFINITIONS},
        }

    elif method == "tools/call":
        params = message.get("params", {})
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        try:
            result = await dispatch_tool(tool_name, arguments)
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result)}],
                },
            }
        except ValueError as e:
            return _make_error_response(msg_id, -32602, str(e))
        except Exception as e:
            return _make_error_response(msg_id, -32603, f"Tool error: {e}")

    else:
        return _make_error_response(msg_id, -32601, f"Method not found: {method}")


def _make_error_response(id, code: int, message: str) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": id,
        "error": {"code": code, "message": message},
    }
