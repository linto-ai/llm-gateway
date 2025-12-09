# Service Templates Guide

Service templates are blueprints for creating services with pre-configured settings.

## Overview

A **Service Template** defines:
- Service type (summary, translation, categorization, etc.)
- Default configuration (processing mode, temperature, chunking)
- Localized descriptions

Templates are stored in the `service_templates` database table and managed by administrators.

## API Reference

### List Templates

```http
GET /api/v1/service-templates?service_type=summary&is_public=true
```

### Get Template

```http
GET /api/v1/service-templates/{template_id}
```

### Create Service from Template

```http
POST /api/v1/service-templates/from-template/{template_id}
Content-Type: application/json

{
  "name": "my-service",
  "route": "my-service",
  "model_id": "uuid",
  "organization_id": "uuid",
  "customizations": {}
}
```

## Related

- **Flavor Presets**: Pre-configured flavor settings. See [Flavor Presets Guide](FLAVOR_PRESETS_GUIDE.md).
- **Synthetic Templates**: Test data for summarization. See below.

---

## Synthetic Templates (Test Data)

Synthetic templates are conversation transcripts for testing services.

### API

```http
GET /api/v1/synthetic-templates
GET /api/v1/synthetic-templates/{filename}/content
```

### Available Files

| File | Language | Type |
|------|----------|------|
| `en_perfect.txt` | English | Ground truth |
| `en_diarization_errors.txt` | English | Speaker splits |
| `en_full_errors.txt` | English | All errors |
| `fr_perfect.txt` | French | Ground truth |
| `fr_diarization_errors.txt` | French | Speaker splits |
| `fr_full_errors.txt` | French | All errors |
| `mixed_perfect.txt` | EN/FR | Ground truth |
| `mixed_diarization_errors.txt` | EN/FR | Speaker splits |
| `mixed_full_errors.txt` | EN/FR | All errors |
