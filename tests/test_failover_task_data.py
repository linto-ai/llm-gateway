"""Unit tests for `_get_failover_task_data` (celery_app).

The failover task_data must be built from the failover flavor the same way the
dispatch path builds it (#28): provider via `flavor.model.provider` with the key
decrypted, backendParams from `build_backend_params`, and the prompts from the
failover flavor. No DB; the model and provider are real ORM instances so their
attributes are the real column names.
"""

from types import SimpleNamespace
from unittest.mock import patch, MagicMock

from app.http_server import celery_app
from app.models.model import Model
from app.models.provider import Provider

FAILOVER_FLAVOR_ID = "ffffffff-ffff-ffff-ffff-ffffffffffff"


def _failover_flavor(prompt_user_content="Summarize: {}"):
    provider = Provider(
        api_key_encrypted="ENC",
        api_base_url="https://failover.example/api/v1",
        provider_type="openai",
    )
    model = Model(
        model_name="Failover Display Name",
        model_identifier="failover-model",
        context_length=32000,
        max_generation_length=1024,
        tokenizer_class="FailoverTokenizer",
        tokenizer_name="failover/tokenizer",
        provider=provider,
    )
    return SimpleNamespace(
        id=FAILOVER_FLAVOR_ID,
        name="Failover flavor",
        is_active=True,
        model=model,
        temperature=0.2,
        top_p=0.9,
        processing_mode="single_pass",
        estimated_cost_per_1k_tokens=0.0,
        tokenizer_override=None,
        create_new_turn_after=300,
        summary_turns=2,
        max_new_turns=6,
        reduce_summary=True,
        consolidate_summary=False,
        reduce_prompt=SimpleNamespace(name="failover-reduce"),
        output_type="text",
        prompt_system_content="Failover system",
        prompt_user_content=prompt_user_content,
        prompt_reduce_content="Failover reduce: {}",
        placeholder_extraction_prompt=SimpleNamespace(content="Failover extraction"),
        categorization_prompt=None,
        failover_enabled=False,
        failover_flavor_id=None,
        failover_on_timeout=False,
        failover_on_rate_limit=False,
        failover_on_model_error=False,
        failover_on_content_filter=False,
        max_failover_depth=3,
    )


def _original_task_data():
    return {
        "flavor_id": "00000000-0000-0000-0000-000000000000",
        "backend": "old_backend",
        "backendParams": {"modelName": "old", "maxGenerationLength": 1, "processing_mode": "iterative"},
        "providerConfig": {"api_url": "https://old", "api_key": "old", "provider_type": "old"},
        "content": "unchanged",
        "prompt_system_content": "Original system",
        "prompt_user_content": "Summary so far: {} New turns: {}",
        "prompt_reduce_content": "Original reduce: {}",
        "prompt_extraction_content": "Original extraction",
        "prompt_categorization_content": "Original categorization",
        "fields": 2,
    }


def _build(flavor):
    session = MagicMock()
    # session.query(...).options(...).filter(...).first() -> flavor
    session.query.return_value.options.return_value.filter.return_value.first.return_value = flavor
    enc = MagicMock()
    enc.decrypt.return_value = "DECRYPTED_KEY"
    with patch.object(celery_app, "_get_sync_db_session", return_value=session), \
         patch("app.core.security.get_encryption_service", return_value=enc):
        out = celery_app._get_failover_task_data(_original_task_data(), FAILOVER_FLAVOR_ID)
    return out, enc


def test_failover_task_data_is_built_from_the_failover_flavor():
    out, enc = _build(_failover_flavor())

    assert out is not None, "failover task_data must be built, not None"
    assert out["providerConfig"] == {
        "api_key": "DECRYPTED_KEY",
        "api_url": "https://failover.example/api/v1",
        "provider_type": "openai",
    }
    enc.decrypt.assert_called_once_with("ENC")
    assert out["backend"] == "openai"
    assert out["flavor_id"] == FAILOVER_FLAVOR_ID
    assert out["backendParams"] == {
        "modelName": "failover-model",
        "totalContextLength": 32000,
        "maxGenerationLength": 1024,
        "tokenizerClass": "FailoverTokenizer",
        "tokenizer": "failover/tokenizer",
        "temperature": 0.2,
        "top_p": 0.9,
        "createNewTurnAfter": 300,
        "summaryTurns": 2,
        "maxNewTurns": 6,
        "reduceSummary": True,
        "consolidateSummary": False,
        "reduce_prompt": "failover-reduce",
        "type": "text",
        "processing_mode": "single_pass",
        "estimated_cost_per_1k_tokens": 0.0,
    }
    assert out["prompt_system_content"] == "Failover system"
    assert out["prompt_user_content"] == "Summarize: {}"
    assert out["prompt_reduce_content"] == "Failover reduce: {}"
    assert out["prompt_extraction_content"] == "Failover extraction"
    assert out["prompt_categorization_content"] is None
    assert out["fields"] == 1
    # Request content is kept.
    assert out["content"] == "unchanged"


def test_failover_flavor_without_user_prompt_does_not_inherit_the_original_one():
    out, _ = _build(_failover_flavor(prompt_user_content=None))

    assert out is not None, "failover task_data must be built, not None"
    # Same as dispatch for this flavor: no user prompt and no placeholders, so the
    # single_pass worker never formats the original 2-placeholder prompt.
    assert out["prompt_user_content"] is None
    assert out["fields"] == 0


def test_failover_keeps_request_overrides():
    flavor = _failover_flavor()
    session = MagicMock()
    session.query.return_value.options.return_value.filter.return_value.first.return_value = flavor
    original = {**_original_task_data(), "requestOverrides": {"temperature": 0.0, "top_p": None}}
    with patch.object(celery_app, "_get_sync_db_session", return_value=session), \
         patch("app.core.security.get_encryption_service", return_value=MagicMock()):
        out = celery_app._get_failover_task_data(original, FAILOVER_FLAVOR_ID)

    assert out is not None, "failover task_data must be built, not None"
    # The request's temperature applies to the failover flavor; top_p was not overridden.
    assert out["backendParams"]["temperature"] == 0.0
    assert out["backendParams"]["top_p"] == 0.9
