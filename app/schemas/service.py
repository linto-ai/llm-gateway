#!/usr/bin/env python3
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime
from uuid import UUID


class ServiceFlavorBase(BaseModel):
    """Base schema for ServiceFlavor with common fields."""
    name: str = Field(..., min_length=1, max_length=50)
    model_id: UUID
    temperature: float = Field(..., ge=0, le=2)
    top_p: float = Field(default=0.9, gt=0, le=1)

    # Default flavor flag
    is_default: bool = False

    # Advanced configuration
    description: Optional[str] = Field(None, max_length=500)
    is_active: bool = True
    frequency_penalty: float = Field(default=0.0, ge=0, le=2, description="Penalizes repeated tokens. Higher values reduce repetition (0.0-2.0)")
    presence_penalty: float = Field(default=0.0, ge=0, le=2, description="Penalizes tokens already present. Encourages new topics (0.0-2.0)")
    stop_sequences: List[str] = Field(default_factory=list, max_length=4)
    custom_params: Dict[str, Any] = Field(default_factory=dict)
    estimated_cost_per_1k_tokens: Optional[float] = Field(None, gt=0)
    max_concurrent_requests: Optional[int] = Field(None, gt=0)
    priority: int = Field(default=5, ge=0, le=9, description="Task priority (0=urgent, 5=normal, 9=background)")

    # Chunking/Resampling parameters for conversation processing
    create_new_turn_after: Optional[int] = Field(
        None, gt=0,
        description="Token count threshold after which a long turn is split into virtual turns using sentence segmentation"
    )
    summary_turns: Optional[int] = Field(
        None, ge=1, le=20,
        description="Number of previous summary turns to include in context for continuity"
    )
    max_new_turns: Optional[int] = Field(
        None, ge=1, le=50,
        description="Maximum number of new turns to accumulate before triggering summarization batch"
    )
    reduce_summary: bool = False
    consolidate_summary: bool = False

    output_type: Literal['text', 'markdown', 'json'] = 'text'

    # Prompt options - template OR content
    system_prompt_template_id: Optional[UUID] = None
    user_prompt_template_id: Optional[UUID] = None
    reduce_prompt_template_id: Optional[UUID] = None

    prompt_system_content: Optional[str] = None
    prompt_user_content: Optional[str] = None
    prompt_reduce_content: Optional[str] = None


    # Tokenizer override
    tokenizer_override: Optional[str] = Field(
        None, max_length=200,
        description="Override model's default tokenizer (e.g., 'gpt2', 'mistralai/Mistral-7B-v0.1')"
    )

    # Processing mode configuration
    processing_mode: Literal["single_pass", "iterative"] = "iterative"

    # Fallback configuration
    fallback_flavor_id: Optional[UUID] = Field(
        None,
        description="Explicit flavor to use when input exceeds context limit. Can be from any service."
    )

    # Failover configuration (triggers on processing errors, not context overflow)
    failover_flavor_id: Optional[UUID] = Field(
        None,
        description="Flavor to failover to when this flavor fails during processing"
    )
    failover_enabled: bool = Field(
        default=False,
        description="Enable automatic failover on processing errors"
    )
    failover_on_timeout: bool = Field(
        default=True,
        description="Failover on API timeout"
    )
    failover_on_rate_limit: bool = Field(
        default=True,
        description="Failover on rate limit exceeded"
    )
    failover_on_model_error: bool = Field(
        default=True,
        description="Failover on model errors (503, 404)"
    )
    failover_on_content_filter: bool = Field(
        default=False,
        description="Failover on content filter triggered"
    )
    max_failover_depth: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Max failover chain depth"
    )

    # Placeholder extraction configuration
    placeholder_extraction_prompt_id: Optional[UUID] = None

    # Categorization prompt configuration
    categorization_prompt_id: Optional[UUID] = None

    # Job TTL configuration
    default_ttl_seconds: Optional[int] = Field(
        None,
        gt=0,
        le=31536000,  # Max 1 year in seconds
        description="Default TTL for jobs in seconds. NULL = never expire."
    )


class ServiceFlavorCreate(ServiceFlavorBase):
    """Schema for creating a new service flavor."""
    pass


