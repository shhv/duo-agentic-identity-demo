#!/usr/bin/env bash
# Show the active Cloudflare tunnel URL and warn if it doesn't match .env.
# Run by `make up` and `make status`. Never fails the build — it only warns.
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

ENV_URL=$(grep -E '^GATEWAY_URL=' "$DIR/.env" 2>/dev/null | head -1 | cut -d= -f2-)
TUNNEL_URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' /tmp/cloudflared.log 2>/dev/null | head -1)
RUNNING=0
pgrep -f "cloudflared tunnel" > /dev/null 2>&1 && RUNNING=1

echo "─── Cloudflare Tunnel ───"
echo ""

# Named tunnel or custom domain: nothing to compare against.
if [ -n "$ENV_URL" ] && [[ "$ENV_URL" != *trycloudflare.com* ]]; then
    echo "  Gateway URL (.env): $ENV_URL"
    echo "  (not a quick tunnel — skipping URL check)"
    echo ""
    exit 0
fi

if [ "$RUNNING" -eq 0 ] || [ -z "$TUNNEL_URL" ]; then
    echo "  ⚠  No quick tunnel is running."
    echo "     Agents can't reach the gateway until you run:"
    echo "       make setup   # starts a new tunnel and updates .env + quickstart.conf"
    echo "       make up      # restart containers with the new URL"
    echo "     Then update the new URL in Duo Admin (setup prints the exact fields)."
    echo ""
    exit 0
fi

echo "  Tunnel URL:          $TUNNEL_URL"
echo "  Gateway URL (.env):  ${ENV_URL:-<not set>}"
echo ""

if [ "$ENV_URL" != "${TUNNEL_URL}/mcp" ]; then
    echo "  ⚠  MISMATCH — .env points at a different tunnel than the one running."
    echo "     Run 'make setup' then 'make up' to resync."
    echo ""
    exit 0
fi

echo "  ✓ .env matches the running tunnel."
echo "  Duo Admin must use the same URL (${TUNNEL_URL}/mcp) in:"
echo "    1. MCP OIDC integration → General → Resource URLs"
echo "    2. agentgateway integration → agentgateway URLs (keep the gateway name unchanged)"
echo ""
