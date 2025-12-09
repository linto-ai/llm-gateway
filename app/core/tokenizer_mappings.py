#!/usr/bin/env python3
"""
Tokenizer Mappings for known model families.

This module provides mappings from model identifiers to their corresponding
tokenizers, supporting both tiktoken (for OpenAI/Anthropic/Google) and
HuggingFace tokenizers.
"""

import re
from typing import Dict, Any, Optional

# Known model-to-tokenizer mappings
TOKENIZER_MAPPINGS: Dict[str, Dict[str, Any]] = {
    # OpenAI models - tiktoken (no download needed)
    "gpt-4o": {"type": "tiktoken", "encoding": "o200k_base"},
    "gpt-4o-mini": {"type": "tiktoken", "encoding": "o200k_base"},
    "gpt-4-turbo": {"type": "tiktoken", "encoding": "cl100k_base"},
    "gpt-4": {"type": "tiktoken", "encoding": "cl100k_base"},
    "gpt-3.5-turbo": {"type": "tiktoken", "encoding": "cl100k_base"},
    "o1": {"type": "tiktoken", "encoding": "o200k_base"},
    "o1-mini": {"type": "tiktoken", "encoding": "o200k_base"},
    "o1-preview": {"type": "tiktoken", "encoding": "o200k_base"},
    "o3-mini": {"type": "tiktoken", "encoding": "o200k_base"},
    "o3": {"type": "tiktoken", "encoding": "o200k_base"},
    "chatgpt": {"type": "tiktoken", "encoding": "o200k_base"},

    # Anthropic models - tiktoken estimation (no official tokenizer)
    "claude-3": {"type": "tiktoken", "encoding": "cl100k_base", "estimated": True},
    "claude-3.5": {"type": "tiktoken", "encoding": "cl100k_base", "estimated": True},
    "claude-3.7": {"type": "tiktoken", "encoding": "cl100k_base", "estimated": True},
    "claude-sonnet": {"type": "tiktoken", "encoding": "cl100k_base", "estimated": True},
    "claude-opus": {"type": "tiktoken", "encoding": "cl100k_base", "estimated": True},
    "claude-haiku": {"type": "tiktoken", "encoding": "cl100k_base", "estimated": True},
    "claude": {"type": "tiktoken", "encoding": "cl100k_base", "estimated": True},

    # Meta Llama models - HuggingFace
    "llama-3.3": {"type": "huggingface", "repo": "meta-llama/Llama-3.3-70B-Instruct"},
    "llama-3.2": {"type": "huggingface", "repo": "meta-llama/Llama-3.2-3B-Instruct"},
    "llama-3.1": {"type": "huggingface", "repo": "meta-llama/Llama-3.1-8B-Instruct"},
    "llama-3": {"type": "huggingface", "repo": "meta-llama/Llama-3-8B-Instruct"},
    "llama-2": {"type": "huggingface", "repo": "meta-llama/Llama-2-7b-hf"},
    "llama": {"type": "huggingface", "repo": "meta-llama/Llama-2-7b-hf"},

    # Mistral models - HuggingFace
    "mistral-large": {"type": "huggingface", "repo": "mistralai/Mistral-Large-Instruct-2411"},
    "mistral-small": {"type": "huggingface", "repo": "mistralai/Mistral-Small-24B-Instruct-2501"},
    "mistral-nemo": {"type": "huggingface", "repo": "mistralai/Mistral-Nemo-Instruct-2407"},
    "mixtral": {"type": "huggingface", "repo": "mistralai/Mixtral-8x7B-Instruct-v0.1"},
    "codestral": {"type": "huggingface", "repo": "mistralai/Codestral-22B-v0.1"},
    "mistral-7b": {"type": "huggingface", "repo": "mistralai/Mistral-7B-Instruct-v0.3"},
    "mistral": {"type": "huggingface", "repo": "mistralai/Mistral-7B-Instruct-v0.3"},

    # Qwen models - HuggingFace
    "qwen-2.5": {"type": "huggingface", "repo": "Qwen/Qwen2.5-72B-Instruct"},
    "qwen-2": {"type": "huggingface", "repo": "Qwen/Qwen2-72B-Instruct"},
    "qwen2.5": {"type": "huggingface", "repo": "Qwen/Qwen2.5-72B-Instruct"},
    "qwen2": {"type": "huggingface", "repo": "Qwen/Qwen2-72B-Instruct"},
    "qwq": {"type": "huggingface", "repo": "Qwen/QwQ-32B"},
    "qwen": {"type": "huggingface", "repo": "Qwen/Qwen2-72B-Instruct"},

    # DeepSeek models - HuggingFace
    "deepseek-v3": {"type": "huggingface", "repo": "deepseek-ai/DeepSeek-V3"},
    "deepseek-r1": {"type": "huggingface", "repo": "deepseek-ai/DeepSeek-R1"},
    "deepseek-coder": {"type": "huggingface", "repo": "deepseek-ai/deepseek-coder-33b-instruct"},
    "deepseek": {"type": "huggingface", "repo": "deepseek-ai/DeepSeek-V3"},

    # Google models - tiktoken estimation
    "gemini-2": {"type": "tiktoken", "encoding": "cl100k_base", "estimated": True},
    "gemini-1.5": {"type": "tiktoken", "encoding": "cl100k_base", "estimated": True},
    "gemini-pro": {"type": "tiktoken", "encoding": "cl100k_base", "estimated": True},
    "gemini": {"type": "tiktoken", "encoding": "cl100k_base", "estimated": True},

    # Cohere models - HuggingFace
    "command-r": {"type": "huggingface", "repo": "CohereForAI/c4ai-command-r-plus"},
    "command": {"type": "huggingface", "repo": "CohereForAI/c4ai-command-r-plus"},

    # Microsoft Phi models - HuggingFace
    "phi-4": {"type": "huggingface", "repo": "microsoft/phi-4"},
    "phi-3": {"type": "huggingface", "repo": "microsoft/Phi-3-medium-128k-instruct"},
    "phi": {"type": "huggingface", "repo": "microsoft/Phi-3-medium-128k-instruct"},

    # Yi models - HuggingFace
    "yi-large": {"type": "huggingface", "repo": "01-ai/Yi-1.5-34B-Chat"},
    "yi": {"type": "huggingface", "repo": "01-ai/Yi-1.5-34B-Chat"},

    # Falcon models - HuggingFace
    "falcon": {"type": "huggingface", "repo": "tiiuae/falcon-40b-instruct"},

    # Gemma models - HuggingFace
    "gemma-2": {"type": "huggingface", "repo": "google/gemma-2-27b-it"},
    "gemma": {"type": "huggingface", "repo": "google/gemma-7b-it"},
}

