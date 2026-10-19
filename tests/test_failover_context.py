"""Context check on failover (#31).

Before switching to a failover flavor, the input is checked against it the way
dispatch does: use the target if the input fits, else its fallback flavor if
that one fits, else move on to the next flavor in the failover chain. If
nothing fits, the job fails with the original error. No DB; flavors are looked
up by id from a dict and token counts are fixed.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import RateLimitFailoverError
from app.http_server import celery_app
from app.models.model import Model
from app.models.provider import Provider

PRIMARY = "00000000-0000-0000-0000-000000000000"
TARGET = "11111111-1111-1111-1111-111111111111"
TARGET_FALLBACK = "22222222-2222-2222-2222-222222222222"
NEXT = "33333333-3333-3333-3333-333333333333"

# available = context_length - max_generation_length - 500
SMALL_CONTEXT = 4000   # 2476 available
LARGE_CONTEXT = 32000  # 30476 available
INPUT_TOKENS = 10000


def _flavor(flavor_id, *, context_length=LARGE_CONTEXT, processing_mode="single_pass",
            fallback_flavor_id=None, failover_flavor_id=None, is_active=True):
    provider = Provider(
        api_key_encrypted="ENC",
        api_base_url="https://llm.example/api/v1",
        provider_type="openai",
    )
    model = Model(
        model_name=f"model-{flavor_id[:4]}",
        model_identifier=f"model-{flavor_id[:4]}",
        context_length=context_length,
        max_generation_length=1024,
        tokenizer_class="SomeTokenizer",
        tokenizer_name="some/tokenizer",
        provider=provider,
    )
    return SimpleNamespace(
        id=flavor_id,
        name=f"flavor-{flavor_id[:4]}",
        is_active=is_active,
        model=model,
        temperature=0.2,
        top_p=0.9,
        processing_mode=processing_mode,
        estimated_cost_per_1k_tokens=0.0,
        tokenizer_override=None,
        create_new_turn_after=None,
        summary_turns=None,
        max_new_turns=None,
        reduce_summary=False,
        consolidate_summary=False,
        reduce_prompt=None,
        output_type="text",
        prompt_system_content="System",
        prompt_user_content="Summarize: {}",
        prompt_reduce_content=None,
        placeholder_extraction_prompt=None,
        categorization_prompt=None,
        fallback_flavor_id=fallback_flavor_id,
        failover_enabled=failover_flavor_id is not None,
        failover_flavor_id=failover_flavor_id,
        failover_on_timeout=True,
        failover_on_rate_limit=True,
        failover_on_model_error=True,
        failover_on_content_filter=False,
        max_failover_depth=3,
    )


def _task_data():
    return {
        "flavor_id": PRIMARY,
        "backendParams": {},
        "providerConfig": {},
        "content": "x" * 100,
        "failoverConfig": {
            "failover_enabled": True,
            "failover_flavor_id": TARGET,
            "failover_on_rate_limit": True,
            "max_failover_depth": 3,
        },
    }


@pytest.fixture
def chain():
    """Flavors by id; tests fill it. Patches DB lookup and token counting."""
    flavors = {}
    tokenizer = MagicMock()
    tokenizer.count_tokens.return_value = INPUT_TOKENS
    with patch.object(celery_app, "_get_sync_db_session", return_value=MagicMock()), \
         patch.object(celery_app, "_load_flavor", side_effect=lambda s, fid: flavors.get(str(fid))), \
         patch("app.services.context_check.TokenizerManager.get_instance", return_value=tokenizer), \
         patch("app.core.security.get_encryption_service", return_value=MagicMock()):
        yield flavors, tokenizer


def _get(max_hops=3):
    return celery_app._get_failover_task_data(_task_data(), TARGET, max_hops=max_hops)


def test_target_used_when_input_fits(chain):
    flavors, _ = chain
    flavors[TARGET] = _flavor(TARGET)

    out, hops = _get()

    assert out["flavor_id"] == TARGET
    assert hops == 1


def test_target_fallback_used_when_target_too_small(chain):
    flavors, _ = chain
    flavors[TARGET] = _flavor(TARGET, context_length=SMALL_CONTEXT,
                              fallback_flavor_id=TARGET_FALLBACK, failover_flavor_id=NEXT)
    flavors[TARGET_FALLBACK] = _flavor(TARGET_FALLBACK, context_length=SMALL_CONTEXT,
                                       processing_mode="iterative")
    flavors[NEXT] = _flavor(NEXT)

    out, hops = _get()

    # The iterative fallback chunks the input; it wins over the next flavor in the chain.
    assert out["flavor_id"] == TARGET_FALLBACK
    assert out["backendParams"]["processing_mode"] == "iterative"
    assert hops == 1


def test_next_in_chain_when_target_has_no_fallback(chain):
    flavors, _ = chain
    flavors[TARGET] = _flavor(TARGET, context_length=SMALL_CONTEXT, failover_flavor_id=NEXT)
    flavors[NEXT] = _flavor(NEXT)

    out, hops = _get()

    assert out["flavor_id"] == NEXT
    assert hops == 2


def test_chain_not_followed_when_target_has_failover_disabled(chain):
    flavors, _ = chain
    flavors[TARGET] = _flavor(TARGET, context_length=SMALL_CONTEXT, failover_flavor_id=NEXT)
    flavors[TARGET].failover_enabled = False
    flavors[NEXT] = _flavor(NEXT)

    out, hops = _get()

    # The UI keeps failover_flavor_id when failover is turned off; the link must not be used.
    assert out is None
    assert hops == 1


def test_next_in_chain_when_fallback_does_not_fit_either(chain):
    flavors, _ = chain
    flavors[TARGET] = _flavor(TARGET, context_length=SMALL_CONTEXT,
                              fallback_flavor_id=TARGET_FALLBACK, failover_flavor_id=NEXT)
    flavors[TARGET_FALLBACK] = _flavor(TARGET_FALLBACK, context_length=SMALL_CONTEXT)
    flavors[NEXT] = _flavor(NEXT)

    out, hops = _get()

    assert out["flavor_id"] == NEXT
    assert hops == 2


def test_inactive_fallback_is_not_used(chain):
    flavors, _ = chain
    flavors[TARGET] = _flavor(TARGET, context_length=SMALL_CONTEXT,
                              fallback_flavor_id=TARGET_FALLBACK, failover_flavor_id=NEXT)
    flavors[TARGET_FALLBACK] = _flavor(TARGET_FALLBACK, processing_mode="iterative", is_active=False)
    flavors[NEXT] = _flavor(NEXT)

    out, _ = _get()

    assert out["flavor_id"] == NEXT


def test_iterative_target_is_not_token_counted(chain):
    flavors, tokenizer = chain
    flavors[TARGET] = _flavor(TARGET, context_length=SMALL_CONTEXT, processing_mode="iterative")

    out, _ = _get()

    assert out["flavor_id"] == TARGET
    tokenizer.count_tokens.assert_not_called()


def test_nothing_fits_logs_why_each_target_was_skipped(chain, caplog):
    flavors, _ = chain
    flavors[TARGET] = _flavor(TARGET, context_length=SMALL_CONTEXT, failover_flavor_id=NEXT)
    flavors[NEXT] = _flavor(NEXT, context_length=SMALL_CONTEXT)

    out, hops = _get()

    assert out is None
    assert hops == 2
    skipped = [r.getMessage() for r in caplog.records if r.getMessage().startswith("Skipping failover flavor")]
    assert len(skipped) == 2
    assert "flavor-1111" in skipped[0] and "flavor-3333" in skipped[1]
    assert f"input ({INPUT_TOKENS} tokens) exceeds context limit (2476 available)" in skipped[0]


def test_chain_walk_stops_at_max_hops(chain):
    flavors, _ = chain
    flavors[TARGET] = _flavor(TARGET, context_length=SMALL_CONTEXT, failover_flavor_id=NEXT)
    flavors[NEXT] = _flavor(NEXT)

    out, hops = _get(max_hops=1)

    assert out is None
    assert hops == 1


def test_chain_walk_on_a_cycle_is_bounded_by_max_hops(chain):
    flavors, _ = chain
    flavors[TARGET] = _flavor(TARGET, context_length=SMALL_CONTEXT, failover_flavor_id=NEXT)
    flavors[NEXT] = _flavor(NEXT, context_length=SMALL_CONTEXT, failover_flavor_id=TARGET)

    out, hops = _get(max_hops=3)

    assert out is None
    assert hops == 3


def test_run_with_failover_raises_original_error_when_nothing_fits(chain):
    flavors, _ = chain
    flavors[TARGET] = _flavor(TARGET, context_length=SMALL_CONTEXT)
    engine = MagicMock()
    engine.return_value.run.side_effect = RateLimitFailoverError("primary rate limited")

    with patch.object(celery_app, "LLMInferenceEngine", engine):
        with pytest.raises(RateLimitFailoverError, match="primary rate limited"):
            celery_app._run_with_failover(MagicMock(), _task_data(), failover_depth=0)

    # The failover flavor was never called with an input that doesn't fit it.
    assert engine.call_count == 1


def test_run_with_failover_counts_skipped_flavors_in_depth(chain):
    flavors, _ = chain
    flavors[TARGET] = _flavor(TARGET, context_length=SMALL_CONTEXT, failover_flavor_id=NEXT)
    flavors[NEXT] = _flavor(NEXT)
    engine = MagicMock()
    engine.return_value.run.side_effect = [
        RateLimitFailoverError("primary rate limited"),
        {"output": "ok"},
    ]

    with patch.object(celery_app, "LLMInferenceEngine", engine):
        result = celery_app._run_with_failover(MagicMock(), _task_data(), failover_depth=0)

    assert result["final_flavor_id"] == NEXT
    assert result["failover_depth"] == 2
