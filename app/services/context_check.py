"""Check whether an input fits a model's context window.

Shared by the dispatch path (app/api/v1/services.py) and failover
(app/http_server/celery_app.py), so both count tokens the same way.
"""

import logging

from app.services.tokenizer_manager import TokenizerManager

logger = logging.getLogger(__name__)

# Reserve for system/user prompts
PROMPT_BUFFER = 500


def check_context_fit(model, content: str) -> tuple[bool, int, int]:
    """
    Check if content fits within a model's context window.

    Returns:
        tuple: (fits, input_tokens, available_tokens)
    """
    try:
        manager = TokenizerManager.get_instance()
        input_tokens = manager.count_tokens(model, content)
    except Exception as e:
        logger.warning(f"Tokenizer count failed, using estimate: {e}", exc_info=True)
        input_tokens = len(content) // 4  # Rough estimate

    available = model.context_length - model.max_generation_length - PROMPT_BUFFER
    return input_tokens <= available, input_tokens, available
