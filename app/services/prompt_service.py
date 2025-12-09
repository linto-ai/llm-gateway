#!/usr/bin/env python3
"""Business logic for prompt management."""

from typing import Optional, Tuple, List
from uuid import UUID
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.prompt import Prompt
from app.models.prompt_type import PromptType
from app.models.service_type import ServiceType
from app.models.service_flavor import ServiceFlavor
from app.schemas.prompt import CreatePrompt, UpdatePrompt, DuplicatePrompt


async def _resolve_prompt_type_id(
    db: AsyncSession,
    prompt_type_code: Optional[str]
) -> Optional[UUID]:
    """Resolve prompt type code to ID."""
    if not prompt_type_code:
        return None

    result = await db.execute(
        select(PromptType).where(PromptType.code == prompt_type_code)
    )
    prompt_type = result.scalar_one_or_none()

    if not prompt_type:
        raise ValueError(f"Prompt type '{prompt_type_code}' not found")

    return prompt_type.id


async def _validate_service_type(
    db: AsyncSession,
    service_type_code: str
) -> None:
    """Validate service type exists in database."""
    result = await db.execute(
        select(ServiceType).where(ServiceType.code == service_type_code)
    )
    if not result.scalar_one_or_none():
        raise ValueError(f"Service type '{service_type_code}' not found")


async def create_prompt(
    db: AsyncSession,
    data: CreatePrompt
) -> Prompt:
    """
    Create a new prompt.

    Args:
        db: Database session
        data: Prompt creation data

    Returns:
        Created prompt

    Raises:
        IntegrityError: If duplicate (name, org, language) exists
        ValueError: If prompt_type or service_type is invalid
    """
    # Validate service_type against database
    await _validate_service_type(db, data.service_type)

    # Resolve prompt_type code to ID
    prompt_type_id = await _resolve_prompt_type_id(db, data.prompt_type)

    prompt = Prompt(
        name=data.name,
        content=data.content,
        description=data.description,
        organization_id=data.organization_id,
        service_type=data.service_type,
        prompt_category=data.prompt_category,
        prompt_type_id=prompt_type_id,
    )

    db.add(prompt)
    await db.commit()
    await db.refresh(prompt, ["prompt_type"])

    return prompt


async def list_prompts(
    db: AsyncSession,
    organization_id: Optional[str] = None,
    name: Optional[str] = None,
    service_type: Optional[str] = None,
    prompt_category: Optional[str] = None,
    prompt_type: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
) -> Tuple[List[Prompt], int]:
    """
    List prompts with optional filters.

    Args:
        db: Database session
        organization_id: Filter by organization
        name: Partial name match (case-insensitive)
        service_type: Filter by service type
        prompt_category: Filter by category ('system' or 'user')
        prompt_type: Filter by prompt type code (e.g., 'standard', 'reduce')
        limit: Max results (max 100)
        offset: Skip N results

    Returns:
        Tuple of (prompts list, total count)
    """
    # Enforce limit maximum
    limit = min(limit, 100)

    # Build query with eager loading of prompt_type
    query = select(Prompt).options(selectinload(Prompt.prompt_type))

    # Apply filters
    if organization_id:
        query = query.where(Prompt.organization_id == organization_id)

    if name:
        query = query.where(Prompt.name.ilike(f"%{name}%"))

    if prompt_category:
        query = query.where(Prompt.prompt_category == prompt_category)

    # Filter by prompt type code (join with prompt_types table)
    if prompt_type:
        query = query.join(PromptType, Prompt.prompt_type_id == PromptType.id)
        query = query.where(PromptType.code == prompt_type)

    # Service type filtering (simplified - all prompts now have service_type)
    if service_type:
        query = query.where(Prompt.service_type == service_type)

    # Get total count (need to build count query before pagination)
    count_subquery = query.subquery()
    count_query = select(func.count()).select_from(count_subquery)
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination
    query = query.limit(limit).offset(offset)

    # Execute query
    result = await db.execute(query)
    prompts = result.scalars().all()

    return list(prompts), total


async def get_prompt(
    db: AsyncSession,
    prompt_id: str
) -> Optional[Prompt]:
    """
    Get prompt by ID.

    Args:
        db: Database session
        prompt_id: Prompt UUID

    Returns:
        Prompt or None if not found
    """
    result = await db.execute(
        select(Prompt)
        .options(selectinload(Prompt.prompt_type))
        .where(Prompt.id == UUID(prompt_id))
    )
    return result.scalar_one_or_none()


async def update_prompt(
    db: AsyncSession,
    prompt_id: str,
    data: UpdatePrompt
) -> Optional[Prompt]:
    """
    Update prompt content and/or description.

    Args:
        db: Database session
        prompt_id: Prompt UUID
        data: Update data

    Returns:
        Updated prompt or None if not found

    Raises:
        ValueError: If prompt_type or service_type is invalid
    """
    prompt = await get_prompt(db, prompt_id)

    if not prompt:
        return None

    # Update fields
    if data.content is not None:
        prompt.content = data.content

    if data.description is not None:
        prompt.description = data.description

    if data.service_type is not None:
        await _validate_service_type(db, data.service_type)
        prompt.service_type = data.service_type

    if data.prompt_category is not None:
        prompt.prompt_category = data.prompt_category

    if data.prompt_type is not None:
        prompt_type_id = await _resolve_prompt_type_id(db, data.prompt_type)
        prompt.prompt_type_id = prompt_type_id

    await db.commit()
    await db.refresh(prompt, ["prompt_type"])

    return prompt


