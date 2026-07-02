.PHONY: setup up down demo logs check clean

setup:
	@bash scripts/setup.sh

up:
	docker compose up -d --build
	@echo ""
	@sleep 3
	@bash scripts/check-health.sh

down:
	docker compose down

demo:
	@bash scripts/demo.sh

logs:
	docker compose logs -f

check:
	@bash scripts/check-health.sh

clean:
	docker compose down -v --remove-orphans
	rm -rf gateway/secrets/*.key gateway/secrets/*.pem
	@echo "Cleaned up containers, volumes, and secrets."
