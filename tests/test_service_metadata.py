"""The API's `metadata` field lands on the `service_metadata` column (SQLAlchemy
reserves `metadata`), on creation and on update — this is where LinTO Studio
and Meet read the service's icon from."""

import pytest

from app.schemas.service import ServiceCreate, ServiceUpdate
from app.services.service_service import ServiceService


@pytest.mark.asyncio
async def test_metadata_persists_on_create_and_update(async_db_session, async_sample_model):
    service = ServiceService()
    created = await service.create_service(
        async_db_session,
        ServiceCreate(
            name="Minutes",
            route="minutes-meta",
            service_type="summary",
            description={"en": "Minutes"},
            scopes=["linto", "meet"],
            metadata={"icon": "file-text"},
            flavors=[
                {
                    "name": "Default",
                    "model_id": str(async_sample_model.id),
                    "is_default": True,
                    "temperature": 0.2,
                }
            ],
        ),
    )
    assert created.metadata == {"icon": "file-text"}

    fetched = await service.get_service_by_id(async_db_session, created.id)
    assert fetched.metadata == {"icon": "file-text"}

    updated = await service.update_service(
        async_db_session, created.id, ServiceUpdate(metadata={"icon": "article"})
    )
    assert updated.metadata == {"icon": "article"}
    fetched = await service.get_service_by_id(async_db_session, created.id)
    assert fetched.metadata == {"icon": "article"}
