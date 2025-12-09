# Document Templates Guide

Document templates enable DOCX/PDF export of job results with automatic metadata extraction.

## How It Works

```
Job Result → Extraction Prompt → Metadata → Template → DOCX/PDF
```

1. **Job completes** with a result (summary, translation, etc.)
2. **Extraction prompt** (LLM call) extracts metadata fields from the result
3. **Placeholders** in the template are replaced with extracted values
4. **DOCX/PDF** is generated for download

## Setup

### 1. Create an Extraction Prompt

The extraction prompt tells the LLM which fields to extract. Use placeholders with hints:

```
Extract the following from this document:

{{title: Main title or subject}}
{{date: Date mentioned, format YYYY-MM-DD}}
{{participants: List of people mentioned}}
{{summary: Brief 2-3 sentence summary}}
{{action_items: Bullet list of action items}}

Document:
{}

Fields to extract:
{}

Return JSON only.
```

- `{{field: hint}}` - Placeholder with extraction hint for the LLM
- `{}` - Will be replaced with the job result content
- Second `{}` - Will be replaced with the list of fields

### 2. Create a DOCX Template

Create a Word document with placeholders:

```
MEETING SUMMARY - {{date}}

Title: {{title}}

Participants: {{participants}}

Summary:
{{summary}}

Action Items:
{{action_items}}

Full Content:
{{output}}
```

- `{{output}}` is a reserved placeholder containing the full job result
- Other placeholders are filled from extracted metadata

### 3. Configure the Flavor

In the flavor settings, set:
- **Placeholder Extraction Prompt**: Select your extraction prompt
- **Upload Template**: Attach to the service

## Placeholder Syntax

| Syntax | Description |
|--------|-------------|
| `{{field}}` | Simple placeholder |
| `{{field: hint}}` | Placeholder with LLM extraction hint |
| `{{output}}` | Reserved: full job result (supports markdown formatting) |

The hint guides the LLM during extraction. Example:
```
{{sentiment: Overall tone - positive, negative, neutral, or mixed}}
```

## Using Templates

### Export via UI

1. Go to **Jobs** > completed job
2. Click **Export** > **DOCX** or **PDF**
3. Select template (or use default)
4. Download

### Export via API

```bash
# Export to DOCX
curl "http://localhost:8000/api/v1/jobs/{job_id}/export/docx" -o result.docx

# Export to PDF
curl "http://localhost:8000/api/v1/jobs/{job_id}/export/pdf" -o result.pdf

# With specific template
curl "http://localhost:8000/api/v1/jobs/{job_id}/export/docx?template_id={uuid}" -o result.docx
```

### Manual Metadata Extraction

Trigger extraction manually on a completed job:

```bash
curl -X POST "http://localhost:8000/api/v1/jobs/{job_id}/extract-metadata"
```

## Default Fields

If no template is configured, these fields are available by default:

`title`, `summary`, `participants`, `date`, `topics`, `action_items`, `sentiment`, `language`, `word_count`, `key_points`

## API Reference

See [Swagger](http://localhost:8000/docs) for full API. Key endpoints:

| Endpoint | Description |
|----------|-------------|
| `POST /templates` | Upload template (multipart) |
| `GET /templates` | List templates |
| `GET /templates/{id}/placeholders` | Get extracted placeholders |
| `GET /jobs/{id}/export/{format}` | Export job (docx/pdf) |
| `POST /jobs/{id}/extract-metadata` | Trigger extraction |
