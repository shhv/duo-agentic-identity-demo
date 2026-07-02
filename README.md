# Duo Agentic Identity Demo

Demonstrates Duo's agentic authorization for AI agents using the MCP protocol. Two scripted agents (HR and Finance) authenticate via Duo SSO and connect through agentgateway — showing how Duo policies enforce **shared read, split write** access to MCP tools.

**Key insight:** Same tools, same server, same client — different user, different permissions.

## What This Shows

| Script | User | Shared Reads | HR Writes | Finance Writes |
|--------|------|-------------|-----------|---------------|
| HR Agent | HR user | ✓ 4 tools | ✓ 2 tools | ✗ DENIED |
| Finance Agent | Finance user | ✓ 4 tools | ✗ DENIED | ✓ 2 tools |
| Any script | HR user | ✓ | ✓ | ✗ |
| Any script | Finance user | ✓ | ✗ | ✓ |

The script doesn't matter — **the user identity determines access**.

## Architecture

```
Agent scripts (Python)
    │
    │ OAuth Authorization Code + PKCE (browser-based Duo SSO)
    ▼
Cloudflare Tunnel (public HTTPS)
    │
    ▼
agentgateway (:3000)
    │
    ├── authz-bridge (:9001) → Duo Cloud API (policy evaluation)
    │
    ▼
MCP Server (:8000) — 8 tools, no auth, mock data
```

## Prerequisites

- Docker & Docker Compose v2+
- Python 3.11+
- Duo Premier subscription with Agentic Identity alpha access
- `cloudflared` CLI (`brew install cloudflared`)

---

## Screenshots

### Duo Admin — MCP Servers page
Your gateway appears here after services are running. Click "Configure policy" to set up rules.

![MCP Servers page](screenshots/02-mcp-servers-page.png)

### Configure Policy — JSON rules + tool list
Paste the JSON policy on the left. The tool drawer on the right shows all 8 tools discovered from your MCP server.

![Configure Policy](screenshots/03-configure-policy.png)

### Clients tab — Admin Panel + Agent Client
You need two confidential clients: one for the admin panel (tool fetching) and one for agent authentication.

![Clients tab](screenshots/04-clients-tab.png)

### Authentication Log — shows all agent logins
Duo Admin → Reports shows every authentication event against the MCP OIDC integration.

![Auth Log](screenshots/01-duo-auth-log.png)

---

## First-Time Setup

### Step 1: Duo Admin — Create MCP OIDC Integration

1. **Applications → Application Catalog** → search "MCP" → add **"Model Context Protocol (MCP)"**
2. **General tab:**
   - Check **Client Credentials** (admin panel uses this)
   - Set **Sign-In Redirect URLs**: `http://localhost:8085/callback`
   - Set **Resource URLs**: `https://<your-tunnel>.trycloudflare.com/mcp` (add after Step 4)
3. **Clients tab:**
   - Rename default client to `MCPGW Tool List Client` — set scope to `openid`
   - Click **+ Add Another Client** → name it `Agent Client` — set scope to `openid`
   - Copy the **Agent Client's** Client ID and Client Secret

### Step 2: Duo Admin — Create agentgateway Integration

1. **Applications → Application Catalog** → search "agentgateway" → add it
2. Copy from **Details** section: API hostname, Integration key, Secret key
3. In **Connect Duo Authorization to Gateway Authentication**:
   - Select your MCP OIDC integration from the dropdown
   - Add agentgateway URL: `https://<your-tunnel>.trycloudflare.com/mcp`
   - Set gateway name (e.g. `mcpgw`)
4. Save

### Step 3: Duo Admin — Create Groups and Users

1. **Groups** → create `HR Team` and `Finance Team`
2. **Users** → create test users, assign to groups:
   - `hr-user@...` → HR Team
   - `finance-user@...` → Finance Team

### Step 4: Start the Cloudflare Tunnel

```bash
cloudflared tunnel --url http://localhost:3000
```

Copy the generated URL (e.g. `https://random-words.trycloudflare.com`).

Now go back to Duo Admin and paste `https://<your-url>/mcp` into:
- MCP OIDC integration → General tab → **Resource URLs**
- agentgateway integration → **agentgateway URLs**

### Step 5: Configure This Project

```bash
cd duo-agentic-identity-demo

# Create secrets directory and add Duo secret key
mkdir -p secrets
echo -n "YOUR_DUO_SECRET_KEY" > secrets/duo_skey
chmod 600 secrets/duo_skey
```

Edit `quickstart.conf`:
- `gateway.external_url` → your tunnel URL + `/mcp`
- `oauth.issuer` → your Duo SSO issuer URL
- `oauth.admin_panel_client_id` → MCPGW Tool List Client's Client ID
- `duo.host` → API hostname from agentgateway integration
- `duo.integration_key` → Integration key from agentgateway integration

Edit `.env`:
- `OAUTH_AUTHORIZE_URL` → `https://sso-XXXX.sso.duosecurity.com/oauth2/XXXX/authorize`
- `OAUTH_TOKEN_URL` → `https://sso-XXXX.sso.duosecurity.com/oauth2/XXXX/token`
- `OAUTH_CLIENT_ID` → **Agent Client** Client ID (NOT the admin panel one)
- `OAUTH_CLIENT_SECRET` → Agent Client Secret
- `GATEWAY_URL` → your tunnel URL + `/mcp`

### Step 6: Start Services

