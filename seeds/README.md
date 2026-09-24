# Seed Data Directory

This directory contains declarative seed data for the LLM Gateway application.

## Directory Structure

```
seeds/
├── README.md                    # This file
├── prompts/                     # Production prompts (versioned)
│   ├── summarize/
│   │   ├── manifest.json        # Prompt manifest
│   │   ├── user-en.md           # English user prompt
│   │   └── user-fr.md           # French user prompt
│   ├── extraction/
│   ├── categorization/
│   └── field-extraction/
├── services/                    # Public service catalog (no credentials), installed with --catalog
│   ├── compte-rendu/manifest.json   # display_order 0: first service returned by the API
│   └── ...
├── presets/                     # Flavor presets (versioned)
│   ├── summary-fast/manifest.json
│   ├── summary-quality/manifest.json
│   └── ...
└── dev/                         # GITIGNORED - Dev data with credentials
    ├── .gitkeep
    ├── providers/
    │   └── linagora-mistral/manifest.json
    └── services/
        └── summarize-en/manifest.json
```

## LinTO catalog

The gateway ships a catalog of meeting services built on Mistral Small class models, each with one
flavor, one prompt and one DOCX template:

| Route | Label | Position | Prompt | Template |
|---|---|---|---|---|
| compte-rendu | Compte rendu | 0 | linto-compte-rendu | linto-compte-rendu.docx |
| points-cles | Points clés | 10 | linto-points-cles | linto-points-cles.docx |
| tableau-de-suivi | Tableau de suivi | 20 | linto-tableau-de-suivi | linto-tableau-de-suivi.docx |
| brief-commercial | Brief commercial | 30 | linto-brief-commercial | linto-brief-commercial.docx |
| note-technique | Note technique | 40 | linto-note-technique | linto-note-technique.docx |

All flavors share the extraction prompt `linto-extraction-champs`. Templates are built by
`scripts/templates/` and rely on the template renderers (`docs/TEMPLATE_RENDERERS.md`).

Prompts and templates are seeded at every API start. The services need a model, so they are created
only on request, on a model that already exists:

```bash
docker exec llm-gateway-llm-gateway-1 python -m app.seeds.base_seed --catalog mistralai/mistral-small-3.2-24b-instruct
```

or at API start with `SEED_CATALOG_MODEL=<model identifier>`. A missing model only logs an error.

## Never overwriting a deployment

The seed runs automatically at each API start (`scripts/docker-entrypoint.sh`) and is non-destructive:
- a prompt that already exists is kept, even if its content differs from the seed
  (`--update-prompts` overwrites library prompts; flavors keep their own inline copy anyway);
- a global template whose French name exists is kept;
- a catalog service whose route exists is kept, flavors and templates included.

## Service order

`services.display_order` (migration 012) sorts `GET /api/v1/services`: ascending, then newest first.
Existing services get 100. Put a service first with `PATCH /api/v1/services/{id}` `{"display_order": 0}`
or from the admin UI (service form, « Position dans la liste »).

## Usage

### Seed production data (prompts + presets + templates)
```bash
docker exec llm-gateway-llm-gateway-1 python -m app.seeds.base_seed
```

### Include dev data (providers + services)
```bash
docker exec llm-gateway-llm-gateway-1 python -m app.seeds.base_seed --dev
```

### Seed specific category only
```bash
docker exec llm-gateway-llm-gateway-1 python -m app.seeds.base_seed --only prompts
docker exec llm-gateway-llm-gateway-1 python -m app.seeds.base_seed --only presets
docker exec llm-gateway-llm-gateway-1 python -m app.seeds.base_seed --only templates
```

## Manifest Schemas

### Prompt Manifest (seeds/prompts/*/manifest.json)

```json
{
  "name": "extraction",
  "description": {
    "en": "Metadata extraction prompts",
    "fr": "Prompts d'extraction de metadonnees"
  },
  "service_type": "summary",
  "prompt_type": "standard",
  "languages": ["en", "fr"],
  "version": "1.0.0",
  "files": {
    "user-en.md": {
      "prompt_category": "user",
      "prompt_name": "generic-metadata-extraction-en"
    }
  }
}
```

### Preset Manifest (seeds/presets/*/manifest.json)

```json
{
  "name": "summary-fast",
  "service_type": "summary",
  "description": {
    "en": "Fast summarization with lower quality",
    "fr": "Resume rapide avec qualite moindre"
  },
  "version": "1.0.0",
  "is_system": true,
  "config": {
    "temperature": 0.3,
    "top_p": 0.8,
    "output_type": "text",
    "processing_mode": "single_pass"
  }
}
```

### Dev Provider Manifest (seeds/dev/providers/*/manifest.json)

```json
{
  "name": "Mistral",
  "description": "Mistral",
  "provider_type": "openai_compatible",
  "api_base_url": "https://mydomain/api/v1",
  "api_key_env": "API_KEY",
  "api_key": "sk-xxxxx",
  "models": [
    {
      "name": "Mistral Small 3.1 24B",
      "model_identifier": "Mistral-Small-3.1-24B-Instruct-2503",
      "context_length": 8192,
      "max_generation_length": 4096
    }
  ]
}
```

### Dev Service Manifest (seeds/dev/services/*/manifest.json)

```json
{
  "name": "summarize-en",
  "route": "summarize-en",
  "service_type": "summary",
  "description": {
    "en": "English summarization service",
    "fr": "Service de resume en anglais"
  },
  "flavor": {
    "name": "default",
    "model_identifier": "Mistral-Small-3.1-24B-Instruct-2503",
    "provider_name": "LINAGORA-MISTRAL",
    "temperature": 0.2,
    "top_p": 0.7,
    "is_default": true,
    "user_prompt_name": "summarize-en"
  }
}
```

## API Key Configuration

For dev providers, you can configure API keys in two ways:

1. **Environment variable** (recommended): Set `api_key_env` to the name of an environment variable
2. **Direct value**: Set `api_key` directly (not recommended for production)

If both are set, the environment variable takes precedence.

## Adding New Prompts

1. Create a new directory under `seeds/prompts/`
2. Create a `manifest.json` with the prompt metadata
3. Create markdown files for each language/variant
4. Run `python -m app.seeds.base_seed --only prompts`

## Adding New Presets

1. Create a new directory under `seeds/presets/`
2. Create a `manifest.json` with the preset configuration
3. Run `python -m app.seeds.base_seed --only presets`

## Adding Dev Providers/Services

1. Create directories under `seeds/dev/providers/` or `seeds/dev/services/`
2. Create `manifest.json` files with your configuration
3. Run `python -m app.seeds.base_seed --dev`

Note: Dev data is gitignored and should contain sensitive credentials.
