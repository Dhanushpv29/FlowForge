# FlowForge

**A distributed workflow orchestration engine** — define workflows as DAGs of tasks,
schedule them, run them on a pool of workers, and track every state change.


## Tech stack

FastAPI · Pydantic v2 · SQLAlchemy 2.0 · Alembic · PostgreSQL 16 · Redis 7 ·
pytest · Ruff · Docker Compose · GitHub Actions.


## Quick start

### Docker

```bash
docker compose up --build
```

Then open <http://localhost:8000/docs>. Compose starts PostgreSQL and Redis, runs the
migrations as a one-shot job, then starts the API.

### Local development

Requires Python 3.12 and a reachable PostgreSQL 16 and Redis.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
uvicorn flowforge.main:app --reload --app-dir src
```

```bash
curl localhost:8000/health   # {"status":"ok","service":"FlowForge","version":"0.1.0"}
curl localhost:8000/ready    # database + redis component status
```

## Running the tests

```bash
docker compose up -d db redis        # creates flowforge_test automatically
make test                            # pytest with coverage
make lint                            # ruff check + format check
```

Integration tests need real PostgreSQL and Redis. Locally they are **skipped with a clear
reason** if those services are unreachable; CI sets `REQUIRE_INTEGRATION=1` so an
unreachable service **fails** the build instead of silently skipping. Override the
connection strings with `TEST_DATABASE_URL` and `TEST_REDIS_URL`.

## Project layout

```
src/flowforge/
  api/routes/   HTTP endpoints (no business logic)
  services/     business rules
  models/       SQLAlchemy tables
  schemas/      Pydantic request/response models
  core/ db/     settings, logging, engine and sessions
alembic/        migration history
docs/           architecture, database, roadmap, ADRs
tests/          unit + integration tests
```
