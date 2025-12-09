#!/usr/bin/env python3
"""API routes for service templates."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import get_db
from app.services import template_service
from app.schemas.service_template import (
    ServiceTemplateResponse,
    ServiceTemplateListResponse,
    CreateFromTemplate,
    CreateFromTemplateResponse
)

router = APIRouter(prefix="/service-templates", tags=["Service Templates"])


@router.get("", response_model=ServiceTemplateListResponse)
async def list_templates(
    service_type: Optional[str] = Query(None),
    is_public: Optional[bool] = Query(True),
    db: AsyncSession = Depends(get_db)
):
    """
    List service templates with optional filters.

    - **service_type**: Filter by type (summary, translation, categorization, etc.)
    - **is_public**: Filter by public status (default: true)
    """
    templates = await template_service.list_templates(
        db,
        service_type=service_type,
        is_public=is_public
    )

    return {"items": templates}


@router.get("/{template_id}", response_model=ServiceTemplateResponse)
async def get_template(
    template_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get service template by ID."""
    template = await template_service.get_template(db, template_id)

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return template


@router.post("/from-template/{template_id}", response_model=CreateFromTemplateResponse, status_code=201)
async def create_service_from_template(
    template_id: str,
    data: CreateFromTemplate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a service from a template.

    Atomically creates a service and its first flavor based on template defaults
    with optional customizations.

    - **name**: Service name (required)
    - **route**: Service route (required, unique per organization)
    - **model_id**: Model UUID to use (required)
    - **organization_id**: Organization UUID (optional)
    - **customizations**: Override template defaults (optional)
    """
    try:
        result = await template_service.create_service_from_template(
            db,
            template_id,
            data
        )

        # Convert SQLAlchemy models to dicts for response
        from app.schemas.service import ServiceResponse
        from pydantic import TypeAdapter

        service_adapter = TypeAdapter(ServiceResponse)

        return {
            "service": service_adapter.dump_python(result['service'], mode='json'),
            "flavor": {
                "id": str(result['flavor'].id),
                "service_id": str(result['flavor'].service_id),
                "model_id": str(result['flavor'].model_id),
                "name": result['flavor'].name,
                "temperature": result['flavor'].temperature,
                "top_p": result['flavor'].top_p,
                "create_new_turn_after": result['flavor'].create_new_turn_after,
                "summary_turns": result['flavor'].summary_turns,
                "max_new_turns": result['flavor'].max_new_turns,
                "reduce_summary": result['flavor'].reduce_summary,
                "consolidate_summary": result['flavor'].consolidate_summary,
                "output_type": result['flavor'].output_type,
                "system_prompt_id": str(result['flavor'].system_prompt_id) if result['flavor'].system_prompt_id else None,
                "user_prompt_template_id": str(result['flavor'].user_prompt_template_id) if result['flavor'].user_prompt_template_id else None,
                "reduce_prompt_id": str(result['flavor'].reduce_prompt_id) if result['flavor'].reduce_prompt_id else None,
                "created_at": result['flavor'].created_at.isoformat(),
                "updated_at": result['flavor'].updated_at.isoformat(),
            }
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="Duplicate route in organization"
        )
