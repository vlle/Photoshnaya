.PHONY: sync run lint prod-up prod-down dev-up dev-down test test-down

sync:
	uv venv --python 3.11
	uv sync --frozen --extra dev

run:
	uv run python app/bot.py

lint:
	uv run flake8 . --exclude=.venv,.uv-cache --count --select=E9,F63,F7,F82 --show-source --statistics
	uv run flake8 . --exclude=.venv,.uv-cache --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

prod-up:
	docker compose -f docker-compose.yml up --build -d

prod-down:
	docker compose -f docker-compose.yml down --remove-orphans

dev-up:
	docker compose -f docker-compose.dev.yml up --build -d

dev-down:
	docker compose -f docker-compose.dev.yml down -v --remove-orphans

test:
	docker compose -f docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from web

test-down:
	docker compose -f docker-compose.test.yml down -v --remove-orphans
