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

    # Logging
    # Full override: path to a JSON file passed to logging.config.dictConfig.
    # When set, every LOG_* knob below is ignored (Winston WINSTON_CONFIG_PATH equivalent).
    logging_config_file: str = ""
    log_level: str = "INFO"          # DEBUG / INFO / WARNING / ERROR (DEBUG=true forces DEBUG)
    log_format: str = "text"         # "text" or "json"
    log_name: str = "llm-gateway"    # service label injected into JSON / Stackdriver logs
    # Rotating file sink (disabled unless LOG_FILE is set)
    log_file: str = ""
    log_file_level: str = ""         # defaults to log_level when empty
    log_file_max_bytes: int = 10485760  # 10 MiB
    log_file_backup_count: int = 5
    # HTTP POST sink (disabled unless LOG_HTTP_URL is set)
    log_http_url: str = ""
    log_http_method: str = "POST"
    log_http_headers: str = ""       # JSON object string, e.g. {"Authorization": "Bearer ..."}
    log_http_level: str = ""         # defaults to log_level when empty
    log_http_timeout: float = 5.0
    # Google Cloud Logging / Stackdriver sink (needs the google-cloud-logging package)
    log_stackdriver_enabled: bool = False
    log_stackdriver_project: str = ""   # GCP project id; auto-detected when empty
    log_stackdriver_level: str = ""     # defaults to log_level when empty

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

    # CORS - must be configured via CORS_ORIGINS env var (comma-separated origins)
    cors_origins: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        if self.cors_origins == "*":
            return ["*"]
        origins = [origin.strip() for origin in self.cors_origins.split(',') if origin.strip()]
        if not origins:
            raise ValueError(
                "CORS_ORIGINS must be configured (comma-separated origins, or '*' for development). "
                "Example: CORS_ORIGINS=http://localhost:3000,https://my-domain.com"
            )
        return origins


# Global settings instance
settings = Settings()
