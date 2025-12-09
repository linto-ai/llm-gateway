#!/usr/bin/env python3
"""Service type configuration registry.

This module defines the service type configurations used throughout the application
to determine which prompts and features are available for each service type.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel


class PromptFieldConfig(BaseModel):
    """Configuration for a prompt field in a service type."""
    required: bool = False
    prompt_category: str  # 'system' or 'user'
    prompt_type: Optional[str] = None  # 'standard', 'reduce', or custom
    description_en: str
    description_fr: str


class ServiceTypeConfig(BaseModel):
    """Configuration for a service type."""
    name_en: str
    name_fr: str
    description_en: str
    description_fr: str
    prompts: Dict[str, PromptFieldConfig]
    supports_reduce: bool = False
    supports_chunking: bool = False
    default_processing_mode: str = "single_pass"


SERVICE_TYPE_CONFIGS: Dict[str, ServiceTypeConfig] = {
    "summary": ServiceTypeConfig(
        name_en="Summary",
        name_fr="Resume",
        description_en="Summarize transcripts and documents",
        description_fr="Resumer des transcriptions et documents",
        prompts={
            "system_prompt": PromptFieldConfig(
                required=False,
                prompt_category="system",
                prompt_type="standard",
                description_en="System instructions for the model",
                description_fr="Instructions systeme pour le modele"
            ),
            "user_prompt": PromptFieldConfig(
                required=True,
                prompt_category="user",
                prompt_type="standard",
                description_en="Main summarization prompt template",
                description_fr="Template principal de resume"
            ),
            "reduce_prompt": PromptFieldConfig(
                required=False,
                prompt_category="user",
                prompt_type="reduce",
                description_en="Consolidation prompt for map-reduce mode (optional)",
                description_fr="Prompt de consolidation pour le mode map-reduce (optionnel)"
            )
        },
        supports_reduce=True,
        supports_chunking=True,
        default_processing_mode="iterative"
    ),
    "translation": ServiceTypeConfig(
        name_en="Translation",
        name_fr="Traduction",
        description_en="Translate documents between languages",
        description_fr="Traduire des documents entre langues",
        prompts={
            "system_prompt": PromptFieldConfig(
                required=False,
                prompt_category="system",
                prompt_type="standard",
                description_en="System instructions for translation",
                description_fr="Instructions systeme pour la traduction"
            ),
            "user_prompt": PromptFieldConfig(
                required=True,
                prompt_category="user",
                prompt_type="standard",
                description_en="Translation prompt template",
                description_fr="Template de traduction"
            )
        },
        supports_reduce=False,
        supports_chunking=True,
        default_processing_mode="iterative"
    ),
    "categorization": ServiceTypeConfig(
        name_en="Categorization",
        name_fr="Categorisation",
        description_en="Classify documents into categories",
        description_fr="Classer des documents en categories",
        prompts={
            "system_prompt": PromptFieldConfig(
                required=False,
                prompt_category="system",
                prompt_type="standard",
                description_en="System instructions for categorization",
                description_fr="Instructions systeme pour la categorisation"
            ),
            "user_prompt": PromptFieldConfig(
                required=True,
                prompt_category="user",
                prompt_type="standard",
                description_en="Categorization prompt with candidates",
                description_fr="Prompt de categorisation avec candidats"
            )
        },
        supports_reduce=False,
        supports_chunking=False,
        default_processing_mode="single_pass"
    ),
    "diarization_correction": ServiceTypeConfig(
        name_en="Diarization Correction",
        name_fr="Correction de diarisation",
        description_en="Fix speaker attribution errors in transcripts",
        description_fr="Corriger les erreurs d'attribution de locuteurs",
        prompts={
            "system_prompt": PromptFieldConfig(
                required=False,
                prompt_category="system",
                prompt_type="standard",
                description_en="System instructions for diarization correction",
                description_fr="Instructions systeme pour la correction de diarisation"
            ),
            "user_prompt": PromptFieldConfig(
                required=True,
                prompt_category="user",
                prompt_type="standard",
                description_en="Diarization correction prompt",
                description_fr="Prompt de correction de diarisation"
            )
        },
        supports_reduce=False,
        supports_chunking=True,
        default_processing_mode="iterative"
    ),
    "speaker_correction": ServiceTypeConfig(
        name_en="Speaker Correction",
        name_fr="Correction de locuteurs",
        description_en="Correct speaker labels in transcripts",
        description_fr="Corriger les etiquettes de locuteurs dans les transcriptions",
        prompts={
            "system_prompt": PromptFieldConfig(
                required=False,
                prompt_category="system",
                prompt_type="standard",
                description_en="System instructions for speaker correction",
                description_fr="Instructions systeme pour la correction de locuteurs"
            ),
            "user_prompt": PromptFieldConfig(
                required=True,
                prompt_category="user",
                prompt_type="standard",
                description_en="Speaker correction prompt",
                description_fr="Prompt de correction de locuteurs"
            )
        },
        supports_reduce=False,
        supports_chunking=True,
        default_processing_mode="iterative"
    ),
    "generic": ServiceTypeConfig(
        name_en="Generic",
        name_fr="Generique",
        description_en="Generic LLM service for custom use cases",
        description_fr="Service LLM generique pour cas d'usage personnalises",
        prompts={
            "system_prompt": PromptFieldConfig(
                required=False,
                prompt_category="system",
                prompt_type="standard",
                description_en="System instructions for the model",
                description_fr="Instructions systeme pour le modele"
            ),
            "user_prompt": PromptFieldConfig(
                required=True,
                prompt_category="user",
                prompt_type="standard",
                description_en="Main prompt template",
                description_fr="Template principal de prompt"
            ),
            "reduce_prompt": PromptFieldConfig(
                required=False,
                prompt_category="user",
                prompt_type="reduce",
                description_en="Consolidation prompt for map-reduce mode (optional)",
                description_fr="Prompt de consolidation pour le mode map-reduce (optionnel)"
            )
        },
        supports_reduce=True,
        supports_chunking=True,
        default_processing_mode="single_pass"
    )
}


def get_service_type_config(service_type: str) -> Optional[ServiceTypeConfig]:
    """Get configuration for a service type.

    Args:
        service_type: The service type identifier

    Returns:
        ServiceTypeConfig if found, None otherwise
    """
    return SERVICE_TYPE_CONFIGS.get(service_type)


def get_available_service_types() -> List[str]:
    """Get list of all available service types.

    Returns:
        List of service type identifiers
    """
    return list(SERVICE_TYPE_CONFIGS.keys())
