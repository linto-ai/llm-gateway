# Model Token Limits Guide

This guide explains how LLM Gateway manages model token limits and how to configure them correctly for optimal performance.

## Table of Contents

1. [Understanding Token Limits](#understanding-token-limits)
2. [How Limits Are Discovered](#how-limits-are-discovered)
3. [Known Models Database](#known-models-database)
4. [Setting Manual Overrides](#setting-manual-overrides)
5. [API Reference](#api-reference)
6. [Troubleshooting](#troubleshooting)

---

## Understanding Token Limits

Every Large Language Model (LLM) has two fundamental token limits:

### Context Window (Context Length)

The **context window** is the total number of tokens the model can process in a single request. This includes both:
- Your input text (prompt, conversation history, documents)
- The model's generated output

**Example sizes:**
| Model | Context Window |
|-------|----------------|
| GPT-4o | 128,000 tokens (~300 pages) |
| Claude 3.5 Sonnet | 200,000 tokens (~500 pages) |
| Llama 3.1 | 128,000 tokens (~300 pages) |
| Mistral Large | 128,000 tokens (~300 pages) |

### Generation Limit (Max Output)

The **generation limit** (also called `max_output` or `max_generation_length`) is the maximum number of tokens the model can generate in a single response. This is always smaller than the context window.

**Example sizes:**
| Model | Max Output |
|-------|------------|
| GPT-4o | 16,384 tokens (~40 pages) |
| Claude 3.5 Sonnet | 8,192 tokens (~20 pages) |
| Claude Sonnet 4 | 64,000 tokens (~160 pages) |
| Llama 3.1 | 4,096 tokens (~10 pages) |

### The Formula

```
Available Input = Context Window - Generation Limit
```

**Example:** If a model has:
- Context Window: 128,000 tokens
- Generation Limit: 16,000 tokens
- **Available for Input: 112,000 tokens**

This means you can send up to ~112K tokens of input and still have room for the model to generate a full-length response.

---

## How Limits Are Discovered

LLM Gateway uses a multi-tier approach to determine model limits:

### Priority Order

1. **Manual Override** (highest priority)
   - User-configured values via the UI or API
   - Always trusted when set

2. **Provider API** (when available)
   - Some providers (like OpenRouter) return `context_length` in their API
   - Marked as "discovered" in the UI

3. **Known Models Database**
   - Built-in database of documented model limits
   - Covers major models from OpenAI, Anthropic, Mistral, Meta (Llama), DeepSeek, Qwen
   - Marked as "documented" in the UI

4. **Estimation** (fallback)
   - Conservative estimates when no other data is available
   - Default: 4,096 context, 2,048 max output
   - Marked as "estimated" in the UI - **verify these values!**

### Limits Source Indicators

In the UI, each model displays a badge indicating where its limits come from:

| Badge | Meaning | Action Needed |
|-------|---------|---------------|
| 🔵 **Manual** | User-configured override | None - trusted values |
| 🟢 **Documented** | From known models database | Generally accurate |
| 🟢 **Discovered** | From provider API | Generally accurate |
| 🟡 **Estimated** | Fallback heuristic | **Verify and override if wrong** |

---

## Known Models Database

LLM Gateway includes a comprehensive database of model limits. Here are the supported model families:

### OpenAI
| Model Pattern | Context | Max Output |
|---------------|---------|------------|
| gpt-4o | 128,000 | 16,384 |
| gpt-4o-mini | 128,000 | 16,384 |
| gpt-4-turbo | 128,000 | 4,096 |
| gpt-4 | 8,192 | 4,096 |
| gpt-3.5-turbo | 16,385 | 4,096 |
| o1 | 200,000 | 100,000 |
| o1-mini | 128,000 | 65,536 |
| o1-preview | 128,000 | 32,768 |
| o3-mini | 200,000 | 100,000 |

### Anthropic
| Model Pattern | Context | Max Output |
|---------------|---------|------------|
| claude-sonnet-4 | 200,000 | 64,000 |
| claude-3-5-sonnet | 200,000 | 8,192 |
| claude-3-opus | 200,000 | 4,096 |
| claude-3-haiku | 200,000 | 4,096 |

### Mistral
| Model Pattern | Context | Max Output |
|---------------|---------|------------|
| mistral-large | 128,000 | 8,192 |
| mistral-medium | 32,000 | 8,192 |
| mistral-small | 32,000 | 8,192 |
| mistral-nemo | 128,000 | 4,096 |
| codestral | 32,000 | 8,192 |
| mixtral | 32,000 | 4,096 |

### Meta (Llama)
| Model Pattern | Context | Max Output |
|---------------|---------|------------|
| llama-3.3 | 128,000 | 4,096 |
| llama-3.2 | 128,000 | 4,096 |
| llama-3.1 | 128,000 | 4,096 |
| llama-3 | 8,192 | 2,048 |
| llama-2 | 4,096 | 2,048 |

### DeepSeek
| Model Pattern | Context | Max Output |
|---------------|---------|------------|
| deepseek-v3 | 64,000 | 8,192 |
| deepseek-r1 | 64,000 | 8,192 |
| deepseek-coder | 16,000 | 4,096 |
| deepseek-chat | 32,000 | 4,096 |

### Qwen
| Model Pattern | Context | Max Output |
|---------------|---------|------------|
| qwen-2.5 / qwen2.5 | 131,072 | 8,192 |
| qwen-2 / qwen2 | 32,768 | 8,192 |
| qwen-max | 32,768 | 8,192 |
| qwen-plus | 131,072 | 8,192 |
| qwen-turbo | 131,072 | 8,192 |

### Other Models
| Model Pattern | Context | Max Output |
|---------------|---------|------------|
| phi-3 / phi-4 | 128,000 | 4,096 |
| gemma-2 | 8,192 | 4,096 |
| gemma | 8,192 | 4,096 |
| command-r | 128,000 | 4,096 |
| command | 4,096 | 4,096 |

**Note:** Pattern matching is case-insensitive and uses substring matching. For example, `Mistral-Small-3.1-24B-Instruct-2503` will match the `mistral-small` pattern.

---

## Setting Manual Overrides

When the discovered or estimated values are incorrect, you can set manual overrides.

### Via the Web UI

1. Navigate to **Models** in the sidebar
2. Click on the model you want to configure
3. Click **Edit** to open the edit form
4. Scroll to the **Token Limits** section
5. You'll see:
   - **Discovered values** - what was found from the provider/database
   - **Source indicator** - discovered, documented, or estimated
   - **Manual override fields** - input fields for corrections

6. Enter the correct values in the override fields:
   - **Actual context window**: The real context length in tokens
   - **Actual generation limit**: The real max output in tokens

7. Click **Save** to apply the overrides

### Via the API

```http
PATCH /api/v1/models/{model_id}
Content-Type: application/json

{
  "context_length_override": 128000,
  "max_generation_length_override": 16384
}
```

**Response:**
```json
{
  "id": "uuid",
  "model_name": "custom-model",
  "context_length": 128000,
  "max_generation_length": 16384,
  "limits_source": "manual",
  "context_length_override": 128000,
  "max_generation_length_override": 16384
}
```

### Clearing Overrides

To remove manual overrides and revert to discovered/estimated values:

```http
PATCH /api/v1/models/{model_id}
Content-Type: application/json

{
  "context_length_override": null,
  "max_generation_length_override": null
}
```

---

## API Reference

### Get Model Limits

Retrieve the effective token limits for a specific model.

```http
GET /api/v1/models/{model_id}/limits
```

**Response:**
```json
{
  "model_id": "550e8400-e29b-41d4-a716-446655440000",
  "model_name": "gpt-4o",
  "context_length": 128000,
  "max_generation_length": 16384,
  "available_for_input": 111616,
  "source": "documented",
  "discovered_values": {
    "context_length": 128000,
    "max_generation_length": 16384
  }
}
```

**Fields:**
| Field | Description |
|-------|-------------|
| `context_length` | Effective context window (override or discovered) |
| `max_generation_length` | Effective max output (override or discovered) |
| `available_for_input` | Context minus generation minus safety margin |
| `source` | Where the values come from: `manual`, `documented`, `discovered`, `estimated` |
| `discovered_values` | Original values before any overrides |

### Update Model with Overrides

```http
PATCH /api/v1/models/{model_id}
Content-Type: application/json

{
  "context_length_override": 128000,
  "max_generation_length_override": 16384
}
```

### Model Response Schema

When fetching a model, the response includes limit information:

```json
{
  "id": "uuid",
  "model_id": "gpt-4o",
  "model_name": "GPT-4o",
  "provider_id": "provider-uuid",
  "context_length": 128000,
  "max_generation_length": 16384,
  "limits_source": "documented",
  "context_length_override": null,
  "max_generation_length_override": null,
  "is_active": true
}
```

---

## Troubleshooting

### "Context window exceeded" errors

**Symptom:** Job fails with error about context window being exceeded.

**Causes:**
1. Input text is too long for the model's context window
2. Model limits are incorrectly estimated (too high)

**Solutions:**
1. Check the model's `limits_source` - if "estimated", verify the actual limits
2. Set manual overrides with correct values
3. Use the `/validate-execution` endpoint to check before submitting

### Incorrect limits after model discovery

**Symptom:** Discovered model has wrong context_length or max_generation_length.

**Cause:** Provider API doesn't return accurate limit information (common with OpenAI-compatible APIs).

**Solution:**
1. Check the model documentation for correct values
2. Set manual overrides via UI or API
3. Reference resources like [llm-context-limits](https://github.com/taylorwilsdon/llm-context-limits)

### Model not in known database

**Symptom:** New model shows "estimated" limits with default values.

**Solution:**
1. Set manual overrides for the correct values
2. The overrides persist and will be used for all future requests

### vLLM/Local models showing wrong limits

**Symptom:** Self-hosted models via vLLM show incorrect context length.

**Cause:** vLLM's OpenAI-compatible API doesn't expose `--max-model-len` in the models endpoint.

**Solution:**
1. Check your vLLM server's `--max-model-len` configuration
2. Set manual overrides to match your server configuration

---

## Best Practices

1. **Always verify estimated limits** - When a model shows "estimated" source, look up the actual values and set overrides.

2. **Use the limits endpoint** - Before processing large documents, call `/models/{id}/limits` to understand available capacity.

3. **Account for prompts** - Remember that system prompts and user prompt templates consume tokens from the available input space.

4. **Monitor execution validation** - Use `/services/{id}/validate-execution` (dry run) to pre-check if content fits before submitting jobs. The response includes:
   - `input_tokens`: Actual token count (content + prompts)
   - `max_generation`: Reserved tokens for model output
   - `context_length`: Total context available
   - `warning`: Alert if close to limit (>80%) or exceeds context

5. **Document custom models** - When deploying custom or fine-tuned models, immediately set the correct limits via overrides.

---

## Resources

- [OpenAI Model Specs](https://platform.openai.com/docs/models)
- [Anthropic Context Windows](https://docs.anthropic.com/en/docs/build-with-claude/context-windows)
- [LLM Context Limits Database](https://github.com/taylorwilsdon/llm-context-limits)
- [vLLM Documentation](https://docs.vllm.ai/)
