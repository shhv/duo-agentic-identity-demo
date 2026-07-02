#!/usr/bin/env bash
# Restore configs from configs/local/ for repeat use.
# After restoring, update the tunnel URL in all 3 files if it changed.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ ! -f "$DIR/configs/local/quickstart.conf" ]; then
    echo "✗ No saved configs found in configs/local/"
    echo "  Run the demo once with 'make setup' to generate them."
    exit 1
fi

cp "$DIR/configs/local/quickstart.conf" "$DIR/quickstart.conf"
cp "$DIR/configs/local/.env" "$DIR/.env"
mkdir -p "$DIR/secrets"
cp "$DIR/configs/local/duo_skey" "$DIR/secrets/duo_skey"
chmod 600 "$DIR/secrets/duo_skey"

echo "✓ Configs restored from configs/local/"
echo ""
echo "If your Cloudflare tunnel URL changed, update it in:"
echo "  1. quickstart.conf → gateway.external_url"
echo "  2. .env → GATEWAY_URL"
echo "  3. Duo Admin → MCP OIDC integration → Resource URLs"
echo "  4. Duo Admin → agentgateway integration → agentgateway URLs"
echo ""
echo "Then restart: docker compose down && COMPOSE_PROFILES=agentgateway docker compose up -d"