async def delete_prompt(
    db: AsyncSession,
    prompt_id: str
) -> bool:
    """
    Delete prompt after checking FK references.

    Args:
        db: Database session
        prompt_id: Prompt UUID

    Returns:
        True if deleted, False if not found

    Raises:
        ValueError: If prompt is referenced by service flavors
    """
    prompt = await get_prompt(db, prompt_id)

    if not prompt:
        return False

    # Check if referenced by any service_flavors
    result = await db.execute(
        select(ServiceFlavor).where(
            or_(
                ServiceFlavor.system_prompt_id == UUID(prompt_id),
                ServiceFlavor.user_prompt_template_id == UUID(prompt_id),
                ServiceFlavor.reduce_prompt_id == UUID(prompt_id)
            )
        )
    )

    if result.scalars().first():
        raise ValueError("Cannot delete prompt: referenced by service flavors")

    # Safe to delete
    await db.delete(prompt)
    await db.commit()

    return True


async def duplicate_prompt(
    db: AsyncSession,
    prompt_id: str,
    data: DuplicatePrompt
) -> Optional[Prompt]:
    """
    Duplicate a prompt with new name.

    Args:
        db: Database session
        prompt_id: Source prompt UUID
        data: Duplication data (new name, optional org)

    Returns:
        New prompt or None if source not found

    Raises:
        IntegrityError: If duplicate (name, org) exists
    """
    source = await get_prompt(db, prompt_id)

    if not source:
        return None

    # Create duplicate with new name
    new_prompt = Prompt(
        name=data.new_name,
        content=source.content,
        description=source.description,
        organization_id=data.organization_id if data.organization_id else source.organization_id,
        service_type=source.service_type,
        prompt_category=source.prompt_category,
        prompt_type_id=source.prompt_type_id,
    )

    db.add(new_prompt)
    await db.commit()
    await db.refresh(new_prompt, ["prompt_type"])

    return new_prompt


async def save_as_template(
    db: AsyncSession,
    prompt_id: str,
    template_name: str,
    category: str,
    prompt_type: Optional[str] = None,
    description: Optional[dict] = None,
    organization_id: Optional[str] = None
) -> Prompt:
    """
    Save prompt as reusable template.

    Args:
        db: Database session
        prompt_id: Source prompt UUID
        template_name: Name for the template
        category: Prompt category ('system' or 'user')
        prompt_type: Optional prompt type code (e.g., 'standard', 'reduce')
        description: Optional i18n description
        organization_id: Optional organization UUID

    Returns:
        Created template prompt

    Raises:
        ValueError: If source prompt not found or prompt_type is invalid
        IntegrityError: If template name already exists
    """
    # Get source prompt
    source = await get_prompt(db, prompt_id)
    if not source:
        raise ValueError(f"Prompt {prompt_id} not found")

    # Resolve prompt_type if provided, otherwise use source's prompt_type_id
    if prompt_type:
        prompt_type_id = await _resolve_prompt_type_id(db, prompt_type)
    else:
        prompt_type_id = source.prompt_type_id

    # Check for duplicate template name
    from fastapi import HTTPException
    query = select(Prompt).where(
        Prompt.name == template_name,
    )
    if organization_id:
        query = query.where(Prompt.organization_id == organization_id)
    else:
        query = query.where(Prompt.organization_id == source.organization_id)

    result = await db.execute(query)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"Template with name '{template_name}' already exists"
        )

    # Create template
    template = Prompt(
        name=template_name,
        content=source.content,
        description=description or source.description,
        organization_id=organization_id if organization_id else source.organization_id,
        service_type=source.service_type,
        prompt_category=category,
        prompt_type_id=prompt_type_id,
        parent_template_id=UUID(prompt_id)
    )

    db.add(template)
    await db.commit()
    await db.refresh(template, ["prompt_type"])

    return template


async def list_templates(
    db: AsyncSession,
    category: Optional[str] = None,
    prompt_type: Optional[str] = None,
    service_type: Optional[str] = None,
    page: int = 1,
    page_size: int = 50
) -> dict:
    """
    List prompt templates with filtering.

    Note: All prompts are now templates (is_template column removed).
    This function returns all prompts with optional filters.

    Args:
        db: Database session
        category: Filter by prompt_category ('system' or 'user')
        prompt_type: Filter by prompt type code (e.g., 'standard', 'reduce')
        service_type: Filter by service type
        page: Page number (1-indexed)
        page_size: Items per page (max 100)

    Returns:
        Dict with items, total, page, page_size, total_pages
    """
    # Enforce limits
    page_size = min(page_size, 100)
    page = max(page, 1)

    # Build query with eager loading of prompt_type
    query = select(Prompt).options(selectinload(Prompt.prompt_type))

    if category:
        query = query.where(Prompt.prompt_category == category)
    if prompt_type:
        query = query.join(PromptType, Prompt.prompt_type_id == PromptType.id)
        query = query.where(PromptType.code == prompt_type)

    # Service type filtering (simplified - all prompts now have service_type)
    if service_type:
        query = query.where(Prompt.service_type == service_type)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    query = query.order_by(Prompt.created_at.desc())

    result = await db.execute(query)
    items = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size

    return {
        "items": list(items),
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }
