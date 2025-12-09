#!/usr/bin/env python3
"""Application configuration using Pydantic settings."""
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra='ignore'
    )

    # Database
    database_url: str
    db_pool_size: int = 5
    db_max_overflow: int = 10

    # Redis / Celery Broker
    services_broker: str = "redis://localhost:6379"
    services_broker_password: str = ""

    # API Server
    api_v1_prefix: str = "/api/v1"
    service_port: int = Field(default=8000, validation_alias='HTTP_PORT')
    workers: int = 1
    debug: bool = False

    # App Info
    app_name: str = "LLM Gateway"
    app_description: str = "Gateway for LLM service management"
    docs_url: str = "/docs"

    # Security
    encryption_key: str

    # Task Queue
    task_expiration: int = 86400  # 24h - task result TTL
    task_cleanup_interval: int = 3600  # 1h - cleanup frequency
    task_cutoff_seconds: int = 3600  # 1h - max task runtime before considered stuck
    stale_job_check_interval: int = 300  # 5min - periodic stale job detection

    # LLM API Retry
    api_max_retries: int = 6
    api_retry_min_delay: int = 1  # seconds
    api_retry_max_delay: int = 60  # seconds

    # Tokenizer Storage
    tokenizer_storage_path: str = "/var/www/data/tokenizers"

    # CORS
    cors_origins: str = "*"

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(',') if origin.strip()]


# Global settings instance
settings = Settings()
