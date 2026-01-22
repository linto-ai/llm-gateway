import pytest
import pytest_asyncio
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# Set test environment variables - use in-memory SQLite for testing
from cryptography.fernet import Fernet
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()
os.environ["CELERY_BROKER_URL"] = "redis://localhost:6379/0"
os.environ["CELERY_RESULT_BACKEND"] = "redis://localhost:6379/0"
os.environ["REDIS_URL"] = "redis://localhost:6379"
os.environ["SERVICES_BROKER"] = "redis://localhost:6379"

from app.database import Base as LegacyBase, get_db, Provider, Organization
from app.core.database import Base as CoreBase
from app.api.v1 import models, services, prompts
from fastapi import FastAPI, APIRouter, UploadFile, Form, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_
from typing import Optional
from uuid import UUID
from math import ceil
import uuid as uuid_mod

from app.schemas import CreateProviderRequest, UpdateProviderRequest, ProviderResponse
from app.schemas.common import PaginatedResponse
from app.utils import encrypt_api_key

# Test database setup - SYNC engine for table creation and basic tests (in-memory)
SYNC_TEST_DATABASE_URL = "sqlite:///:memory:"
sync_test_engine = create_engine(
    SYNC_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
SyncTestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_test_engine)

# ASYNC engine for async tests (in-memory with StaticPool)
ASYNC_TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
async_test_engine = create_async_engine(
    ASYNC_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
AsyncTestSessionLocal = async_sessionmaker(
    async_test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# =============================================================================
# Test-only Provider Router (sync SQLite compatible)
# =============================================================================

def _provider_to_response(provider: Provider) -> ProviderResponse:
    return ProviderResponse(
        id=provider.id,
        name=provider.name,
        provider_type=provider.provider_type,
        api_base_url=provider.api_base_url,
        api_key_exists=bool(provider.api_key_encrypted),
        security_level=provider.security_level,
        created_at=provider.created_at,
        updated_at=provider.updated_at,
        metadata=provider.provider_metadata or {}
    )


def create_test_providers_router():
    """Create a test-only providers router that works with sync SQLite."""
    router = APIRouter(prefix="/api/v1/providers", tags=["providers"])

    @router.post("", response_model=ProviderResponse, status_code=201)
    async def create_provider(request: CreateProviderRequest, db: Session = Depends(get_db)):
        try:
            provider = Provider(
                name=request.name,
                provider_type=request.provider_type,
                api_base_url=request.api_base_url,
                api_key_encrypted=encrypt_api_key(request.api_key),
                security_level=request.security_level,
                provider_metadata=request.metadata
            )
            db.add(provider)
            db.commit()
            db.refresh(provider)
            return _provider_to_response(provider)
        except IntegrityError as e:
            db.rollback()
            if "unique" in str(e).lower():
                raise HTTPException(status_code=409, detail="Provider name already exists")
            raise HTTPException(status_code=400, detail=str(e))

    @router.get("")
    async def list_providers(
        security_level: Optional[int] = Query(None, ge=0, le=2),
        provider_type: Optional[str] = Query(None),
        page: int = Query(1, ge=1),
        limit: int = Query(20, ge=1, le=100),
        db: Session = Depends(get_db)
    ):
        query = db.query(Provider)
        filters = []
        if security_level is not None:
            filters.append(Provider.security_level == security_level)
        if provider_type:
            filters.append(Provider.provider_type == provider_type)
        if filters:
            query = query.filter(and_(*filters))
        total = query.count()
        providers = query.offset((page - 1) * limit).limit(limit).all()
        return PaginatedResponse[ProviderResponse](
            items=[_provider_to_response(p) for p in providers],
            total=total, page=page, page_size=limit,
            total_pages=ceil(total / limit) if limit > 0 else 0
        )

    @router.get("/{provider_id}", response_model=ProviderResponse)
    async def get_provider(provider_id: UUID, db: Session = Depends(get_db)):
        provider = db.query(Provider).filter(Provider.id == provider_id).first()
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")
        return _provider_to_response(provider)

    @router.patch("/{provider_id}", response_model=ProviderResponse)
    async def update_provider(provider_id: UUID, request: UpdateProviderRequest, db: Session = Depends(get_db)):
        provider = db.query(Provider).filter(Provider.id == provider_id).first()
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")
        try:
            if request.name is not None:
                provider.name = request.name
            if request.api_base_url is not None:
                provider.api_base_url = request.api_base_url
            if request.api_key is not None:
                provider.api_key_encrypted = encrypt_api_key(request.api_key)
            if request.security_level is not None:
                provider.security_level = request.security_level
            if request.metadata is not None:
                provider.provider_metadata = request.metadata
            db.commit()
            db.refresh(provider)
            return _provider_to_response(provider)
        except IntegrityError as e:
            db.rollback()
            if "unique" in str(e).lower():
                raise HTTPException(status_code=409, detail="Provider name already exists")
            raise HTTPException(status_code=400, detail=str(e))

    @router.delete("/{provider_id}", status_code=204)
    async def delete_provider(provider_id: UUID, db: Session = Depends(get_db)):
        provider = db.query(Provider).filter(Provider.id == provider_id).first()
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")
        db.delete(provider)
        db.commit()
        return None

    return router


# =============================================================================
# Test App Fixture
# =============================================================================

@pytest.fixture(scope="session")
def test_app():
    """Create test FastAPI app with test-compatible routers."""
    app = FastAPI()

    # Test-only providers router (sync SQLite compatible)
    app.include_router(create_test_providers_router())

    # V1 API routers
    app.include_router(models.router, prefix="/api/v1", tags=["models"])
    app.include_router(services.router, prefix="/api/v1", tags=["services"])
    app.include_router(prompts.router, prefix="/api/v1", tags=["prompts"])

    # Health endpoint for tests
    @app.get("/healthcheck")
    async def healthcheck():
        from datetime import datetime
        return {
            "status": "healthy",
            "database": "connected",
            "redis": "connected",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

    return app


# =============================================================================
# Database Session Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def db_session():
    """Create a fresh SYNC database session for each test."""
    # Create tables for both legacy and core bases
    LegacyBase.metadata.create_all(bind=sync_test_engine)
    CoreBase.metadata.create_all(bind=sync_test_engine)
    session = SyncTestSessionLocal()
    yield session
    session.close()
    CoreBase.metadata.drop_all(bind=sync_test_engine)
    LegacyBase.metadata.drop_all(bind=sync_test_engine)


@pytest_asyncio.fixture(scope="function")
async def async_db_session():
    """Create a fresh ASYNC database session for each test."""
    # Create tables for both legacy and core bases
    async with async_test_engine.begin() as conn:
        await conn.run_sync(LegacyBase.metadata.create_all)
        await conn.run_sync(CoreBase.metadata.create_all)
    async with AsyncTestSessionLocal() as session:
        yield session
    async with async_test_engine.begin() as conn:
        await conn.run_sync(CoreBase.metadata.drop_all)
        await conn.run_sync(LegacyBase.metadata.drop_all)


# =============================================================================
# Client Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def client(test_app, db_session):
    """Create test client with SYNC database override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    test_app.dependency_overrides[get_db] = override_get_db
    with TestClient(test_app) as test_client:
        yield test_client
    test_app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def async_client(test_app, async_db_session):
    """Create async test client with ASYNC database override."""
    import httpx

    async def override_get_db():
        yield async_db_session

    test_app.dependency_overrides[get_db] = override_get_db
    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    test_app.dependency_overrides.clear()


# =============================================================================
# Sample Data Fixtures
# =============================================================================

@pytest.fixture
def sample_organization(db_session):
    """Create a sample organization for testing"""
    org = Organization(name="test-org-123")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    return org


@pytest.fixture
def sample_provider(db_session):
    """Create a sample provider for testing"""
    provider = Provider(
        name="test-provider",
        provider_type="openai",
        api_base_url="https://api.openai.com/v1",
        api_key_encrypted=encrypt_api_key("sk-test-key"),
        security_level=1,
        provider_metadata={"version": "1"}
    )
    db_session.add(provider)
    db_session.commit()
    db_session.refresh(provider)
    return provider


# =============================================================================
# Async Sample Data Fixtures
# =============================================================================

@pytest_asyncio.fixture
async def async_sample_organization(async_db_session):
    """Create a sample organization for async testing"""
    org = Organization(name="test-org-async-123")
    async_db_session.add(org)
    await async_db_session.commit()
    await async_db_session.refresh(org)
    return org


@pytest_asyncio.fixture
async def async_sample_provider(async_db_session):
    """Create a sample provider for async testing"""
    provider = Provider(
        name="test-provider-async",
        provider_type="openai",
        api_base_url="https://api.openai.com/v1",
        api_key_encrypted=encrypt_api_key("sk-test-key-async"),
        security_level=1,
        provider_metadata={"version": "1"}
    )
    async_db_session.add(provider)
    await async_db_session.commit()
    await async_db_session.refresh(provider)
    return provider


@pytest_asyncio.fixture
async def async_sample_model(async_db_session, async_sample_provider):
    """Create a sample model for async testing"""
    from app.models.model import Model

    model = Model(
        provider_id=async_sample_provider.id,
        model_name="Test Model Async",
        model_identifier="test-model-async",
        context_length=4096,
        max_generation_length=2048,
        is_active=True
    )
    async_db_session.add(model)
    await async_db_session.commit()
    await async_db_session.refresh(model)
    return model


@pytest_asyncio.fixture
async def async_sample_service(async_db_session, async_sample_model):
    """Create a sample service with flavor for async testing"""
    from app.models.service import Service
    from app.models.service_flavor import ServiceFlavor

    service = Service(
        name="Test Service Async",
        route="test-service-async",
        service_type="summary",
        is_active=True
    )
    async_db_session.add(service)
    await async_db_session.commit()
    await async_db_session.refresh(service)

    flavor = ServiceFlavor(
        service_id=service.id,
        model_id=async_sample_model.id,
        name="default-async",
        is_default=True,
        is_active=True,
        temperature=0.7,
        top_p=0.9
    )
    async_db_session.add(flavor)
    await async_db_session.commit()
    await async_db_session.refresh(service)

    return service
