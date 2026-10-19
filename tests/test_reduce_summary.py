"""reduce_summary with no reduce prompt.

A flavor with reduce_summary on and no reduce prompt used to fail at the end of
the iterative passes ('NoneType' object has no attribute 'format'). The summary
is now returned as it is, and the backend loads the reduce prompt from the
flavor's inline content.
"""

import logging
from unittest.mock import MagicMock, patch

from app.backends.backend import LLMBackend
from app.backends.batch_manager import BatchManager


def test_reduce_summary_without_reduce_prompt_returns_summary():
    manager = BatchManager.__new__(BatchManager)
    manager.reduce_prompt = None
    manager.logger = logging.getLogger("test")
    manager.celery_task = MagicMock()

    summary = ["- point one", "- point two"]
    assert manager.reduce_summary(summary) == summary
    manager.celery_task.update_state.assert_not_called()


def _backend(prompt_reduce_content, reduce_prompt_name):
    task_data = {
        "task_id": "task-id",
        "content": "text",
        "name": "summary",
        "type": "summary",
        "fields": 2,
        "prompt_user_content": "Summarize {} {}",
        "prompt_reduce_content": prompt_reduce_content,
        "backendParams": {
            "tokenizer": "some/tokenizer",
            "createNewTurnAfter": 100,
            "reduceSummary": True,
            "reduce_prompt": reduce_prompt_name,
        },
    }
    tokenizer = MagicMock(side_effect=lambda text: {"input_ids": text.split()})
    with patch.object(LLMBackend, "_load_tokenizer", return_value=tokenizer):
        backend = LLMBackend.__new__(LLMBackend)
        LLMBackend.__init__(backend, task_data)  # __init__ returns True, as subclasses call it
    return backend


def test_backend_loads_inline_reduce_prompt_without_linked_prompt():
    # Inline content, no linked prompt (reduce_prompt name is None)
    assert _backend("Reduce: {}", None).reduce_prompt == "Reduce: {}"


def test_backend_without_reduce_content_has_no_reduce_prompt():
    assert _backend(None, "linked-but-empty").reduce_prompt is None
