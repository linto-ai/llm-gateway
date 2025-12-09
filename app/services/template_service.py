#!/usr/bin/env python3
"""Business logic for service template management."""

from typing import Optional, List
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.service_template import ServiceTemplate
from app.models.service import Service
from app.models.service_flavor import ServiceFlavor
from app.models.model import Model
from app.schemas.service_template import CreateFromTemplate


async def list_templates(
    db: AsyncSession,
    service_type: Optional[str] = None,
    is_public: Optional[bool] = True
) -> List[ServiceTemplate]:
    """
    List service templates with optional filters.

    Args:
        db: Database session
        service_type: Filter by service type
        is_public: Filter by public/private status

    Returns:
        List of templates
    """
    query = select(ServiceTemplate)

    if service_type:
        query = query.where(ServiceTemplate.service_type == service_type)

    if is_public is not None:
        query = query.where(ServiceTemplate.is_public == is_public)

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_template(
    db: AsyncSession,
    template_id: str
) -> Optional[ServiceTemplate]:
    """
    Get template by ID.

    Args:
        db: Database session
        template_id: Template UUID

    Returns:
        Template or None if not found
    """
    result = await db.execute(
        select(ServiceTemplate).where(ServiceTemplate.id == UUID(template_id))
    )
    return result.scalar_one_or_none()


async def create_service_from_template(
    db: AsyncSession,
    template_id: str,
    data: CreateFromTemplate
) -> dict:
    """
    Create service + flavor from template atomically.

    Args:
        db: Database session
        template_id: Template UUID
        data: Service creation data with customizations

    Returns:
        Dict with 'service' and 'flavor' keys

    Raises:
        ValueError: If template or model not found
        IntegrityError: If duplicate route in organization
    """
    # Get template
    template = await get_template(db, template_id)
    if not template:
        raise ValueError(f"Template {template_id} not found")

    # Verify model exists
    model_result = await db.execute(
        select(Model).where(Model.id == UUID(data.model_id))
    )
    model = model_result.scalar_one_or_none()
    if not model:
        raise ValueError(f"Model {data.model_id} not found")

    # Merge template defaults with customizations
    service_config = {**template.default_config.get('service', {})}
    if data.customizations and 'service' in data.customizations:
        service_config.update(data.customizations['service'])

    flavor_config = {**template.default_config.get('flavor', {})}
    if data.customizations and 'flavor' in data.customizations:
        flavor_config.update(data.customizations['flavor'])

    prompt_config = {**template.default_config.get('prompts', {})}
    if data.customizations and 'prompts' in data.customizations:
        prompt_config.update(data.customizations['prompts'])

    # Atomic transaction: create service + flavor
    async with db.begin():
        # Create service
        service = Service(
            name=data.name,
            route=data.route,
            service_type=template.service_type,
            organization_id=data.organization_id,
            fields=service_config.get('fields', 2),
            description=service_config.get('description', {}),
            is_active=True,
        )
        db.add(service)
        await db.flush()  # Get service ID

        # Create flavor
        flavor = ServiceFlavor(
            service_id=service.id,
            model_id=UUID(data.model_id),
            name=flavor_config.get('name', 'default'),
            temperature=flavor_config.get('temperature', 0.3),
            top_p=flavor_config.get('top_p', 0.9),
            create_new_turn_after=flavor_config.get('create_new_turn_after', 400),
            summary_turns=flavor_config.get('summary_turns', 8),
            max_new_turns=flavor_config.get('max_new_turns', 20),
            reduce_summary=flavor_config.get('reduce_summary', False),
            consolidate_summary=flavor_config.get('consolidate_summary', False),
            output_type=flavor_config.get('output_type', 'abstractive'),
            # Prompt references
            system_prompt_id=UUID(prompt_config['system_prompt_id']) if prompt_config.get('system_prompt_id') else None,
            user_prompt_template_id=UUID(prompt_config['user_prompt_template_id']) if prompt_config.get('user_prompt_template_id') else None,
            reduce_prompt_id=UUID(prompt_config['reduce_prompt_id']) if prompt_config.get('reduce_prompt_id') else None,
        )
        db.add(flavor)

    # Refresh to get all fields
    await db.refresh(service)
    await db.refresh(flavor)

    return {
        'service': service,
        'flavor': flavor
    }
