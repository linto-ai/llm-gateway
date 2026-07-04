# 2.5.2

_2026_07_04_

Tokenizer resolution can no longer stall or crash a Celery worker, which was
wedging the job queue on closed sites (no HuggingFace egress).

Root cause: `AutoTokenizer.from_pretrained` fetched tokenizer files through the
HF xet CDN, a separate host with no usable timeout. A site that reached
huggingface.co but blackholed the xet CDN hung the fetch until the task time
limit. With prefork + `worker_prefetch_multiplier=1`, the message prefetched
behind a busy child stays unacked and, once past the broker visibility timeout,
is redelivered, so even fresh workers stop taking new tasks.

- Tokenizer resolution is now a single non-hanging, non-raising path: tiktoken /
  disk cache / bundled / bounded download / tiktoken estimate fallback. A job can
  no longer stall or die on tokenizer loading.
- HF xet disabled (`HF_HUB_DISABLE_XET`) plus bounded metadata/download timeouts,
  so a fetch fails fast instead of hanging. `TOKENIZER_DOWNLOAD_TIMEOUT` (default
  30 s) hard-caps a single download.
- Tokenizers baked into the image (`scripts/bake_tokenizers.py`: mistral family
  plus the tiktoken encodings, so the fallback works offline too) resolve with
  zero egress. `TOKENIZER_OFFLINE=1` skips any job-time fetch. Mount-based
  tokenizer dirs keep working unchanged: the writable cache is read first, the
  bundled set is purely additive.
- Celery backstop cut to soft 9 min / hard 10 min (`TASK_SOFT_TIME_LIMIT` /
  `TASK_TIME_LIMIT`), and the Redis broker visibility timeout pinned to 15 min
  (`BROKER_VISIBILITY_TIMEOUT`), kept above the hard limit so an in-flight or
  prefetched message is never redelivered before its task is force-killed.
- Stale/orphaned job cleanup now revokes the Celery task (`terminate=True`) so the
  worker slot is freed, not just the DB row marked failed.
- llm-admin tokenizer selector surfaces bundled/cached tokenizers (offline-ready
  first) and preloads one on demand with clear success/failure feedback.

---

# 2.5.1

_2026_07_02_

Hotfix: guardrails against unresponsive LLM providers. Before this release, a
provider endpoint that accepted the connection but never answered (dead
backend, proxy black-holing the request...) blocked the Celery worker forever:
the job stayed "started" with no error and no log, and the worker never took
another task.

- Explicit timeout on every provider HTTP call (`PROVIDER_REQUEST_TIMEOUT`,
  default 300 s; `PROVIDER_CONNECT_TIMEOUT`, default 10 s). Applies to all
  call paths, including streaming (read timeout between chunks)
- Celery task time limits as last-resort backstop (`TASK_SOFT_TIME_LIMIT`,
  default 90 min; `TASK_TIME_LIMIT`, soft + 5 min): a stuck task now ends as a
  `failed` job with a readable error instead of holding the worker forever
- SDK-internal silent retries disabled: tenacity owns the retry policy and logs
  every attempt (`LLM API retry n/N: <error>`)
