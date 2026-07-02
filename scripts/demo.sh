#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
AGENTS_DIR="$PROJECT_DIR/agents"

if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "✗ No .env file found. Run 'make setup' first."
    exit 1
fi

# Source env for agent scripts
set -a
source "$PROJECT_DIR/.env"
set +a

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║   Duo Agentic Identity Demo                                ║"
echo "║   Showing: shared read / split write policy enforcement    ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Press Enter to start HR Agent demo..."
read -r

cd "$AGENTS_DIR"
python3 hr_agent.py

echo ""
echo "Press Enter to start Finance Agent demo..."
read -r

python3 finance_agent.py

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  Demo complete."
echo "  HR Agent:      4 shared reads ✓ + 2 HR writes ✓ + 2 finance writes ✗"
echo "  Finance Agent: 4 shared reads ✓ + 2 HR writes ✗ + 2 finance writes ✓"
echo "════════════════════════════════════════════════════════════════"
