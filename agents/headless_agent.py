#!/usr/bin/env python3
"""Headless Agent — demonstrates non-interactive Client Credentials flow.

No browser needed. The agent authenticates as itself (not a user) using
client_id + client_secret. Policy is tied to the client identity, not a user.

Requires a Client Credentials client configured in Duo Admin:
  MCP OIDC integration → Clients tab → Add Client → Grant type: client_credentials
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import httpx
from dotenv import load_dotenv

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
TOKEN_URL = os.environ.get("OAUTH_TOKEN_URL")
CLIENT_ID = os.environ.get("HEADLESS_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("HEADLESS_CLIENT_SECRET", "")

TOOL_CALLS = [
    ("acme-tools_hr_get_employee", {"employee_id": "EMP001"}),
    ("acme-tools_hr_list_departments", {}),
    ("acme-tools_hr_create_employee", {
        "name": "Headless Hire",
        "email": "headless@acmecorp.com",
        "department": "Engineering",
        "title": "Bot Engineer",
        "salary": 100000,
    }),
    ("acme-tools_hr_update_salary", {
        "employee_id": "EMP001",
        "new_salary": 200000,
        "reason": "Automated adjustment",
    }),
    ("acme-tools_finance_get_budget", {"budget_code": "ENG-2024"}),
    ("acme-tools_finance_list_expenses", {"department": "Engineering"}),
    ("acme-tools_finance_create_expense", {
        "submitted_by": "EMP001",
        "department": "Engineering",
        "amount": 250.00,
        "description": "Headless test expense",
        "category": "misc",
    }),
    ("acme-tools_finance_approve_payment", {
        "payment_id": "PAY001",
        "approver_id": "EMP005",
    }),
]


async def get_token_client_credentials() -> str:
    """Acquire token via OAuth 2.0 Client Credentials grant — no browser, no user."""
    if not TOKEN_URL or not CLIENT_ID or not CLIENT_SECRET:
        raise ValueError(
            "Missing env vars. Set OAUTH_TOKEN_URL, HEADLESS_CLIENT_ID, HEADLESS_CLIENT_SECRET"
        )

    data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "openid",
    }
    resource = os.environ.get("GATEWAY_URL", "")
    if resource:
        data["resource"] = resource

    async with httpx.AsyncClient() as client:
        resp = await client.post(TOKEN_URL, data=data)
        resp.raise_for_status()
        result = resp.json()

    token = result.get("access_token")
    if not token:
        raise ValueError(f"No access_token in response: {result}")
    return token


async def main():
    banner("HEADLESS AGENT (Client Credentials)", Colors.MAGENTA)

    # Step 1: Get token — no browser
    section("Authentication (Client Credentials)")
    info("No browser needed — authenticating with client_id + secret...")

    try:
        token = await get_token_client_credentials()
        success(f"Token acquired (…{token[-8:]})")
    except Exception as e:
        error(f"Failed to get token: {e}")
        sys.exit(1)

    # Step 2: Connect to gateway
    section("Connection")
    info(f"Connecting to agentgateway at {GATEWAY_URL}...")

    client = AsyncMCPClient(GATEWAY_URL, token)
    try:
        post_url = await client.connect()
        success(f"Connected — session endpoint: {post_url}")
    except Exception as e:
        error(f"Connection failed: {e}")
        sys.exit(1)

    # Step 3: Initialize
    init_resp = await client.initialize()
    success(f"MCP initialized (protocol {init_resp.get('result', {}).get('protocolVersion', '?')})")

    # Step 4: List tools
    section("Available Tools (filtered by Duo policy)")
    tools = await client.list_tools()
    for t in tools:
        info(f"{t['name']} — {t.get('description', '')[:60]}")
    print(f"\n  {Colors.BOLD}{len(tools)} tools visible{Colors.RESET}\n")

    # Step 5: Call tools
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
