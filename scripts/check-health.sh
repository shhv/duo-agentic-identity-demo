#!/usr/bin/env bash
set -euo pipefail

echo "Checking service health..."
echo ""

check() {
    local name=$1
    local url=$2
    if curl -sf "$url" > /dev/null 2>&1; then
        echo "  ✓ $name"
        return 0
    else
        echo "  ✗ $name (unreachable: $url)"
        return 1
    fi
}

failures=0

check "MCP Server" "http://localhost:8000/health" || ((failures++))
check "Agent Gateway" "http://localhost:3000/health" || ((failures++))
check "Authz Connector" "http://localhost:9001/health" || ((failures++))

echo ""
if [ $failures -eq 0 ]; then
    echo "All services healthy ✓"
else
    echo "$failures service(s) unhealthy"
    exit 1
fi
