"""Same-service rule for fallback/failover flavors, and cycle check on save (#31).

No DB: the session is a mock whose `execute` results are queued in call order.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1 import services as services_api
from app.schemas.service import ServiceFlavorCreate, ServiceFlavorUpdate
from app.services import flavor_service
from app.services.flavor_service import FlavorService

SERVICE_ID = uuid4()
OTHER_SERVICE_ID = uuid4()


def _result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _db(*values):
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[_result(v) for v in values])
    db.commit = AsyncMock()
    return db


@pytest.mark.parametrize("field", ["fallback_flavor_id", "failover_flavor_id"])
async def test_flavor_of_another_service_is_rejected(field):
    db = _db(OTHER_SERVICE_ID)
    links = {"fallback_flavor_id": None, "failover_flavor_id": None, field: uuid4()}

    with pytest.raises(HTTPException) as exc:
        await FlavorService.validate_flavor_links(db, SERVICE_ID, **links)

    assert exc.value.status_code == 400
    assert field in exc.value.detail


async def test_flavors_of_the_same_service_are_accepted():
    db = _db(SERVICE_ID, SERVICE_ID)

    await FlavorService.validate_flavor_links(db, SERVICE_ID, uuid4(), uuid4())

    assert db.execute.await_count == 2


async def test_no_links_no_query():
    db = _db()

    await FlavorService.validate_flavor_links(db, SERVICE_ID, None, None)

    db.execute.assert_not_awaited()


async def test_update_rejects_failover_flavor_of_another_service():
    flavor = SimpleNamespace(id=uuid4(), service_id=SERVICE_ID)
    db = _db(flavor, OTHER_SERVICE_ID)

    with pytest.raises(HTTPException) as exc:
        await FlavorService.update_flavor(
            db, flavor.id, ServiceFlavorUpdate(failover_flavor_id=uuid4())
        )

    assert exc.value.status_code == 400
    db.commit.assert_not_awaited()


CYCLE = (False, "Cycle detected: flavor chain loops back", 2, [])


def _stored_flavor(failover_enabled, failover_flavor_id=None):
    return SimpleNamespace(
        id=uuid4(), service_id=SERVICE_ID, name="f", processing_mode="iterative",
        prompt_user_content=None, user_prompt_template_id=None,
        failover_enabled=failover_enabled, failover_flavor_id=failover_flavor_id,
    )


async def test_update_rejects_failover_cycle():
    flavor = _stored_flavor(failover_enabled=True)
    target_id = uuid4()
    db = _db(flavor, SERVICE_ID)
    chain = AsyncMock(return_value=CYCLE)

    with patch.object(flavor_service.failover_service, "validate_failover_chain", chain):
        with pytest.raises(HTTPException) as exc:
            await FlavorService.update_flavor(
                db, flavor.id, ServiceFlavorUpdate(failover_flavor_id=target_id)
            )

    assert exc.value.status_code == 400
    assert exc.value.detail == "Cycle detected: flavor chain loops back"
    chain.assert_awaited_once_with(db, flavor.id, target_id)
    db.commit.assert_not_awaited()


async def test_add_flavor_rejects_failover_flavor_of_another_service():
    db = _db(OTHER_SERVICE_ID)
    db.add = MagicMock()
    request = ServiceFlavorCreate(name="f", model_id=uuid4(), temperature=0.2, failover_flavor_id=uuid4())

    with patch.object(services_api.service_service, "get_service_by_id",
                      AsyncMock(return_value=SimpleNamespace(id=SERVICE_ID))):
        with pytest.raises(HTTPException) as exc:
            await services_api.add_flavor_to_service(SERVICE_ID, request, db)

    assert exc.value.status_code == 400
    db.add.assert_not_called()


async def test_create_service_rejects_nested_flavor_failover_of_another_service():
    from app.schemas.service import ServiceCreate
    from app.services.service_service import service_service

    # 1st execute: model lookup (active); 2nd: the linked flavor's service
    db = _db(SimpleNamespace(is_active=True, model_name="m"), OTHER_SERVICE_ID)
    db.add = MagicMock()
    db.flush = AsyncMock()
    request = ServiceCreate(
        name="svc", service_type="summary",
        flavors=[ServiceFlavorCreate(name="f", model_id=uuid4(), temperature=0.2, failover_flavor_id=uuid4())],
    )

    with pytest.raises(HTTPException) as exc:
        await service_service.create_service(db, request)

    assert exc.value.status_code == 400
    assert "failover_flavor_id" in exc.value.detail
    # Only the service was added, not the flavor.
    assert db.add.call_count == 1


async def test_update_with_failover_off_skips_cycle_check():
    # The wizard resends the stored failover_flavor_id with failover turned off;
    # that save must go through even if the stored link is part of a loop.
    flavor = _stored_flavor(failover_enabled=True, failover_flavor_id=uuid4())
    db = _db(flavor, SERVICE_ID)
    db.execute.side_effect = list(db.execute.side_effect) + [MagicMock()]
    db.refresh = AsyncMock()
    chain = AsyncMock(return_value=CYCLE)
    update = ServiceFlavorUpdate(failover_enabled=False, failover_flavor_id=flavor.failover_flavor_id)

    with patch.object(flavor_service.failover_service, "validate_failover_chain", chain):
        await FlavorService.update_flavor(db, flavor.id, update)

    chain.assert_not_awaited()
    db.commit.assert_awaited_once()


async def test_update_turning_failover_on_checks_the_stored_target():
    stored_target = uuid4()
    flavor = _stored_flavor(failover_enabled=False, failover_flavor_id=stored_target)
    db = _db(flavor)
    chain = AsyncMock(return_value=CYCLE)

    with patch.object(flavor_service.failover_service, "validate_failover_chain", chain):
        with pytest.raises(HTTPException) as exc:
            await FlavorService.update_flavor(db, flavor.id, ServiceFlavorUpdate(failover_enabled=True))

    assert exc.value.status_code == 400
    chain.assert_awaited_once_with(db, flavor.id, stored_target)
    db.commit.assert_not_awaited()


def _chain_db(start_name, row):
    """execute #1: the starting flavor's name; #2: (name, next id, failover_enabled)."""
    first, second = MagicMock(), MagicMock()
    first.scalar_one_or_none.return_value = start_name
    second.one_or_none.return_value = row
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[first, second])
    return db