- Surface the real provider exception in the job error ("Request timed out"
  instead of tenacity's opaque `RetryError[...]`)
- Debug-friendly logs across the chain:
  - API: `Dispatched job <id>: celery_task_id=... service=... flavor=... model=... provider=...`
  - worker: task start now logs job_id, model and provider URL
  - adapter: `LLM request ->` / `LLM response <- ... in N s (n retries)` /
    `LLM request FAILED` with duration, retry count and error

---

# 2.5.0

_2026_06_26_

- Multi-organization / user scoping for services and templates
  - `services` and `document_templates` can be granted to several organizations and/or users via list-based scoping (`allowed_organization_ids` / `allowed_user_ids`); legacy scalar `organization_id` / `user_id` columns are kept and back-compat-derived so existing clients (LinTO Studio) keep working
  - Service ↔ template links
- Template rework (#25)
  - New `conversation_name` and `organization_name` placeholders
  - Preserve embedded images during placeholder substitution
  - Template export fix
- Configurable logging
  - Selectable log sinks
  - Preserve tracebacks in error logs and stop logging user content
- Service types
  - Single source of truth for service types (drop dead divergent enums)
  - Allow `chat` in the `service_templates` service_type CHECK constraint
- API version 1.0.0 → 1.1.0; admin footer now reads the version from `package.json`
- DB migrations: 006 (chat service template constraint), 007 (job name metadata), 008 (multi-scope + service/template links)
- CI/CD: staging deploy stage, preprod auto-redeploy on `latest-unstable`, deploy SSH host/user moved to Jenkins credentials

---

# 2.3.2

_2026_04_17_

- Localized DOCX/PDF export
  - Add optional `timezone` query parameter to `GET /jobs/{id}/export` (IANA, e.g. `Europe/Paris`) to format `job_date` and `generated_at` placeholders; falls back to UTC on invalid input (#20)
  - Remap htmldocx hard-coded English styleIds (`Heading1`, `ListBullet`, `Title`, …) to the template's actual styleIds via the canonical `<w:name>`; restores look-and-feel on localized Word templates (#21)
- Bug fixes
  - Fix `proxy.ts` TypeScript error after Next.js 16 removed `request.ip`

---

# 2.3.1

_2026_03_11_

- Add access logs with timestamps for API (uvicorn) and frontend (Next.js proxy)
- Add timestamps to Celery worker logs

---

# 2.3.0

_2026_03_10_

- Security remediation
  - Upgrade python-multipart 0.0.16 → 0.0.22 (CVE-2026-24486, CVE-2024-53981)
  - Upgrade fastapi 0.115.3 → 0.115.12 (starlette transitive CVEs)
  - Upgrade next.js >=16.1.5, axios >=1.13.5, transitive deps (rollup, ajv, devalue, lodash)
  - Python runtime 3.11 → 3.12, Node runtime 20 → 22 LTS
  - CORS: default changed from wildcard `*` to mandatory explicit configuration
- Chat usage tracking and cost analytics
- Production DOCX report template (LINAGORA/LinTO branding)
- Bug fixes
  - Fix custom tokenizer input not showing when switching from preset
  - Fix tokenizer HuggingFace repo IDs for Mistral and Llama
  - Strip wrapping code fences from LLM output before DOCX conversion
  - DELETE endpoint for job result versions

---

# 2.2.2

_2026_03_01_

- Chat service type
  - New "chat" service type with system prompt configuration
  - Streaming chat completions endpoint with input validation limits
  - OpenAI adapter `stream_chat()` method with SSE token streaming
  - DB migration and system prompt seed
- API improvements
  - Service type config endpoint (`GET /api/v1/service-types/config/{code}`)
  - Fix flavor deletion URL in frontend API client
  - Sanitized error messages (no internal details leakage)
- Admin UI
  - Hide execute and templates tabs for chat services

---

# 2.2.1

## Patch Release - Real-time Progress Updates (2026-01-12)

### New Features

**Real-time Job Progress via WebSocket**
- Progress updates now published to Redis pub/sub during batch processing
- Clients receive percentage and phase updates (processing, reducing, extracting, categorizing)
- Enables real-time progress display in LinTO Studio frontend

### Changes
- `batch_manager.py`: Added Redis pub/sub publishing in `update_task()` method
- `services.py`: Pass `job_id` and `organization_id` to task data for progress broadcasting
- `celery_app.py`: Added `type: "job_update"` field to Redis messages for LinTO Studio compatibility

---

# 2.2.0

## Feature Release - Job TTL and Export Bug Fixes (2025-12-16)

### New Features

**Job TTL (Time-To-Live)**
- Jobs can now have an expiration date via `expires_at` field
- Flavors support `default_ttl_seconds` configuration to auto-expire jobs
- New endpoint `POST /api/v1/jobs/cleanup-expired` to delete expired jobs
- Frontend UI to configure TTL on service flavors
- Celery task support for automated cleanup

### Bug Fixes

**Version-Aware Export Extraction**
- Fixed: JIT extraction was losing placeholder descriptions when extracting for non-current versions
- Fixed: Template change was not triggering re-extraction (restored `template_changed` logic)
- Fixed: Frontend metadata display now falls back to `version_extractions` when `extracted_metadata` is empty

### Database Changes
- Added `expires_at` column to `jobs` table (nullable timestamp)
- Added `default_ttl_seconds` column to `service_flavors` table (nullable integer)
- Migration: `002_add_job_ttl.py`

### API Changes

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/jobs/cleanup-expired` | POST | Delete all jobs past their expiration date |

### Frontend Changes
- Flavor configuration now includes TTL settings
- Jobs list shows expiration status
- Job detail page shows expiration date

---

# 2.1.0

## Feature Release - User-Scoped Templates and Version-Aware Export (2025-12-14)

### New Features

**User-Scoped Document Templates**
- Templates now support three scope levels: system, organization, and user (personal)
- Users can upload their own DOCX templates via the `/api/v1/document-templates` endpoint
- Hierarchical visibility: users see system templates, org templates, and their personal templates
- Templates can be imported from higher scopes (system -> org -> user)

**Version-Aware Export**
- Export endpoint now supports `version_number` parameter for exporting specific job versions
- Per-version extraction cache: JIT metadata extraction is cached separately per version
- Extraction results stored in `job.result.version_extractions[version_number]`

**Template Scoping API**
- `organization_id` and `user_id` fields accept any string (supports MongoDB ObjectIds)
- GET `/api/v1/document-templates` accepts `organization_id`, `user_id`, and `include_system` filters
- DELETE `/api/v1/document-templates/{id}` with ownership validation

### API Changes

**Document Templates Endpoint**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/document-templates` | POST | Upload new template (multipart/form-data) |
| `/api/v1/document-templates` | GET | List templates with scope filtering |
| `/api/v1/document-templates/{id}` | GET | Get template details |
| `/api/v1/document-templates/{id}` | PUT | Update template metadata or file |
| `/api/v1/document-templates/{id}` | DELETE | Delete template |
| `/api/v1/document-templates/{id}/placeholders` | GET | Get template placeholders with metadata |
| `/api/v1/document-templates/{id}/download` | GET | Download original DOCX file |
| `/api/v1/document-templates/{id}/import` | POST | Copy template to lower scope |
| `/api/v1/document-templates/{id}/set-default` | POST | Set as default for a service |
| `/api/v1/document-templates/{id}/set-global-default` | POST | Set as global default |

**Export Endpoint Updates**
- `GET /api/v1/jobs/{id}/export/{format}?version_number=N` - Export specific version
- JIT extraction now uses version content when `version_number` specified
- Extraction cache is per-version in `version_extractions`

### Database Changes
- `document_templates` table: `organization_id` and `user_id` changed from UUID to VARCHAR(100)
- Added `scope` computed property: "system", "organization", or "user"

### Integration Notes
- LinTO Studio integration via `/api/publication/*` proxy endpoints
- Template upload forwarded with proper multipart handling
- User ID from JWT payload used for personal template scoping

---

# 2.0.0

## Major Release - Complete Platform Rewrite (2025-12-01)

This release represents a complete rewrite of the LLM Gateway, transforming it from a simple summarization service into a full-featured LLM gateway platform.

### Highlights
- Full database-backed configuration (PostgreSQL replacing Hydra YAML)
- Next.js 16 admin frontend with i18n support (EN/FR)
- Multi-provider LLM support with encrypted credentials
- Real-time job tracking via WebSocket
- Iterative document processing with configurable chunking
- DOCX export with customizable templates

### Architecture Changes
- Replaced Hydra YAML configuration with PostgreSQL database
- Added Alembic migrations for schema management
- Introduced service flavors for model configuration
- Added organization-scoped resource management

### Backend Features
- FastAPI with full async support
- Celery task queue with Redis broker
- Fernet encryption for API keys at rest
- Automatic tokenizer resolution (tiktoken + HuggingFace)
- Orphaned job detection and cleanup
- Retry logic with exponential backoff
- Model health verification with caching

### Frontend Features
- Next.js 16 with App Router
- Server/Client Components architecture
- TailwindCSS + shadcn/ui components
- French/English internationalization
- Real-time job status via WebSocket
- Analytics dashboard with usage metrics

### Processing Modes
- **single_pass**: Direct LLM call for short documents
- **iterative**: Batched processing with rolling context
- **map_reduce**: Iterative + final consolidation pass
- Auto-fallback when context exceeded

### API Surface
- RESTful endpoints for all resources (75+ endpoints)
- WebSocket streaming for job progress
- Swagger/OpenAPI documentation
- Provider model discovery

### Document Features
- DOCX template system with placeholders
- Metadata extraction from LLM output
- Template library with global templates
- PDF export via LibreOffice

### Database Schema
13 tables supporting full CRUD operations:
- organizations, providers, models
- services, service_flavors, service_versions
- prompts, service_templates
- jobs, job_result_versions
- flavor_usage, flavor_presets
- document_templates

---

## Previous Versions

### 1.1.0

- Migrated backend to FastAPI with full async support and WebSocket result streaming
- Replaced local vLLM models with Exaion-hosted models for improved scalability
- Integrated Celery for async task management and status tracking
- Improved sentence parsing using spaCy, with cleaner LLM output and better error handling

### 1.0.0 (Initial)
- Basic summarization service
- Hydra YAML configuration
- Single provider support

### 0.1.0

- mixtral rolling prompt
- cra, cred summarization
