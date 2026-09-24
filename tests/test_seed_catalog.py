#!/usr/bin/env python3
"""Seed of the LinTO catalog: prompts, templates and services shipped with the open source gateway,
non-destructive seeding, and the service display_order used to sort the service list."""
import json
import re
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from app.schemas.service import ServiceCreate, ServiceUpdate
from app.seeds.base_seed import get_or_create_prompt
from app.seeds.loader import SeedLoader

ROOT = Path(__file__).resolve().parent.parent
SEEDS = ROOT / "seeds"


def test_catalog_loaded_in_display_order_with_compte_rendu_first():
    services = SeedLoader().load_catalog_services()
    assert [s.route for s in services] == ["compte-rendu", "points-cles", "tableau-de-suivi", "brief-commercial", "note-technique"]
    assert services[0].display_order == 0
    assert all(s.scopes == ["linto"] for s in services)


def test_catalog_references_exist():
    prompt_names = {f["prompt_name"] for m in (SEEDS / "prompts").glob("*/manifest.json")
                    for f in json.loads(m.read_text()).get("files", {}).values()}
    for s in SeedLoader().load_catalog_services():
        assert s.flavor["user_prompt_name"] in prompt_names
        assert s.flavor["extraction_prompt_name"] in prompt_names
        assert (ROOT / "templates" / "default" / s.template_file).exists(), s.template_file


def test_catalog_labels_are_short():
    # LinTO Studio shows the service description as the tab label
    for s in SeedLoader().load_catalog_services():
        assert 0 < len(s.description["fr"]) <= 20 and 0 < len(s.description["en"]) <= 20


@pytest.mark.parametrize("prompt_dir", sorted(p.name for p in (SEEDS / "prompts").glob("linto-*")))
def test_shipped_prompts_are_brand_free_and_formattable(prompt_dir):
    text = (SEEDS / "prompts" / prompt_dir / "user.md").read_text()
    for word in ("LINAGORA", "linagora", "Parlement", "Parliament", "18442"):
        assert word not in text, f"{prompt_dir} contains {word}"
    if prompt_dir == "linto-extraction-champs":
        assert "{{output}}" in text and "{{metadata_fields}}" in text and "{}" not in text
    else:
        assert text.count("{}") == 1
        text.format("transcription")  # the gateway fills service prompts with str.format


def test_catalog_manifests_are_brand_free():
    for m in (SEEDS / "services").glob("*/manifest.json"):
        assert not re.search(r"linagora", m.read_text(), re.I), m


def _db_with(prompt):
    db = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = prompt
    db.execute = AsyncMock(return_value=result)
    return db


@pytest.mark.asyncio
async def test_existing_prompt_kept_unless_update_requested():
    prompt = MagicMock(content="version modifiée par un admin")
    await get_or_create_prompt(_db_with(prompt), name="linto-compte-rendu", content="version du seed")
    assert prompt.content == "version modifiée par un admin"
    await get_or_create_prompt(_db_with(prompt), name="linto-compte-rendu", content="version du seed", update_existing=True)
    assert prompt.content == "version du seed"


def test_display_order_defaults_and_bounds():
    assert ServiceCreate(name="x", service_type="summary").display_order == 100
    assert ServiceUpdate(display_order=0).display_order == 0
    assert ServiceUpdate().display_order is None
    with pytest.raises(ValidationError):
        ServiceUpdate(display_order=-1)


def test_display_order_migration_chain():
    text = (ROOT / "app/migrations/versions/012_service_display_order.py").read_text()
    assert "revision: str = '012'" in text and "down_revision: Union[str, None] = '011'" in text
    assert 'server_default="100"' in text