# Quantization patterns to strip from model identifiers
QUANT_PATTERNS = [
    r"-q\d+[_\w]*",       # -q4_0, -q8_0, -q4_K_M
    r":Q\d+[_\w]*",       # :Q4_K_M, :Q8_0
    r"-gguf",             # -gguf suffix
    r"-\d+b",             # -8b, -70b (model size)
    r"-instruct",         # -instruct suffix
    r"-chat",             # -chat suffix
    r"-base",             # -base suffix
    r"-hf",               # -hf suffix
    r"-fp\d+",            # -fp16, -fp32
    r"-bf\d+",            # -bf16
    r"-awq",              # -awq quantization
    r"-gptq",             # -gptq quantization
    r"-bnb",              # -bnb quantization
    r"-exl2",             # -exl2 quantization
]


def extract_base_model(model_identifier: str) -> Optional[str]:
    """
    Extract base model name from a potentially quantized model identifier.

    Examples:
        "llama-3.1-8b-q4_0" -> "llama-3.1"
        "Mistral-7B-Instruct-v0.3:Q4_K_M" -> "mistral"
        "meta-llama/Llama-3.1-8B-Instruct" -> "llama-3.1"

    Args:
        model_identifier: The model identifier string

    Returns:
        Base model name if found in mappings, None otherwise
    """
    # Normalize: lowercase and remove owner prefix (e.g., "meta-llama/")
    normalized = model_identifier.lower()
    if "/" in normalized:
        normalized = normalized.split("/")[-1]

    # Strip quantization patterns
    for pattern in QUANT_PATTERNS:
        normalized = re.sub(pattern, "", normalized, flags=re.IGNORECASE)

    # Clean up trailing dashes and underscores
    normalized = normalized.strip("-_")

    # Try to match against known prefixes (sorted by length desc for longest match first)
    sorted_keys = sorted(TOKENIZER_MAPPINGS.keys(), key=len, reverse=True)
    for prefix in sorted_keys:
        if normalized.startswith(prefix) or prefix in normalized:
            return prefix

    return None


def get_tokenizer_config(model_identifier: str) -> Optional[Dict[str, Any]]:
    """
    Get tokenizer configuration for a model identifier.

    Args:
        model_identifier: The model identifier (e.g., "llama-3.1-8b-q4_0")

    Returns:
        Tokenizer config dict with 'type' and other fields, or None if not found
    """
    # Try direct lookup first (normalize to lowercase)
    normalized = model_identifier.lower()

    # Check exact matches first
    for key, config in TOKENIZER_MAPPINGS.items():
        if key.lower() == normalized or normalized.startswith(key.lower()):
            return config

    # Try extracting base model
    base_model = extract_base_model(model_identifier)
    if base_model and base_model in TOKENIZER_MAPPINGS:
        return TOKENIZER_MAPPINGS[base_model]

    return None


def get_fallback_tokenizer_config() -> Dict[str, Any]:
    """
    Get the fallback tokenizer configuration (tiktoken cl100k_base).

    Returns:
        Tokenizer config for fallback
    """
    return {
        "type": "tiktoken",
        "encoding": "cl100k_base",
        "fallback": True,
    }