class ServiceFlavorUpdate(BaseModel):
    """Schema for updating a service flavor (partial update)."""
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    model_id: Optional[UUID] = Field(None, description="Model to use for this flavor")
    temperature: Optional[float] = Field(None, ge=0, le=2)
    top_p: Optional[float] = Field(None, gt=0, le=1)

    # Default flavor flag
    is_default: Optional[bool] = None

    # Advanced configuration
    description: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None
    frequency_penalty: Optional[float] = Field(None, ge=0, le=2, description="Penalizes repeated tokens. Higher values reduce repetition (0.0-2.0)")
    presence_penalty: Optional[float] = Field(None, ge=0, le=2, description="Penalizes tokens already present. Encourages new topics (0.0-2.0)")
    stop_sequences: Optional[List[str]] = Field(None, max_length=4)
    custom_params: Optional[Dict[str, Any]] = None
    estimated_cost_per_1k_tokens: Optional[float] = Field(None, gt=0)
    max_concurrent_requests: Optional[int] = Field(None, gt=0)
    priority: Optional[int] = Field(None, ge=0, le=9, description="Task priority (0=urgent, 5=normal, 9=background)")

    # Inline prompt editing (edits local copy, not template)
    prompt_system_content: Optional[str] = None
    prompt_user_content: Optional[str] = None
    prompt_reduce_content: Optional[str] = None

    # Template replacement (replaces inline content with template)
    system_prompt_template_id: Optional[UUID] = None
    user_prompt_template_id: Optional[UUID] = None
    reduce_prompt_template_id: Optional[UUID] = None

    create_new_turn_after: Optional[int] = Field(None, gt=0)
    summary_turns: Optional[int] = Field(None, gt=0)
    max_new_turns: Optional[int] = Field(None, gt=0)
    reduce_summary: Optional[bool] = None
    consolidate_summary: Optional[bool] = None
    output_type: Optional[Literal['text', 'markdown', 'json']] = None

    # Tokenizer override
    tokenizer_override: Optional[str] = Field(
        None, max_length=200,
        description="Override model's default tokenizer"
    )

    # Processing mode configuration
    processing_mode: Optional[Literal["single_pass", "iterative"]] = None

    # Fallback configuration
    fallback_flavor_id: Optional[UUID] = Field(
        None,
        description="Explicit flavor to use when input exceeds context limit."
    )

    # Failover configuration
    failover_flavor_id: Optional[UUID] = None
    failover_enabled: Optional[bool] = None
    failover_on_timeout: Optional[bool] = None
    failover_on_rate_limit: Optional[bool] = None
    failover_on_model_error: Optional[bool] = None
    failover_on_content_filter: Optional[bool] = None
    max_failover_depth: Optional[int] = Field(None, ge=1, le=10)

    # Placeholder extraction configuration
    placeholder_extraction_prompt_id: Optional[UUID] = None

    # Categorization prompt configuration
    categorization_prompt_id: Optional[UUID] = None

    # Job TTL configuration
    default_ttl_seconds: Optional[int] = Field(
        None,
        gt=0,
        le=31536000,  # Max 1 year in seconds
        description="Default TTL for jobs. NULL = never expire."
    )


class ModelInfo(BaseModel):
    """Schema for nested model information in flavor response."""
    id: UUID
    model_name: str
    model_identifier: str
    provider_id: UUID
    provider_name: str  # Enhanced model info with provider name
    # Token limits - essential for processing decisions
    context_length: Optional[int] = None
    max_generation_length: Optional[int] = None
    # Security classification for the model
    security_level: Optional[str] = None

    class Config:
        from_attributes = True


