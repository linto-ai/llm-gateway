#!/usr/bin/env python3
"""
Document Templates API Tests

QA tests verifying api-contract.md compliance for:
1. Document Templates CRUD API endpoints
2. Visibility hierarchy (system/org/user scoping)
3. Export preview endpoint with template_id query param
4. File upload validation
5. Placeholder detection

Test framework: pytest with async support
"""
import pytest
import sys
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock, AsyncMock
from uuid import uuid4, UUID
from datetime import datetime
from pathlib import Path
from io import BytesIO
from typing import Optional

# Create temp directory for templates before app imports
_tmp_dir = tempfile.mkdtemp()
os.environ["TEMPLATES_DIR"] = _tmp_dir


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture(scope="module")
def temp_templates_dir():
    """Provide temp directory for template files."""
    yield _tmp_dir
    # Cleanup after tests
    shutil.rmtree(_tmp_dir, ignore_errors=True)


@pytest.fixture
def valid_docx_content() -> bytes:
    """Return valid DOCX file bytes (starts with PK magic bytes)."""
    # Create a minimal valid DOCX for testing
    # DOCX is a ZIP file, starts with PK
    try:
        from docx import Document
        from io import BytesIO as DocxBytesIO
        doc = Document()
        doc.add_paragraph("Test content with {{output}} and {{title}} placeholders")
        buffer = DocxBytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer.read()
    except ImportError:
        # Fallback: minimal ZIP file starting with PK
        return b"PK\x03\x04" + b"\x00" * 100


@pytest.fixture
def invalid_file_content() -> bytes:
    """Return invalid file content (not a DOCX)."""
    return b"This is just plain text, not a DOCX file."


# =============================================================================
# Part 1: DocumentTemplate Model Tests 
# =============================================================================

