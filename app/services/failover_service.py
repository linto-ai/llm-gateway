"""Service for managing flavor failover chains.

This module provides functionality for validating failover chains (cycle detection),
retrieving complete failover chains, and helper methods for flavor lookups.
"""
import logging
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.service_flavor import ServiceFlavor

logger = logging.getLogger(__name__)


class FailoverService:
    """Service for managing flavor failover chains."""

    @staticmethod
    async def validate_failover_chain(
        db: AsyncSession,
        flavor_id: UUID,
        failover_flavor_id: UUID,
        max_depth: int = 10
    ) -> Tuple[bool, Optional[str], int, List[str]]:
        """
        Validate that adding this failover doesn't create a cycle.

        Args:
            db: Database session
            flavor_id: ID of the flavor being configured
            failover_flavor_id: ID of the proposed failover flavor
            max_depth: Maximum chain depth to traverse (default: 10)

        Returns:
            Tuple of (is_valid, error_message, chain_depth, chain_preview)
            - is_valid: True if the chain is valid (no cycles)
            - error_message: Error description if invalid, None otherwise
            - chain_depth: Total depth of the chain if valid
            - chain_preview: List of flavor names in the chain
        """
        if flavor_id == failover_flavor_id:
            return False, "Cannot set failover to self", 0, []

        visited = {flavor_id}
        current_id = failover_flavor_id
        depth = 1
        chain_preview = []

        # Get the starting flavor name
        result = await db.execute(
            select(ServiceFlavor.name)
            .where(ServiceFlavor.id == flavor_id)
        )
        starting_name = result.scalar_one_or_none()
        if starting_name:
            chain_preview.append(starting_name)

        while current_id and depth <= max_depth:
            if current_id in visited:
                return False, "Cycle detected: flavor chain loops back", depth, chain_preview

            visited.add(current_id)

            # Get current flavor info and next in chain
            result = await db.execute(
                select(ServiceFlavor.name, ServiceFlavor.failover_flavor_id)
                .where(ServiceFlavor.id == current_id)
            )
            row = result.one_or_none()
            if row is None:
                # Flavor not found, end of chain
                break

            name, next_id = row
            chain_preview.append(name)
            current_id = next_id
            depth += 1

        return True, None, len(chain_preview), chain_preview

    @staticmethod
    async def get_failover_chain(
        db: AsyncSession,
        flavor_id: UUID,
        max_depth: int = 10
    ) -> Tuple[List[dict], bool]:
        """
        Get the complete failover chain for a flavor.

        Args:
            db: Database session
            flavor_id: ID of the starting flavor
            max_depth: Maximum chain depth to traverse (default: 10)

        Returns:
            Tuple of (chain, has_cycle)
            - chain: List of flavor info dicts with id, name, service_id, etc.
            - has_cycle: True if a cycle was detected
        """
        chain = []
        visited = set()
        current_id = flavor_id
        depth = 0
        has_cycle = False

        while current_id and depth < max_depth:
            if current_id in visited:
                has_cycle = True
                break

            visited.add(current_id)

            result = await db.execute(
                select(ServiceFlavor)
                .options(
                    joinedload(ServiceFlavor.model),
                    joinedload(ServiceFlavor.service)
                )
                .where(ServiceFlavor.id == current_id)
            )
            flavor = result.unique().scalar_one_or_none()

            if not flavor:
                break

            chain.append({
                "id": str(flavor.id),
                "name": flavor.name,
                "service_id": str(flavor.service_id),
                "service_name": flavor.service.name if flavor.service else None,
                "model_name": flavor.model.model_name if flavor.model else None,
                "is_active": flavor.is_active,
                "depth": depth,
            })

            current_id = flavor.failover_flavor_id
            depth += 1

        return chain, has_cycle

    @staticmethod
    async def get_flavor_by_id(
        db: AsyncSession,
        flavor_id: UUID
    ) -> Optional[ServiceFlavor]:
        """
        Get a flavor by ID with relationships loaded.

        Args:
            db: Database session
            flavor_id: UUID of the flavor to retrieve

        Returns:
            ServiceFlavor instance with model and service relationships loaded,
            or None if not found.
        """
        result = await db.execute(
            select(ServiceFlavor)
            .options(
                joinedload(ServiceFlavor.model),
                joinedload(ServiceFlavor.service),
                joinedload(ServiceFlavor.failover_flavor)
            )
            .where(ServiceFlavor.id == flavor_id)
        )
        return result.unique().scalar_one_or_none()


# Singleton instance for convenience
failover_service = FailoverService()