@pytest.mark.parametrize("enabled, expected_valid", [(True, False), (False, True)])
async def test_chain_check_stops_at_a_flavor_with_failover_off(enabled, expected_valid):
    from app.services.failover_service import failover_service

    a, b = uuid4(), uuid4()
    # A -> B is proposed; B already points back to A.
    db = _chain_db("A", ("B", a, enabled))

    is_valid, _, _, preview = await failover_service.validate_failover_chain(db, a, b)

    # B -> A only loops when B has failover on, as at runtime.
    assert is_valid is expected_valid
    assert preview == ["A", "B"]


async def test_update_service_rejects_nested_flavor_failover_of_another_service():
    from app.schemas.service import ServiceUpdate
    from app.services.service_service import service_service

    service = SimpleNamespace(id=SERVICE_ID, flavors=[])
    # 1st execute: the service; 2nd: model lookup; 3rd: the linked flavor's service
    db = _db(service, SimpleNamespace(is_active=True, model_name="m"), OTHER_SERVICE_ID)
    db.add = MagicMock()
    db.flush = AsyncMock()
    request = ServiceUpdate(
        flavors=[ServiceFlavorCreate(name="f", model_id=uuid4(), temperature=0.2, failover_flavor_id=uuid4())],
    )

    with pytest.raises(HTTPException) as exc:
        await service_service.update_service(db, SERVICE_ID, request)

    assert exc.value.status_code == 400
    assert "failover_flavor_id" in exc.value.detail
    db.add.assert_not_called()
