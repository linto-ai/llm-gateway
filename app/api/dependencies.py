#!/usr/bin/env python3
from app.core.database import get_db
from app.services.provider_service import provider_service


async def get_provider_service():
    """Dependency for getting the provider service."""
    return provider_service


# Re-export get_db for convenience
__all__ = ["get_db", "get_provider_service"]
