.PHONY: setup restore up down demo logs check clean status next

setup:
	@bash scripts/restore-configs.sh

restore:
	@bash scripts/restore-configs.sh

up:
	@docker info > /dev/null 2>&1 || (echo ""; echo "  ✗ Docker is not running. Please start Docker Desktop and try again."; echo ""; exit 1)
	COMPOSE_PROFILES=agentgateway docker compose up -d --build
	@echo ""
	@sleep 5
	@bash scripts/check-health.sh || true
	@echo ""
	@bash scripts/check-tunnel.sh
	@echo "  Next: run 'make next' to see how to test the setup."
	@echo ""

down:
	COMPOSE_PROFILES=agentgateway docker compose down
	@pkill -f "cloudflared tunnel" 2>/dev/null || true
	@lsof -ti :8085 | xargs kill 2>/dev/null || true
	@echo "  Stopped containers, tunnel, and callback server."

next:
	@bash scripts/next-steps.sh

demo:
	@bash scripts/demo.sh

logs:
	COMPOSE_PROFILES=agentgateway docker compose logs -f

check:
	@bash scripts/check-health.sh

status:
	@echo ""
	@bash scripts/check-tunnel.sh
	@echo "─── Containers ───"
	@docker ps --format "  {{.Names}}\t{{.Status}}" 2>/dev/null || echo "  Docker not running"
	@echo ""

clean:
	COMPOSE_PROFILES=agentgateway docker compose down -v --remove-orphans
	@pkill -f "cloudflared tunnel" 2>/dev/null || true
	@lsof -ti :8085 | xargs kill 2>/dev/null || true
	rm -rf secrets/ config/
	@echo "Cleaned up containers, volumes, tunnel, and secrets."
