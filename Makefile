COMPOSE ?= docker compose
LOADTEST_USERS ?= 200
SCENARIO ?= mixed_realistic.js

.PHONY: up down logs ps migrate migration seed seed-loadtest test e2e smoke lint openapi gen-client loadtest contention

up:
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f backend

ps:
	$(COMPOSE) ps

migrate:
	$(COMPOSE) exec backend alembic upgrade head

# usage: make migration m="add something"
migration:
	$(COMPOSE) exec backend alembic revision --autogenerate -m "$(m)"

seed:
	$(COMPOSE) exec backend python -m app.seed

seed-loadtest:
	$(COMPOSE) exec backend python -m app.seed --loadtest-users $(LOADTEST_USERS)

test:
	$(COMPOSE) exec backend pytest -q -p no:cacheprovider
	cd frontend && npm test

# Browser tests against the running stack (first time: cd frontend && npx playwright install chromium)
e2e:
	cd frontend && npm run e2e

# API-level smoke test (~90 checks) against the running stack; needs uv (or: pip install httpx)
smoke:
	uv run --no-project --with httpx==0.27.2 python scripts/api_smoke.py

lint:
	$(COMPOSE) exec backend ruff check --no-cache app tests alembic
	$(COMPOSE) exec backend mypy --cache-dir=/tmp/mypy-cache app
	cd frontend && npm run typecheck

openapi:
	curl -fsS http://localhost:8080/api/openapi.json -o openapi.json

gen-client: openapi
	cd frontend && npx openapi-typescript ../openapi.json -o src/api/schema.d.ts

# usage: make loadtest SCENARIO=scenarios/guest_browse.js
loadtest:
	$(COMPOSE) --profile loadtest run --rm -e TIME_SCALE=$(or $(TIME_SCALE),1) k6 run -o experimental-prometheus-rw /scripts/$(SCENARIO)

contention:
	$(MAKE) loadtest SCENARIO=scenarios/slot_contention.js
