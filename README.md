# LLM Gateway

> **TL;DR**: LLM Gateway is an orchestration layer that exposes high-level API services (extraction, summarization, etc.) on top of LLM inference engines,
>  managing context overflow, job tracking, and result consistency for production applications.

## Deployment Model

LLM Gateway is designed as an **internal backend service**, not a public-facing API:

- **No built-in authentication** - Deploy behind your application's existing auth layer
- **No API key management** - Your backend calls LLM Gateway directly
- **Multi-tenant support** - Use `organization_id` to isolate services and jobs between tenants
- **Trust boundary** - LLM Gateway trusts all incoming requests; secure at the network level

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Your App       │────▶│  Your Backend   │────▶│  LLM Gateway    │
│  (public)       │     │  (auth, authz)  │     │  (internal)     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

Pass `organization_id` when creating / executing services and to filter jobs and results per tenant.

## Why LLM Gateway?

Calling LLM APIs directly works for simple use cases, but production applications face real challenges:

- **Context limits**: Long documents exceed model context windows, causing failures
- **No job management**: Difficult to track progress, handle failures, or manage concurrent requests
- **Cost unpredictability**: Token usage and costs are unknown until after processing
- **No result management**: No caching, versioning, or structured output handling

LLM Gateway solves these problems with a service-oriented architecture that handles document chunking, job queuing with real-time updates, token tracking with cost estimation, and comprehensive result management including caching and versioning.

## The Problem: Without LLM Gateway

Each application implementing LLM features must handle its own complexity:

```
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐     │
│  │ Messaging App   │     │ Document App    │     │ Meeting App     │     │
│  │                 │     │                 │     │                 │     │
│  │ Feature:        │     │ Feature:        │     │ Feature:        │     │
│  │ "Email Response"│     │ "Doc Formatting"│     │ "ASR Summary"   │     │
│  │                 │     │                 │     │                 │     │
│  │ - retry logic   │     │ - retry logic   │     │ - retry logic   │     │
│  │ - job tracking  │     │ - job tracking  │     │ - job tracking  │     │
│  │ - token count   │     │ - token count   │     │ - token count   │     │
│  │ - long doc      │     │ - long doc      │     │ - long doc      │     │
│  │   handling      │     │   handling      │     │   handling      │     │
│  └────────┬────────┘     └────────┬────────┘     └────────┬────────┘     │
│           │                       │                       │              │
│           │    DUPLICATED CODE    │    DUPLICATED CODE    │              │
│           ▼                       ▼                       ▼              │
│  ┌───────────────────────────────────────────────────────────────────┐   │
│  │                         OpenAI / vLLM API                         │   │
│  └───────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘

Issues:
• Document too long → FAILURE
• API rate limit → Silent failure
• No visibility on running jobs
• Costs known only at end of month
• Every team reinvents the wheel
```

## The Solution: With LLM Gateway

```
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐     │
│  │ Messaging App   │     │ Document App    │     │ Meeting App     │     │
│  │                 │     │                 │     │                 │     │
│  │ (business logic │     │ (business logic │     │ (business logic │     │
│  │  only)          │     │  only)          │     │  only)          │     │
│  └────────┬────────┘     └────────┬────────┘     └────────┬────────┘     │
│           │                       │                       │              │
│           │         POST /api/v1/services/{id}/execute    │              │
│           │         WS   /ws/jobs/{id}                    │              │
│           └───────────────────────┼───────────────────────┘              │
│                                   ▼                                      │
│  ┌───────────────────────────────────────────────────────────────────┐   │
│  │                         LLM GATEWAY                               │   │
│  │                                                                   │   │
│  │   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐             │   │
│  │   │ Service     │   │ Service     │   │ Service     │             │   │
│  │   │ "Email      │   │ "Doc        │   │ "Meeting    │   ...       │   │
│  │   │  Response"  │   │  Formatting"│   │  Summary"   │             │   │
│  │   └─────────────┘   └─────────────┘   └─────────────┘             │   │
│  │                                                                   │   │
│  │   Common infrastructure:                                          │   │
│  │   • Auto chunking (all languages)   • Retry + backoff             │   │
│  │   • Job queue (Celery)              • Token/cost tracking         │   │
│  │   • Real-time WebSocket             • DOCX/PDF export             │   │
│  └───────────────────────────┬───────────────────────────────────────┘   │
│                               ▼                                          │
│           ┌───────────────────────────────────────────────┐              │
│           │          OpenAI / vLLM / Ollama API           │              │
│           └───────────────────────────────────────────────┘              │
└──────────────────────────────────────────────────────────────────────────┘

Result:
• Uniform integration: same API for all services
• Document too long → auto chunking, success
• Rate limit → transparent retry, success
• Real-time job monitoring via WebSocket
• Costs tracked per request
```

