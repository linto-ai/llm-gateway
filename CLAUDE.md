# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LLM Gateway is an orchestration layer for LLM providers (OpenAI, vLLM, Ollama). It handles document chunking, job queuing, token tracking, and result management for production applications.

**Stack:**
- Backend: Python 3.11 (FastAPI, Celery, SQLAlchemy async, PostgreSQL)
- Frontend: TypeScript (Next.js 16, React 19, Zustand, shadcn/ui)
- Infrastructure: Redis (task broker), Docker Compose

## Common Commands

### Backend

```bash
# Run tests
pytest                              # All tests
pytest tests/test_jobs.py           # Single file
pytest -m "not slow"                # Skip slow tests
pytest -k "test_chunking"           # Pattern match

# Server (development)
python -m app                       # Start FastAPI server
celery -A app.http_server.celery_app worker  # Start Celery worker

# Database migrations
alembic upgrade head                # Apply migrations
alembic downgrade -1                # Rollback one
alembic revision --autogenerate -m "description"  # New migration
```

### Frontend

```bash
cd frontend
npm install
npm run dev                         # Development server
npm run build                       # Production build
npm run lint                        # ESLint
npm run format                      # Prettier
```

### Docker

```bash
docker compose up -d                # Production (works out-of-box)
docker compose -f docker-compose.dev.yml up --build  # Dev with hot-reload
docker compose up -d --scale celery-worker=4         # Scale workers
```

## Architecture

```
app/
├── api/v1/           # REST endpoints (19 modules)
├── backends/         # LLM processing (chunking, inference, batch management)
├── core/             # Config, database, exceptions, tokenizer mappings
├── models/           # SQLAlchemy ORM models (17 files)
├── schemas/          # Pydantic DTOs (18 files)
├── services/         # Business logic layer (22 files)
├── http_server/      # FastAPI app setup, Celery tasks, WebSocket
└── migrations/       # Alembic migrations

frontend/
├── app/[locale]/     # Next.js App Router (i18n: EN/FR)
├── components/       # React components (dashboard, jobs, services, ui)
├── stores/           # Zustand state management
├── schemas/          # Zod validation
└── hooks/            # Custom React hooks
```

### Key Processing Flow

1. Request → FastAPI endpoint → Job stored in PostgreSQL
2. Task queued to Redis
3. Celery worker processes: chunking → LLM inference → retries
4. Status updates via WebSocket
5. Result versioned and stored

### Processing Modes

- **Single Pass**: Direct LLM call for short documents
- **Iterative**: Batch processing with rolling context for long documents
- **Map-Reduce**: Iterative + final consolidation
- **Automatic Fallback**: Switch to iterative if context exceeded
- **Provider Failover**: Chain of backup flavors on API errors

### Key Parameters

- `create_new_turn_after`: Token threshold for splitting turns
- `max_new_turns`: Turns per batch (controls output granularity)
- `summary_turns`: Previous summaries kept in context
- `reduce_summary`: Enable final consolidation step
- `fallback_flavor_id`: Automatic fallback on context overflow
- `failover_flavor_id`: Failover on provider errors

## Important Patterns

### Database Session (async context manager)
```python
async with get_db() as session:
    result = await session.execute(stmt)
```

### Multi-tenancy
All queries filter by `organization_id`. Pass it when creating/executing services.

### Tokenizer Resolution
- tiktoken for OpenAI models
- HuggingFace transformers for others
- Override per-flavor via `tokenizer_name`

### Frontend State
- Zustand stores for client state
- React Query for server synchronization
- Zod schemas for form validation

## Testing

Tests use SQLite in-memory (via aiosqlite). Key fixtures in `tests/conftest.py`.

Markers:
- `slow`: Long-running tests
- `integration`: Requires running server

## Configuration

Key environment variables (see `.env.example`):
- `DATABASE_URL`: PostgreSQL async connection
- `SERVICES_BROKER`: Redis URL
- `ENCRYPTION_KEY`: Fernet key for API key encryption
- `API_MAX_RETRIES`, `API_RETRY_MIN_DELAY`, `API_RETRY_MAX_DELAY`: Retry config

## macOS Development (Docker)

Optimized Docker Compose for macOS with Apple Silicon support:

```bash
# Start all services (builds locally for ARM64)
docker compose -f docker-compose.macos.yml up --build

# Or in detached mode
docker compose -f docker-compose.macos.yml up -d --build

# View logs
docker compose -f docker-compose.macos.yml logs -f

# Stop services
docker compose -f docker-compose.macos.yml down
```

### Services URLs
- API: http://localhost:8000/docs
- Frontend: http://localhost:3000
- PostgreSQL: localhost:5432
- Redis: localhost:6379

### Features
- Native ARM64 builds (Apple Silicon)
- Volume mounts with `:cached` for better I/O performance
- Hot-reload for backend and frontend code
- No .env file required (sensible defaults)
