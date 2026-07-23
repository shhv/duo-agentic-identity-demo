#!/usr/bin/env bash
set -euo pipefail

echo "Checking service health..."
echo ""

check_http() {
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

check_container() {
    local name=$1
    local container=$2
    local status
    status=$(docker inspect --format='{{.State.Status}}' "$container" 2>/dev/null || echo "not found")
    if [ "$status" = "running" ]; then
        echo "  ✓ $name (running)"
        return 0
    else
        echo "  ✗ $name (status: $status)"
        return 1
    fi
}

failures=0

check_http "MCP Server" "http://localhost:8000/health" || ((failures++))
check_container "Agent Gateway" "agentgateway" || ((failures++))
check_container "Authz Connector" "authz-bridge" || ((failures++))

echo ""
if [ $failures -eq 0 ]; then
    echo "All services healthy ✓"
else
    echo "$failures service(s) unhealthy"
    exit 1
fi
