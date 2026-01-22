#!/usr/bin/env python3
"""
Base seed logic for development data.

Uses a declarative directory-based structure for seed data:
- seeds/prompts/*  - Production prompts (versioned)
- seeds/presets/*  - Production flavor presets (versioned)
- seeds/dev/*      - Dev providers and services (gitignored)

Usage:
    # Seed production data (prompts + presets + templates)
    docker exec llm-gateway-llm-gateway-1 python -m app.seeds.base_seed

    # Include dev data (providers + services)
    docker exec llm-gateway-llm-gateway-1 python -m app.seeds.base_seed --dev

    # Seed specific category only
    docker exec llm-gateway-llm-gateway-1 python -m app.seeds.base_seed --only prompts
    docker exec llm-gateway-llm-gateway-1 python -m app.seeds.base_seed --only presets
    docker exec llm-gateway-llm-gateway-1 python -m app.seeds.base_seed --only templates
"""
import argparse
import asyncio
import logging
from typing import Dict, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.security import get_encryption_service
from app.models.flavor_preset import FlavorPreset
from app.models.model import Model
from app.models.prompt import Prompt
from app.models.provider import Provider
from app.models.service import Service
from app.models.service_flavor import ServiceFlavor
from app.seeds.loader import (
    PresetSeed,
    PromptSeed,
    ProviderSeed,
    SeedLoader,
    ServiceSeed,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


async def get_or_create_provider(
    db: AsyncSession,
    name: str,
    provider_type: str,
    base_url: str,
    api_key: str,
    is_active: bool = True,
) -> Provider:
    """Get existing provider by name or create new one."""
    encryption_service = get_encryption_service()

    result = await db.execute(
        select(Provider).where(Provider.name == name)
    )
    provider = result.scalar_one_or_none()

    if provider:
        logger.info(f"Provider '{name}' already exists, skipping creation")
        return provider

    # Encrypt API key
    encrypted_key = encryption_service.encrypt(api_key)

    provider = Provider(
        name=name,
        provider_type=provider_type,
        api_base_url=base_url,
        api_key_encrypted=encrypted_key,
        security_level=1,  # 1 = Medium security
    )

    db.add(provider)
    await db.flush()
    await db.refresh(provider)

    logger.info(f"Created provider: {name} ({provider.id})")
    return provider


def _validate_huggingface_repo(hf_repo: Optional[str]) -> Optional[str]:
    """Validate HuggingFace repo string. Returns None if invalid."""
    if not hf_repo:
        return None
    # Must contain '/' and not start with 'test/'
    if '/' not in hf_repo or hf_repo.startswith('test/'):
        logger.warning(f"Invalid huggingface_repo '{hf_repo}' - ignoring")
        return None
    return hf_repo


async def get_or_create_model(
    db: AsyncSession,
    provider_id: UUID,
    model_name: str,
    model_identifier: str,
    context_length: int = 32000,
    max_generation_length: int = 8192,
    is_active: bool = True,
    tokenizer_name: Optional[str] = None,
    huggingface_repo: Optional[str] = None,
) -> Model:
    """Get existing model by identifier or create new one."""
    result = await db.execute(
        select(Model).where(
            Model.provider_id == provider_id,
            Model.model_identifier == model_identifier
        )
    )
    model = result.scalar_one_or_none()

    if model:
        logger.info(f"Model '{model_identifier}' already exists, skipping creation")
        return model

    # Validate huggingface_repo before setting
    validated_hf_repo = _validate_huggingface_repo(huggingface_repo)

    model = Model(
        provider_id=provider_id,
        model_name=model_name,
        model_identifier=model_identifier,
        context_length=context_length,
        max_generation_length=max_generation_length,
        is_active=is_active,
        tokenizer_name=tokenizer_name,
        huggingface_repo=validated_hf_repo,
    )

    db.add(model)
    await db.flush()
    await db.refresh(model)

    logger.info(f"Created model: {model_name} ({model.id})")
    return model


async def get_or_create_prompt(
    db: AsyncSession,
    name: str,
    content: str,
    description: Optional[dict] = None,
    prompt_category: str = "user",
    prompt_type: Optional[str] = None,
    service_type: str = "summary",
) -> Prompt:
    """Get existing prompt by name or create/update it."""
    from app.models.prompt_type import PromptType

    result = await db.execute(
        select(Prompt).where(Prompt.name == name)
    )
    prompt = result.scalar_one_or_none()

    if prompt:
        # Update content if changed
        if prompt.content != content:
            prompt.content = content
            logger.info(f"Prompt '{name}' content updated")
        else:
            logger.info(f"Prompt '{name}' already exists, no changes")
        return prompt

    # Resolve prompt_type code to ID
    prompt_type_id = None
    if prompt_type:
        pt_result = await db.execute(
            select(PromptType).where(PromptType.code == prompt_type)
        )
        pt = pt_result.scalar_one_or_none()
        if pt:
            prompt_type_id = pt.id
        else:
            logger.warning(f"Prompt type '{prompt_type}' not found, setting to None")

    prompt = Prompt(
        name=name,
        content=content,
        description=description or {},
        prompt_category=prompt_category,
        prompt_type_id=prompt_type_id,
        organization_id=None,
        service_type=service_type,
    )

    db.add(prompt)
    await db.flush()
    await db.refresh(prompt)

    logger.info(f"Created prompt: {name} ({prompt.id})")
    return prompt


async def get_or_create_service(
    db: AsyncSession,
    name: str,
    route: str,
    service_type: str,
    description: dict,
    is_active: bool = True,
) -> Service:
    """Get existing service by name or create new one."""
    result = await db.execute(
        select(Service).where(Service.name == name)
    )
    service = result.scalar_one_or_none()

    if service:
        logger.info(f"Service '{name}' already exists, skipping creation")
        return service

    service = Service(
        name=name,
        route=route,
        service_type=service_type,
        description=description,
        is_active=is_active,
        organization_id=None,
    )

    db.add(service)
    await db.flush()
    await db.refresh(service)

    logger.info(f"Created service: {name} ({service.id})")
    return service


async def get_or_create_flavor(
    db: AsyncSession,
    service_id: UUID,
    model_id: UUID,
    name: str,
    temperature: float = 0.2,
    top_p: float = 0.7,
    is_default: bool = False,
    user_prompt_id: Optional[UUID] = None,
    prompt_user_content: Optional[str] = None,
    output_type: str = "text",
    create_new_turn_after: Optional[int] = None,
    summary_turns: Optional[int] = None,
    max_new_turns: Optional[int] = None,
    reduce_summary: bool = False,
    consolidate_summary: bool = False,
    reduce_prompt_id: Optional[UUID] = None,
    prompt_reduce_content: Optional[str] = None,
    estimated_cost_per_1k_tokens: Optional[float] = None,
) -> ServiceFlavor:
    """Get existing flavor by name or create new one."""
    result = await db.execute(
        select(ServiceFlavor).where(
            ServiceFlavor.service_id == service_id,
            ServiceFlavor.name == name
        )
    )
    flavor = result.scalar_one_or_none()

    if flavor:
        logger.info(f"Flavor '{name}' already exists for service, skipping creation")
        return flavor

    flavor = ServiceFlavor(
        service_id=service_id,
        model_id=model_id,
        name=name,
        temperature=temperature,
        top_p=top_p,
        is_default=is_default,
        is_active=True,
        user_prompt_template_id=user_prompt_id,
        prompt_user_content=prompt_user_content,
        output_type=output_type,
        create_new_turn_after=create_new_turn_after,
        summary_turns=summary_turns,
        max_new_turns=max_new_turns,
        reduce_summary=reduce_summary,
        consolidate_summary=consolidate_summary,
        reduce_prompt_id=reduce_prompt_id,
        prompt_reduce_content=prompt_reduce_content,
        estimated_cost_per_1k_tokens=estimated_cost_per_1k_tokens,
    )

    db.add(flavor)
    await db.flush()
    await db.refresh(flavor)

    logger.info(f"Created flavor: {name} ({flavor.id})")
    return flavor


async def get_or_create_preset(
    db: AsyncSession,
    name: str,
    service_type: str,
    description_en: str,
    description_fr: str,
    config: dict,
    is_system: bool = True,
) -> FlavorPreset:
    """Get existing preset by name or create new one."""
    result = await db.execute(
        select(FlavorPreset).where(FlavorPreset.name == name)
    )
    preset = result.scalar_one_or_none()

    if preset:
        logger.info(f"Preset '{name}' already exists, skipping creation")
        return preset

    preset = FlavorPreset(
        name=name,
        service_type=service_type,
        description_en=description_en,
        description_fr=description_fr,
        config=config,
        is_system=is_system,
        is_active=True,
    )

    db.add(preset)
    await db.flush()
    await db.refresh(preset)

    logger.info(f"Created preset: {name} ({preset.id})")
    return preset


async def seed_prompts(db: AsyncSession, prompts: list[PromptSeed]) -> int:
    """Seed prompts from loaded seed data.

    Args:
        db: Database session.
        prompts: List of PromptSeed objects.

    Returns:
        Number of prompts created/verified.
    """
    count = 0
    for prompt_seed in prompts:
        prompt = await get_or_create_prompt(
            db=db,
            name=prompt_seed.name,
            content=prompt_seed.content,
            description=prompt_seed.description,
            prompt_category=prompt_seed.prompt_category,
            prompt_type=prompt_seed.prompt_type,
            service_type=prompt_seed.service_type,
        )
        if prompt:
            count += 1

    logger.info(f"Seeded {count} prompts")
    return count


async def seed_presets(db: AsyncSession, presets: list[PresetSeed]) -> int:
    """Seed flavor presets from loaded seed data.

    Args:
        db: Database session.
        presets: List of PresetSeed objects.

    Returns:
        Number of presets created/verified.
    """
    count = 0
    for preset_seed in presets:
        preset = await get_or_create_preset(
            db=db,
            name=preset_seed.name,
            service_type=preset_seed.service_type,
            description_en=preset_seed.description_en,
            description_fr=preset_seed.description_fr,
            config=preset_seed.config,
            is_system=preset_seed.is_system,
        )
        if preset:
            count += 1

    logger.info(f"Seeded {count} flavor presets")
    return count


async def seed_providers(
    db: AsyncSession, providers: list[ProviderSeed]
) -> tuple[int, int, Dict[str, Model]]:
    """Seed providers and their models from loaded seed data.

    Args:
        db: Database session.
        providers: List of ProviderSeed objects.

    Returns:
        Tuple of (providers_count, models_count, model_map).
    """
    providers_count = 0
    models_count = 0
    model_map: Dict[str, Model] = {}

    for provider_seed in providers:
        provider = await get_or_create_provider(
            db=db,
            name=provider_seed.name,
            provider_type=provider_seed.provider_type,
            base_url=provider_seed.base_url,
            api_key=provider_seed.api_key,
            is_active=provider_seed.is_active,
        )
        providers_count += 1

        for model_seed in provider_seed.models:
            model = await get_or_create_model(
                db=db,
                provider_id=provider.id,
                model_name=model_seed.name,
                model_identifier=model_seed.model_identifier,
                context_length=model_seed.context_length,
                max_generation_length=model_seed.max_generation_length,
                is_active=model_seed.is_active,
                tokenizer_name=model_seed.tokenizer_name,
                huggingface_repo=model_seed.huggingface_repo,
            )
            # Map by both name and identifier for flexible lookups
            model_map[model_seed.name] = model
            model_map[model_seed.model_identifier] = model
            models_count += 1

    logger.info(f"Seeded {providers_count} providers, {models_count} models")
    return providers_count, models_count, model_map


async def seed_services(
    db: AsyncSession,
    services: list[ServiceSeed],
    model_map: Dict[str, Model],
    prompt_map: Dict[str, Prompt],
) -> tuple[int, int]:
    """Seed services and their flavors from loaded seed data.

    Args:
        db: Database session.
        services: List of ServiceSeed objects.
        model_map: Map of model name/identifier to Model objects.
        prompt_map: Map of prompt name to Prompt objects.

    Returns:
        Tuple of (services_count, flavors_count).
    """
    services_count = 0
    flavors_count = 0

    for service_seed in services:
        service = await get_or_create_service(
            db=db,
            name=service_seed.name,
            route=service_seed.route,
            service_type=service_seed.service_type,
            description=service_seed.description,
            is_active=service_seed.is_active,
        )
        services_count += 1

        for flavor_seed in service_seed.flavors:
            # Resolve model
            model = model_map.get(flavor_seed.model_identifier)
            if not model:
                logger.warning(
                    f"Model '{flavor_seed.model_identifier}' not found, "
                    f"skipping flavor '{flavor_seed.name}' for service '{service_seed.name}'"
                )
                continue

            # Resolve user prompt
            user_prompt = prompt_map.get(flavor_seed.user_prompt_name) if flavor_seed.user_prompt_name else None
            user_prompt_id = user_prompt.id if user_prompt else None
            prompt_content = user_prompt.content if user_prompt else None

            # Resolve reduce prompt
            reduce_prompt = prompt_map.get(flavor_seed.reduce_prompt_name) if flavor_seed.reduce_prompt_name else None
            reduce_prompt_id = reduce_prompt.id if reduce_prompt else None
            reduce_prompt_content = reduce_prompt.content if reduce_prompt else None

            await get_or_create_flavor(
                db=db,
                service_id=service.id,
                model_id=model.id,
                name=flavor_seed.name,
                temperature=flavor_seed.temperature,
                top_p=flavor_seed.top_p,
                is_default=flavor_seed.is_default,
                user_prompt_id=user_prompt_id,
                prompt_user_content=prompt_content,
                output_type=flavor_seed.output_type,
                create_new_turn_after=flavor_seed.create_new_turn_after,
                summary_turns=flavor_seed.summary_turns,
                max_new_turns=flavor_seed.max_new_turns,
                reduce_summary=flavor_seed.reduce_summary,
                consolidate_summary=flavor_seed.consolidate_summary,
                reduce_prompt_id=reduce_prompt_id,
                prompt_reduce_content=reduce_prompt_content,
            )
            flavors_count += 1

    logger.info(f"Seeded {services_count} services, {flavors_count} flavors")
    return services_count, flavors_count


async def seed_global_document_templates(db: AsyncSession) -> int:
    """Seed global document templates from templates/default/ directory.

    Returns:
        Number of templates created.
    """
    try:
        from app.seeds.document_templates import seed_global_templates
        stats = await seed_global_templates(db)
        logger.info(f"Seeded {stats['templates_created']} global document templates")
        return stats["templates_created"]
    except ImportError:
        logger.warning("document_templates.py not found - skipping")
        return 0
    except Exception as e:
        logger.warning(f"Failed to seed global document templates: {e}")
        return 0


async def seed_production(db: AsyncSession, only: Optional[str] = None) -> dict:
    """Seed production data: prompts, presets, templates.

    Args:
        db: Database session.
        only: If specified, only seed this category ("prompts", "presets", "templates").

    Returns:
        Dict with counts of created entities.
    """
    loader = SeedLoader()
    stats = {
        "prompts_created": 0,
        "presets_created": 0,
        "templates_created": 0,
    }

    # Prompts from seeds/prompts/
    if only is None or only == "prompts":
        prompts = loader.load_prompts()
        stats["prompts_created"] = await seed_prompts(db, prompts)

    # Presets from seeds/presets/
    if only is None or only == "presets":
        presets = loader.load_presets()
        stats["presets_created"] = await seed_presets(db, presets)

    # Templates from templates/default/
    if only is None or only == "templates":
        stats["templates_created"] = await seed_global_document_templates(db)

    return stats


async def seed_dev(db: AsyncSession) -> dict:
    """Seed dev data: providers, services (in addition to production).

    Args:
        db: Database session.

    Returns:
        Dict with counts of created entities.
    """
    loader = SeedLoader()

    # First seed production data
    stats = await seed_production(db)

    # Then add dev-specific data
    providers = loader.load_dev_providers()
    if providers:
        providers_count, models_count, model_map = await seed_providers(db, providers)
        stats["providers_created"] = providers_count
        stats["models_created"] = models_count

        # Build prompt map for service flavor resolution
        result = await db.execute(select(Prompt))
        all_prompts = result.scalars().all()
        prompt_map = {p.name: p for p in all_prompts}

        services = loader.load_dev_services()
        if services:
            services_count, flavors_count = await seed_services(
                db, services, model_map, prompt_map
            )
            stats["services_created"] = services_count
            stats["flavors_created"] = flavors_count
    else:
        logger.info("No dev providers found - skipping dev seed")

    return stats


async def run_seed(dev: bool = False, only: Optional[str] = None) -> dict:
    """Run the seed process.

    Args:
        dev: If True, include dev data (providers, services).
        only: If specified, only seed this category ("prompts", "presets", "templates").

    Returns:
        Dict with counts of created entities.
    """
    logger.info(f"Starting seed (dev={dev}, only={only})...")

    async with AsyncSessionLocal() as db:
        try:
            if dev:
                result = await seed_dev(db)
            else:
                result = await seed_production(db, only=only)

            await db.commit()
            logger.info(f"Seed completed: {result}")
            return result
        except Exception as e:
            logger.error(f"Seed failed: {e}")
            raise


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Seed database with production and/or development data."
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Include dev data (providers, services from seeds/dev/)",
    )
    parser.add_argument(
        "--only",
        choices=["prompts", "presets", "templates"],
        help="Seed only a specific category",
    )
    return parser.parse_args()


async def main():
    """Entry point for the seed command."""
    args = parse_args()

    if args.dev and args.only:
        logger.warning("--only is ignored when --dev is specified")

    result = await run_seed(dev=args.dev, only=args.only if not args.dev else None)
    logger.info(f"Final stats: {result}")


if __name__ == "__main__":
    asyncio.run(main())
