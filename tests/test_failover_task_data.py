"""Unit test for `_get_failover_task_data` (celery_app).

Regression guard for the failover provider-config build: the provider is
reached via `flavor.model.provider` (ServiceFlavor has no `provider`
relationship), the key is stored encrypted (`api_key_encrypted`) and the URL in
`api_base_url`. The previous code read `flavor.provider.api_key/api_url`, which
raised AttributeError and aborted every failover. No DB; the model and provider
are real ORM instances so the test only uses attributes that exist (#28).
"""

from types import SimpleNamespace
from unittest.mock import patch, MagicMock

from app.http_server import celery_app
from app.models.model import Model
from app.models.provider import Provider


def _fake_flavor(prompt_user_content=None):
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
    # SimpleNamespace deliberately has NO `provider` attribute, so the old code
    # (`if flavor.provider:`) would raise AttributeError and return None.
    return SimpleNamespace(
        id="ffffffff-ffff-ffff-ffff-ffffffffffff",
        name="Failover flavor",
        is_active=True,
        model=model,
        temperature=0.2,
        top_p=0.9,
        processing_mode="single",
        estimated_cost_per_1k_tokens=0.0,
        prompt_system_content=None,
        prompt_user_content=prompt_user_content,
        tokenizer_override=None,
        prompt_reduce_content=None,
        failover_enabled=False,
        failover_flavor_id=None,
        failover_on_timeout=False,
        failover_on_rate_limit=False,
        failover_on_model_error=False,
        failover_on_content_filter=False,
        max_failover_depth=3,
    )


def test_failover_task_data_reads_provider_via_model_and_decrypts():
    flavor = _fake_flavor()

    session = MagicMock()
    # session.query(...).options(...).filter(...).first() -> flavor
    session.query.return_value.options.return_value.filter.return_value.first.return_value = flavor

    original = {
        "flavor_id": "00000000-0000-0000-0000-000000000000",
        "backend": "old_backend",
        "backendParams": {"modelName": "old", "maxGenerationLength": 1},
        "providerConfig": {"api_url": "https://old", "api_key": "old", "provider_type": "old"},
        "content": "unchanged",
        "prompt_user_content": "Summary so far: {} New turns: {}",
        "fields": 2,
    }

    enc = MagicMock()
    enc.decrypt.return_value = "DECRYPTED_KEY"

    with patch.object(celery_app, "_get_sync_db_session", return_value=session), \
         patch("app.core.security.get_encryption_service", return_value=enc):
        out = celery_app._get_failover_task_data(
            original, "ffffffff-ffff-ffff-ffff-ffffffffffff"
        )

    assert out is not None, "failover task_data must be built, not None"
    assert out["providerConfig"] == {
        "api_key": "DECRYPTED_KEY",
        "api_url": "https://failover.example/api/v1",
        "provider_type": "openai",
    }
    assert out["backend"] == "openai"
    assert out["flavor_id"] == "ffffffff-ffff-ffff-ffff-ffffffffffff"
    assert out["backendParams"]["modelName"] == "failover-model"
    assert out["backendParams"]["maxGenerationLength"] == 1024
    assert out["backendParams"]["totalContextLength"] == 32000
    assert out["backendParams"]["tokenizerClass"] == "FailoverTokenizer"
    assert out["backendParams"]["tokenizer"] == "failover/tokenizer"
    # untouched content preserved
    assert out["content"] == "unchanged"
    # The failover flavor has no user prompt: the original prompt and its fields are kept.
    assert out["prompt_user_content"] == "Summary so far: {} New turns: {}"
    assert out["fields"] == 2
    enc.decrypt.assert_called_once_with("ENC")


def test_failover_task_data_recounts_fields_for_failover_prompt():
    flavor = _fake_flavor(prompt_user_content="Summarize: {}")

    session = MagicMock()
    session.query.return_value.options.return_value.filter.return_value.first.return_value = flavor

    original = {
        "backendParams": {"modelName": "old"},
        "prompt_user_content": "Summary so far: {} New turns: {}",
        "fields": 2,
    }

    with patch.object(celery_app, "_get_sync_db_session", return_value=session), \
         patch("app.core.security.get_encryption_service", return_value=MagicMock()):
        out = celery_app._get_failover_task_data(
            original, "ffffffff-ffff-ffff-ffff-ffffffffffff"
        )

    assert out is not None, "failover task_data must be built, not None"
    assert out["prompt_user_content"] == "Summarize: {}"
    assert out["fields"] == 1
