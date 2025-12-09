#!/usr/bin/env python3
from pydantic import BaseModel
from datetime import datetime
from enum import Enum


class ConnectionStatus(str, Enum):
    """Connection status for external services."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"


class HealthStatus(str, Enum):
    """Overall health status."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"


class HealthCheckResponse(BaseModel):
    """Health check response schema."""
    status: HealthStatus
    database: ConnectionStatus
    redis: ConnectionStatus
    timestamp: datetime

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