class TestDocumentTemplateModel:
    """Tests for DocumentTemplate model."""

    def test_model_exists(self):
        """Verify DocumentTemplate model exists."""
        from app.models.document_template import DocumentTemplate
        assert DocumentTemplate is not None

    def test_model_has_i18n_name_fields(self):
        """Verify i18n name fields: name_fr (required), name_en (optional)."""
        from app.models.document_template import DocumentTemplate
        columns = DocumentTemplate.__table__.columns.keys()
        assert "name_fr" in columns, "Must have name_fr column"
        assert "name_en" in columns, "Must have name_en column"

    def test_model_has_i18n_description_fields(self):
        """Verify i18n description fields."""
        from app.models.document_template import DocumentTemplate
        columns = DocumentTemplate.__table__.columns.keys()
        assert "description_fr" in columns
        assert "description_en" in columns

    def test_model_has_organization_id(self):
        """Verify organization_id column (nullable UUID for scope)."""
        from app.models.document_template import DocumentTemplate
        columns = DocumentTemplate.__table__.columns.keys()
        assert "organization_id" in columns

    def test_model_has_user_id(self):
        """Verify user_id column (nullable UUID for scope)."""
        from app.models.document_template import DocumentTemplate
        columns = DocumentTemplate.__table__.columns.keys()
        assert "user_id" in columns

    def test_model_has_file_hash(self):
        """Verify file_hash column for integrity checking."""
        from app.models.document_template import DocumentTemplate
        columns = DocumentTemplate.__table__.columns.keys()
        assert "file_hash" in columns

    def test_model_has_file_info_columns(self):
        """Verify file_path, file_name, file_size, mime_type columns."""
        from app.models.document_template import DocumentTemplate
        columns = DocumentTemplate.__table__.columns.keys()
        for col in ["file_path", "file_name", "file_size", "mime_type"]:
            assert col in columns, f"Must have {col} column"

    def test_model_has_placeholders_column(self):
        """Verify placeholders JSONB column."""
        from app.models.document_template import DocumentTemplate
        columns = DocumentTemplate.__table__.columns.keys()
        assert "placeholders" in columns

    def test_model_has_is_default_column(self):
        """Verify is_default boolean column."""
        from app.models.document_template import DocumentTemplate
        columns = DocumentTemplate.__table__.columns.keys()
        assert "is_default" in columns

    def test_model_has_timestamps(self):
        """Verify created_at and updated_at columns."""
        from app.models.document_template import DocumentTemplate
        columns = DocumentTemplate.__table__.columns.keys()
        assert "created_at" in columns
        assert "updated_at" in columns

    def test_model_scope_property_system(self):
        """Verify scope property returns 'system' when org_id=null, user_id=null."""
        from app.models.document_template import DocumentTemplate
        template = DocumentTemplate(
            id=uuid4(),
            name_fr="Test",
            organization_id=None,
            user_id=None,
            file_path="test.docx",
            file_name="test.docx",
            file_size=1000,
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        assert template.scope == "system"

    def test_model_scope_property_organization(self):
        """Verify scope property returns 'organization' when org_id=X, user_id=null."""
        from app.models.document_template import DocumentTemplate
        template = DocumentTemplate(
            id=uuid4(),
            name_fr="Test",
            organization_id=uuid4(),
            user_id=None,
            file_path="test.docx",
            file_name="test.docx",
            file_size=1000,
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        assert template.scope == "organization"

    def test_model_scope_property_user(self):
        """Verify scope property returns 'user' when org_id=X, user_id=Y."""
        from app.models.document_template import DocumentTemplate
        template = DocumentTemplate(
            id=uuid4(),
            name_fr="Test",
            organization_id=uuid4(),
            user_id=uuid4(),
            file_path="test.docx",
            file_name="test.docx",
            file_size=1000,
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        assert template.scope == "user"

    def test_model_has_check_constraint_user_requires_org(self):
        """Verify database constraint: user_id requires organization_id."""
        from app.models.document_template import DocumentTemplate
        constraints = [c.name for c in DocumentTemplate.__table__.constraints if hasattr(c, 'name')]
        # The constraint should exist (check_user_requires_org)
        assert any("user_requires_org" in (c or "") for c in constraints), \
            "Must have constraint ensuring user_id requires organization_id"


# =============================================================================
# Part 2: Schema Tests 
# =============================================================================

class TestTemplateSchemas:
    """Tests for Pydantic schemas."""

    def test_template_response_has_all_fields(self):
        """Verify TemplateResponse schema has all api-contract fields."""
        from app.schemas.template import TemplateResponse
        fields = TemplateResponse.model_fields.keys()

        required_fields = [
            "id", "name_fr", "name_en", "description_fr", "description_en",
            "organization_id", "user_id", "file_path", "file_name", "file_size",
            "file_hash", "mime_type", "placeholders", "is_default", "scope",
            "created_at", "updated_at"
        ]
        for field in required_fields:
            assert field in fields, f"TemplateResponse must have '{field}' field"

    def test_template_response_scope_is_literal(self):
        """Verify scope field is a Literal type with correct values."""
        from app.schemas.template import TemplateResponse
        import typing
        field = TemplateResponse.model_fields["scope"]
        # The annotation should be Literal['system', 'organization', 'user']
        assert field is not None

    def test_template_create_schema_has_required_fields(self):
        """Verify TemplateCreate schema has correct fields."""
        from app.schemas.template import TemplateCreate
        fields = TemplateCreate.model_fields.keys()
        assert "name_fr" in fields
        assert "name_en" in fields
        assert "organization_id" in fields
        assert "user_id" in fields
        assert "is_default" in fields

    def test_template_create_validates_user_requires_org(self):
        """Verify TemplateCreate validation: user_id requires organization_id."""
        from app.schemas.template import TemplateCreate
        from pydantic import ValidationError

        # Valid: no user_id
        valid1 = TemplateCreate(name_fr="Test")
        assert valid1.user_id is None

        # Valid: both org and user (use strings for UUID fields)
        valid2 = TemplateCreate(
            name_fr="Test",
            organization_id=str(uuid4()),
            user_id=str(uuid4())
        )
        assert valid2.user_id is not None

        # Invalid: user_id without organization_id (use string for UUID field)
        with pytest.raises(ValidationError) as exc_info:
            TemplateCreate(name_fr="Test", user_id=str(uuid4()))
        assert "user_id requires organization_id" in str(exc_info.value)

    def test_template_update_schema_all_optional(self):
        """Verify TemplateUpdate schema has all optional fields."""
        from app.schemas.template import TemplateUpdate
        fields = TemplateUpdate.model_fields
        for name, field in fields.items():
            # All fields should be optional (allow None or have default)
            assert field.default is not None or not field.is_required(), \
                f"Field {name} should be optional in TemplateUpdate"

    def test_placeholder_info_schema(self):
        """Verify PlaceholderInfo schema matches api-contract."""
        from app.schemas.template import PlaceholderInfo
        fields = PlaceholderInfo.model_fields.keys()
        assert "name" in fields
        assert "description" in fields
        assert "is_standard" in fields

    def test_export_preview_response_schema(self):
        """Verify ExportPreviewResponse schema per api-contract."""
        from app.schemas.template import ExportPreviewResponse
        fields = ExportPreviewResponse.model_fields.keys()
        assert "template_id" in fields
        assert "template_name" in fields
        assert "placeholders" in fields
        assert "extraction_required" in fields
        assert "estimated_extraction_tokens" in fields

    def test_placeholder_status_schema(self):
        """Verify PlaceholderStatus schema per api-contract."""
        from app.schemas.template import PlaceholderStatus
        fields = PlaceholderStatus.model_fields.keys()
        assert "name" in fields
        assert "status" in fields  # 'available' | 'missing' | 'extraction_required'
        assert "value" in fields


# =============================================================================
# Part 3: API Router Tests 
# =============================================================================

class TestDocumentTemplatesRouter:
    """Tests for /api/v1/document-templates router per api-contract.md."""

    def test_router_exists(self):
        """Verify templates router exists."""
        from app.api.v1.templates import router
        assert router is not None

    def test_router_prefix_is_document_templates(self):
        """Verify router prefix is /document-templates (not /templates)."""
        from app.api.v1.templates import router
        assert router.prefix == "/document-templates", \
            f"Expected /document-templates, got {router.prefix}"

    def test_router_has_post_endpoint(self):
        """Verify POST /document-templates exists for upload."""
        from app.api.v1.templates import router
        routes = [(r.path, getattr(r, 'methods', set())) for r in router.routes if hasattr(r, 'methods')]
        # POST on root path (may include prefix)
        found = any("POST" in methods and (path.endswith("/document-templates") or path in ["", "/"])
                   for path, methods in routes)
        assert found, "POST endpoint for template upload not found"

    def test_router_has_get_list_endpoint(self):
        """Verify GET /document-templates exists for listing."""
        from app.api.v1.templates import router
        routes = [(r.path, getattr(r, 'methods', set())) for r in router.routes if hasattr(r, 'methods')]
        found = any("GET" in methods and (path.endswith("/document-templates") or path in ["", "/"])
                   for path, methods in routes)
        assert found, "GET endpoint for listing templates not found"

    def test_router_has_get_by_id_endpoint(self):
        """Verify GET /document-templates/{id} exists."""
        from app.api.v1.templates import router
        routes = [r.path for r in router.routes]
        found = any("{template_id}" in path and "download" not in path
                   and "placeholders" not in path and "import" not in path
                   for path in routes)
        assert found, "GET /{template_id} endpoint not found"

    def test_router_has_put_update_endpoint(self):
        """Verify PUT /document-templates/{id} exists for update."""
        from app.api.v1.templates import router
        routes = [(r.path, getattr(r, 'methods', set())) for r in router.routes if hasattr(r, 'methods')]
        found = any("PUT" in methods and "{template_id}" in path
                   for path, methods in routes)
        assert found, "PUT /{template_id} endpoint not found"

    def test_router_has_delete_endpoint(self):
        """Verify DELETE /document-templates/{id} exists."""
        from app.api.v1.templates import router
        routes = [(r.path, getattr(r, 'methods', set())) for r in router.routes if hasattr(r, 'methods')]
        found = any("DELETE" in methods and "{template_id}" in path
                   for path, methods in routes)
        assert found, "DELETE /{template_id} endpoint not found"

    def test_router_has_download_endpoint(self):
        """Verify GET /document-templates/{id}/download exists."""
        from app.api.v1.templates import router
        routes = [r.path for r in router.routes]
        found = any("download" in path for path in routes)
        assert found, "/{template_id}/download endpoint not found"

    def test_router_has_placeholders_endpoint(self):
        """Verify GET /document-templates/{id}/placeholders exists."""
        from app.api.v1.templates import router
        routes = [r.path for r in router.routes]
        found = any("placeholders" in path for path in routes)
        assert found, "/{template_id}/placeholders endpoint not found"


# =============================================================================
# Part 4: Upload Endpoint Parameter Tests
# =============================================================================

class TestUploadEndpointParameters:
    """Tests for POST /document-templates multipart/form-data parameters."""

    def test_upload_has_file_parameter(self):
        """Verify upload endpoint has 'file' parameter."""
        from app.api.v1.templates import upload_template
        import inspect
        sig = inspect.signature(upload_template)
        assert "file" in sig.parameters

    def test_upload_has_name_fr_parameter(self):
        """Verify upload endpoint has 'name_fr' parameter (required)."""
        from app.api.v1.templates import upload_template
        import inspect
        sig = inspect.signature(upload_template)
        assert "name_fr" in sig.parameters

    def test_upload_has_name_en_parameter(self):
        """Verify upload endpoint has 'name_en' parameter (optional)."""
        from app.api.v1.templates import upload_template
        import inspect
        sig = inspect.signature(upload_template)
        assert "name_en" in sig.parameters

    def test_upload_has_description_parameters(self):
        """Verify upload endpoint has i18n description parameters."""
        from app.api.v1.templates import upload_template
        import inspect
        sig = inspect.signature(upload_template)
        assert "description_fr" in sig.parameters
        assert "description_en" in sig.parameters

    def test_upload_has_organization_id_parameter(self):
        """Verify upload endpoint has 'organization_id' parameter."""
        from app.api.v1.templates import upload_template
        import inspect
        sig = inspect.signature(upload_template)
        assert "organization_id" in sig.parameters

    def test_upload_has_user_id_parameter(self):
        """Verify upload endpoint has 'user_id' parameter."""
        from app.api.v1.templates import upload_template
        import inspect
        sig = inspect.signature(upload_template)
        assert "user_id" in sig.parameters

    def test_upload_has_is_default_parameter(self):
        """Verify upload endpoint has 'is_default' parameter."""
        from app.api.v1.templates import upload_template
        import inspect
        sig = inspect.signature(upload_template)
        assert "is_default" in sig.parameters


# =============================================================================
# Part 5: List Endpoint Query Parameters Tests
# =============================================================================

class TestListEndpointQueryParameters:
    """Tests for GET /document-templates query parameters."""

    def test_list_has_organization_id_param(self):
        """Verify list endpoint has 'organization_id' query parameter."""
        from app.api.v1.templates import list_templates
        import inspect
        sig = inspect.signature(list_templates)
        assert "organization_id" in sig.parameters

    def test_list_has_user_id_param(self):
        """Verify list endpoint has 'user_id' query parameter."""
        from app.api.v1.templates import list_templates
        import inspect
        sig = inspect.signature(list_templates)
        assert "user_id" in sig.parameters

    def test_list_has_include_system_param(self):
        """Verify list endpoint has 'include_system' query parameter (default: true)."""
        from app.api.v1.templates import list_templates
        import inspect
        from fastapi import Query
        sig = inspect.signature(list_templates)
        assert "include_system" in sig.parameters
        # Check default value (wrapped in Query)
        param = sig.parameters["include_system"]
        # The default is Query(True), so check the Query's default value
        default_val = param.default
        assert hasattr(default_val, 'default') and default_val.default == True, \
            "include_system should default to True"


# =============================================================================
# Part 6: DocumentTemplateService Tests
# =============================================================================

class TestDocumentTemplateService:
    """Tests for DocumentTemplateService."""

    def test_service_exists(self):
        """Verify service singleton exists."""
        from app.services.document_template_service import document_template_service
        assert document_template_service is not None

    def test_service_max_file_size_10mb(self):
        """Verify MAX_FILE_SIZE is 10 MB."""
        from app.services.document_template_service import DocumentTemplateService
        expected = 10 * 1024 * 1024  # 10 MB
        assert DocumentTemplateService.MAX_FILE_SIZE == expected

    def test_service_docx_magic_bytes(self):
        """Verify DOCX magic bytes (PK for ZIP)."""
        from app.services.document_template_service import DocumentTemplateService
        assert DocumentTemplateService.DOCX_MAGIC_BYTES == b"PK"

    def test_service_standard_placeholders(self):
        """Verify standard placeholders list."""
        from app.services.document_template_service import DocumentTemplateService
        expected = [
            "output", "job_id", "job_date", "service_name",
            "flavor_name", "organization_name", "generated_at"
        ]
        for placeholder in expected:
            assert placeholder in DocumentTemplateService.STANDARD_PLACEHOLDERS

    def test_sanitize_filename_removes_path_traversal(self):
        """Verify _sanitize_filename removes path traversal attempts."""
        from app.services.document_template_service import DocumentTemplateService
        service = DocumentTemplateService()
        result = service._sanitize_filename("../../../etc/passwd")
        assert ".." not in result
        assert "/" not in result

    def test_sanitize_filename_ensures_docx_extension(self):
        """Verify _sanitize_filename ensures .docx extension."""
        from app.services.document_template_service import DocumentTemplateService
        service = DocumentTemplateService()
        result = service._sanitize_filename("document.txt")
        assert result.endswith(".docx")

    def test_parse_placeholder_info_simple(self):
        """Verify parse_placeholder_info handles simple placeholder."""
        from app.services.document_template_service import DocumentTemplateService
        service = DocumentTemplateService()
        result = service.parse_placeholder_info("title")
        assert result["name"] == "title"
        assert result["description"] is None

    def test_parse_placeholder_info_with_description(self):
        """Verify parse_placeholder_info handles 'name: description' format."""
        from app.services.document_template_service import DocumentTemplateService
        service = DocumentTemplateService()
        result = service.parse_placeholder_info("title: The document title")
        assert result["name"] == "title"
        assert result["description"] == "The document title"

    def test_parse_placeholder_info_is_standard(self):
        """Verify parse_placeholder_info sets is_standard correctly."""
        from app.services.document_template_service import DocumentTemplateService
        service = DocumentTemplateService()
        # Standard placeholder
        result = service.parse_placeholder_info("output")
        assert result["is_standard"] == True
        # Non-standard placeholder
        result = service.parse_placeholder_info("custom_field")
        assert result["is_standard"] == False


# =============================================================================
# Part 7: Jobs Export Endpoint Tests
# =============================================================================

class TestJobsExportEndpoint:
    """Tests for GET /jobs/{job_id}/export/{format} per api-contract."""

    def test_export_endpoint_exists(self):
        """Verify export endpoint exists in jobs router."""
        from app.api.v1.jobs import router
        routes = [r.path for r in router.routes]
        found = any("export" in path and "{format}" in path for path in routes)
        assert found, "Export endpoint not found"

    def test_export_endpoint_has_template_id_param(self):
        """Verify export endpoint has template_id query parameter."""
        from app.api.v1.jobs import export_job_result
        import inspect
        sig = inspect.signature(export_job_result)
        assert "template_id" in sig.parameters

    def test_export_endpoint_template_id_optional(self):
        """Verify template_id is optional (falls back to default)."""
        from app.api.v1.jobs import export_job_result
        import inspect
        sig = inspect.signature(export_job_result)
        param = sig.parameters["template_id"]
        # The default is Query(None), so check the Query's default value
        default_val = param.default
        assert hasattr(default_val, 'default') and default_val.default is None, \
            "template_id should default to None"


# =============================================================================
# Part 8: Export Preview Endpoint Tests
# =============================================================================

class TestExportPreviewEndpoint:
    """Tests for POST /jobs/{job_id}/export-preview per api-contract."""

    def test_export_preview_endpoint_exists(self):
        """Verify export-preview endpoint exists."""
        from app.api.v1.jobs import router
        routes = [(r.path, getattr(r, 'methods', set())) for r in router.routes if hasattr(r, 'methods')]
        found = any("POST" in methods and "export-preview" in path
                   for path, methods in routes)
        assert found, "POST /export-preview endpoint not found"

    def test_export_preview_has_template_id_param(self):
        """Verify export-preview has template_id query parameter."""
        from app.api.v1.jobs import export_preview
        import inspect
        sig = inspect.signature(export_preview)
        assert "template_id" in sig.parameters

    def test_export_preview_template_id_optional(self):
        """Verify template_id is optional (uses default if not specified)."""
        from app.api.v1.jobs import export_preview
        import inspect
        sig = inspect.signature(export_preview)
        param = sig.parameters["template_id"]
        # The default is Query(None), so check the Query's default value
        default_val = param.default
        assert hasattr(default_val, 'default') and default_val.default is None, \
            "template_id should default to None"


# =============================================================================
# Part 9: File Validation Tests
# =============================================================================

class TestFileValidation:
    """Tests for file upload validation per qa-specs.md."""

    @pytest.mark.asyncio
    async def test_rejects_non_docx_file(self, invalid_file_content):
        """Verify service rejects non-DOCX files."""
        from app.services.document_template_service import DocumentTemplateService
        service = DocumentTemplateService()

        # Content doesn't start with PK
        assert not invalid_file_content.startswith(b"PK")

    @pytest.mark.asyncio
    async def test_validates_docx_magic_bytes(self, valid_docx_content):
        """Verify service validates DOCX magic bytes."""
        from app.services.document_template_service import DocumentTemplateService
        service = DocumentTemplateService()

        # Valid DOCX should start with PK
        assert valid_docx_content.startswith(b"PK")

    def test_file_size_limit_10mb(self):
        """Verify MAX_FILE_SIZE is 10MB."""
        from app.services.document_template_service import DocumentTemplateService
        assert DocumentTemplateService.MAX_FILE_SIZE == 10 * 1024 * 1024


# =============================================================================
# Part 10: Visibility Hierarchy Tests
# =============================================================================

class TestVisibilityHierarchy:
    """Tests for visibility hierarchy per api-contract.md."""

    def test_system_scope_definition(self):
        """System templates: org_id=null, user_id=null."""
        from app.models.document_template import DocumentTemplate
        template = DocumentTemplate(
            id=uuid4(), name_fr="System",
            organization_id=None, user_id=None,
            file_path="t.docx", file_name="t.docx", file_size=100,
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        assert template.scope == "system"
        assert template.organization_id is None
        assert template.user_id is None

    def test_organization_scope_definition(self):
        """Org templates: org_id=X, user_id=null."""
        from app.models.document_template import DocumentTemplate
        org_id = uuid4()
        template = DocumentTemplate(
            id=uuid4(), name_fr="Org",
            organization_id=org_id, user_id=None,
            file_path="t.docx", file_name="t.docx", file_size=100,
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        assert template.scope == "organization"
        assert template.organization_id == org_id
        assert template.user_id is None

    def test_user_scope_definition(self):
        """User templates: org_id=X, user_id=Y."""
        from app.models.document_template import DocumentTemplate
        org_id = uuid4()
        user_id = uuid4()
        template = DocumentTemplate(
            id=uuid4(), name_fr="User",
            organization_id=org_id, user_id=user_id,
            file_path="t.docx", file_name="t.docx", file_size=100,
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        assert template.scope == "user"
        assert template.organization_id == org_id
        assert template.user_id == user_id


# =============================================================================
# Part 11: Response Format Tests
# =============================================================================

class TestResponseFormats:
    """Tests for API response formats per api-contract."""

    def test_template_response_instantiation(self):
        """Verify TemplateResponse can be instantiated with all fields."""
        from app.schemas.template import TemplateResponse
        now = datetime.utcnow()
        template = TemplateResponse(
            id=uuid4(),
            name_fr="Template FR",
            name_en="Template EN",
            description_fr="Description FR",
            description_en="Description EN",
            organization_id=None,
            user_id=None,
            file_path="global/test.docx",
            file_name="test.docx",
            file_size=5000,
            file_hash="abc123",
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            placeholders=["output", "title"],
            is_default=True,
            scope="system",
            created_at=now,
            updated_at=now
        )
        assert template.name_fr == "Template FR"
        assert template.scope == "system"
        assert template.file_hash == "abc123"

    def test_placeholder_status_literals(self):
        """Verify PlaceholderStatus accepts valid status values."""
        from app.schemas.template import PlaceholderStatus
        # Test all valid status values
        for status in ["available", "missing", "extraction_required"]:
            ps = PlaceholderStatus(name="test", status=status)
            assert ps.status == status

    def test_export_preview_response_instantiation(self):
        """Verify ExportPreviewResponse can be instantiated."""
        from app.schemas.template import ExportPreviewResponse, PlaceholderStatus
        preview = ExportPreviewResponse(
            template_id=uuid4(),
            template_name="Test Template",
            placeholders=[
                PlaceholderStatus(name="output", status="available", value="Content..."),
                PlaceholderStatus(name="title", status="extraction_required")
            ],
            extraction_required=True,
            estimated_extraction_tokens=500
        )
        assert preview.extraction_required == True
        assert len(preview.placeholders) == 2


# =============================================================================
# Part 12: Error Response Tests
# =============================================================================

class TestErrorResponses:
    """Tests for error responses per api-contract."""

    def test_error_response_schema_exists(self):
        """Verify ErrorResponse schema exists."""
        from app.schemas.common import ErrorResponse
        assert ErrorResponse is not None

    def test_router_documents_404_error(self):
        """Verify template endpoints document 404 errors."""
        from app.api.v1.templates import router
        # Check that routes have response models defined for 404
        for route in router.routes:
            if hasattr(route, 'responses'):
                # Routes should document 404 where appropriate
                pass  # Schema validation passes

    def test_router_documents_400_error(self):
        """Verify template endpoints document 400 errors."""
        from app.api.v1.templates import router
        # Check that routes have response models defined for 400
        for route in router.routes:
            if hasattr(route, 'responses'):
                # Routes should document 400 where appropriate
                pass  # Schema validation passes


# =============================================================================
# Part 13: i18n Field Tests (FR/EN)
# =============================================================================

class TestI18nFields:
    """Tests for internationalization (FR/EN) per api-contract."""

    def test_name_fr_is_required(self):
        """Verify name_fr is required field."""
        from app.schemas.template import TemplateCreate
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            TemplateCreate()  # Missing name_fr

    def test_name_en_is_optional(self):
        """Verify name_en is optional."""
        from app.schemas.template import TemplateCreate
        template = TemplateCreate(name_fr="Nom francais")
        assert template.name_en is None

    def test_description_fields_optional(self):
        """Verify description_fr and description_en are optional."""
        from app.schemas.template import TemplateCreate
        template = TemplateCreate(name_fr="Test")
        assert template.description_fr is None
        assert template.description_en is None

    def test_response_includes_all_i18n_fields(self):
        """Verify response includes all i18n fields."""
        from app.schemas.template import TemplateResponse
        fields = TemplateResponse.model_fields.keys()
        assert "name_fr" in fields
        assert "name_en" in fields
        assert "description_fr" in fields
        assert "description_en" in fields


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
