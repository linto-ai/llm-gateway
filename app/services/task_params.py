"""Build the backendParams a Celery task gets for a service flavor.

Shared by the dispatch path (app/api/v1/services.py) and failover
(app/http_server/celery_app.py), so both send the same parameters for a flavor.
"""


def resolve_tokenizer_for_flavor(flavor) -> str:
    """
    Resolve the tokenizer to use for a flavor.

    This function uses TokenizerManager to resolve the tokenizer config,
    then returns the appropriate tokenizer identifier string for backward
    compatibility with the existing task_data format.

    Priority (handled by TokenizerManager):
    1. flavor.tokenizer_override (if set)
    2. flavor.model.tokenizer_name (if set)
    3. TOKENIZER_MAPPINGS lookup by model_identifier
    4. Extract base model from quantized identifier
    5. Fallback to tiktoken cl100k_base
    """
    from app.core.tokenizer_mappings import get_tokenizer_config, get_fallback_tokenizer_config

    # Priority 1: flavor.tokenizer_override
    if flavor.tokenizer_override:
        return flavor.tokenizer_override

    # Priority 2: flavor.model.tokenizer_name
    if flavor.model.tokenizer_name:
        return flavor.model.tokenizer_name

    # Use tokenizer mappings for resolution
    config = get_tokenizer_config(flavor.model.model_identifier)
    if not config:
        config = get_fallback_tokenizer_config()

    if config["type"] == "tiktoken":
        # For tiktoken, return the encoding name (will be handled by TokenizerManager)
        return config["encoding"]
    else:
        # For HuggingFace, return the repo
        return config["repo"]


def build_backend_params(flavor, temperature: float | None = None, top_p: float | None = None) -> dict:
    """Return the task backendParams for a flavor and its model.

    ``temperature``/``top_p`` override the flavor's values when given.
    """
    return {
        "modelName": flavor.model.model_identifier,
        # Model token limits
        "totalContextLength": flavor.model.context_length,
        "maxGenerationLength": flavor.model.max_generation_length,
        "tokenizerClass": flavor.model.tokenizer_class,
        "tokenizer": resolve_tokenizer_for_flavor(flavor),
        "temperature": temperature if temperature is not None else flavor.temperature,
        "top_p": top_p if top_p is not None else flavor.top_p,
        "createNewTurnAfter": flavor.create_new_turn_after or 500,  # Default: 500 tokens
        "summaryTurns": flavor.summary_turns or 3,  # Default: 3 turns for summary context
        "maxNewTurns": flavor.max_new_turns or 10,  # Default: 10 turns per batch
        "reduceSummary": flavor.reduce_summary,
        "consolidateSummary": flavor.consolidate_summary,
        "reduce_prompt": flavor.reduce_prompt.name if flavor.reduce_prompt else None,
        "type": flavor.output_type,
        # Processing mode
        "processing_mode": flavor.processing_mode,
        # Cost estimation rate
        "estimated_cost_per_1k_tokens": flavor.estimated_cost_per_1k_tokens,
    }