class ServiceFlavorResponse(BaseModel):
    """Schema for service flavor response with database fields."""
    id: UUID
    service_id: UUID
    model_id: UUID
    name: str
    temperature: float
    top_p: float

    # Default flavor flag
    is_default: bool

    # Advanced configuration
    description: Optional[str]
    is_active: bool
    frequency_penalty: float
    presence_penalty: float
    stop_sequences: List[str]
    custom_params: Dict[str, Any]
    estimated_cost_per_1k_tokens: Optional[float]
    max_concurrent_requests: Optional[int]
    priority: int

    # Chunking/Resampling parameters (nullable)
    create_new_turn_after: Optional[int]
    summary_turns: Optional[int]
    max_new_turns: Optional[int]
    reduce_summary: bool
    consolidate_summary: bool

    output_type: str

    # Template references (for tracking origin)
    system_prompt_id: Optional[UUID]
    user_prompt_template_id: Optional[UUID]
    reduce_prompt_id: Optional[UUID]

    # Prompt names for display (populated from relationships)
    system_prompt_name: Optional[str] = None
    user_prompt_template_name: Optional[str] = None
    reduce_prompt_name: Optional[str] = None

    # Inline content (actual prompts used)
    prompt_system_content: Optional[str]
    prompt_user_content: Optional[str]
    prompt_reduce_content: Optional[str]

    # Tokenizer override
    tokenizer_override: Optional[str] = None

    # Processing mode configuration
    processing_mode: str

    # Fallback configuration
    fallback_flavor_id: Optional[UUID] = None
    fallback_flavor_name: Optional[str] = None
    fallback_service_name: Optional[str] = None

    # Failover configuration
    failover_flavor_id: Optional[UUID] = None
    failover_flavor_name: Optional[str] = None
    failover_service_name: Optional[str] = None
    failover_enabled: bool = False
    failover_on_timeout: bool = True
    failover_on_rate_limit: bool = True
    failover_on_model_error: bool = True
    failover_on_content_filter: bool = False
    max_failover_depth: int = 3

    # Placeholder extraction configuration
    placeholder_extraction_prompt_id: Optional[UUID] = None
    placeholder_extraction_prompt_name: Optional[str] = None

    # Categorization prompt configuration
    categorization_prompt_id: Optional[UUID] = None
    categorization_prompt_name: Optional[str] = None

    # Job TTL configuration
    default_ttl_seconds: Optional[int] = None

    created_at: datetime
    updated_at: datetime

    model: Optional[ModelInfo] = None

    class Config:
        from_attributes = True


class ExecutionValidationResponse(BaseModel):
    """Response for pre-execution validation (dry run)."""
    valid: bool  # True if execution can proceed with this flavor
    warning: Optional[str] = None  # Warning/recommendation if close to limits or exceeds
    input_tokens: Optional[int] = None  # Actual input tokens (content + prompts)
    max_generation: Optional[int] = None  # Max generation length from model config
    context_length: Optional[int] = None  # Total context length from model
    estimated_cost: Optional[float] = None  # Estimated cost based on flavor's cost_per_1k_tokens


class ServiceBase(BaseModel):
    """Base schema for Service with common fields."""
    name: str = Field(..., min_length=1, max_length=100)
    route: str = Field(..., min_length=1, max_length=100)
    service_type: str = Field(..., min_length=1, max_length=50)
    description: Dict[str, str] = Field(default_factory=dict)
    # Free-form organization identifier (any string up to 100 chars)
    organization_id: Optional[str] = Field(None, max_length=100)
    is_active: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Service category (allows custom types)
    service_category: Optional[str] = Field(None, max_length=50)


class ServiceCreate(BaseModel):
    """Schema for creating a new service."""
    name: str = Field(..., min_length=1, max_length=100)
    route: Optional[str] = Field(None, min_length=1, max_length=100)  # Auto-generated from name if not provided
    service_type: str = Field(..., min_length=1, max_length=50)
    description: Dict[str, str] = Field(default_factory=dict)
    # Free-form organization identifier (any string up to 100 chars)
    organization_id: Optional[str] = Field(None, max_length=100)
    is_active: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)
    service_category: Optional[str] = Field(None, max_length=50)
    flavors: List[ServiceFlavorCreate] = Field(default_factory=list)  # Optional, can be added later


