#!/usr/bin/env python3
import logging
from typing import Optional
from uuid import UUID
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload, joinedload
from app.models.service import Service
from app.models.service_flavor import ServiceFlavor
from app.models.model import Model
from app.models.prompt import Prompt
from app.schemas.service import (
    ServiceCreate, ServiceUpdate, ServiceResponse, ServiceListResponse,
    ServiceFlavorResponse
)
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class ServiceService:
    """Service layer for service business logic."""

    @staticmethod
    def _is_global_service():
        """SQLAlchemy condition: service visible to everyone (no scope restrictions)."""
        return and_(
            func.cardinality(Service.allowed_organization_ids) == 0,
            func.cardinality(Service.allowed_user_ids) == 0,
            or_(Service.organization_id.is_(None), Service.organization_id == ""),
        )

    @staticmethod
    def _normalize_ids(ids) -> list:
        """Strip, drop blanks/dupes and sort a list of free-form IDs (stable equality)."""
        if not ids:
            return []
        seen = []
        for raw in ids:
            if raw is None:
                continue
            val = str(raw).strip()
            if val and val not in seen:
                seen.append(val)
        return sorted(seen)

    @classmethod
    def _resolve_scope_lists(cls, allowed_organization_ids, allowed_user_ids,
                             organization_id_alias=None):
        """Build effective (orgs, users) lists, folding the deprecated org alias in."""
        orgs = cls._normalize_ids(allowed_organization_ids)
        users = cls._normalize_ids(allowed_user_ids)
        if not orgs and organization_id_alias:
            orgs = cls._normalize_ids([organization_id_alias])
        return orgs, users

    async def _load_prompt_contents(
        self,
        db: AsyncSession,
        flavor_dict: dict
    ) -> dict:
        """
        Load prompt content from template IDs if content fields are not set.

        When a prompt template ID is provided but the corresponding content field
        is empty, this method fetches the prompt and populates the content.

        Args:
            db: Database session
            flavor_dict: Flavor data dict with potential template IDs

        Returns:
            Updated flavor_dict with prompt contents populated
        """
        # Map of template ID field -> content field
        prompt_mappings = [
            ('system_prompt_id', 'prompt_system_content'),
            ('user_prompt_template_id', 'prompt_user_content'),
            ('reduce_prompt_id', 'prompt_reduce_content'),
        ]

        for id_field, content_field in prompt_mappings:
            prompt_id = flavor_dict.get(id_field)
            content = flavor_dict.get(content_field)

            # Only load if ID is set but content is empty
            if prompt_id and not content:
                result = await db.execute(
                    select(Prompt).where(Prompt.id == prompt_id)
                )
                prompt = result.scalar_one_or_none()
                if prompt:
                    flavor_dict[content_field] = prompt.content
                    logger.debug(f"Loaded {content_field} from prompt {prompt.name}")

        return flavor_dict

    def _get_flavor_load_options(self):
        """
        Get SQLAlchemy load options for flavors with all relationships.

        Includes prompt relationships for prompt name display.
        """
        return (
            selectinload(Service.flavors)
            .joinedload(ServiceFlavor.model)
            .joinedload(Model.provider),
            selectinload(Service.flavors)
            .joinedload(ServiceFlavor.system_prompt),
            selectinload(Service.flavors)
            .joinedload(ServiceFlavor.user_prompt_template),
            selectinload(Service.flavors)
            .joinedload(ServiceFlavor.reduce_prompt),
            selectinload(Service.flavors)
            .joinedload(ServiceFlavor.placeholder_extraction_prompt),
            selectinload(Service.flavors)
            .joinedload(ServiceFlavor.categorization_prompt),
            selectinload(Service.flavors)
            .joinedload(ServiceFlavor.fallback_flavor)
            .joinedload(ServiceFlavor.service),
            selectinload(Service.flavors)
            .joinedload(ServiceFlavor.failover_flavor)
            .joinedload(ServiceFlavor.service),
        )

    def _to_flavor_response(self, flavor: ServiceFlavor) -> ServiceFlavorResponse:
        """Convert ServiceFlavor ORM object to response schema with prompt names."""
        # Build dict from ORM object
        flavor_dict = {
            "id": flavor.id,
            "service_id": flavor.service_id,
            "model_id": flavor.model_id,
            "name": flavor.name,
            "temperature": flavor.temperature,
            "top_p": flavor.top_p,
            "is_default": flavor.is_default,
            "description": flavor.description,
            "is_active": flavor.is_active,
            "frequency_penalty": flavor.frequency_penalty,
            "presence_penalty": flavor.presence_penalty,
            "stop_sequences": flavor.stop_sequences or [],
            "custom_params": flavor.custom_params or {},
            "estimated_cost_per_1k_tokens": flavor.estimated_cost_per_1k_tokens,
            "max_concurrent_requests": flavor.max_concurrent_requests,
            "priority": flavor.priority,
            "create_new_turn_after": flavor.create_new_turn_after,
            "summary_turns": flavor.summary_turns,
            "max_new_turns": flavor.max_new_turns,
            "reduce_summary": flavor.reduce_summary,
            "consolidate_summary": flavor.consolidate_summary,
            "output_type": flavor.output_type,
            "system_prompt_id": flavor.system_prompt_id,
            "user_prompt_template_id": flavor.user_prompt_template_id,
            "reduce_prompt_id": flavor.reduce_prompt_id,
            # Populate prompt names from loaded relationships
            "system_prompt_name": flavor.system_prompt.name if flavor.system_prompt else None,
            "user_prompt_template_name": flavor.user_prompt_template.name if flavor.user_prompt_template else None,
            "reduce_prompt_name": flavor.reduce_prompt.name if flavor.reduce_prompt else None,
            "prompt_system_content": flavor.prompt_system_content,
            "prompt_user_content": flavor.prompt_user_content,
            "prompt_reduce_content": flavor.prompt_reduce_content,
            "tokenizer_override": flavor.tokenizer_override,
            # Processing mode
            "processing_mode": flavor.processing_mode,
            # Fallback configuration
            "fallback_flavor_id": flavor.fallback_flavor_id,
            "fallback_flavor_name": flavor.fallback_flavor.name if flavor.fallback_flavor else None,
            "fallback_service_name": flavor.fallback_flavor.service.name if flavor.fallback_flavor and flavor.fallback_flavor.service else None,
            # Failover configuration
            "failover_flavor_id": flavor.failover_flavor_id,
            "failover_flavor_name": flavor.failover_flavor.name if flavor.failover_flavor else None,
            "failover_service_name": flavor.failover_flavor.service.name if flavor.failover_flavor and flavor.failover_flavor.service else None,
            "failover_enabled": flavor.failover_enabled,
            "failover_on_timeout": flavor.failover_on_timeout,
            "failover_on_rate_limit": flavor.failover_on_rate_limit,
            "failover_on_model_error": flavor.failover_on_model_error,
            "failover_on_content_filter": flavor.failover_on_content_filter,
            "max_failover_depth": flavor.max_failover_depth,
            # Placeholder extraction
            "placeholder_extraction_prompt_id": flavor.placeholder_extraction_prompt_id,
            "placeholder_extraction_prompt_name": flavor.placeholder_extraction_prompt.name if flavor.placeholder_extraction_prompt else None,
            # Categorization
            "categorization_prompt_id": flavor.categorization_prompt_id,
            "categorization_prompt_name": flavor.categorization_prompt.name if flavor.categorization_prompt else None,
            "created_at": flavor.created_at,
            "updated_at": flavor.updated_at,
            "model": flavor.model,
        }
        return ServiceFlavorResponse.model_validate(flavor_dict)

    def _to_response(self, service: Service) -> ServiceResponse:
        """Convert Service ORM object to response schema."""
        # Build dict with explicit metadata mapping to avoid SQLAlchemy namespace collision
        # Use _to_flavor_response for each flavor to include prompt names
        service_dict = {
            "id": service.id,
            "name": service.name,
            "route": service.route,
            "service_type": service.service_type,
            "description": service.description,
            "allowed_organization_ids": list(service.allowed_organization_ids or []),
            "allowed_user_ids": list(service.allowed_user_ids or []),
            "organization_id": service.organization_id,
            "is_active": service.is_active,
            "metadata": service.service_metadata,  # Map service_metadata -> metadata
            "service_category": service.service_category,
            "default_template_id": service.default_template_id,
            "template_ids": [t.id for t in (service.document_templates or [])],
            "flavors": [self._to_flavor_response(f) for f in service.flavors],
            "created_at": service.created_at,
            "updated_at": service.updated_at
        }
        return ServiceResponse.model_validate(service_dict)

    async def create_service(
        self,
        db: AsyncSession,
        request: ServiceCreate
    ) -> ServiceResponse:
        """
        Create a new service with flavors.

        Args:
            db: Database session
            request: Service creation request

        Returns:
            Created service response

        Raises:
            HTTPException: 409 if service name/route already exists
            HTTPException: 404 if referenced model not found
            HTTPException: 422 if model is not active
        """
        # Validate all model references exist and are active
        for flavor_data in request.flavors:
            model_result = await db.execute(
                select(Model)
                .options(joinedload(Model.provider))
                .where(Model.id == flavor_data.model_id)
            )
            model = model_result.scalar_one_or_none()

            if not model:
                raise HTTPException(
                    status_code=404,
                    detail=f"Model with ID {flavor_data.model_id} not found"
                )

            if not model.is_active:
                raise HTTPException(
                    status_code=422,
                    detail=f"Model {model.model_name} is not active"
                )

        # Auto-generate route from name if not provided
        route = request.route
        if not route:
            # Convert name to URL-friendly route (lowercase, replace spaces with hyphens)
            route = request.name.lower().replace(' ', '-').replace('_', '-')

        # Resolve multi-scope access lists (fold deprecated organization_id alias)
        orgs, users = self._resolve_scope_lists(
            request.allowed_organization_ids,
            request.allowed_user_ids,
            request.organization_id,
        )

        # Create service
        service = Service(
            name=request.name,
            route=route,
            service_type=request.service_type,
            description=request.description or {},
            allowed_organization_ids=orgs,
            allowed_user_ids=users,
            # Keep legacy single-org column in sync for backward compat.
            organization_id=(orgs[0] if len(orgs) == 1 and not users else None),
            is_active=request.is_active,
            metadata=request.metadata or {}
        )

        db.add(service)

        try:
            await db.flush()

            # Link available document templates if provided
            if request.template_ids is not None:
                await self._apply_template_links(db, service, request.template_ids)

            # Create flavors
            for flavor_data in request.flavors:
                # Convert Pydantic model to dict
                flavor_dict = flavor_data.model_dump()

                # Map schema field names to model field names
                if 'system_prompt_template_id' in flavor_dict:
                    flavor_dict['system_prompt_id'] = flavor_dict.pop('system_prompt_template_id')
                if 'reduce_prompt_template_id' in flavor_dict:
                    flavor_dict['reduce_prompt_id'] = flavor_dict.pop('reduce_prompt_template_id')

                # Load prompt content from templates if not explicitly provided
                flavor_dict = await self._load_prompt_contents(db, flavor_dict)

                flavor = ServiceFlavor(
                    service_id=service.id,
                    **flavor_dict
                )
                db.add(flavor)

            # Flush to persist flavors
            await db.flush()

            # Reload service with all relationships properly loaded
            result = await db.execute(
                select(Service)
                .options(*self._get_flavor_load_options())
                .where(Service.id == service.id)
            )
            service = result.unique().scalar_one()

        except IntegrityError as e:
            await db.rollback()
            error_str = str(e)
            if "uq_service_name_org" in error_str:
                raise HTTPException(
                    status_code=409,
                    detail=f"Service with name '{request.name}' already exists for this organization"
                )
            elif "uq_service_route_org" in error_str:
                raise HTTPException(
                    status_code=409,
                    detail=f"Service with route '{request.route}' already exists for this organization"
                )
            elif "uq_service_flavor_name" in error_str:
                raise HTTPException(
                    status_code=409,
                    detail="Duplicate flavor names within service"
                )
            raise

        logger.info(f"Created service: {service.id} ({service.name})")
        return self._to_response(service)

    async def get_services(
        self,
        db: AsyncSession,
        service_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        organization_id: Optional[str] = None,
        user_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> ServiceListResponse:
        """
        Get all services with optional filtering.

        Args:
            db: Database session
            service_type: Filter by service type
            is_active: Filter by active status
            organization_id: Visibility filter by organization
            user_id: Visibility filter by user
            skip: Pagination offset
            limit: Page size

        Returns:
            List of services with total count
        """
        # Build query with prompt relationships
        query = select(Service).options(*self._get_flavor_load_options())

        filters = []
        if service_type:
            filters.append(Service.service_type == service_type)
        if is_active is not None:
            filters.append(Service.is_active == is_active)
        if organization_id or user_id:
            # Visibility filter: a service is visible when it is global (no scope
            # restrictions) OR the caller's org/user is in its access lists.
            visibility = [self._is_global_service()]
            if organization_id:
                visibility.append(
                    Service.allowed_organization_ids.any(organization_id)
                )
                # Legacy single-org fallback (pre-migration / external writers)
                visibility.append(Service.organization_id == organization_id)
            if user_id:
                visibility.append(Service.allowed_user_ids.any(user_id))
            filters.append(or_(*visibility))

        if filters:
            query = query.where(and_(*filters))

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar_one()

        # Get paginated results
        query = query.offset(skip).limit(limit).order_by(Service.created_at.desc())
        result = await db.execute(query)
        services = result.scalars().unique().all()

        return ServiceListResponse(
            total=total,
            items=[self._to_response(s) for s in services]
        )

    async def get_service_by_id(
        self,
        db: AsyncSession,
        service_id: UUID
    ) -> Optional[ServiceResponse]:
        """
        Get a single service by ID.

        Args:
            db: Database session
            service_id: Service UUID

        Returns:
            Service response or None if not found
        """
        result = await db.execute(
            select(Service)
            .options(*self._get_flavor_load_options())
            .where(Service.id == service_id)
        )
        service = result.scalar_one_or_none()

        if not service:
            return None

        return self._to_response(service)

    async def update_service(
        self,
        db: AsyncSession,
        service_id: UUID,
        request: ServiceUpdate
    ) -> ServiceResponse:
        """
        Update an existing service.

        Args:
            db: Database session
            service_id: Service UUID
            request: Service update request

        Returns:
            Updated service response

        Raises:
            HTTPException: 404 if service not found
        """
        result = await db.execute(
            select(Service)
            .options(*self._get_flavor_load_options())
            .where(Service.id == service_id)
        )
        service = result.scalar_one_or_none()

        if not service:
            raise HTTPException(
                status_code=404,
                detail="Service not found"
            )

        # Update scope (access lists) if provided. Handled explicitly so we can
        # normalize, fold the deprecated organization_id alias, and keep the
        # legacy single-org column in sync.
        provided = request.model_dump(exclude_unset=True)
        scope_touched = any(
            k in provided for k in ("allowed_organization_ids", "allowed_user_ids", "organization_id")
        )
        if scope_touched:
            orgs, users = self._resolve_scope_lists(
                provided.get("allowed_organization_ids", service.allowed_organization_ids),
                provided.get("allowed_user_ids", service.allowed_user_ids),
                provided.get("organization_id"),
            )
            service.allowed_organization_ids = orgs
            service.allowed_user_ids = users
            service.organization_id = orgs[0] if len(orgs) == 1 and not users else None

        # Update remaining scalar fields (scope + relationship handled separately)
        update_data = request.model_dump(
            exclude_unset=True,
            exclude={"flavors", "template_ids", "allowed_organization_ids",
                     "allowed_user_ids", "organization_id"},
        )
        for field, value in update_data.items():
            setattr(service, field, value)

        # Replace linked document templates if provided
        if request.template_ids is not None:
            await self._apply_template_links(db, service, request.template_ids)

        # Update flavors if provided
        if request.flavors is not None:
            # Delete existing flavors
            for flavor in service.flavors:
                await db.delete(flavor)
            await db.flush()

            # Create new flavors
            for flavor_data in request.flavors:
                # Validate model exists and is active
                model_result = await db.execute(
                    select(Model)
                    .options(joinedload(Model.provider))
                    .where(Model.id == flavor_data.model_id)
                )
                model = model_result.scalar_one_or_none()

                if not model:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Model with ID {flavor_data.model_id} not found"
                    )

                # Convert Pydantic model to dict
                flavor_dict = flavor_data.model_dump()

                # Map schema field names to model field names
                if 'system_prompt_template_id' in flavor_dict:
                    flavor_dict['system_prompt_id'] = flavor_dict.pop('system_prompt_template_id')
                if 'reduce_prompt_template_id' in flavor_dict:
                    flavor_dict['reduce_prompt_id'] = flavor_dict.pop('reduce_prompt_template_id')

                # Load prompt content from templates if not explicitly provided
                flavor_dict = await self._load_prompt_contents(db, flavor_dict)

                flavor = ServiceFlavor(
                    service_id=service.id,
                    **flavor_dict
                )
                db.add(flavor)

            # Flush to persist flavors
            await db.flush()

            # Reload service with all relationships properly loaded
            result = await db.execute(
                select(Service)
                .options(*self._get_flavor_load_options())
                .where(Service.id == service.id)
            )
            service = result.unique().scalar_one()

        try:
            pass  # No additional work needed, already reloaded with relationships
        except IntegrityError as e:
            await db.rollback()
            error_str = str(e)
            if "uq_service_name_org" in error_str:
                raise HTTPException(
                    status_code=409,
                    detail="Service name already exists for this organization"
                )
            elif "uq_service_route_org" in error_str:
                raise HTTPException(
                    status_code=409,
                    detail="Service route already exists for this organization"
                )
            raise

        logger.info(f"Updated service: {service.id}")
        return self._to_response(service)

    async def delete_service(
        self,
        db: AsyncSession,
        service_id: UUID
    ) -> None:
        """
        Delete a service (cascades to flavors).

        Args:
            db: Database session
            service_id: Service UUID

        Raises:
            HTTPException: 404 if service not found
        """
        result = await db.execute(
            select(Service).where(Service.id == service_id)
        )
        service = result.scalar_one_or_none()

        if not service:
            raise HTTPException(
                status_code=404,
                detail="Service not found"
            )

        await db.delete(service)
        await db.flush()
        logger.info(f"Deleted service: {service_id}")

    async def _apply_template_links(self, db: AsyncSession, service: Service, template_ids) -> None:
        """Replace the set of document templates available for a service.

        Validates that every id exists, then sets the relationship wholesale.
        """
        from app.models.document_template import DocumentTemplate

        ids = list(dict.fromkeys(template_ids or []))  # dedupe, preserve order
        if not ids:
            service.document_templates = []
            return

        result = await db.execute(
            select(DocumentTemplate).where(DocumentTemplate.id.in_(ids))
        )
        templates = list(result.scalars().all())
        found = {t.id for t in templates}
        missing = [str(tid) for tid in ids if tid not in found]
        if missing:
            raise HTTPException(
                status_code=404,
                detail=f"Document template(s) not found: {', '.join(missing)}"
            )
        service.document_templates = templates

    async def set_service_templates(
        self, db: AsyncSession, service_id: UUID, template_ids
    ) -> ServiceResponse:
        """Replace the linked templates for a service and return the service."""
        result = await db.execute(
            select(Service)
            .options(*self._get_flavor_load_options())
            .where(Service.id == service_id)
        )
        service = result.scalar_one_or_none()
        if not service:
            raise HTTPException(status_code=404, detail="Service not found")

        await self._apply_template_links(db, service, template_ids)
        await db.flush()

        result = await db.execute(
            select(Service)
            .options(*self._get_flavor_load_options())
            .where(Service.id == service_id)
        )
        service = result.unique().scalar_one()
        logger.info(f"Updated template links for service {service_id}: {len(template_ids or [])} templates")
        return self._to_response(service)

    async def get_service_templates(
        self,
        db: AsyncSession,
        service_id: UUID,
        organization_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        """Return the document templates available for a service.

        - If the service has explicitly linked templates: those, filtered by the
          caller's visibility scope (org/user/system).
        - If it has no links: fall back to the global default template (if any).
        Raises 404 if the service does not exist.
        """
        from app.services.document_template_service import document_template_service

        result = await db.execute(
            select(Service)
            .options(selectinload(Service.document_templates))
            .where(Service.id == service_id)
        )
        service = result.scalar_one_or_none()
        if not service:
            raise HTTPException(status_code=404, detail="Service not found")

        linked = list(service.document_templates or [])
        if not linked:
            # Fallback: global default template (system-scoped, is_default=True)
            default = await document_template_service.get_default_template(db)
            return [default] if default else []

        def _visible(t) -> bool:
            if not t.allowed_organization_ids and not t.allowed_user_ids:
                return True  # system template, visible to all
            if organization_id and organization_id in (t.allowed_organization_ids or []):
                return True
            if user_id and user_id in (t.allowed_user_ids or []):
                return True
            # No scope context provided => return links as-is (admin/no-filter view)
            return organization_id is None and user_id is None

        return [t for t in linked if _visible(t)]


# Singleton instance
service_service = ServiceService()
