#!/usr/bin/env python3
"""
Known model limits database for accurate context window management.

OpenAI and most providers do NOT return context limits in their /v1/models API.
This database provides documented limits for common models.
"""

from typing import Optional, Dict, Any

# Known model limits with documented sources
KNOWN_MODEL_LIMITS: Dict[str, Dict[str, Any]] = {
    # OpenAI Models
    "gpt-4o": {"context_length": 128000, "max_generation_length": 16384, "source": "documented"},
    "gpt-4o-mini": {"context_length": 128000, "max_generation_length": 16384, "source": "documented"},
    "gpt-4-turbo": {"context_length": 128000, "max_generation_length": 4096, "source": "documented"},
    "gpt-4-1106": {"context_length": 128000, "max_generation_length": 4096, "source": "documented"},
    "gpt-4": {"context_length": 8192, "max_generation_length": 4096, "source": "documented"},
    "gpt-3.5-turbo-16k": {"context_length": 16385, "max_generation_length": 4096, "source": "documented"},
    "gpt-3.5-turbo": {"context_length": 16385, "max_generation_length": 4096, "source": "documented"},
    "o1": {"context_length": 200000, "max_generation_length": 100000, "source": "documented"},
    "o1-mini": {"context_length": 128000, "max_generation_length": 65536, "source": "documented"},
    "o1-preview": {"context_length": 128000, "max_generation_length": 32768, "source": "documented"},

    # Anthropic Models
    "claude-sonnet-4": {"context_length": 200000, "max_generation_length": 64000, "source": "documented"},
    "claude-3-5-sonnet": {"context_length": 200000, "max_generation_length": 8192, "source": "documented"},
    "claude-3-opus": {"context_length": 200000, "max_generation_length": 4096, "source": "documented"},
    "claude-3-sonnet": {"context_length": 200000, "max_generation_length": 4096, "source": "documented"},
    "claude-3-haiku": {"context_length": 200000, "max_generation_length": 4096, "source": "documented"},

    # Mistral Models
    "mistral-small": {"context_length": 32000, "max_generation_length": 8192, "source": "documented"},
    "mistral-large": {"context_length": 128000, "max_generation_length": 8192, "source": "documented"},
    "mistral-nemo": {"context_length": 128000, "max_generation_length": 4096, "source": "documented"},
    "mistral-7b": {"context_length": 32000, "max_generation_length": 4096, "source": "documented"},
    "mixtral-8x7b": {"context_length": 32000, "max_generation_length": 4096, "source": "documented"},
    "mixtral-8x22b": {"context_length": 65000, "max_generation_length": 4096, "source": "documented"},

    # Llama Models
    "llama-3.3": {"context_length": 128000, "max_generation_length": 4096, "source": "documented"},
    "llama-3.2": {"context_length": 128000, "max_generation_length": 4096, "source": "documented"},
    "llama-3.1": {"context_length": 128000, "max_generation_length": 4096, "source": "documented"},
    "llama-3": {"context_length": 8192, "max_generation_length": 2048, "source": "documented"},
    "llama-2": {"context_length": 4096, "max_generation_length": 2048, "source": "documented"},

    # DeepSeek Models
    "deepseek-v3": {"context_length": 64000, "max_generation_length": 8192, "source": "documented"},
    "deepseek-r1": {"context_length": 64000, "max_generation_length": 8192, "source": "documented"},
    "deepseek-coder": {"context_length": 64000, "max_generation_length": 4096, "source": "documented"},

    # Qwen Models
    "qwen-2.5": {"context_length": 131072, "max_generation_length": 8192, "source": "documented"},
    "qwen2.5": {"context_length": 131072, "max_generation_length": 8192, "source": "documented"},
    "qwen-2": {"context_length": 32000, "max_generation_length": 4096, "source": "documented"},
    "qwen-turbo": {"context_length": 131072, "max_generation_length": 8192, "source": "documented"},

    # Phi Models
    "phi-3": {"context_length": 128000, "max_generation_length": 4096, "source": "documented"},
    "phi-4": {"context_length": 16000, "max_generation_length": 4096, "source": "documented"},

    # Gemma Models
    "gemma-2": {"context_length": 8192, "max_generation_length": 2048, "source": "documented"},
    "gemma": {"context_length": 8192, "max_generation_length": 2048, "source": "documented"},
}


def match_model_limits(model_id: str) -> Optional[Dict[str, Any]]:
    """
    Match model identifier against known patterns.

    Uses substring matching to handle versioned model names like:
    - "gpt-4o-2024-08-06" matches "gpt-4o"
    - "claude-3-5-sonnet-20241022" matches "claude-3-5-sonnet"
    - "Mistral-Small-3.1-24B-Instruct" matches "mistral-small"

    Args:
        model_id: Model identifier from provider

    Returns:
        Dict with context_length, max_generation_length, source
        or None if no match
    """
    model_lower = model_id.lower()

    # Sort patterns by length (longest first) to match more specific patterns
    sorted_patterns = sorted(KNOWN_MODEL_LIMITS.keys(), key=len, reverse=True)

    for pattern in sorted_patterns:
        if pattern in model_lower:
            return KNOWN_MODEL_LIMITS[pattern].copy()

    return None


def get_conservative_estimate(model_id: str) -> Dict[str, Any]:
    """
    Return conservative estimates when model is not recognized.

    Args:
        model_id: Model identifier

    Returns:
        Conservative limits with "estimated" source
    """
    return {
        "context_length": 4096,
        "max_generation_length": 2048,
        "source": "estimated"
    }
