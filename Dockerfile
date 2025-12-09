FROM python:3.11-slim
LABEL maintainer="dlaine@linagora.com"

# Build arguments for UID/GID (defaults to 1000)
ARG USER_ID=1000
ARG GROUP_ID=1000

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/usr/src \
    SERVICE_TYPE=llm_gateway \
    UV_SYSTEM_PYTHON=1 \
    UV_COMPILE_BYTECODE=1

WORKDIR /usr/src

# Install system dependencies as root
# - libreoffice-writer: DOCX to PDF conversion (fallback)
# - weasyprint deps: libpango, libcairo, fonts for PDF generation
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libreoffice-writer \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    gir1.2-gdkpixbuf-2.0 \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package installer)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Create non-root user with configurable UID/GID
RUN groupadd -g ${GROUP_ID} appgroup 2>/dev/null || true \
    && useradd -u ${USER_ID} -g appgroup -m -s /bin/bash appuser 2>/dev/null || true

# Install Python dependencies with uv (much faster than pip)
COPY requirements.txt ./
RUN uv pip install --no-cache -r requirements.txt

# Copy application code
COPY --chown=appuser:appgroup . /usr/src

# Ensure scripts are executable
RUN chmod +x ./scripts/healthcheck.sh ./scripts/celery-healthcheck.sh ./scripts/wait-for-it.sh ./scripts/docker-entrypoint.sh

# Create data directories with correct ownership
RUN mkdir -p /var/www/data/tokenizers \
    && mkdir -p /var/www/data/templates \
    && chown -R appuser:appgroup /var/www/data

# Switch to non-root user
USER appuser

HEALTHCHECK CMD ./scripts/healthcheck.sh

# Entrypoint waits for dependencies (Postgres, Redis) then runs command
ENTRYPOINT ["./scripts/docker-entrypoint.sh"]

# Default: run FastAPI server (Celery worker runs as separate container with command override)
CMD ["python", "-m", "app"]
