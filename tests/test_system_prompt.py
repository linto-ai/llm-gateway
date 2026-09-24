#!/usr/bin/env python3
"""Flavor system prompt: loaded alongside the user prompt and sent as the system message of
every generation call (it used to be dropped whenever a user prompt was set)."""
import logging
from unittest.mock import MagicMock

import pytest

from app.backends.backend import LLMBackend
from app.backends.batch_manager import BatchManager


def _backend(task_data):
    b = LLMBackend.__new__(LLMBackend)
    b.task_data, b.name, b.logger = task_data, "svc", logging.getLogger("test")
    b.loadPrompt()
    return b


class TestLoadPrompt:
    def test_user_and_system(self):
        b = _backend({"prompt_user_content": "Résume : {}", "prompt_system_content": "Tu es rédacteur."})
        assert b.prompt == "Résume : {}" and b.system_prompt == "Tu es rédacteur."

    def test_user_only(self):
        b = _backend({"prompt_user_content": "Résume : {}", "prompt_system_content": None})
        assert b.prompt == "Résume : {}" and b.system_prompt is None

    def test_blank_system_ignored(self):
        assert _backend({"prompt_user_content": "{}", "prompt_system_content": "  "}).system_prompt is None

    def test_system_only_is_the_legacy_template(self):
        b = _backend({"prompt_system_content": "Résume : {}"})
        assert b.prompt == "Résume : {}" and b.system_prompt is None

    def test_no_prompt_raises(self):
        with pytest.raises(ValueError):
            _backend({})


def _batch_manager(system_prompt):
    bm = BatchManager.__new__(BatchManager)
    bm.prompt, bm.system_prompt, bm.reduce_prompt = "Résume : {}", system_prompt, "Réduis : {}"
    bm.task_id, bm.logger = "t", logging.getLogger("test")
    bm.celery_task = MagicMock()
    bm.check_if_revoked = lambda: None
    bm._record_pass_metrics = lambda *a, **k: None
    bm.openai_adapter = MagicMock()
    bm.openai_adapter.publish.return_value = ("## Résultat\nligne", {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2})
    return bm


@pytest.mark.parametrize("system_prompt", ["Tu es rédacteur.", None])
def test_single_pass_sends_system_prompt(system_prompt):
    bm = _batch_manager(system_prompt)
    assert bm.run_single_pass("transcription") == ["## Résultat", "ligne"]
    args, kwargs = bm.openai_adapter.publish.call_args
    assert args[0] == "Résume : transcription"
    assert kwargs["system_prompt"] == system_prompt


def test_adapter_puts_system_message_first():
    import inspect
    from app.backends.openai_adapter import OpenAIAdapter
    src = inspect.getsource(OpenAIAdapter.publish)
    assert 'messages = [{"role": "system", "content": system_prompt}] if system_prompt else []' in src
    assert 'messages.append({"role": "user", "content": content})' in src
