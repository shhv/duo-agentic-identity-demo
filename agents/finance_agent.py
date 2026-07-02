#!/usr/bin/env python3
"""Finance Agent — demonstrates Duo policy allowing finance read+write, denying HR write."""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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

GATEWAY_URL = os.environ.get("GATEWAY_URL", "https://your-tunnel.cfargotunnel.com")

TOOL_CALLS = [
    ("acme-tools_hr_get_employee", {"employee_id": "EMP003"}),
    ("acme-tools_hr_list_departments", {}),
    ("acme-tools_hr_create_employee", {
        "name": "Unauthorized Hire",
        "email": "bad.hire@acmecorp.com",
        "department": "Finance",
        "title": "Analyst",
        "salary": 100000,
    }),
    ("acme-tools_hr_update_salary", {
        "employee_id": "EMP003",
        "new_salary": 200000,
        "reason": "Unauthorized raise attempt",
    }),
    ("acme-tools_finance_get_budget", {"budget_code": "FIN-2024"}),
    ("acme-tools_finance_list_expenses", {"department": "Finance"}),
    ("acme-tools_finance_create_expense", {
        "submitted_by": "EMP003",
        "department": "Finance",
        "amount": 3500.00,
        "description": "Bloomberg terminal monthly subscription",
        "category": "tools_and_licenses",
    }),
    ("acme-tools_finance_approve_payment", {
        "payment_id": "PAY003",
        "approver_id": "EMP003",
    }),
]


async def main():
    banner("FINANCE AGENT", Colors.MAGENTA)

    # Step 1: Authenticate via browser (Duo SSO)
    section("Authentication")
    info("Starting Duo SSO browser login...")
    info("Log in as a user in the 'Finance Team' group.")

    try:
        token = await get_access_token()
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

    # Step 4: List available tools
    section("Available Tools (filtered by Duo policy)")
    tools = await client.list_tools()
    for t in tools:
        info(f"{t['name']} — {t.get('description', '')[:60]}")
    print(f"\n  {Colors.BOLD}{len(tools)} tools visible{Colors.RESET} (policy-filtered from 8 total)\n")

    # Step 5: Call all tools
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
            content = resp.get("result", {}).get("content", [])
            preview = ""
            if content and content[0].get("text"):
                import json
                data = json.loads(content[0]["text"])
                if isinstance(data, dict):
                    keys = list(data.keys())[:3]
                    preview = f"keys: {keys}"
            tool_result(tool_name, allowed=True, detail=preview)
            allowed_count += 1

    summary(allowed_count, denied_count)


if __name__ == "__main__":
    asyncio.run(main())
