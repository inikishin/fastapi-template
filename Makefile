install:
	pip install -r requirements.txt

run:
	python src/main.py

lint:
	.venv/bin/pre-commit run --all-files

test:
	.venv/bin/pytest

migrate:
	.venv/bin/alembic revision --autogenerate -m ${msg}

upgrade:
	.venv/bin/alembic upgrade head

downgrade:
	.venv/bin/alembic downgrade -1

history:
	.venv/bin/alembic history