class ServiceUpdate(BaseModel):
    """Schema for updating an existing service."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    route: Optional[str] = Field(None, min_length=1, max_length=100)
    service_type: Optional[str] = None
    description: Optional[Dict[str, str]] = None
    is_active: Optional[bool] = None
    flavors: Optional[List[ServiceFlavorCreate]] = None
    metadata: Optional[Dict[str, Any]] = None
    service_category: Optional[str] = Field(None, max_length=50)
    default_template_id: Optional[UUID] = Field(None, description="Default document template for export")


class ServiceResponse(ServiceBase):
    """Schema for service response with database fields."""
    id: UUID
    flavors: List[ServiceFlavorResponse]
    default_template_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ServiceListResponse(BaseModel):
    """Response schema for paginated service list (internal use)."""
    total: int
    items: List[ServiceResponse]


class ServiceFlavorListResponse(BaseModel):
    """Response schema for list flavors endpoint."""
    items: List[ServiceFlavorResponse]
    total: int


class CategorizationTag(BaseModel):
    """Tag definition for document categorization."""
    name: str = Field(..., description="Tag identifier/name")
    description: str = Field(..., description="Description of what this tag represents")
    category: Optional[str] = Field(None, description="Optional category grouping for the tag")

    model_config = {"extra": "allow"}


class CategorizationContext(BaseModel):
    """Context data for document categorization.

    When provided with a flavor that has a categorization_prompt configured,
    the document will be analyzed and matched against the provided tags.
    """
    tags: List[CategorizationTag] = Field(
        ...,
        description="List of tags to match against the document. Each tag has a name and description."
    )
    input: Optional[str] = Field(
        None,
        description="Optional: Override the document to categorize. If not provided, uses the main output."
    )
    allow_new_tags: Optional[bool] = Field(
        False,
        description="If true, the LLM may suggest new tags not in the provided list"
    )

    model_config = {"extra": "allow"}


class ServiceExecuteRequest(BaseModel):
    """Request schema for service execution with flavor selection."""
    input: str = Field(..., min_length=1, description="Service input data")
    flavor_id: Optional[UUID] = Field(None, description="Specific flavor ID to use")
    flavor_name: Optional[str] = Field(None, description="Flavor name to resolve")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional execution metadata")
    context: Optional[CategorizationContext] = Field(
        None,
        description=(
            "Context data for document categorization. Requires a flavor with categorization_prompt configured. "
            "Provide 'tags' as a list of {name, description} objects to match against the processed document."
        )
    )


class ServiceExecuteResponse(BaseModel):
    """Response schema for service execution."""
    job_id: str
    status: str
    service_id: str
    service_name: str
    flavor_id: str
    flavor_name: str
    created_at: str
    estimated_completion_time: Optional[str] = None

    # Fallback tracking (context overflow)
    fallback_applied: bool = False
    original_flavor_id: Optional[str] = None
    original_flavor_name: Optional[str] = None
    fallback_reason: Optional[str] = None
    input_tokens: Optional[int] = None
    context_available: Optional[int] = None

    # Failover tracking (processing errors)
    failover_applied: bool = False
    failover_chain: List["FailoverStep"] = Field(default_factory=list)
    final_flavor_id: Optional[str] = None
    final_flavor_name: Optional[str] = None


class ExecutionErrorResponse(BaseModel):
    """Structured error response for execution failures."""
    detail: str
    error_code: str  # CONTEXT_EXCEEDED, CONTEXT_EXCEEDED_NO_FALLBACK, FLAVOR_INACTIVE, FALLBACK_FLAVOR_INACTIVE
    input_tokens: Optional[int] = None
    available_tokens: Optional[int] = None
    flavor_id: Optional[str] = None
    flavor_name: Optional[str] = None
    original_flavor_id: Optional[str] = None
    suggestion: Optional[str] = None


class FallbackAvailabilityResponse(BaseModel):
    """Response for fallback availability check."""
    fallback_available: bool
    fallback_flavor_id: Optional[str] = None
    fallback_flavor_name: Optional[str] = None
    reason: Optional[str] = None


class PromptValidationRequest(BaseModel):
    """Request for prompt placeholder validation endpoint."""
    processing_mode: Literal["single_pass", "iterative"]
    prompt_content: Optional[str] = None
    user_prompt_template_id: Optional[UUID] = None


class PromptValidationResponse(BaseModel):
    """Response for prompt placeholder validation endpoint."""
    valid: bool
    placeholder_count: int
    processing_mode: str
    required_placeholders: int
    error: Optional[str] = None


# =============================================================================
# Failover Chain Schemas
# =============================================================================

class FailoverStep(BaseModel):
    """Represents one step in the failover chain during execution."""
    from_flavor_id: str
    from_flavor_name: str
    to_flavor_id: str
    to_flavor_name: str
    reason: Literal["timeout", "rate_limit", "model_error", "content_filter"]
    error_message: Optional[str] = None
    attempt_number: int
    timestamp: datetime


class FailoverChainItem(BaseModel):
    """Single item in a failover chain."""
    id: str
    name: str
    service_id: str
    service_name: Optional[str] = None
    model_name: Optional[str] = None
    is_active: bool
    depth: int


class FailoverChainResponse(BaseModel):
    """Response for failover chain endpoint."""
    chain: List[FailoverChainItem]
    max_depth: int
    has_cycle: bool


class ValidateFailoverRequest(BaseModel):
    """Request for failover validation."""
    failover_flavor_id: UUID


class ValidateFailoverResponse(BaseModel):
    """Response for failover validation."""
    valid: bool
    error: Optional[str] = None
    chain_depth: int
    chain_preview: List[str]


# Resolve forward references for ServiceExecuteResponse
ServiceExecuteResponse.model_rebuild()
