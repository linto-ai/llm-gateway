#!/usr/bin/env python3
"""Business logic for flavor management."""

import logging
from typing import Optional, List, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, func
from sqlalchemy.orm import joinedload
from fastapi import HTTPException, status

from app.models.service_flavor import ServiceFlavor
from app.models.model import Model
from app.models.job import Job
from app.models.prompt import Prompt
from app.schemas.service import ServiceFlavorCreate, ServiceFlavorUpdate
from app.core.prompt_validation import validate_prompt_for_processing_mode

logger = logging.getLogger(__name__)


class FlavorService:
    """Business logic for flavor management."""

    @staticmethod
    async def _validate_prompt_for_mode(
        db: AsyncSession,
        prompt_content: Optional[str],
        prompt_template_id: Optional[UUID],
        processing_mode: str,
        field_name: str = "user_prompt_template_id"
    ) -> Tuple[bool, Optional[dict]]:
        """
        Validate prompt compatibility with processing mode.

        Checks either inline content or fetches template content.

        Args:
            db: Database session
            prompt_content: Inline prompt content (if any)
            prompt_template_id: Prompt template UUID (if any)
            processing_mode: Processing mode to validate against
            field_name: Field name for error messages

        Returns:
            Tuple of (is_valid, error_details or None)
        """
        content = prompt_content
        prompt_name = None

        # If using template, fetch its content
        if not content and prompt_template_id:
            result = await db.execute(
                select(Prompt).where(Prompt.id == prompt_template_id)
            )
            template = result.scalar_one_or_none()
            if template:
                content = template.content
                prompt_name = template.name

        if not content:
            return True, None  # No prompt to validate

        return validate_prompt_for_processing_mode(
            content, processing_mode, prompt_name, field_name
        )

    @staticmethod
    def _get_flavor_options():
        """
        Get SQLAlchemy load options for flavors with all relationships.

        Includes prompt relationships for prompt name display.
        """
        return [
            joinedload(ServiceFlavor.model).joinedload(Model.provider),
            joinedload(ServiceFlavor.system_prompt),
            joinedload(ServiceFlavor.user_prompt_template),
            joinedload(ServiceFlavor.reduce_prompt),
            joinedload(ServiceFlavor.placeholder_extraction_prompt),
            joinedload(ServiceFlavor.categorization_prompt),
            joinedload(ServiceFlavor.fallback_flavor).joinedload(ServiceFlavor.service),
        ]

    @staticmethod
    async def create_flavor(
        db: AsyncSession,
        service_id: UUID,
        flavor_data: ServiceFlavorCreate
    ) -> ServiceFlavor:
        """
        Create a new flavor with validation.

        Args:
            db: Database session
            service_id: ID of the service
            flavor_data: Flavor creation data

        Returns:
            ServiceFlavor: Created flavor

        Raises:
            HTTPException: If validation fails or name conflicts
        """
        # Check name uniqueness within service
        result = await db.execute(
            select(ServiceFlavor).where(
                and_(
                    ServiceFlavor.service_id == service_id,
                    ServiceFlavor.name == flavor_data.name
                )
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Flavor name '{flavor_data.name}' already exists for this service"
            )

        # Validate prompt compatibility with processing mode
        processing_mode = flavor_data.processing_mode or 'iterative'
        is_valid, error_details = await FlavorService._validate_prompt_for_mode(
            db,
            flavor_data.prompt_user_content,
            flavor_data.user_prompt_template_id,
            processing_mode
        )
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_details
            )

        # If is_default=True, unset other defaults
        if flavor_data.is_default:
            await db.execute(
                update(ServiceFlavor)
                .where(ServiceFlavor.service_id == service_id)
                .values(is_default=False)
            )

        # Create flavor - map schema field names to model column names
        flavor_dict = flavor_data.model_dump()

        # Rename schema fields to match model columns
        if "system_prompt_template_id" in flavor_dict:
            flavor_dict["system_prompt_id"] = flavor_dict.pop("system_prompt_template_id")
        if "reduce_prompt_template_id" in flavor_dict:
            flavor_dict["reduce_prompt_id"] = flavor_dict.pop("reduce_prompt_template_id")

        flavor = ServiceFlavor(**flavor_dict, service_id=service_id)
        db.add(flavor)
        await db.commit()
        await db.refresh(flavor)

        # Load with joined model/provider and prompt data
        result = await db.execute(
            select(ServiceFlavor)
            .options(*FlavorService._get_flavor_options())
            .where(ServiceFlavor.id == flavor.id)
        )
        flavor = result.scalar_one()

        return flavor

    @staticmethod
    async def update_flavor(
        db: AsyncSession,
        flavor_id: UUID,
        flavor_update: ServiceFlavorUpdate
    ) -> ServiceFlavor:
        """
        Update a flavor configuration.

        Args:
            db: Database session
            flavor_id: ID of the flavor
            flavor_update: Flavor update data

        Returns:
            ServiceFlavor: Updated flavor

        Raises:
            HTTPException: If validation fails or flavor not found
        """
        # Get existing flavor
        result = await db.execute(
            select(ServiceFlavor).where(ServiceFlavor.id == flavor_id)
        )
        flavor = result.scalar_one_or_none()
        if not flavor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Flavor not found"
            )

        # Check name uniqueness if name is being updated
        if flavor_update.name and flavor_update.name != flavor.name:
            result = await db.execute(
                select(ServiceFlavor).where(
                    and_(
                        ServiceFlavor.service_id == flavor.service_id,
                        ServiceFlavor.name == flavor_update.name,
                        ServiceFlavor.id != flavor_id
                    )
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Flavor name '{flavor_update.name}' already exists for this service"
                )

        # If is_default=True, unset other defaults
        if flavor_update.is_default:
            await db.execute(
                update(ServiceFlavor)
                .where(
                    and_(
                        ServiceFlavor.service_id == flavor.service_id,
                        ServiceFlavor.id != flavor_id
                    )
                )
                .values(is_default=False)
            )

        # Validate prompt compatibility with processing mode
        # Determine effective processing mode and prompt for validation
        effective_processing_mode = flavor_update.processing_mode or flavor.processing_mode
        prompt_content = flavor_update.prompt_user_content
        prompt_template_id = flavor_update.user_prompt_template_id

        # If neither provided in update, use existing values
        if prompt_content is None and prompt_template_id is None:
            prompt_content = flavor.prompt_user_content
            prompt_template_id = flavor.user_prompt_template_id

        # Only validate if processing_mode or prompt is changing
        needs_validation = (
            flavor_update.processing_mode is not None or
            flavor_update.prompt_user_content is not None or
            flavor_update.user_prompt_template_id is not None
        )

        if needs_validation:
            is_valid, error_details = await FlavorService._validate_prompt_for_mode(
                db,
                prompt_content,
                prompt_template_id,
                effective_processing_mode
            )
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_details
                )

        # Update flavor fields - map schema field names to model column names
        update_data = flavor_update.model_dump(exclude_unset=True)

        # Handle template ID -> content copying
        # System prompt template
        if "system_prompt_template_id" in update_data and update_data["system_prompt_template_id"]:
            template_id = update_data["system_prompt_template_id"]
            result = await db.execute(select(Prompt).where(Prompt.id == template_id))
            template = result.scalar_one_or_none()
            if template:
                update_data["prompt_system_content"] = template.content
            update_data["system_prompt_id"] = update_data.pop("system_prompt_template_id")
        elif "system_prompt_template_id" in update_data:
            update_data.pop("system_prompt_template_id")

        # User prompt template
        if "user_prompt_template_id" in update_data and update_data["user_prompt_template_id"]:
            template_id = update_data["user_prompt_template_id"]
            # Only copy content if not providing inline content
            if "prompt_user_content" not in update_data or not update_data.get("prompt_user_content"):
                result = await db.execute(select(Prompt).where(Prompt.id == template_id))
                template = result.scalar_one_or_none()
                if template:
                    update_data["prompt_user_content"] = template.content

        # Reduce prompt template
        if "reduce_prompt_template_id" in update_data and update_data["reduce_prompt_template_id"]:
            template_id = update_data["reduce_prompt_template_id"]
            result = await db.execute(select(Prompt).where(Prompt.id == template_id))
            template = result.scalar_one_or_none()
            if template:
                update_data["prompt_reduce_content"] = template.content
            update_data["reduce_prompt_id"] = update_data.pop("reduce_prompt_template_id")
        elif "reduce_prompt_template_id" in update_data:
            update_data.pop("reduce_prompt_template_id")

        for field, value in update_data.items():
            setattr(flavor, field, value)

        await db.commit()
        await db.refresh(flavor)

        # Load with joined model/provider and prompt data
        result = await db.execute(
            select(ServiceFlavor)
            .options(*FlavorService._get_flavor_options())
            .where(ServiceFlavor.id == flavor.id)
        )
        flavor = result.scalar_one()

        return flavor

    @staticmethod
    async def list_flavors(
        db: AsyncSession,
        service_id: UUID,
        is_active: Optional[bool] = None
    ) -> tuple[List[ServiceFlavor], int]:
        """
        List flavors for a service with optional filtering.

        Args:
            db: Database session
            service_id: ID of the service
            is_active: Optional filter by active status

        Returns:
            Tuple of (items, total_count)
        """
        from sqlalchemy import select, func

        # Build base query
        query = select(ServiceFlavor).where(ServiceFlavor.service_id == service_id)

        # Apply filters
        if is_active is not None:
            query = query.where(ServiceFlavor.is_active == is_active)

        # Get total count
        count_query = select(func.count()).select_from(ServiceFlavor).where(ServiceFlavor.service_id == service_id)
        if is_active is not None:
            count_query = count_query.where(ServiceFlavor.is_active == is_active)
        count_result = await db.execute(count_query)
        total = count_result.scalar()

        # Get items with model/provider and prompt relationships
        query = query.options(*FlavorService._get_flavor_options())
        query = query.order_by(ServiceFlavor.priority.desc(), ServiceFlavor.created_at)

        result = await db.execute(query)
        items = list(result.scalars().all())

        return items, total

    @staticmethod
    async def get_flavor_by_name(
        db: AsyncSession,
        service_id: UUID,
        name: str
    ) -> Optional[ServiceFlavor]:
        """
        Get flavor by name within a service.

        Args:
            db: Database session
            service_id: ID of the service
            name: Name of the flavor

        Returns:
            ServiceFlavor or None
        """
        result = await db.execute(
            select(ServiceFlavor)
            .options(*FlavorService._get_flavor_options())
            .where(
                and_(
                    ServiceFlavor.service_id == service_id,
                    ServiceFlavor.name == name
                )
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_flavor(
        db: AsyncSession,
        flavor_id: UUID
    ) -> ServiceFlavor:
        """
        Get flavor details with model/provider info.

        Args:
            db: Database session
            flavor_id: ID of the flavor

        Returns:
            ServiceFlavor: Flavor with joined data

        Raises:
            HTTPException: If flavor not found
        """
        result = await db.execute(
            select(ServiceFlavor)
            .options(*FlavorService._get_flavor_options())
            .where(ServiceFlavor.id == flavor_id)
        )
        flavor = result.scalar_one_or_none()
        if not flavor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Flavor not found"
            )
        return flavor

    @staticmethod
    async def set_default_flavor(
        db: AsyncSession,
        flavor_id: UUID
    ) -> ServiceFlavor:
        """
        Set a flavor as default (unset others in same service).

        Args:
            db: Database session
            flavor_id: ID of the flavor

        Returns:
            ServiceFlavor: Updated flavor

        Raises:
            HTTPException: If flavor not found or not active
        """
        # Get flavor
        result = await db.execute(
            select(ServiceFlavor).where(ServiceFlavor.id == flavor_id)
        )
        flavor = result.scalar_one_or_none()
        if not flavor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Flavor not found"
            )

        if not flavor.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot set inactive flavor as default"
            )

        # Transaction: unset all defaults for service, set this one
        await db.execute(
            update(ServiceFlavor)
            .where(ServiceFlavor.service_id == flavor.service_id)
            .values(is_default=False)
        )

        flavor.is_default = True
        await db.commit()
        await db.refresh(flavor)

        return flavor

    @staticmethod
    async def validate_flavor_config(
        db: AsyncSession,
        flavor: ServiceFlavor
    ) -> List[str]:
        """
        Validate flavor configuration against model limits.

        Note: max_tokens field removed - uses model's max_generation_length.

        Args:
            db: Database session
            flavor: Flavor to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Validate parameter ranges
        if flavor.temperature < 0 or flavor.temperature > 2:
            errors.append("temperature must be between 0 and 2")

        if flavor.top_p <= 0 or flavor.top_p > 1:
            errors.append("top_p must be between 0 (exclusive) and 1 (inclusive)")

        if flavor.frequency_penalty < 0 or flavor.frequency_penalty > 2:
            errors.append("frequency_penalty must be between 0 and 2")

        if flavor.presence_penalty < 0 or flavor.presence_penalty > 2:
            errors.append("presence_penalty must be between 0 and 2")

        if len(flavor.stop_sequences) > 4:
            errors.append("stop_sequences can have at most 4 items")

        if flavor.priority < 0:
            errors.append("priority must be >= 0")

        return errors

    @staticmethod
    async def get_default_flavor(
        db: AsyncSession,
        service_id: UUID
    ) -> Optional[ServiceFlavor]:
        """
        Get the default flavor for a service.

        Args:
            db: Database session
            service_id: ID of the service

        Returns:
            ServiceFlavor or None
        """
        result = await db.execute(
            select(ServiceFlavor)
            .options(*FlavorService._get_flavor_options())
            .where(
                and_(
                    ServiceFlavor.service_id == service_id,
                    ServiceFlavor.is_default
                )
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def delete_flavor(
        db: AsyncSession,
        flavor_id: UUID
    ) -> None:
        """
        Delete a flavor with safety checks.

        Args:
            db: Database session
            flavor_id: ID of the flavor

        Raises:
            HTTPException: If flavor cannot be deleted
        """
        # Get flavor
        result = await db.execute(
            select(ServiceFlavor).where(ServiceFlavor.id == flavor_id)
        )
        flavor = result.scalar_one_or_none()
        if not flavor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Flavor not found"
            )

        # Cannot delete if is_default=True
        if flavor.is_default:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete default flavor. Set another flavor as default first."
            )

        # Cannot delete if has active jobs
        result = await db.execute(
            select(func.count(Job.id))
            .where(
                and_(
                    Job.flavor_id == flavor_id,
                    Job.status.in_(['queued', 'started', 'processing'])
                )
            )
        )
        active_job_count = result.scalar()
        if active_job_count > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot delete flavor with {active_job_count} active job(s)"
            )

        # Delete flavor (cascade deletes usage records)
        await db.delete(flavor)
        await db.commit()

    @staticmethod
    async def find_iterative_fallback(
        db: AsyncSession,
        service_id: UUID,
        exclude_flavor_id: UUID
    ) -> Optional[ServiceFlavor]:
        """
        Find an active iterative flavor as fallback.

        Selection criteria:
        1. Same service_id
        2. is_active=True
        3. processing_mode='iterative'
        4. Exclude specified flavor
        5. Order by priority DESC, created_at ASC

        Args:
            db: Database session
            service_id: ID of the service
            exclude_flavor_id: Flavor ID to exclude

        Returns:
            ServiceFlavor or None
        """
        query = (
            select(ServiceFlavor)
            .options(*FlavorService._get_flavor_options())
            .where(
                and_(
                    ServiceFlavor.service_id == service_id,
                    ServiceFlavor.id != exclude_flavor_id,
                    ServiceFlavor.is_active,
                    ServiceFlavor.processing_mode == 'iterative'
                )
            )
            .order_by(ServiceFlavor.priority.desc(), ServiceFlavor.created_at)
        )

        result = await db.execute(query)
        return result.scalars().first()

    @staticmethod
    async def has_iterative_fallback(
        db: AsyncSession,
        service_id: UUID,
        exclude_flavor_id: Optional[UUID] = None
    ) -> bool:
        """
        Check if service has at least one active iterative flavor
        (excluding the specified flavor if provided).

        Args:
            db: Database session
            service_id: ID of the service
            exclude_flavor_id: Optional flavor ID to exclude

        Returns:
            True if fallback exists, False otherwise
        """
        conditions = [
            ServiceFlavor.service_id == service_id,
            ServiceFlavor.is_active,
            ServiceFlavor.processing_mode == 'iterative'
        ]

        if exclude_flavor_id:
            conditions.append(ServiceFlavor.id != exclude_flavor_id)

        query = select(func.count()).select_from(ServiceFlavor).where(and_(*conditions))
        result = await db.execute(query)
        count = result.scalar()

        return count > 0
