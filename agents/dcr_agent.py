#!/usr/bin/env python3
"""DCR Agent — demonstrates Dynamic Client Registration with agentgateway.

Instead of using a pre-configured client, this agent registers itself
on-the-fly with Duo SSO, then authenticates a user through the new client.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import httpx
from dotenv import load_dotenv

from shared.auth import get_access_token
from shared.mcp_client import AsyncMCPClient
from shared.output import (
    Colors,
    banner,
    error,
    info,
    section,
    success,
    summary,
    tool_result,
)

load_dotenv()

GATEWAY_URL = os.environ.get("GATEWAY_URL", "https://your-tunnel.trycloudflare.com/mcp")
DCR_URL = "https://sso-cd6ab40d.sso.duosecurity.com/oauth2/DIRRU85N51QCWHXP8HEV/register"

TOOL_CALLS = [
    ("acme-tools_hr_get_employee", {"employee_id": "EMP001"}),
    ("acme-tools_hr_list_departments", {}),
    ("acme-tools_hr_create_employee", {
        "name": "DCR Test Hire",
        "email": "dcr.test@acmecorp.com",
        "department": "Engineering",
        "title": "DCR Engineer",
        "salary": 120000,
    }),
    ("acme-tools_finance_get_budget", {"budget_code": "ENG-2024"}),
    ("acme-tools_finance_create_expense", {
        "submitted_by": "EMP001",
        "department": "Engineering",
        "amount": 99.00,
        "description": "DCR test expense",
        "category": "misc",
    }),
]


async def register_client() -> tuple[str, str]:
    """Dynamically register a new OAuth client with Duo SSO."""
    metadata = {
        "client_name": "DCR Demo Agent",
        "redirect_uris": ["http://localhost:8085/callback"],
        "grant_types": ["authorization_code"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "client_secret_post",
        "scope": "openid",
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(DCR_URL, json=metadata)
        resp.raise_for_status()
        data = resp.json()

    client_id = data.get("client_id")
    client_secret = data.get("client_secret")

    if not client_id:
        raise ValueError(f"DCR failed — no client_id in response: {data}")

    return client_id, client_secret


async def main():
    banner("DCR AGENT", Colors.YELLOW)

    # Step 1: Dynamic Client Registration
    section("Dynamic Client Registration")
    info(f"Registering new client at: {DCR_URL}")

    try:
        client_id, client_secret = await register_client()
        success(f"Client registered: {client_id}")
        if client_secret:
            info(f"Secret: {client_secret[:8]}...")
    except Exception as e:
        error(f"DCR failed: {e}")
        sys.exit(1)

    # Step 2: Authenticate using the dynamically registered client
    section("Authentication (via DCR client)")
    info("Opening browser for Duo SSO login...")

    # Override env vars with DCR credentials
    os.environ["OAUTH_CLIENT_ID"] = client_id
    if client_secret:
        os.environ["OAUTH_CLIENT_SECRET"] = client_secret
    else:
        os.environ.pop("OAUTH_CLIENT_SECRET", None)

    try:
        token = await get_access_token()
        success(f"Token acquired (…{token[-8:]})")
    except Exception as e:
        error(f"Failed to get token: {e}")
        sys.exit(1)

    # Step 3: Connect to gateway
    section("Connection")
    info(f"Connecting to agentgateway at {GATEWAY_URL}...")

    client = AsyncMCPClient(GATEWAY_URL, token)
    try:
        post_url = await client.connect()
        success(f"Connected — session endpoint: {post_url}")
    except Exception as e:
        error(f"Connection failed: {e}")
        sys.exit(1)

    # Step 4: Initialize
    init_resp = await client.initialize()
    proto = init_resp.get("result", {}).get("protocolVersion", "?")
    success(f"MCP initialized (protocol {proto})")

    # Step 5: List tools
    section("Available Tools (filtered by Duo policy)")
    tools = await client.list_tools()
    for t in tools:
        info(f"{t['name']} — {t.get('description', '')[:60]}")
    print(f"\n  {Colors.BOLD}{len(tools)} tools visible{Colors.RESET}\n")

    # Step 6: Call tools
    section("Tool Call Results")
    allowed_count = 0
    denied_count = 0

    for tool_name, args in TOOL_CALLS:
        resp = await client.call_tool(tool_name, args)

        if "error" in resp:
            err_msg = resp["error"].get("message", "Access denied")
            tool_result(tool_name, allowed=False, detail=err_msg)
            denied_count += 1
        else:
            import json
            content = resp.get("result", {}).get("content", [])
            preview = ""
            if content and content[0].get("text"):
                data = json.loads(content[0]["text"])
                if isinstance(data, dict):
                    keys = list(data.keys())[:3]
                    preview = f"keys: {keys}"
            tool_result(tool_name, allowed=True, detail=preview)
            allowed_count += 1

    summary(allowed_count, denied_count)


if __name__ == "__main__":
    asyncio.run(main())
