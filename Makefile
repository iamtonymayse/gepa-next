.PHONY: run lint typecheck test qa docker-build docker-run taste taste-fast

run:
	uvicorn innerloop.main:app --reload

lint:
	ruff check .

typecheck:
	mypy .

test:
	python -m pytest -q

qa: lint typecheck test

docker-build:
	docker build -t gepa-next .

docker-run:
	docker run -p 8000:8000 gepa-next

taste:
	python tools/taste_and_smell.py

taste-fast:
	python tools/taste_and_smell.py --fast