```bash
COMPOSE_PROFILES=agentgateway docker compose up -d
```

Verify:
```bash
docker ps  # Should show: mcp-server, authz-bridge, agentgateway
docker logs authz-bridge 2>&1 | grep "health check passed"
docker logs agentgateway 2>&1 | grep "server ready"
```

### Step 7: Configure Duo Authorization Policy

1. Duo Admin → **Applications → MCP Servers** → find your gateway → **Configure policy**
2. Add rules (JSON or form):

```json
{
  "rules": [
    {
      "tools": [
        "acme-tools_hr_get_employee",
        "acme-tools_hr_list_departments",
        "acme-tools_finance_get_budget",
        "acme-tools_finance_list_expenses"
      ],
      "groups": ["HR Team", "Finance Team"]
    },
    {
      "tools": ["acme-tools_hr_create_employee", "acme-tools_hr_update_salary"],
      "groups": ["HR Team"]
    },
    {
      "tools": ["acme-tools_finance_create_expense", "acme-tools_finance_approve_payment"],
      "groups": ["Finance Team"]
    }
  ]
}
```

3. Save policy

### Step 8: Run the Demo

```bash
cd agents
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export $(grep -v '^#' ../.env | xargs)

# Run as HR user
python3 hr_agent.py    # Log in as HR Team user → 6/8 allowed

# Run as Finance user
python3 finance_agent.py  # Log in as Finance Team user → 6/8 allowed
```

---

## Returning / Repeat Use

The Cloudflare quick tunnel URL changes every time you restart it. When that happens:

### Update these 3 places:

1. **`quickstart.conf`** → update `gateway.external_url`
2. **`.env`** → update `GATEWAY_URL`
3. **Duo Admin Panel** (both of these):
   - MCP OIDC integration → General tab → **Resource URLs**
   - agentgateway integration → **agentgateway URLs**

### Then restart:

```bash
# Regenerate gateway config with new URL
docker compose down
COMPOSE_PROFILES=agentgateway docker compose up -d

# Verify
docker logs agentgateway 2>&1 | tail -5
```

### Tip: Use a Named Tunnel for Stable URLs

To avoid updating URLs every session, create a permanent tunnel:

```bash
cloudflared tunnel login          # One-time: links to your Cloudflare account
cloudflared tunnel create duo-demo
cloudflared tunnel route dns duo-demo demo.yourdomain.com
cloudflared tunnel run --url http://localhost:3000 duo-demo
```

Then use `https://demo.yourdomain.com/mcp` everywhere — it never changes.

---

## Project Structure

```
├── quickstart.conf          # Gateway + authz-bridge config (edit with your values)
├── docker-compose.yml       # MCP server, authz-bridge, agentgateway
├── secrets/
│   └── duo_skey             # Duo secret key (gitignored)
├── config/                  # Generated configs (auto-created by init containers)
├── mcp-server/
│   ├── Dockerfile
│   └── src/
│       ├── server.py        # FastAPI MCP server (Streamable HTTP + SSE)
│       ├── tools.py         # 8 tool definitions + mock implementations
│       └── mock_data.py     # Fake employees, budgets, expenses
├── agents/
│   ├── hr_agent.py          # Demo script: tries all 8 tools as HR user
│   ├── finance_agent.py     # Demo script: tries all 8 tools as Finance user
│   ├── requirements.txt
│   └── shared/
│       ├── auth.py          # OAuth Authorization Code + PKCE flow
│       ├── mcp_client.py    # Streamable HTTP MCP client for agentgateway
│       └── output.py        # ANSI colored terminal output
├── .env                     # Your credentials (gitignored)
├── .env.example             # Template
└── docs/
    ├── DUO_SETUP.md
    ├── CLOUDFLARE_SETUP.md
    └── DEMO_SCRIPT.md
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Token acquired but all tools "Unauthorized" | Wrong Client ID (using admin panel client) | Use the **Agent Client** ID in `.env`, not the MCPGW Tool List Client |
| Token acquired but all tools "Forbidden" | User not in any policy group | Check user's group membership in Duo Admin |
| "admin panel client: non-listing operation" in authz-bridge logs | Same as above — using admin panel client for tool calls | Switch `OAUTH_CLIENT_ID` to Agent Client |
| "InvalidAudience" in agentgateway logs | Token doesn't have the gateway URL as audience | Add `resource` param to auth request (already in code) — verify `GATEWAY_URL` matches Resource URLs in Duo |
| Tools list works but calls return 500 "Unknown tool" | Policy denies the tool for this user | This IS the enforcement working — expected for denied tools |
| 405 Method Not Allowed on upstream | MCP server doesn't handle POST on the SSE endpoint | Already fixed in this repo — ensure MCP server is rebuilt |
| Tunnel unreachable | Quick tunnel died | Restart `cloudflared tunnel --url http://localhost:3000` and update URLs |
| "Authentication timed out" | Browser redirect didn't reach localhost:8085 | Check `http://localhost:8085/callback` is in Sign-In Redirect URLs |

## Key Concepts

- **agentgateway** — proxy that sits in front of MCP servers, enforces auth + policy
- **authz-bridge** — Duo's authorization connector, evaluates policies against Duo Cloud
- **MCP Server** — exposes tools (no auth needed, trusts internal network)
- **Policy** — maps Duo user groups → allowed tools, configured in Duo Admin Panel
- **Streamable HTTP** — the MCP transport agentgateway uses (POST JSON-RPC, get JSON/SSE back)
