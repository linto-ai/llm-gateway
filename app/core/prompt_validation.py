#!/usr/bin/env python3
"""Prompt placeholder validation utilities.

Validates prompt placeholder count matches processing mode requirements.
"""

from typing import Tuple, Optional


def count_placeholders(content: str) -> int:
    """
    Count {} placeholders in prompt content.

    Counts empty braces {} which are used as positional placeholders.
    Does NOT count named placeholders like {name} or {variable}.

    Args:
        content: Prompt content string

    Returns:
        Number of {} placeholders found
    """
    if not content:
        return 0

    count = 0
    i = 0
    while i < len(content) - 1:
        if content[i] == '{' and content[i + 1] == '}':
            count += 1
            i += 2
        else:
            i += 1
    return count


def get_required_placeholders(processing_mode: str) -> int:
    """
    Get required placeholder count for a processing mode.

    Args:
        processing_mode: One of 'single_pass', 'iterative'

    Returns:
        Required number of placeholders (1 or 2)
    """
    if processing_mode == 'iterative':
        return 2
    return 1  # single_pass


def validate_prompt_for_processing_mode(
    prompt_content: str,
    processing_mode: str,
    prompt_name: Optional[str] = None,
    field_name: str = "user_prompt_template_id"
) -> Tuple[bool, Optional[dict]]:
    """
    Validate that prompt placeholder count matches processing mode requirements.

    Args:
        prompt_content: The prompt content to validate
        processing_mode: The processing mode ('single_pass', 'iterative')
        prompt_name: Optional prompt name for error messages
        field_name: Field name for error details (default: user_prompt_template_id)

    Returns:
        Tuple of (is_valid, error_details or None)

        error_details structure:
        {
            "type": "prompt_validation_error",
            "field": "user_prompt_template_id",
            "message": "...",
            "processing_mode": "...",
            "required_placeholders": N,
            "actual_placeholders": N,
            "prompt_name": "..." (optional)
        }
    """
    if not prompt_content:
        return True, None  # Empty content is valid (will use defaults)

    actual = count_placeholders(prompt_content)
    required = get_required_placeholders(processing_mode)

    if actual != required:
        mode_label = processing_mode.replace('_', ' ').capitalize()

        if processing_mode == 'iterative':
            message = (
                f"Iterative processing requires exactly 2 placeholders "
                f"({{}} for previous summary and {{}} for new content), "
                f"but prompt has {actual}"
            )
        else:
            message = (
                f"{mode_label} processing requires exactly 1 placeholder ({{}}), "
                f"but prompt has {actual}"
            )

        error_details = {
            "type": "prompt_validation_error",
            "field": field_name,
            "message": message,
            "processing_mode": processing_mode,
            "required_placeholders": required,
            "actual_placeholders": actual,
        }

        if prompt_name:
            error_details["prompt_name"] = prompt_name

        return False, error_details

    return True, None
