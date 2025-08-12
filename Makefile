.PHONY: run lint typecheck test qa docker-build docker-run

run:
uvicorn innerloop.main:app --reload

lint:
ruff .

typecheck:
mypy .

test:
python -m pytest -q

qa: lint typecheck test

docker-build:
docker build -t gepa-next .

docker-run:
docker run -p 8000:8000 gepa-next
