# How LLM Gateway Works

## Overview

LLM Gateway is a service orchestration layer that sits between your application and LLM providers. It solves the complexity of managing long-running LLM tasks, handling context limits, tracking costs, and ensuring reliable execution.

## Architecture

```
┌─────────────────┐         ┌─────────────────┐         ┌──────────────────┐
│   Your App      │         │   LLM Gateway   │         │   LLM Provider   │
│                 │         │                 │         │                  │
│  - Frontend     │ ──────> │  - Services     │ ──────> │  - OpenAI        │
│  - Backend      │  HTTP   │  - Job Queue    │   API   │  - vLLM          │
│  - Workflows    │         │  - Caching      │         │  - Ollama        │
└─────────────────┘         └─────────────────┘         └──────────────────┘
                                     │
                              ┌──────┴──────┐
                              │  Database   │
                              │  - Services │
                              │  - Jobs     │
                              │  - Results  │
                              └─────────────┘
```

## Processing Modes

### Single Pass Mode

For documents that fit within the model's context window:

```
Input ──► LLM ──► Output
```

- User prompt requires exactly 1 placeholder: `{}`
- Use cases: Document categorization, metadata extraction, single-shot Q&A

### Iterative Mode

For long documents that exceed context limits, or when you need fine-grained control over the output.

**How it works:**

1. **Turn normalization** (`create_new_turn_after`): If a speaker turn exceeds this token threshold, it's split into smaller "virtual turns" using Spacy sentence segmentation.

2. **Batch creation** (`max_new_turns`): Turns are grouped into batches. Each batch is sent to the LLM with the previous summary as context.

```
ASR Transcription
       │
       ▼
┌─────────────────────────────────┐
│  Turn Normalization             │
│  (create_new_turn_after: 200)   │
│                                 │
│  Long turn (800 tokens)         │
│       → split into 4 turns      │
└───────────────┬─────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│  Batch Creation                 │
│  (max_new_turns: 15)            │
└───────────────┬─────────────────┘
                │
     ┌──────────┼──────────┐
     ▼          ▼          ▼
  Batch 1    Batch 2    Batch N
     │
     ▼
  Summary 1 ────────┐
                    ▼
            Batch 2 + Summary 1
                    │
                    ▼
            Summary 2 ───> ... ───> Final
                                      │
                                      ▼ (if reduce_summary = true)
                                REDUCE STEP
```

**Configuration**:
- `processing_mode: "iterative"`
- User prompt requires 2 placeholders: `{}{}`
- `create_new_turn_after`: Token threshold for splitting long turns (100-500)
- `max_new_turns`: Turns per batch (10-50) - **controls output granularity**
- `summary_turns`: Previous summary turns kept in context
- `reduce_summary`: Enable final consolidation step

**Controlling output detail**: Fewer turns per batch (`max_new_turns`) = more LLM passes = more detailed output preserving individual speaker interventions. Useful for compliance scenarios where ALL statements must be kept.

## Services and Flavors

Services define reusable LLM tasks. Each service can have multiple **flavors** - different model configurations for the same task:

```
┌──────────────────────────────────────────────────┐
│              Service: "summarize-meeting"        │
├──────────────────────────────────────────────────┤
│                                                  │
│  Flavor: "detailed" (compliance)                 │
│  ├─ Model: gpt-4o                                │
│  ├─ Processing: iterative                        │
│  ├─ create_new_turn_after: 200                   │
│  ├─ max_new_turns: 10  ← SMALL BATCHES           │
│  └─ Preserves ALL speaker interventions          │
│                                                  │
│  Flavor: "standard"                              │
│  ├─ Model: gpt-4o                                │
│  ├─ Processing: iterative                        │
│  ├─ max_new_turns: 24                            │
│  └─ Balanced compression                         │
│                                                  │
│  Flavor: "fast"                                  │
│  ├─ Model: gpt-4o-mini                           │
│  ├─ Processing: single_pass                      │
│  └─ Quick overview                               │
│                                                  │
└──────────────────────────────────────────────────┘
```

**Flavor parameters**:
- **Model selection**: Link to any configured model/provider
- **LLM parameters**: temperature, top_p, stop_sequences
- **Prompts**: system_prompt, user_prompt, reduce_prompt
- **Processing**: mode, chunking parameters
- **Token limits**: Inherited from Model (context_length, max_generation_length)
- **Fallback**: fallback_flavor_id for context overflow, failover_flavor_id for errors

## Job Management

Every service execution creates a **Job** that tracks the entire lifecycle:

```
POST /services/{id}/execute
         │
         ▼
   ┌──────────┐
   │  queued  │  ← Job created
   └────┬─────┘
        │
        ▼
   ┌──────────┐
   │ started  │  ← Worker picked up
   └────┬─────┘
        │
        ▼
 ┌─────────────┐
 │ processing  │  ← Real-time updates via WebSocket
 └──────┬──────┘
        │
   ┌────┴────┐
   │         │
   ▼         ▼
┌──────────┐  ┌─────────┐
│completed │  │ failed  │
└──────────┘  └─────────┘
```

**Features**:
- **Real-time WebSocket Updates**: Live progress with current pass, tokens processed, completion percentage
- **Token Metrics Per Pass**: Detailed breakdown of prompt/completion tokens, duration, and cost for each LLM call
- **Cost Estimation**: Pre-flight calculation based on input tokens
- **Orphaned Job Detection**: Automatic recovery of stuck jobs

## Retry Behavior

Rate limit, timeout, 5xx errors → retry with exponential backoff:

```
Failure ──► 1s ──► 2s ──► 4s ──► 8s ──► 16s ──► 32s (max 6 attempts)
```

400 errors (context exceeded, invalid prompt) → no retry.

## Integration Example

```python
import httpx

# 1. Execute service
response = httpx.post(
    "http://llm-gateway:8000/api/v1/services/{id}/execute",
    json={"input": "...", "flavor_name": "default"}
)
job_id = response.json()["id"]

# 2. Monitor via WebSocket
async with websockets.connect(f"ws://llm-gateway:8000/ws/jobs/{job_id}") as ws:
    async for msg in ws:
        data = json.loads(msg)
        if data["status"] == "completed":
            print(data["result"]["output"])
            break
```
