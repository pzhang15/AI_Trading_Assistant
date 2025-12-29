SHELL := /bin/sh
.PHONY: setup lint test run up down migrate format precommit

PROJECT=trade_guardian

setup:
	@echo "Installing dev tools with uv and setting up pre-commit..."
	uv pip install --system --no-cache -e .
	uv pip install --system --no-cache $(shell python -c "import tomllib,sys;print(' '.join(tomllib.load(open('pyproject.toml','rb')).get('tool',{}).get('uv',{}).get('dev-dependencies',[])))")
	python - << 'PY'\nimport os, shutil\nsrc = 'env.example'\ndst = '.env'\nif os.path.exists(src) and not os.path.exists(dst):\n    shutil.copyfile(src, dst)\n    print('Created .env from env.example')\nelse:\n    print('.env already exists or env.example missing')\nPY
	pre-commit install

lint:
	ruff check .
	black --check .
	mypy src

format:
	ruff check --fix .
	black .

test:
	pytest -q

run:
	uvicorn $(PROJECT).api.main:app --host 0.0.0.0 --port 8000 --reload

up:
	docker compose up -d --build

down:
	docker compose down -v

migrate:
	alembic upgrade head

precommit:
	pre-commit run --all-files


