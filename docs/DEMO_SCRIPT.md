# Demo Script — Presenter Talking Points

## Opening (30 seconds)

> "Today I'm going to show you how Duo's agentic authorization controls which AI agents can access which tools — in real time. We have two agents: an HR agent and a Finance agent. Both connect to the same MCP server with 8 tools, but Duo policy determines who can do what."

## Architecture Slide (30 seconds)

> "The agents authenticate via Duo SSO using OAuth client credentials. They connect through Duo's agentgateway, which consults the Authorization Connector on every tool call. The MCP server itself has no auth — all policy enforcement happens at the gateway layer."

Key point: **Zero-trust at the tool level, not the server level.**

## HR Agent Demo (1 minute)

Run: `python3 agents/hr_agent.py`

**Talk through the output:**

1. "First it authenticates — gets an OAuth token from Duo SSO"
2. "Connects to agentgateway via the Cloudflare tunnel"
3. "tools/list shows 6 tools — Duo already filtered out the 2 it can't use"
4. "Now it tries all 8 tools..."
5. "Green checkmarks for the 4 shared reads — both agents can read"
6. "Green for HR writes — this agent is in the HR Team group"
7. "Red X for finance writes — policy blocks these even though the tools exist on the server"

## Finance Agent Demo (1 minute)

Run: `python3 agents/finance_agent.py`

**Talk through the output:**

1. "Same flow, different identity"
2. "Same 4 shared reads work fine"
3. "Now HR writes are DENIED — Finance agent can't create employees or change salaries"
4. "But Finance writes succeed — create expense, approve payment"

## Key Takeaways (30 seconds)

> "Three things to notice:
> 1. **Shared reads** — both agents can read from both HR and Finance
> 2. **Split writes** — each agent can only write to their own domain
> 3. **Gateway enforcement** — the MCP server never sees unauthorized calls; they're blocked before they arrive"

## Q&A Prompts

- "What happens if you remove the agent from a group?" → Show Duo Admin, remove, re-run
- "Can you do time-based policies?" → Yes, Duo supports time-of-day restrictions
- "What about audit?" → Show Duo Admin → Reports → Client Authorization Log
- "How does this differ from per-tool API keys?" → Central policy, no secrets in agent code, group-based management

## LLM Agent + Prompt Injection (2 minutes)

Run: `python3 agents/llm_agent.py --replay-hijack` (deterministic), or without the flag for a live model.

1. "So far the agents followed a script. Real agents let an LLM pick the tools — and the LLM reads data other people wrote."
2. "Expense EXP006 has instructions hidden in its description: approve a payment, give someone a 400k salary."
3. "The approve-payment call is **denied** — this user isn't in Finance. Policy holds no matter what the model was told."
4. "The salary change **goes through**. HR may call that tool; the gateway checks *which* tool, not *what arguments*. That's the boundary of tool-level policy."
5. "Fixes for the second case live in the tool or an argument-aware policy, plus human confirmation for high-impact writes." → `docs/THREAT_MODEL.md`
