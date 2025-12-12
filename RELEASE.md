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
