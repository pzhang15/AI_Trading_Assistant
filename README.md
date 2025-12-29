## Trade Guardian

A clean, typed FastAPI scaffold for research and exploration. This repo provides a production-minded foundation with clear separation of concerns, first-class local development (Docker Compose), Celery workers, Postgres, Redis, and CI with linting and tests.

Note: No trading/execution is implemented yet.

### Features
- FastAPI app with `/health` endpoint
- Structured package layout: `api/`, `core/`, `integrations/`, `db/`, `workers/`, `utils/`, `tests/`
- Postgres (SQLAlchemy + Alembic) and Redis
- Celery worker scaffold
- Dockerfile + docker-compose for local dev
- Pre-commit (ruff, black, mypy, detect-secrets)
- GitHub Actions CI: lint + tests
- uv-based `pyproject.toml` with strict typing and formatting

### Project Layout
- `src/trade_guardian/api/` — FastAPI routes and app factory
- `src/trade_guardian/core/` — domain models and policy interfaces
- `src/trade_guardian/integrations/` — stubs for Coinbase and LLM
- `src/trade_guardian/db/` — SQLAlchemy models, session, migrations (Alembic)
- `src/trade_guardian/workers/` — Celery app and tasks
- `src/trade_guardian/utils/` — config and logging
- `tests/` — pytest tests

### Quickstart

1) Create `.env` from the example:

```bash
cp env.example .env
```

2) Start everything:

```bash
docker compose up -d --build
```

3) Visit the API:
- Docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

4) Run tests locally:

```bash
uv pip install --system --no-cache -e .
uv pip install --system --no-cache $(python -c "import tomllib,sys;print(' '.join(tomllib.load(open('pyproject.toml','rb')).get('tool',{}).get('uv',{}).get('dev-dependencies',[])))")
pytest -q
```

### Makefile Targets
- `make setup` — install project + dev deps, pre-commit, and create `.env`
- `make lint` — ruff, black --check, mypy
- `make format` — ruff --fix, black
- `make test` — pytest
- `make run` — run API with uvicorn (reload)
- `make up` / `make down` — docker compose up/down
- `make migrate` — Alembic upgrade head

### Migrations

The Alembic configuration is in `alembic.ini` with migrations under `src/trade_guardian/db/migrations`.

Example commands:
```bash
alembic revision -m "init"
alembic upgrade head
```

### Notes
- Configuration uses environment variables only (see `env.example` for available vars).
- Keep code typed, documented, and minimal.
- Detect secrets is enabled via pre-commit hooks; avoid real secrets in the repo.
