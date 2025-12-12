# LLM Gateway API Integration Guide

Complete documentation for integrating with the LLM Gateway API.

**Base URL:** `http://your-host:8000/api/v1`
**Interactive Docs:** [Swagger UI](http://your-host:8000/docs) | [ReDoc](http://your-host:8000/redoc)

---

## Table of Contents

- [Core Concepts](#core-concepts)
- [Service Execution](#service-execution)
- [Job Management](#job-management)
- [Real-Time Updates (WebSocket)](#real-time-updates-websocket)
- [API Reference](#api-reference)
- [Placeholders](#placeholders)
- [Error Handling](#error-handling)
- [Complete Integration Example](#complete-integration-example)

---

## Core Concepts

### Services
A **Service** represents a configured LLM task (e.g., summarization, translation) with:
- Unique name and route
- One or more **Flavors** (model configurations)
- Input field requirements

### Flavors
A **Flavor** is a specific model configuration within a service:
- Links to a Model and Provider
- Contains parameters (temperature, top_p)
- Includes system/user prompt templates
- Supports iterative processing for long documents
- **Token limits inherited from Model** (see [Model Limits Guide](MODEL_LIMITS_GUIDE.md))

### Jobs
A **Job** tracks execution of a service request:
- Unique UUID
- Status flow: `queued` → `started` → `processing` → `completed` | `failed`
- Stores results and progress

---

## Service Execution

### Execute with JSON Input

```http
POST /api/v1/services/{service_id}/execute
Content-Type: application/json
```

**Request:**
```json
{
  "input": "Text to process...",
  "flavor_id": "uuid",        // Optional: specific flavor
  "flavor_name": "default",   // Optional: flavor by name
  "metadata": {},             // Optional: additional metadata
  "context": {                // Optional: for document categorization
    "tags": [
      {"name": "tag-name", "description": "What this tag represents"},
      {"name": "another-tag", "description": "Description of this tag", "category": "optional-grouping"}
    ],
    "allow_new_tags": false   // Optional: allow LLM to suggest new tags
  }
}
```

If neither `flavor_id` nor `flavor_name` is provided, the default flavor is used.

**Document Categorization:**

When `context.tags` is provided and the flavor has a `categorization_prompt` configured, the processed document will be analyzed and matched against the provided tags. The result will include a `categorization` field with:

```json
{
  "result": {
    "output": "...",
    "categorization": {
      "matched_tags": [
        {
          "name": "tag-name",
          "description": "Tag description",
          "confidence": 0.95,
          "mentions": 3
        }
      ],
      "suggested_tags": [],
      "unmatched_tags": ["tags-not-found-in-document"]
    }
  }
}
```

**Response (202 Accepted):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "service_id": "123e4567-e89b-12d3-a456-426614174000",
  "service_name": "summarize-en",
  "flavor_id": "789e0123-e45b-67d8-a901-234567890abc",
  "flavor_name": "default",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Execute with File Upload

```http
POST /api/v1/services/{service_id}/run
Content-Type: multipart/form-data
```

**Form Fields:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `flavor_id` | string | Yes | UUID of flavor |
| `file` | file | No* | File to process |
| `synthetic_template` | string | No* | Synthetic template filename |
| `temperature` | float | No | Override flavor temperature |
| `top_p` | float | No | Override flavor top_p |

*Either `file` OR `synthetic_template` required.

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/services/{service_id}/run" \
  -F "flavor_id=789e0123-e45b-67d8-a901-234567890abc" \
  -F "file=@/path/to/document.txt"
```

### Validate Execution (Dry Run)

Pre-check if content fits within model context limits before execution.

```http
POST /api/v1/services/{service_id}/validate-execution
Content-Type: multipart/form-data
```

**Form Fields:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `flavor_id` | string | Yes | UUID of flavor to validate against |
| `file` | file | No* | File to validate |
| `synthetic_template` | string | No* | Synthetic template filename |

*Either `file` OR `synthetic_template` required.

**Response (Single-pass flavor):**
```json
{
  "valid": true,
  "warning": null,
  "input_tokens": 7755,
  "max_generation": 12000,
  "context_length": 128000,
  "estimated_cost": 0.0234
}
```

**Response fields:**
| Field | Description |
|-------|-------------|
| `valid` | `true` if execution can proceed, `false` if content too large |
| `warning` | Warning message if close to limit (>80%) or content exceeds context |
| `input_tokens` | Actual token count (content + prompts) |
| `max_generation` | Max generation length from model config |
| `context_length` | Total context length from model |
| `estimated_cost` | Estimated cost based on flavor's cost_per_1k_tokens |

**Response (Iterative flavor):**
```json
{
  "valid": true,
  "warning": null
}
```

Iterative flavors always return `valid: true` since content is automatically chunked. Warnings may appear if:
- Reduce phase may exceed context (50% of input + reduce prompt > available context)
- Extraction prompt configured and input > 50% of available context
- Categorization prompt configured and input > 50% of available context

---

## Job Management

### List Jobs

```http
GET /api/v1/jobs?page=1&page_size=50&status=processing&service_id={uuid}
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `page` | int | Page number (default: 1) |
| `page_size` | int | Items per page (1-100, default: 50) |
| `status` | string | Filter by status |
| `service_id` | uuid | Filter by service |

### Get Job Status

```http
GET /api/v1/jobs/{job_id}
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "service_name": "summarize-en",
  "status": "processing",
  "progress": {
    "current": 5,
    "total": 10,
    "percentage": 50.0,
    "phase": "processing",
    "current_batch": 2,
    "total_batches": 4
  },
  "result": null,
  "error": null
}
```

### Additional Job Operations

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/jobs/{id}/cancel` | Cancel job |
| PATCH | `/jobs/{id}/result` | Update result |
| GET | `/jobs/{id}/metrics` | Get token metrics |
| GET | `/jobs/{id}/versions` | List versions |
| GET | `/jobs/{id}/versions/{n}` | Get specific version |
| POST | `/jobs/{id}/versions/{n}/restore` | Restore version |
| GET | `/jobs/{id}/export/{format}` | Export (docx/pdf) |

See [Swagger UI](http://your-host:8000/docs) for details.

---

## Real-Time Updates (WebSocket)

### Per-Job Monitoring

```
ws://your-host:8000/ws/jobs/{job_id}
```

### Global Jobs Monitoring

Monitor all jobs in real-time:

```
ws://your-host:8000/ws/jobs
```

### Message Format

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "event_type": "progress",
  "status": "processing",
  "progress": {
    "current": 5,
    "total": 10,
    "percentage": 50.0,
    "phase": "processing"
  },
  "result": null,
  "error": null,
  "timestamp": "2024-01-15T10:30:15Z"
}
```

### Event Types

| Event | Description |
|-------|-------------|
| `status_change` | Job status changed |
| `progress` | Processing progress update |
| `retry` | LLM API call retry |
| `error` | Non-fatal error |
| `complete` | Job finished |

### Status Values

| Status | Description |
|--------|-------------|
| `queued` | Waiting in queue |
| `started` | Started processing |
| `processing` | Actively processing |
| `completed` | Finished successfully |
| `failed` | Failed |
| `cancelled` | Cancelled by user |

### Processing Phases

The `phase` field in progress updates indicates the current processing stage:

| Phase | Description |
|-------|-------------|
| `processing` | Main content processing (single-pass or iterative batches) |
| `reducing` | Consolidating iterative results into final output |
| `extracting` | Extracting metadata from processed content |
| `categorizing` | Matching document against provided tags |

**Typical phase sequence:**
- **Single-pass:** `processing` → `extracting` (if metadata extraction enabled) → `categorizing` (if tags provided)
- **Iterative:** `processing` (multiple batches) → `reducing` → `extracting` → `categorizing`

### Retry Information

When `event_type` is `retry`:

```json
{
  "retry_info": {
    "attempt": 2,
    "max_attempts": 6,
    "delay_seconds": 4.5,
    "error_type": "RateLimitError",
    "error_message": "Rate limit exceeded"
  }
}
```

**Retry behavior:**
- Exponential backoff: ~1s → ~2s → ~4s → ~8s → ~16s → ~32-60s
- Retries: rate limits, timeouts, 5xx errors
- No retry: 400 errors (context exceeded, invalid request)

### JavaScript Example

```javascript
const ws = new WebSocket(`ws://localhost:8000/ws/jobs/${jobId}`);

ws.onmessage = (event) => {
  const update = JSON.parse(event.data);

  switch (update.event_type) {
    case "retry":
      console.warn(`Retry ${update.retry_info.attempt}/${update.retry_info.max_attempts}`);
      break;
    case "progress":
      console.log(`Progress: ${update.progress.percentage}%`);
      break;
    case "complete":
      console.log(update.status === "completed" ? update.result : update.error);
      break;
  }
};
```

### Python Example

```python
import asyncio, websockets, json

async def monitor_job(job_id):
    uri = f"ws://localhost:8000/ws/jobs/{job_id}"
    async with websockets.connect(uri) as ws:
        async for message in ws:
            update = json.loads(message)
            if update.get("event_type") == "complete":
                print(f"Result: {update['result']}")
                break

asyncio.run(monitor_job("550e8400-e29b-41d4-a716-446655440000"))
```

---

## API Reference

For complete API documentation with request/response schemas, see the interactive documentation:

- **[Swagger UI](http://your-host:8000/docs)** - Interactive API explorer
- **[ReDoc](http://your-host:8000/redoc)** - Alternative documentation view

### Available Resources

| Resource | Description |
|----------|-------------|
| Services | LLM task configurations with flavors |
| Flavors | Model configurations within services |
| Jobs | Execution tracking and results |
| Models | LLM model definitions with token limits |
| Providers | API provider connections (OpenAI, Ollama, etc.) |
| Prompts | Reusable prompt templates |
| Document Templates | DOCX/PDF export templates |
| Flavor Presets | Pre-configured flavor settings |

### Related Guides

- [Model Limits Guide](MODEL_LIMITS_GUIDE.md) - Token limits configuration
- [Flavor Presets Guide](FLAVOR_PRESETS_GUIDE.md) - Pre-configured settings
- [Document Templates Guide](DOCUMENT_TEMPLATES_GUIDE.md) - DOCX/PDF export

---

## Placeholders

### Standard Placeholders (Document Templates)

Used in document templates for DOCX/PDF export:

```
{{output}}         - Job result content
{{job_id}}         - Job UUID
{{service_name}}   - Service name
{{created_at}}     - Job creation timestamp
{{completed_at}}   - Job completion timestamp
```

### Extraction Placeholders (Prompt Templates)

Used in prompts for LLM-guided metadata extraction:

```
{{field_name: extraction hint for LLM}}
```

**Examples:**
```
{{title: The main title or subject of the document}}
{{date: Extract the date mentioned in format YYYY-MM-DD}}
{{participants: List of people mentioned as participants}}
{{summary: A brief 2-3 sentence summary}}
```

The hint guides the LLM during metadata extraction. Without a hint, use simple format: `{{field_name}}`

---

## Error Handling

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| `200` | Success |
| `201` | Created |
| `202` | Accepted (async job queued) |
| `204` | No Content (successful deletion) |
| `400` | Bad Request (invalid input) |
| `404` | Not Found |
| `409` | Conflict (duplicate resource) |
| `422` | Validation Error |
| `500` | Internal Server Error |
| `503` | Service Unavailable |

### Error Response Format

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Pagination

All list endpoints support pagination:

```http
GET /api/v1/jobs?page=2&page_size=25
```

**Response:**
```json
{
  "items": [...],
  "total": 150,
  "page": 2,
  "page_size": 25,
  "pages": 6
}
```

---

## Complete Integration Example

```python
import httpx, asyncio, websockets, json

BASE_URL = "http://localhost:8000/api/v1"
WS_URL = "ws://localhost:8000"

async def execute_and_monitor():
    async with httpx.AsyncClient() as client:
        # 1. List services
        response = await client.get(f"{BASE_URL}/services")
        service = response.json()["items"][0]

        # 2. Execute service
        response = await client.post(
            f"{BASE_URL}/services/{service['id']}/execute",
            json={"input": "Text to process...", "flavor_name": "default"}
        )
        job_id = response.json()["job_id"]

        # 3. Monitor via WebSocket
        async with websockets.connect(f"{WS_URL}/ws/jobs/{job_id}") as ws:
            async for message in ws:
                update = json.loads(message)
                if update["status"] == "completed":
                    print(f"Result: {update['result']}")
                    break
                elif update.get("progress"):
                    print(f"Progress: {update['progress']['percentage']}%")

asyncio.run(execute_and_monitor())
```

---

## Changelog

### v1.1.0
- **New:** Model limits endpoint and override fields
- **New:** Known models database (37+ models)
- **Deprecated:** `max_tokens` in flavor requests (inherited from model)
- **Documentation:** Added Model Limits Guide

### v1.0.0
- Initial stable API release
- Removed legacy endpoints
- WebSocket monitoring at `/ws/jobs/{job_id}` and `/ws/jobs`
