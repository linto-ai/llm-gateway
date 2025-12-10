#!/usr/bin/env python3
"""Document Templates API router."""
import logging
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, File, Form, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.services.document_template_service import document_template_service
from app.schemas.template import (
    TemplateResponse,
    TemplateUpdate,
    TemplateImportRequest,
    PlaceholderInfo,
)
from app.schemas.common import ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/document-templates", tags=["Document Templates"])


@router.post(
    "",
    response_model=TemplateResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
    },
)
async def upload_template(
    file: UploadFile = File(..., description="DOCX template file"),
    name_fr: str = Form(..., min_length=1, max_length=255, description="French name"),
    name_en: Optional[str] = Form(None, max_length=255, description="English name"),
    description_fr: Optional[str] = Form(None, description="French description"),
    description_en: Optional[str] = Form(None, description="English description"),
    # Using str instead of UUID for flexibility with external systems (MongoDB ObjectIds, etc.)
    organization_id: Optional[str] = Form(None, max_length=100, description="Organization scope (null for system)"),
    user_id: Optional[str] = Form(None, max_length=100, description="User scope (null for org/system)"),
    is_default: bool = Form(False, description="Set as default for scope"),
    db: AsyncSession = Depends(get_db),
) -> TemplateResponse:
    """
    Upload a new DOCX template.

    The template file must be a valid DOCX document. Placeholders in the format
    {{placeholder_name}} will be automatically extracted.

    Scope hierarchy:
    - System templates: organization_id=null, user_id=null (visible to all)
    - Organization templates: organization_id=X, user_id=null (visible to org X)
    - User templates: organization_id=X, user_id=Y (visible only to user Y)

    Maximum file size: 10 MB.
    """
    try:
        template = await document_template_service.create_template(
            db=db,
            file=file,
            name_fr=name_fr,
            name_en=name_en,
            description_fr=description_fr,
            description_en=description_en,
            organization_id=organization_id,
            user_id=user_id,
            is_default=is_default,
        )
        await db.commit()
        return template
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "",
    response_model=List[TemplateResponse],
    responses={500: {"model": ErrorResponse}},
)
async def list_templates(
    # Using str instead of UUID for flexibility with external systems
    organization_id: Optional[str] = Query(None, max_length=100, description="Filter by organization scope"),
    user_id: Optional[str] = Query(None, max_length=100, description="Filter by user scope"),
    include_system: bool = Query(True, description="Include system templates (org_id=null, user_id=null)"),
    db: AsyncSession = Depends(get_db),
) -> List[TemplateResponse]:
    """
    List templates with hierarchical visibility.

    Returns templates visible to the given org/user:
    - System templates (org=null, user=null): visible if include_system=true
    - Organization templates (org=X, user=null): visible if org matches
    - User templates (org=X, user=Y): visible only if both org and user match

    Examples:
    - `?include_system=true` -> system templates only
    - `?organization_id=X&include_system=true` -> system + org X templates
    - `?organization_id=X&user_id=Y&include_system=true` -> system + org X + user Y templates
    """
    templates = await document_template_service.list_templates(
        db=db,
        organization_id=organization_id,
        user_id=user_id,
        include_system=include_system,
    )
    return templates


