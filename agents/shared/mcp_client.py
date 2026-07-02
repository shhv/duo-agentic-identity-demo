"""MCP client for connecting to agentgateway via Streamable HTTP transport."""

import json
import uuid

import httpx


class AsyncMCPClient:
    """Async MCP client using Streamable HTTP (POST) to agentgateway.

    agentgateway 0.12+ uses Streamable HTTP: the client POSTs JSON-RPC
    messages to a single endpoint and gets JSON-RPC responses back.
    """

    def __init__(self, base_url: str, access_token: str):
        self.base_url = base_url.rstrip("/")
        self.access_token = access_token
        self.session_id: str | None = None
        self._msg_id = 0
        self._client: httpx.AsyncClient | None = None

    def _headers(self) -> dict:
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        return headers

    def _next_id(self) -> int:
        self._msg_id += 1
        return self._msg_id

    async def connect(self) -> str:
        """Initialize the HTTP client. Returns the base URL."""
        self._client = httpx.AsyncClient(timeout=30.0)
        return self.base_url

    async def send_request(self, method: str, params: dict | None = None) -> dict:
        """Send a JSON-RPC request via POST and return the response.

        Handles both JSON responses and SSE streams from agentgateway.
        """
        if not self._client:
            self._client = httpx.AsyncClient(timeout=30.0)

        msg_id = self._next_id()
        payload = {"jsonrpc": "2.0", "id": msg_id, "method": method}
        if params:
            payload["params"] = params

        resp = await self._client.post(
            self.base_url, headers=self._headers(), json=payload
        )

        # Capture session ID from response
        if "mcp-session-id" in resp.headers:
            self.session_id = resp.headers["mcp-session-id"]

        if resp.status_code == 401:
            return {"error": {"code": -32001, "message": "Unauthorized"}}
        if resp.status_code == 403:
            return {"error": {"code": -32003, "message": "Forbidden"}}
        if resp.status_code >= 400:
            return {"error": {"code": -resp.status_code, "message": f"HTTP {resp.status_code}: {resp.text[:200]}"}}

        content_type = resp.headers.get("content-type", "")

        # JSON response — parse directly
        if "application/json" in content_type:
            return resp.json()

        # SSE stream — parse event data lines for the JSON-RPC response
        if "text/event-stream" in content_type:
            for line in resp.text.splitlines():
                if line.startswith("data:"):
                    data_str = line[5:].strip()
                    if data_str:
                        try:
                            data = json.loads(data_str)
                            if isinstance(data, dict) and data.get("id") == msg_id:
                                return data
                        except json.JSONDecodeError:
                            continue
            return {"error": {"code": -32603, "message": "No valid response in SSE stream"}}

        # Fallback — try parsing as JSON anyway
        text = resp.text.strip()
        if text:
            return json.loads(text)
        return {"error": {"code": -32603, "message": f"Empty response (content-type: {content_type})"}}

    async def initialize(self) -> dict:
        params = {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "duo-demo-agent",
                "version": "1.0.0",
            },
        }
        return await self.send_request("initialize", params)

    async def list_tools(self) -> list[dict]:
        resp = await self.send_request("tools/list")
        if "error" in resp:
            return []
        return resp.get("result", {}).get("tools", [])

    async def call_tool(self, tool_name: str, arguments: dict | None = None) -> dict:
        params = {"name": tool_name, "arguments": arguments or {}}
        return await self.send_request("tools/call", params)

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
