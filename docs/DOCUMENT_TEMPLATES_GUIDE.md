# Document Templates Guide

Document templates enable DOCX/PDF/HTML export of job results with automatic metadata extraction.

## How It Works

```
Job Result → Extraction Prompt → Metadata → Template → DOCX/PDF/HTML
```

1. **Job completes** with a result (summary, translation, etc.)
2. **Extraction prompt** (LLM call) extracts metadata fields from the result
3. **Placeholders** in the template are replaced with extracted values
4. **DOCX/PDF/HTML** is generated for download or preview

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

# Export to HTML (for preview or embedding)
curl "http://localhost:8000/api/v1/jobs/{job_id}/export/html" -o result.html

# With specific template
curl "http://localhost:8000/api/v1/jobs/{job_id}/export/docx?template_id={uuid}" -o result.docx
```

## Metadata Extraction

Metadata extraction happens automatically at job submission time, only when the service's default template has custom placeholders defined. There are no default extraction fields - only template-defined custom placeholders are extracted.

Standard placeholders (`output`, `job_id`, `job_date`, `service_name`, etc.) are computed at export time and don't require LLM extraction.

## Export Formats

| Format | Description | Use Case |
|--------|-------------|----------|
| `docx` | Microsoft Word document | Editable documents, direct download |
| `pdf` | PDF via LibreOffice | Faithful rendering with template styles |
| `html` | HTML via mammoth | Quick preview, embedding in web pages |

### HTML Export Notes

The HTML export uses [mammoth](https://github.com/mwilliamson/python-mammoth) to convert DOCX to HTML. While mammoth handles basic formatting well, some complex template features may not render perfectly:

- **Supported**: Paragraphs, headings, bold/italic/underline, lists, tables, images (base64 embedded)
- **Limited**: Multi-column layouts, headers/footers, complex table borders
- **Not supported**: Page breaks, text boxes, shapes

For faithful rendering of complex templates, use PDF export instead.

## API Reference

See [Swagger](http://localhost:8000/docs) for full API. Key endpoints:

| Endpoint | Description |
|----------|-------------|
| `POST /templates` | Upload template (multipart) |
| `GET /templates` | List templates |
| `GET /templates/{id}/placeholders` | Get extracted placeholders |
| `GET /jobs/{id}/export/{format}` | Export job (docx/pdf/html) |
