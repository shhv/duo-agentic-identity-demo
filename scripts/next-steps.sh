#!/usr/bin/env bash
# Print what to run after `make up` to test the setup.
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
B=$'\033[1m'; D=$'\033[2m'; G=$'\033[92m'; Y=$'\033[93m'; R=$'\033[0m'

ok()   { echo "  ${G}✓${R} $1"; }
todo() { echo "  ${Y}○${R} $1"; }

echo ""
echo "${B}─── Next steps: test the setup ───${R}"
echo ""

# ── Readiness ─────────────────────────────────────────────
[ -f "$DIR/.env" ] && ok ".env present" || todo ".env missing — run: make setup"
if [ -x "$DIR/agents/.venv/bin/python" ]; then
    VENV="agents/.venv"; ok "Python venv: $VENV"
elif [ -x "$DIR/.venv/bin/python" ]; then
    VENV=".venv"; ok "Python venv: $VENV"
else
    VENV="agents/.venv"; todo "No Python venv yet (step 1 creates it)"
fi
if "$DIR/$VENV/bin/python" -c "import anthropic" 2>/dev/null; then
    ok "Agent dependencies installed"
else
    todo "Agent dependencies not installed (step 1)"
fi
if grep -qE '^(ANTHROPIC_API_KEY|ANTHROPIC_AUTH_TOKEN)=.+' "$DIR/.env" 2>/dev/null \
   || [ -n "${ANTHROPIC_API_KEY:-}${ANTHROPIC_AUTH_TOKEN:-}" ]; then
    ok "Anthropic credentials found (needed only for the LLM agent)"
else
    todo "No ANTHROPIC_API_KEY — needed only for llm_agent.py without --replay-hijack"
fi
grep -qE '^HEADLESS_CLIENT_ID=.+' "$DIR/.env" 2>/dev/null \
    && ok "Headless client configured" \
    || todo "HEADLESS_CLIENT_ID/SECRET not in .env — needed only for headless_agent.py"
echo ""

# ── Commands ──────────────────────────────────────────────
cat <<EOF
${B}1. One-time: set up the agents' Python environment${R}
   cd agents
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ${D}# each new terminal: cd agents && source .venv/bin/activate && set -a && source ../.env && set +a${R}

${B}2. Policy enforcement (browser login via Duo SSO)${R}
   python3 hr_agent.py          ${D}# log in as HR user      → 6 allowed, 2 denied (finance writes)${R}
   python3 finance_agent.py     ${D}# log in as Finance user → 6 allowed, 2 denied (HR writes)${R}
   ${D}or run both, guided:  make demo${R}

${B}3. Other identity flows${R}
   python3 dcr_agent.py         ${D}# registers its own client on the fly; policy follows the user${R}
   python3 headless_agent.py    ${D}# client credentials, no browser; policy follows the client${R}

${B}4. LLM agent + prompt injection${R}  ${D}(docs/THREAT_MODEL.md)${R}
   python3 llm_agent.py --replay-hijack   ${D}# deterministic; no API key needed${R}
   python3 llm_agent.py                   ${D}# Claude picks the tools; needs ANTHROPIC_API_KEY${R}
   python3 llm_agent.py --expose-all      ${D}# model sees hidden tools; gateway still denies${R}
   ${D}HR user: injected payment approval → DENIED, injected salary change → EXECUTED${R}
   ${D}Reset mock data afterwards: make down && make setup && make up${R}

${B}5. Verify the decisions${R}
   Duo Admin → Reports → Client Authorization Log   ${D}# every allow/deny with user identity${R}
   docker logs authz-bridge                          ${D}# raw policy decisions${R}
   make status                                       ${D}# tunnel URL vs .env${R}

${B}If something fails${R}
   401 / invalid resource   → Duo Admin URLs don't match the tunnel (make status)
   403 on every tool        → gateway name changed; policy rules point at the old one
   Connection refused        → make check, then make logs
EOF
echo ""
