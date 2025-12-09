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
