#!/usr/bin/env python3
"""
Seed loader module for directory-based seed data.

Loads seed data from the declarative directory structure:
- seeds/prompts/*  - Prompt definitions with markdown content
- seeds/presets/*  - Flavor preset configurations
- seeds/dev/providers/* - Dev provider configurations (gitignored)
- seeds/dev/services/* - Dev service configurations (gitignored)
"""
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PromptSeed:
    """Seed data for a single prompt."""
    name: str
    content: str
    prompt_category: str  # "user" or "system"
    prompt_type: str  # "standard", "reduce", "field_extraction"
    service_type: str
    description: Dict[str, str] = field(default_factory=dict)


@dataclass
class PresetSeed:
    """Seed data for a flavor preset."""
    name: str
    service_type: str
    description_en: str
    description_fr: str
    config: Dict[str, Any]
    is_system: bool = True
    version: str = "1.0.0"


@dataclass
class ModelSeed:
    """Seed data for a model within a provider."""
    name: str
    model_identifier: str
    context_length: int = 32000
    max_generation_length: int = 8192
    is_active: bool = True
    tokenizer_name: Optional[str] = None
    huggingface_repo: Optional[str] = None


@dataclass
class ProviderSeed:
    """Seed data for a provider with its models."""
    name: str
    provider_type: str
    base_url: str
    api_key: str
    description: Optional[str] = None
    is_active: bool = True
    models: List[ModelSeed] = field(default_factory=list)


@dataclass
class FlavorSeed:
    """Seed data for a service flavor."""
    name: str
    model_identifier: str
    provider_name: str
    temperature: float = 0.2
    top_p: float = 0.7
    is_default: bool = False
    output_type: str = "text"
    user_prompt_name: Optional[str] = None
    reduce_prompt_name: Optional[str] = None
    create_new_turn_after: Optional[int] = None
    summary_turns: Optional[int] = None
    max_new_turns: Optional[int] = None
    reduce_summary: bool = False
    consolidate_summary: bool = False


@dataclass
class ServiceSeed:
    """Seed data for a service with its flavors."""
    name: str
    route: str
    service_type: str
    description: Dict[str, str]
    is_active: bool = True
    flavors: List[FlavorSeed] = field(default_factory=list)


