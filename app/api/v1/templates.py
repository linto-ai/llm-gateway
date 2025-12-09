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
    TemplateImportRequest,
)
from app.schemas.common import ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/templates", tags=["Document Templates"])


@router.post(
    "",
    response_model=TemplateResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def upload_template(
    service_id: UUID = Form(..., description="Service to associate template with"),
    name: str = Form(..., min_length=1, max_length=255, description="Template name"),
    description: Optional[str] = Form(None, description="Template description"),
    file: UploadFile = File(..., description="DOCX template file"),
    is_default: bool = Form(False, description="Set as default for service"),
    db: AsyncSession = Depends(get_db),
) -> TemplateResponse:
    """
    Upload a new DOCX template.

    The template file must be a valid DOCX document. Placeholders in the format
    {{placeholder_name}} will be automatically extracted.

    Maximum file size: 10 MB.
    """
    try:
        template = await document_template_service.create_template(
            db=db,
            service_id=service_id,
            file=file,
            name=name,
            description=description,
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
    service_id: Optional[UUID] = Query(None, description="Filter by service"),
    organization_id: Optional[UUID] = Query(None, description="Filter by organization"),
    include_global: bool = Query(False, description="Include global templates (service_id=NULL)"),
    global_only: bool = Query(False, description="Return only global templates"),
    db: AsyncSession = Depends(get_db),
) -> List[TemplateResponse]:
    """
    List all templates, optionally filtered by service or organization.

    Use `global_only=true` to fetch only global templates (template library).
    Use `include_global=true` with a `service_id` to also include global templates.
    """
    templates = await document_template_service.list_templates(
        db=db,
        service_id=service_id,
        organization_id=organization_id,
        include_global=include_global,
        global_only=global_only,
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


@router.post(
    "/{template_id}/set-default",
    response_model=TemplateResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def set_as_default(
    template_id: UUID,
    service_id: UUID = Query(..., description="Service to set default for"),
    db: AsyncSession = Depends(get_db),
) -> TemplateResponse:
    """
    Set template as the default for a service.

    Only one template can be the default per service.
    """
    success = await document_template_service.set_default_template(
        db=db,
        service_id=service_id,
        template_id=template_id,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Template not found or does not belong to the specified service"
        )

    await db.commit()

    template = await document_template_service.get_template(db, template_id)
    return template


@router.get(
    "/{template_id}/placeholders",
    response_model=List[str],
    responses={404: {"model": ErrorResponse}},
)
async def get_template_placeholders(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> List[str]:
    """
    Get list of placeholders found in this template.

    Returns the placeholder names without the {{}} braces.
    """
    template = await document_template_service.get_template(db, template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    return template.placeholders or []


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
    Import a global template to a service.

    Creates a copy of the global template and associates it with the specified service.
    Only global templates (service_id=NULL) can be imported.
    """
    try:
        template = await document_template_service.import_template(
            db=db,
            template_id=template_id,
            service_id=request.service_id,
            new_name=request.new_name,
            organization_id=request.organization_id,
        )
        await db.commit()
        return template
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


router_name = "templates"
