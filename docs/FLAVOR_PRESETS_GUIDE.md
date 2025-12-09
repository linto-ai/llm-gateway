# Flavor Presets Guide

Flavor presets are pre-configured templates for service flavors. Apply a preset to quickly configure processing mode and parameters.

## Built-in Presets

| Preset | Mode | Description |
|--------|------|-------------|
| `single-pass` | single_pass | Process entire document in one LLM call. Auto-fallback to iterative if too long. |
| `iterative` | iterative | Process in batches with rolling context. For long documents. |

### single-pass

```json
{
  "temperature": 0.2,
  "top_p": 0.8,
  "processing_mode": "single_pass",
  "auto_fallback_to_iterative": true
}
```

### iterative

```json
{
  "temperature": 0.2,
  "top_p": 0.7,
  "processing_mode": "iterative",
  "reduce_summary": true,
  "consolidate_summary": true,
  "create_new_turn_after": 150,
  "summary_turns": 3,
  "max_new_turns": 12
}
```

## Using Presets

### Web UI

1. Navigate to **Services** > select a service > **Add Flavor**
2. Select a preset from the dropdown
3. Customize settings as needed
4. Save

### API

```bash
# List presets
curl http://localhost:8000/api/v1/flavor-presets

# Apply preset to create a flavor
curl -X POST "http://localhost:8000/api/v1/flavor-presets/{preset_id}/apply" \
  -H "Content-Type: application/json" \
  -d '{"service_id": "uuid", "model_id": "uuid", "flavor_name": "my-flavor"}'
```

## Creating Custom Presets

Add a directory to `seeds/presets/` with a `manifest.json`:

```json
{
  "name": "my-preset",
  "description": {
    "en": "English description",
    "fr": "Description en francais"
  },
  "version": "1.0.0",
  "is_system": false,
  "config": {
    "temperature": 0.3,
    "processing_mode": "single_pass"
  }
}
```

Then run `python -m app.seeds.base_seed --only presets` to load.

## Configuration Fields

| Field | Description |
|-------|-------------|
| `temperature` | Creativity (0.0-2.0) |
| `top_p` | Nucleus sampling (0.0-1.0) |
| `processing_mode` | `single_pass` or `iterative` |
| `output_type` | `text` or `json` |
| `auto_fallback_to_iterative` | Auto-switch if content exceeds context |
| `create_new_turn_after` | Token threshold for splitting turns |
| `summary_turns` | Context turns to keep |
| `max_new_turns` | Turns per batch |
| `reduce_summary` | Enable final consolidation step |

See [Swagger](http://localhost:8000/docs) for full API reference.