class SeedLoader:
    """Load seed data from directory structure."""

    def __init__(self, seeds_dir: Optional[Path] = None):
        """Initialize the seed loader.

        Args:
            seeds_dir: Path to the seeds directory. Defaults to repository root /seeds.
        """
        if seeds_dir is None:
            # Default: repository root / seeds
            self.seeds_dir = Path(__file__).parent.parent.parent / "seeds"
        else:
            self.seeds_dir = seeds_dir

    def load_prompts(self) -> List[PromptSeed]:
        """Load all prompts from seeds/prompts/.

        Scans each subdirectory for a manifest.json and loads prompt content
        from the referenced markdown files.

        Returns:
            List of PromptSeed objects ready for database insertion.
        """
        prompts_dir = self.seeds_dir / "prompts"
        prompts: List[PromptSeed] = []

        if not prompts_dir.exists():
            logger.warning(f"Prompts directory not found: {prompts_dir}")
            return prompts

        for prompt_subdir in prompts_dir.iterdir():
            if not prompt_subdir.is_dir():
                continue

            manifest_path = prompt_subdir / "manifest.json"
            if not manifest_path.exists():
                logger.warning(f"No manifest.json in {prompt_subdir}, skipping")
                continue

            try:
                manifest = self._load_json(manifest_path)
                loaded = self._load_prompts_from_manifest(prompt_subdir, manifest)
                prompts.extend(loaded)
            except Exception as e:
                logger.error(f"Failed to load prompts from {prompt_subdir}: {e}")
                continue

        logger.info(f"Loaded {len(prompts)} prompts from {prompts_dir}")
        return prompts

    def _load_prompts_from_manifest(
        self, prompt_dir: Path, manifest: Dict[str, Any]
    ) -> List[PromptSeed]:
        """Parse a prompt manifest and load all referenced files.

        Args:
            prompt_dir: Directory containing the manifest and markdown files.
            manifest: Parsed manifest.json content.

        Returns:
            List of PromptSeed objects.
        """
        prompts = []
        service_type = manifest.get("service_type", "summary")
        prompt_type = manifest.get("prompt_type", "standard")
        description = manifest.get("description", {})
        files = manifest.get("files", {})

        for filename, file_config in files.items():
            file_path = prompt_dir / filename
            if not file_path.exists():
                logger.warning(f"Prompt file not found: {file_path}, skipping")
                continue

            try:
                content = file_path.read_text(encoding="utf-8")
            except Exception as e:
                logger.error(f"Failed to read {file_path}: {e}")
                continue

            prompt_name = file_config.get("prompt_name", file_path.stem)
            prompt_category = file_config.get("prompt_category", "user")
            # Per-file prompt_type override (e.g., reduce prompts in a standard set)
            file_prompt_type = file_config.get("prompt_type", prompt_type)

            prompts.append(PromptSeed(
                name=prompt_name,
                content=content,
                prompt_category=prompt_category,
                prompt_type=file_prompt_type,
                service_type=service_type,
                description=description,
            ))

        return prompts

    def load_presets(self) -> List[PresetSeed]:
        """Load all flavor presets from seeds/presets/.

        Scans each subdirectory for a manifest.json file.

        Returns:
            List of PresetSeed objects ready for database insertion.
        """
        presets_dir = self.seeds_dir / "presets"
        presets: List[PresetSeed] = []

        if not presets_dir.exists():
            logger.warning(f"Presets directory not found: {presets_dir}")
            return presets

        for preset_subdir in presets_dir.iterdir():
            if not preset_subdir.is_dir():
                continue

            manifest_path = preset_subdir / "manifest.json"
            if not manifest_path.exists():
                logger.warning(f"No manifest.json in {preset_subdir}, skipping")
                continue

            try:
                manifest = self._load_json(manifest_path)
                preset = self._parse_preset_manifest(manifest)
                if preset:
                    presets.append(preset)
            except Exception as e:
                logger.error(f"Failed to load preset from {preset_subdir}: {e}")
                continue

        logger.info(f"Loaded {len(presets)} presets from {presets_dir}")
        return presets

    def _parse_preset_manifest(self, manifest: Dict[str, Any]) -> Optional[PresetSeed]:
        """Parse a preset manifest.

        Args:
            manifest: Parsed manifest.json content.

        Returns:
            PresetSeed object or None if required fields are missing.
        """
        name = manifest.get("name")
        if not name:
            logger.warning("Preset manifest missing 'name' field")
            return None

        service_type = manifest.get("service_type", "summary")
        description = manifest.get("description", {})
        config = manifest.get("config", {})

        return PresetSeed(
            name=name,
            service_type=service_type,
            description_en=description.get("en", ""),
            description_fr=description.get("fr", ""),
            config=config,
            is_system=manifest.get("is_system", True),
            version=manifest.get("version", "1.0.0"),
        )

    def load_dev_providers(self) -> List[ProviderSeed]:
        """Load providers from seeds/dev/providers/.

        These are gitignored and contain sensitive credentials.

        Returns:
            List of ProviderSeed objects with their associated models.
        """
        providers_dir = self.seeds_dir / "dev" / "providers"
        providers: List[ProviderSeed] = []

        if not providers_dir.exists():
            logger.info(f"Dev providers directory not found: {providers_dir}")
            return providers

        for provider_subdir in providers_dir.iterdir():
            if not provider_subdir.is_dir():
                continue

            manifest_path = provider_subdir / "manifest.json"
            if not manifest_path.exists():
                logger.warning(f"No manifest.json in {provider_subdir}, skipping")
                continue

            try:
                manifest = self._load_json(manifest_path)
                provider = self._parse_provider_manifest(manifest)
                if provider:
                    providers.append(provider)
            except Exception as e:
                logger.error(f"Failed to load provider from {provider_subdir}: {e}")
                continue

        logger.info(f"Loaded {len(providers)} dev providers from {providers_dir}")
        return providers

    def _parse_provider_manifest(
        self, manifest: Dict[str, Any]
    ) -> Optional[ProviderSeed]:
        """Parse a provider manifest.

        Supports environment variable substitution for api_key via api_key_env.

        Args:
            manifest: Parsed manifest.json content.

        Returns:
            ProviderSeed object or None if required fields are missing.
        """
        name = manifest.get("name")
        if not name:
            logger.warning("Provider manifest missing 'name' field")
            return None

        provider_type = manifest.get("provider_type", "openai")
        base_url = manifest.get("api_base_url")
        if not base_url:
            logger.warning(f"Provider '{name}' missing 'api_base_url' field")
            return None

        # API key: prefer environment variable, fallback to direct value
        api_key_env = manifest.get("api_key_env")
        if api_key_env:
            api_key = os.environ.get(api_key_env, "")
            if not api_key:
                logger.warning(
                    f"Environment variable '{api_key_env}' not set for provider '{name}'"
                )
                # Fallback to direct value
                api_key = manifest.get("api_key", "")
        else:
            api_key = manifest.get("api_key", "")

        if not api_key:
            logger.warning(f"Provider '{name}' has no API key configured, skipping")
            return None

        # Parse models
        models_data = manifest.get("models", [])
        models = []
        for model_data in models_data:
            model_name = model_data.get("name", "")
            model_identifier = model_data.get("model_identifier", "")

            # Validate required fields
            if not model_name:
                logger.warning(f"Model in provider '{name}' missing 'name' field, skipping")
                continue
            if not model_identifier:
                logger.warning(f"Model '{model_name}' in provider '{name}' missing 'model_identifier' field, skipping")
                continue

            model = ModelSeed(
                name=model_name,
                model_identifier=model_identifier,
                context_length=model_data.get("context_length", 32000),
                max_generation_length=model_data.get("max_generation_length", 8192),
                is_active=model_data.get("is_active", True),
                tokenizer_name=model_data.get("tokenizer_name"),
                huggingface_repo=model_data.get("huggingface_repo"),
            )
            models.append(model)

        return ProviderSeed(
            name=name,
            provider_type=provider_type,
            base_url=base_url,
            api_key=api_key,
            description=manifest.get("description"),
            is_active=manifest.get("is_active", True),
            models=models,
        )

    def load_dev_services(self) -> List[ServiceSeed]:
        """Load services from seeds/dev/services/.

        These are gitignored and are used for local development.

        Returns:
            List of ServiceSeed objects with their associated flavors.
        """
        services_dir = self.seeds_dir / "dev" / "services"
        services: List[ServiceSeed] = []

        if not services_dir.exists():
            logger.info(f"Dev services directory not found: {services_dir}")
            return services

        for service_subdir in services_dir.iterdir():
            if not service_subdir.is_dir():
                continue

            manifest_path = service_subdir / "manifest.json"
            if not manifest_path.exists():
                logger.warning(f"No manifest.json in {service_subdir}, skipping")
                continue

            try:
                manifest = self._load_json(manifest_path)
                service = self._parse_service_manifest(manifest)
                if service:
                    services.append(service)
            except Exception as e:
                logger.error(f"Failed to load service from {service_subdir}: {e}")
                continue

        logger.info(f"Loaded {len(services)} dev services from {services_dir}")
        return services

    def _parse_service_manifest(
        self, manifest: Dict[str, Any]
    ) -> Optional[ServiceSeed]:
        """Parse a service manifest.

        Args:
            manifest: Parsed manifest.json content.

        Returns:
            ServiceSeed object or None if required fields are missing.
        """
        name = manifest.get("name")
        if not name:
            logger.warning("Service manifest missing 'name' field")
            return None

        route = manifest.get("route", name)
        service_type = manifest.get("service_type", "summary")
        description = manifest.get("description", {})

        # Parse flavors array
        flavors: List[FlavorSeed] = []
        flavors_data = manifest.get("flavors", [])

        for i, flavor_data in enumerate(flavors_data):
            flavor = FlavorSeed(
                name=flavor_data.get("name", f"flavor-{i}"),
                model_identifier=flavor_data.get("model_identifier", ""),
                provider_name=flavor_data.get("provider_name", ""),
                temperature=flavor_data.get("temperature", 0.2),
                top_p=flavor_data.get("top_p", 0.7),
                is_default=flavor_data.get("is_default", i == 0),  # First flavor is default
                output_type=flavor_data.get("output_type", "text"),
                user_prompt_name=flavor_data.get("user_prompt_name"),
                reduce_prompt_name=flavor_data.get("reduce_prompt_name"),
                create_new_turn_after=flavor_data.get("create_new_turn_after"),
                summary_turns=flavor_data.get("summary_turns"),
                max_new_turns=flavor_data.get("max_new_turns"),
                reduce_summary=flavor_data.get("reduce_summary", False),
                consolidate_summary=flavor_data.get("consolidate_summary", False),
            )
            flavors.append(flavor)

        return ServiceSeed(
            name=name,
            route=route,
            service_type=service_type,
            description=description,
            is_active=manifest.get("is_active", True),
            flavors=flavors,
        )

    def _load_json(self, path: Path) -> Dict[str, Any]:
        """Load and parse a JSON file.

        Args:
            path: Path to the JSON file.

        Returns:
            Parsed JSON content as a dictionary.

        Raises:
            json.JSONDecodeError: If the file contains invalid JSON.
            IOError: If the file cannot be read.
        """
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
