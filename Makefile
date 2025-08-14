.PHONY: setup run lint typecheck test fmt qa docker-build docker-run taste taste-fast

setup:
	python -m venv .venv && . .venv/bin/activate && pip install -e .[dev]

run:
	python -m innerloop --dev --host 0.0.0.0 --port ${PORT:-8000} --reload

lint:
	ruff check .

typecheck:
	mypy .

test:
	python -m pytest -q

fmt:
	black . && ruff --fix .

qa: lint typecheck test

docker-build:
	docker build -t gepa-next .

docker-run:
	docker run -p 8000:8000 gepa-next

taste:
	poetry run python tools/taste_and_smell.py

taste-fast:
	python tools/taste_and_smell.py --fast