@router.get(
    "/{template_id}",
    response_model=TemplateResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> TemplateResponse:
    """Get template details by ID."""
    template = await document_template_service.get_template(db, template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    return template


@router.put(
    "/{template_id}",
    response_model=TemplateResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def update_template(
    template_id: UUID,
    file: Optional[UploadFile] = File(None, description="New DOCX file"),
    name_fr: Optional[str] = Form(None, min_length=1, max_length=255, description="French name"),
    name_en: Optional[str] = Form(None, max_length=255, description="English name"),
    description_fr: Optional[str] = Form(None, description="French description"),
    description_en: Optional[str] = Form(None, description="English description"),
    is_default: Optional[bool] = Form(None, description="Set as default"),
    db: AsyncSession = Depends(get_db),
) -> TemplateResponse:
    """
    Update template metadata and/or file.

    All fields are optional - only provided fields will be updated.
    If a new file is provided, placeholders will be re-extracted.
    """
    try:
        template = await document_template_service.update_template(
            db=db,
            template_id=template_id,
            file=file,
            name_fr=name_fr,
            name_en=name_en,
            description_fr=description_fr,
            description_en=description_en,
            is_default=is_default,
        )
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )
        await db.commit()
        return template
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete(
    "/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ErrorResponse}},
)
async def delete_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete a template.

    This will remove both the database record and the file from storage.
    """
    deleted = await document_template_service.delete_template(db, template_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    await db.commit()


@router.get(
    "/{template_id}/download",
    responses={
        404: {"model": ErrorResponse},
        200: {
            "content": {
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {}
            }
        },
    },
)
async def download_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Download the original DOCX template file."""
    template = await document_template_service.get_template(db, template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    file_path = document_template_service.get_file_path(template)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template file not found on disk"
        )

    def iter_file():
        with open(file_path, "rb") as f:
            yield from f

    return StreamingResponse(
        iter_file(),
        media_type=template.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{template.file_name}"'
        }
    )


@router.get(
    "/{template_id}/placeholders",
    response_model=List[PlaceholderInfo],
    responses={404: {"model": ErrorResponse}},
)
async def get_template_placeholders(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> List[PlaceholderInfo]:
    """
    Get parsed placeholders from template.

    Returns detailed information about each placeholder:
    - name: The placeholder name (extracted from "{{name}}" or "{{name: description}}")
    - description: Description hint if provided in "{{name: description}}" format
    - is_standard: True if this is a system-provided placeholder (output, job_id, etc.)
    """
    template = await document_template_service.get_template(db, template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    result = []
    for placeholder in (template.placeholders or []):
        info = document_template_service.parse_placeholder_info(placeholder)
        result.append(PlaceholderInfo(
            name=info["name"],
            description=info["description"],
            is_standard=info["is_standard"],
        ))

    return result


@router.post(
    "/{template_id}/set-default",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"model": ErrorResponse},
    },
)
async def set_default_template(
    template_id: UUID,
    service_id: UUID = Query(..., description="Service ID to set the default template for"),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Set a template as the default for a service.

    Updates the service's default_template_id to point to this template.
    """
    # Verify template exists
    template = await document_template_service.get_template(db, template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    # Update service default_template_id
    from app.models.service import Service
    from sqlalchemy import select, update

    # First check service exists
    result = await db.execute(select(Service).where(Service.id == service_id))
    service = result.scalar_one_or_none()
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )

    # Use explicit UPDATE statement
    await db.execute(
        update(Service)
        .where(Service.id == service_id)
        .values(default_template_id=template_id)
    )
    await db.commit()


@router.post(
    "/{template_id}/set-global-default",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def set_global_default_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Set a template as the global default (for exports without service-specific default).

    Only system-scope templates (organization_id=null, user_id=null) can be set as global default.
    This clears any existing global default.
    """
    # Verify template exists
    template = await document_template_service.get_template(db, template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    # Only system-scope templates can be global default
    if template.organization_id is not None or template.user_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only system-scope templates can be set as global default"
        )

    # Update template to set as default (this clears existing default at same scope)
    await document_template_service.update_template(
        db=db,
        template_id=template_id,
        is_default=True,
    )
    await db.commit()


@router.post(
    "/{template_id}/import",
    response_model=TemplateResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def import_template(
    template_id: UUID,
    request: TemplateImportRequest,
    db: AsyncSession = Depends(get_db),
) -> TemplateResponse:
    """
    Import a system template to an organization or user scope.

    Creates a copy of the template at the target scope. Only templates from
    higher scopes can be imported:
    - System templates can be imported to organization or user scope
    - Organization templates can be imported to user scope
    - User templates cannot be imported (already at lowest scope)
    """
    try:
        template = await document_template_service.import_template(
            db=db,
            template_id=template_id,
            target_organization_id=request.target_organization_id,
            target_user_id=request.target_user_id,
            new_name_fr=request.new_name_fr,
            new_name_en=request.new_name_en,
        )
        await db.commit()
        return template
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


router_name = "document-templates"