**Read more:** [How LLM Gateway Works](docs/HOW_IT_WORKS.md)

## How It Compares

Several open-source solutions exist for routing requests to multiple LLM providers:

- **[LiteLLM](https://github.com/BerriAI/litellm)** - Python SDK/proxy supporting 100+ providers with unified OpenAI format
- **[TensorZero](https://github.com/tensorzero/tensorzero)** - High-performance Rust gateway (<1ms latency)
- **[Portkey](https://github.com/Portkey-AI/gateway)** - AI gateway with caching, observability, guardrails

These are primarily **proxies/routers** - they forward requests to LLMs with added features like load balancing and retries. LLM Gateway goes further by handling **document processing logic**:

| Feature                    | LiteLLM / Portkey / etc. | LLM Gateway                      |
|----------------------------|--------------------------|----------------------------------|
| Multi-provider routing     | Yes                      | Yes                              |
| Cost tracking & caching    | Yes                      | Yes                              |
| Iterative processing       | No                       | Yes (chunking, rolling context)  |
| Async job queue            | Limited                  | Yes (Celery, priorities)         |
| Long documents             | Client-side handling     | Gateway-side handling            |
| Result versioning          | No                       | Yes                              |
| DOCX/PDF export            | No                       | Yes (with templates)             |
| Dynamic placeholder extraction | No                   | Yes (LLM-based)                  |
| Output granularity control | No                       | Yes (batch size → detail level)  |


## Quick Start

```bash
git clone https://github.com/linto-ai/llm-gateway.git
cd llm-gateway
docker compose up -d

# API: http://localhost:8000/docs
# Frontend: http://localhost:8001
```

That's it! The default configuration works out-of-the-box. Database migrations and seed data (prompts, presets, document templates) are applied automatically on first start.

To customize settings, copy `.env.example` to `.env` and edit as needed.

For development with hot-reload:
```bash
cp .env.example .env  # Required for dev mode
docker compose -f docker-compose.dev.yml up --build
```

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Frontend   │────▶│  FastAPI    │────▶│  Celery     │
│  (Next.js)  │     │  (REST/WS)  │     │  (Workers)  │
└─────────────┘     └─────────────┘     └─────────────┘
                           │                   │
                    ┌──────┴──────┐     ┌──────┴──────┐
                    │ PostgreSQL  │     │   Redis     │
                    │ (Services,  │     │  (Tasks,    │
                    │  Jobs, etc) │     │   Broker)   │
                    └─────────────┘     └─────────────┘
```

## Processing Modes

The gateway supports two processing modes for handling documents of varying lengths:

| Mode            | Description                              | Use Case                                               |
|-----------------|------------------------------------------|--------------------------------------------------------|
| **Single Pass** | Process entire document in one LLM call  | Short documents that fit in context window             |
| **Iterative**   | Process in batches with rolling context  | Long documents (ASR transcriptions), progressive output|

### Automatic Fallback

When a document exceeds the context window of a single-pass flavor, the gateway can automatically fall back to an iterative flavor:

```json
{
  "fallback_applied": true,
  "original_flavor_name": "fast-single-pass",
  "flavor_name": "iterative-fallback",
  "fallback_reason": "Input (45000 tokens) exceeds context limit (32000 available)"
}
```

Configure fallback in flavor settings: `fallback_flavor_id` + `auto_fallback_to_iterative`.

### Provider Failover

When a provider or model becomes unavailable (API errors, rate limits, downtime), the gateway can automatically switch to an alternative:

```json
{
  "failover_flavor_id": "uuid-of-backup-flavor",
  "failover_applied": true,
  "original_flavor_name": "gpt-4-primary",
  "flavor_name": "claude-backup",
  "failover_reason": "Provider unavailable: 503 Service Unavailable"
}
```

Configure failover chains to ensure service continuity even when primary providers fail.

### Iterative Processing (for ASR / Long Documents)

For long documents that exceed context limits, the gateway processes content in batches:

1. **Turn normalization** (`create_new_turn_after`): Splits long turns into smaller chunks using universal sentence segmentation (works with all languages)
2. **Batch creation** (`max_new_turns`): Groups turns into batches sent to the LLM with rolling context

**What is a "turn"?** A turn is a line or paragraph separated by newline. In ASR context, turns can have a speaker prefix (`Speaker : text`). The gateway handles both formats transparently.

| Parameter                | Description                                             |
|--------------------------|---------------------------------------------------------|
| `create_new_turn_after`  | Token threshold for splitting long turns                |
| `max_new_turns`          | Turns per batch - controls output granularity           |
| `summary_turns`          | Previous summary turns kept in context                  |
| `reduce_summary`         | Enable final consolidation step on iterative processing |

**Controlling output detail**: Fewer turns per batch = more LLM passes = more detailed output preserving individual speaker interventions.

### Tokenizer Management

LLM Gateway includes integrated tokenizer management supporting both tiktoken (OpenAI) and HuggingFace tokenizers. This ensures accurate token counting for any model, with per-flavor tokenizer override capability.

### Metadata Extraction & Document Categorization

After processing, the gateway can automatically extract structured metadata from results using a configurable extraction prompt. Fields are defined via document templates attached to the service.

**Document Categorization**: Pass tags at execution time to classify documents:

```bash
curl -X POST ".../execute" -d '{
  "input": "Meeting transcript...",
  "context": {
    "tags": [
      {"name": "project-update", "description": "Project status discussions"},
      {"name": "budget", "description": "Financial topics"}
    ]
  }
}'
```

Response includes matched tags with confidence scores:
```json
{
  "categorization": {
    "matched_tags": [{"name": "project-update", "confidence": 0.95, "mentions": 3}],
    "unmatched_tags": ["budget"]
  }
}
```

## Configuration

Create a `.env` file:

| Variable             | Description                  | Default                            |
|----------------------|------------------------------|------------------------------------|
| `DATABASE_URL`       | PostgreSQL connection string | `postgresql+asyncpg://...`         |
| `SERVICES_BROKER`    | Redis broker URL             | `redis://task-broker-redis:6379/0` |
| `ENCRYPTION_KEY`     | Key for encrypting API keys  | (required)                         |
| `CELERY_WORKERS`     | Celery worker count          | `1`                                |

### LLM API Retry Configuration

The gateway automatically retries failed LLM API calls (rate limits, timeouts, 5xx errors) using exponential backoff.

| Variable              | Description                             | Default |
|-----------------------|-----------------------------------------|---------|
| `API_MAX_RETRIES`     | Maximum retry attempts                  | `6`     |
| `API_RETRY_MIN_DELAY` | Minimum delay between retries (seconds) | `1`     |
| `API_RETRY_MAX_DELAY` | Maximum delay between retries (seconds) | `60`    |

## API Endpoints

| Endpoint                       | Method | Description          |
|--------------------------------|--------|----------------------|
| `/api/v1/services`             | GET    | List all services    |
| `/api/v1/services/{id}/execute`| POST   | Execute a service    |
| `/api/v1/jobs/{id}`            | GET    | Get job status       |
| `/ws/jobs/{id}`                | WS     | Real-time job updates|

```bash
# Execute a service
curl -X POST "http://localhost:8000/api/v1/services/{service_id}/execute" \
  -H "Content-Type: application/json" \
  -d '{"input": "Text to process...", "flavor_name": "default"}'

# Monitor job via WebSocket
wscat -c "ws://localhost:8000/ws/jobs/{job_id}"
```

## Production Deployment

### Docker Compose Deployment

Two Docker Compose configurations are available:

| File | Use Case | Description |
|------|----------|-------------|
| `docker-compose.yml` | Production (default) | Works out-of-the-box, uses published images |
| `docker-compose.dev.yml` | Development | Hot-reload, volume mounts, requires `.env` |

```bash
# Quick start (works immediately with defaults)
docker compose up -d

# Or with custom configuration
cp .env.example .env
vim .env  # Edit settings
docker compose up -d
```

### Environment Configuration

Create a `.env` file with production values:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:password@postgres:5432/llm_gateway

# Redis broker
SERVICES_BROKER=redis://redis:6379/0

# Security - generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY=your-fernet-key-here

# CORS origins (comma-separated)
CORS_ORIGINS=https://your-domain.com

# Frontend URLs
NEXT_PUBLIC_API_URL=https://api.your-domain.com
NEXT_PUBLIC_WS_URL=wss://api.your-domain.com
```

### Scaling Celery Workers

Adjust `CELERY_WORKERS` environment variable to scale processing capacity:

```bash
# In docker-compose.yml or .env
CELERY_WORKERS=4  # Number of concurrent task workers
```

For high-throughput deployments, consider running dedicated Celery worker containers:

```bash
docker compose up -d --scale celery-worker=4
```

## Documentation

- **[How It Works](docs/HOW_IT_WORKS.md)** - Architecture and processing modes
- **[API Integration](docs/API_INTEGRATION.md)** - Complete integration guide
- **[Model Limits Guide](docs/MODEL_LIMITS_GUIDE.md)** - Token limits configuration
- **[Flavor Presets Guide](docs/FLAVOR_PRESETS_GUIDE.md)** - Pre-configured settings
- **[Document Templates Guide](docs/DOCUMENT_TEMPLATES_GUIDE.md)** - DOCX export
- **[Security Guide](docs/SECURITY.md)** - Credential rotation and security

## License

Copyright (c) 2024-2025 LINAGORA - [LinTO.ai](https://linto.ai)

[AGPL-3.0](LICENSE)
