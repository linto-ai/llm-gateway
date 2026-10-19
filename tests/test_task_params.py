"""Unit tests for `build_backend_params` (shared by dispatch and failover)."""

from types import SimpleNamespace

from app.models.model import Model
from app.services.task_params import build_backend_params


def _flavor(**overrides):
    model = Model(
        model_name="Display Name",
        model_identifier="model-id",
        context_length=8192,
        max_generation_length=2048,
        tokenizer_class="SomeTokenizer",
        tokenizer_name="org/tokenizer",
    )
    values = dict(
        model=model,
        tokenizer_override=None,
        temperature=0.3,
        top_p=0.8,
        create_new_turn_after=None,
        summary_turns=None,
        max_new_turns=None,
        reduce_summary=False,
        consolidate_summary=True,
        reduce_prompt=SimpleNamespace(name="reduce-en"),
        output_type="markdown",
        processing_mode="iterative",
        estimated_cost_per_1k_tokens=0.01,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def test_build_backend_params_from_flavor_and_model():
    assert build_backend_params(_flavor()) == {
        "modelName": "model-id",
        "totalContextLength": 8192,
        "maxGenerationLength": 2048,
        "tokenizerClass": "SomeTokenizer",
        "tokenizer": "org/tokenizer",
        "temperature": 0.3,
        "top_p": 0.8,
        "createNewTurnAfter": 500,
        "summaryTurns": 3,
        "maxNewTurns": 10,
        "reduceSummary": False,
        "consolidateSummary": True,
        "reduce_prompt": "reduce-en",
        "type": "markdown",
        "processing_mode": "iterative",
        "estimated_cost_per_1k_tokens": 0.01,
    }


def test_build_backend_params_overrides_sampling():
    params = build_backend_params(_flavor(), temperature=0.0, top_p=1.0)
    assert params["temperature"] == 0.0
    assert params["top_p"] == 1.0


def test_build_backend_params_without_reduce_prompt():
    assert build_backend_params(_flavor(reduce_prompt=None))["reduce_prompt"] is None
