.PHONY: setup restore up down demo logs check clean

setup:
	@bash scripts/restore-configs.sh

restore:
	@bash scripts/restore-configs.sh

up:
	COMPOSE_PROFILES=agentgateway docker compose up -d --build
	@echo ""
	@sleep 5
	@bash scripts/check-health.sh

down:
	COMPOSE_PROFILES=agentgateway docker compose down

demo:
	@bash scripts/demo.sh

logs:
	COMPOSE_PROFILES=agentgateway docker compose logs -f

check:
	@bash scripts/check-health.sh

clean:
	COMPOSE_PROFILES=agentgateway docker compose down -v --remove-orphans
	rm -rf secrets/ config/
	@echo "Cleaned up containers, volumes, and secrets."
