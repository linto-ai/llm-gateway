"""initial_schema - LLM Gateway Complete Schema

Revision ID: 001
Revises:
Create Date: 2025-12-14 00:00:00.000000

This migration creates the complete database schema for LLM Gateway.
All tables are created with their final structure.

Schema includes:
- organizations: Multi-tenancy support
- service_types: Lookup table for service types
- prompt_types: Lookup table for prompt types
- providers: LLM API providers with encrypted credentials
- models: LLM model catalog with health monitoring
- prompts: Prompt storage with category/type classification
- services: Service definitions for LLM workflows
- service_flavors: Model-specific configurations with fallback support
- jobs: Job execution tracking with versioning
- flavor_usage: Usage analytics
- flavor_presets: Pre-configured flavor settings
- document_templates: DOCX template management with i18n and hierarchical scoping
- service_templates: Service blueprints

Note: organization_id and user_id in document_templates are VARCHAR(100) for
flexible integration with external identity systems (MongoDB ObjectIds, etc.)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ==========================================================================
    # Create trigger function for updated_at (used by multiple tables)
    # ==========================================================================
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # ==========================================================================
    # 1. organizations - Multi-tenancy support (for reference/optional use)
    # ==========================================================================
    op.create_table(
        'organizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(100), unique=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    )
    op.create_index('ix_organizations_name', 'organizations', ['name'])

    op.execute("""
        CREATE TRIGGER update_organizations_updated_at
            BEFORE UPDATE ON organizations
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)

    # ==========================================================================
    # 2. service_types - Lookup table for service types
    # ==========================================================================
    op.create_table(
        'service_types',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('code', sa.String(50), unique=True, nullable=False),
        sa.Column('name', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('description', postgresql.JSONB, server_default='{}'),
        sa.Column('is_system', sa.Boolean, server_default='false'),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('display_order', sa.Integer, server_default='0'),
        sa.Column('supports_reduce', sa.Boolean, server_default='false'),
        sa.Column('supports_chunking', sa.Boolean, server_default='false'),
        sa.Column('default_processing_mode', sa.String(20), server_default="'single_pass'"),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    )
    op.create_index('idx_service_types_code', 'service_types', ['code'])
    op.create_index('idx_service_types_active', 'service_types', ['is_active'])

    op.execute("""
        CREATE TRIGGER update_service_types_updated_at
            BEFORE UPDATE ON service_types
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)

    # Seed system service types
    op.execute("""
        INSERT INTO service_types (code, name, description, is_system, is_active, display_order, supports_reduce, supports_chunking, default_processing_mode)
        VALUES
            ('summary', '{"en": "Summary", "fr": "Resume"}'::jsonb, '{"en": "Summarize transcripts and documents", "fr": "Resumer des transcriptions et documents"}'::jsonb, true, true, 0, true, true, 'iterative'),
            ('translation', '{"en": "Translation", "fr": "Traduction"}'::jsonb, '{"en": "Translate documents between languages", "fr": "Traduire des documents entre langues"}'::jsonb, true, true, 1, false, true, 'iterative'),
            ('categorization', '{"en": "Categorization", "fr": "Categorisation"}'::jsonb, '{"en": "Classify documents into categories", "fr": "Classer des documents en categories"}'::jsonb, true, true, 2, false, false, 'single_pass'),
            ('diarization_correction', '{"en": "Diarization Correction", "fr": "Correction de diarisation"}'::jsonb, '{"en": "Fix speaker attribution errors in transcripts", "fr": "Corriger les erreurs d''attribution de locuteurs"}'::jsonb, true, true, 3, false, true, 'iterative'),
            ('speaker_correction', '{"en": "Speaker Correction", "fr": "Correction de locuteurs"}'::jsonb, '{"en": "Correct speaker labels in transcripts", "fr": "Corriger les etiquettes de locuteurs dans les transcriptions"}'::jsonb, true, true, 4, false, true, 'iterative'),
            ('generic', '{"en": "Generic", "fr": "Generique"}'::jsonb, '{"en": "Generic LLM service for custom use cases", "fr": "Service LLM generique pour cas d''usage personnalises"}'::jsonb, true, true, 7, true, true, 'single_pass')
    """)

    # ==========================================================================
    # 3. prompt_types - Lookup table for prompt types
    # ==========================================================================
    op.create_table(
        'prompt_types',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('code', sa.String(50), unique=True, nullable=False),
        sa.Column('name', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('description', postgresql.JSONB, server_default='{}'),
        sa.Column('is_system', sa.Boolean, server_default='false'),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('display_order', sa.Integer, server_default='0'),
        sa.Column('service_type_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('service_types.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    )
    op.create_index('idx_prompt_types_code', 'prompt_types', ['code'])
    op.create_index('idx_prompt_types_active', 'prompt_types', ['is_active'])
    op.create_index('idx_prompt_types_service_type', 'prompt_types', ['service_type_id'])

    op.execute("""
        CREATE TRIGGER update_prompt_types_updated_at
            BEFORE UPDATE ON prompt_types
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)

    # Seed system prompt types
    op.execute("""
        INSERT INTO prompt_types (code, name, description, is_system, is_active, display_order, service_type_id)
        SELECT
            'standard',
            '{"en": "Standard", "fr": "Standard"}'::jsonb,
            '{"en": "Standard processing prompt", "fr": "Prompt de traitement standard"}'::jsonb,
            true, true, 0,
            (SELECT id FROM service_types WHERE code = 'summary')
    """)
    op.execute("""
        INSERT INTO prompt_types (code, name, description, is_system, is_active, display_order, service_type_id)
        SELECT
            'reduce',
            '{"en": "Reduce", "fr": "Reduction"}'::jsonb,
            '{"en": "Reduction/consolidation prompt for multi-pass processing", "fr": "Prompt de reduction/consolidation pour le traitement multi-passe"}'::jsonb,
            true, true, 1,
            (SELECT id FROM service_types WHERE code = 'summary')
    """)
    op.execute("""
        INSERT INTO prompt_types (code, name, description, is_system, is_active, display_order, service_type_id)
        SELECT
            'field_extraction',
            '{"en": "Field Extraction", "fr": "Extraction de champs"}'::jsonb,
            '{"en": "Extract structured fields from documents", "fr": "Extraire des champs structures des documents"}'::jsonb,
            true, true, 2,
            (SELECT id FROM service_types WHERE code = 'summary')
    """)
    op.execute("""
        INSERT INTO prompt_types (code, name, description, is_system, is_active, display_order)
        VALUES
            ('categorization', '{"en": "Categorization", "fr": "Categorisation"}'::jsonb, '{"en": "Classify and tag content", "fr": "Classifier et etiqueter le contenu"}'::jsonb, true, true, 3)
    """)

    # ==========================================================================
    # 4. providers - LLM API providers with encrypted credentials
    # ==========================================================================
    op.create_table(
        'providers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('provider_type', sa.String(50), nullable=False),
        sa.Column('api_base_url', sa.Text, nullable=False),
        sa.Column('api_key_encrypted', sa.Text, nullable=False),
        sa.Column('security_level', sa.String(20), nullable=False),
        sa.Column('metadata', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.CheckConstraint("security_level IN ('secure', 'sensitive', 'insecure')", name='check_security_level'),
    )
    op.create_index('ix_providers_provider_type', 'providers', ['provider_type'])
    op.create_index('ix_providers_security_level', 'providers', ['security_level'])
    op.create_index('idx_providers_security', 'providers', ['security_level'])
    op.create_index('idx_providers_type', 'providers', ['provider_type'])

    op.execute("""
        CREATE TRIGGER update_providers_updated_at
            BEFORE UPDATE ON providers
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)

    # ==========================================================================
    # 5. models - LLM model catalog with technical specifications
    # ==========================================================================
    op.create_table(
        'models',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('provider_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('providers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('model_name', sa.String(200), nullable=False),
        sa.Column('model_identifier', sa.String(200), nullable=False),
        sa.Column('context_length', sa.Integer, nullable=False),
        sa.Column('max_generation_length', sa.Integer, nullable=False),
        sa.Column('tokenizer_class', sa.String(100), nullable=True),
        sa.Column('tokenizer_name', sa.String(200), nullable=True),
        sa.Column('is_active', sa.Boolean, default=True, nullable=False),
        # Health monitoring fields
        sa.Column('health_status', sa.String(20), nullable=False, default='unknown'),
        sa.Column('health_checked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('health_error', sa.Text, nullable=True),
        sa.Column('metadata', postgresql.JSONB, nullable=False, server_default='{}'),
        # Extended fields
        sa.Column('huggingface_repo', sa.String(500), nullable=True),
        sa.Column('security_level', sa.String(50), nullable=True),
        sa.Column('deployment_name', sa.String(200), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('best_use', sa.Text, nullable=True),
        sa.Column('usage_type', sa.String(50), nullable=True),
        sa.Column('system_prompt', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.UniqueConstraint('provider_id', 'model_identifier', name='uq_provider_model_identifier'),
        sa.CheckConstraint('context_length > 0', name='check_context_length'),
        sa.CheckConstraint('max_generation_length > 0', name='check_max_gen_length'),
        sa.CheckConstraint("health_status IN ('available', 'unavailable', 'unknown', 'error')", name='check_health_status'),
    )
    op.create_index('ix_models_provider_id', 'models', ['provider_id'])
    op.create_index('ix_models_is_active', 'models', ['is_active'])
    op.create_index('ix_models_health_status', 'models', ['health_status'])
    op.create_index('idx_models_provider', 'models', ['provider_id'])
    op.create_index('idx_models_active', 'models', ['is_active'])
    op.create_index('idx_models_health_status', 'models', ['health_status'])

    op.execute("""
        CREATE TRIGGER update_models_updated_at
            BEFORE UPDATE ON models
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)

    # ==========================================================================
    # 6. prompts - Prompt storage (replaces file-based prompts)
    #    Note: organization_id is VARCHAR(100), not UUID FK
    # ==========================================================================
    op.create_table(
        'prompts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('description', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('organization_id', sa.String(100), nullable=True),
        # Category and type fields
        sa.Column('prompt_category', sa.String(50), nullable=False),
        sa.Column('prompt_type_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('prompt_types.id', ondelete='SET NULL'), nullable=True),
        sa.Column('parent_template_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('prompts.id', ondelete='SET NULL'), nullable=True),
        # Service type affinity
        sa.Column('service_type', sa.String(50), nullable=False, comment='Service type affinity: summary, translation, categorization, etc.'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.UniqueConstraint('name', 'organization_id', name='uq_prompt_name_org'),
        sa.CheckConstraint("prompt_category IN ('system', 'user')", name='check_prompt_category'),
    )
    op.create_index('ix_prompts_organization_id', 'prompts', ['organization_id'])
    op.create_index('ix_prompts_prompt_category', 'prompts', ['prompt_category'])
    op.create_index('ix_prompts_prompt_type_id', 'prompts', ['prompt_type_id'])
    op.create_index('ix_prompts_service_type', 'prompts', ['service_type'])
    op.create_index('idx_prompts_org', 'prompts', ['organization_id'])
    op.create_index('idx_prompts_name', 'prompts', ['name'])
    op.create_index('idx_prompts_prompt_category', 'prompts', ['prompt_category'])
    op.create_index('idx_prompts_prompt_type', 'prompts', ['prompt_type_id'])
    op.create_index('idx_prompts_parent_template', 'prompts', ['parent_template_id'])
    op.create_index('idx_prompts_service_type', 'prompts', ['service_type'])

    op.execute("""
        CREATE TRIGGER update_prompts_updated_at
            BEFORE UPDATE ON prompts
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)

    # ==========================================================================
    # 7. service_templates - Pre-configured service blueprints
    # ==========================================================================
    op.create_table(
        'service_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('service_type', sa.String(50), nullable=False),
        sa.Column('description', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('is_public', sa.Boolean, nullable=False, default=True),
        sa.Column('default_config', postgresql.JSONB, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.CheckConstraint(
            "service_type IN ('summary', 'translation', 'categorization', 'diarization_correction', 'speaker_correction', 'generic')",
            name='check_template_service_type'
        ),
    )
    op.create_index('idx_templates_type', 'service_templates', ['service_type'])
    op.create_index('idx_templates_public', 'service_templates', ['is_public'])

    op.execute("""
        CREATE TRIGGER update_service_templates_updated_at
            BEFORE UPDATE ON service_templates
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)

    # ==========================================================================
    # 8. document_templates - Document generation templates with i18n and scoping
    #    Note: organization_id and user_id are VARCHAR(100) for external system compatibility
    # ==========================================================================
    op.create_table(
        'document_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        # i18n name fields
        sa.Column('name_fr', sa.String(255), nullable=False),
        sa.Column('name_en', sa.String(255), nullable=True),
        # i18n description fields
        sa.Column('description_fr', sa.Text, nullable=True),
        sa.Column('description_en', sa.Text, nullable=True),
        # Hierarchical scoping (VARCHAR for external system compatibility)
        sa.Column('organization_id', sa.String(100), nullable=True),
        sa.Column('user_id', sa.String(100), nullable=True),
        # File information
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('file_name', sa.String(255), nullable=False),
        sa.Column('file_size', sa.Integer, nullable=False),
        sa.Column('file_hash', sa.String(64), nullable=True),
        sa.Column('mime_type', sa.String(100), default='application/vnd.openxmlformats-officedocument.wordprocessingml.document', nullable=False),
        sa.Column('placeholders', postgresql.JSONB, nullable=True),
        sa.Column('is_default', sa.Boolean, default=False, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    )
    op.create_index('idx_templates_org_id', 'document_templates', ['organization_id'])
    op.create_index('idx_templates_user_id', 'document_templates', ['user_id'])
    op.create_index('idx_templates_scope', 'document_templates', ['organization_id', 'user_id'])
    op.create_index('idx_templates_file_hash', 'document_templates', ['file_hash'])

    # Add check constraint: user_id requires organization_id
    op.execute("""
        ALTER TABLE document_templates
        ADD CONSTRAINT check_user_requires_org
        CHECK ((user_id IS NULL) OR (organization_id IS NOT NULL))
    """)

    op.execute("""
        CREATE TRIGGER update_document_templates_updated_at
            BEFORE UPDATE ON document_templates
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)

    # ==========================================================================
    # 9. services - Service definitions for LLM-powered workflows
    #    Note: organization_id is VARCHAR(100), not UUID FK
    # ==========================================================================
    op.create_table(
        'services',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('route', sa.String(100), nullable=False),
        sa.Column('service_type', sa.String(50), nullable=False),
        sa.Column('description', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('organization_id', sa.String(100), nullable=True),
        sa.Column('is_active', sa.Boolean, default=True, nullable=False),
        sa.Column('metadata', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('service_category', sa.String(50), nullable=True, default='custom'),
        sa.Column('default_template_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('document_templates.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.UniqueConstraint('name', 'organization_id', name='uq_service_name_org'),
        sa.UniqueConstraint('route', 'organization_id', name='uq_service_route_org'),
    )
    op.create_index('ix_services_route', 'services', ['route'])
    op.create_index('ix_services_service_type', 'services', ['service_type'])
    op.create_index('ix_services_organization_id', 'services', ['organization_id'])
    op.create_index('ix_services_is_active', 'services', ['is_active'])
    op.create_index('idx_services_org', 'services', ['organization_id'])
    op.create_index('idx_services_type', 'services', ['service_type'])
    op.create_index('idx_services_active', 'services', ['is_active'])
    op.create_index('idx_services_route', 'services', ['route'])

    op.execute("""
        CREATE TRIGGER update_services_updated_at
            BEFORE UPDATE ON services
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)

    # ==========================================================================
    # 10. service_flavors - Model-specific configurations for services
    #     Includes failover chain support
    # ==========================================================================
    op.create_table(
        'service_flavors',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('service_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('services.id', ondelete='CASCADE'), nullable=False),
        sa.Column('model_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('models.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('temperature', sa.Float, nullable=False),
        sa.Column('top_p', sa.Float, nullable=False),
        sa.Column('is_default', sa.Boolean, nullable=False, default=False),
        # Advanced configuration
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, default=True),
        sa.Column('frequency_penalty', sa.Float, nullable=False, default=0.0),
        sa.Column('presence_penalty', sa.Float, nullable=False, default=0.0),
        sa.Column('stop_sequences', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('custom_params', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('estimated_cost_per_1k_tokens', sa.Float, nullable=True),
        sa.Column('max_concurrent_requests', sa.Integer, nullable=True),
        sa.Column('priority', sa.Integer, nullable=False, default=0),
        # Chunking/Resampling parameters
        sa.Column('create_new_turn_after', sa.Integer, nullable=True),
        sa.Column('summary_turns', sa.Integer, nullable=True),
        sa.Column('max_new_turns', sa.Integer, nullable=True),
        sa.Column('reduce_summary', sa.Boolean, default=False, nullable=False),
        sa.Column('consolidate_summary', sa.Boolean, default=False, nullable=False),
        sa.Column('output_type', sa.String(50), nullable=False),
        # Prompt references (template IDs)
        sa.Column('system_prompt_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('prompts.id', ondelete='SET NULL'), nullable=True),
        sa.Column('user_prompt_template_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('prompts.id', ondelete='SET NULL'), nullable=True),
        sa.Column('reduce_prompt_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('prompts.id', ondelete='SET NULL'), nullable=True),
        # Inline prompt content
        sa.Column('prompt_system_content', sa.Text, nullable=True),
        sa.Column('prompt_user_content', sa.Text, nullable=True),
        sa.Column('prompt_reduce_content', sa.Text, nullable=True),
        # Tokenizer override
        sa.Column('tokenizer_override', sa.String(200), nullable=True),
        # Processing mode configuration
        sa.Column('processing_mode', sa.String(20), nullable=False, server_default='iterative',
                  comment="Processing strategy: 'single_pass' or 'iterative'"),
        # Explicit fallback flavor reference
        sa.Column('fallback_flavor_id', postgresql.UUID(as_uuid=True), nullable=True),
        # Failover flavor reference (self-referencing FK, added separately)
        sa.Column('failover_flavor_id', postgresql.UUID(as_uuid=True), nullable=True),
        # Placeholder extraction
        sa.Column('placeholder_extraction_prompt_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('prompts.id', ondelete='SET NULL'), nullable=True),
        # Document categorization
        sa.Column('categorization_prompt_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('prompts.id', ondelete='SET NULL'), nullable=True),
        # Failover chain configuration
        sa.Column('failover_enabled', sa.Boolean, nullable=False, server_default='false',
                  comment='Enable automatic failover on processing errors'),
        sa.Column('failover_on_timeout', sa.Boolean, nullable=False, server_default='true',
                  comment='Failover when API timeout occurs'),
        sa.Column('failover_on_rate_limit', sa.Boolean, nullable=False, server_default='true',
                  comment='Failover when rate limit is exceeded (after retries)'),
        sa.Column('failover_on_model_error', sa.Boolean, nullable=False, server_default='true',
                  comment='Failover when model returns error (503, 404, etc.)'),
        sa.Column('failover_on_content_filter', sa.Boolean, nullable=False, server_default='false',
                  comment='Failover when content filter is triggered'),
        sa.Column('max_failover_depth', sa.Integer, nullable=False, server_default='3',
                  comment='Maximum depth of failover chain (prevents infinite loops)'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.UniqueConstraint('service_id', 'name', name='uq_service_flavor_name'),
        sa.CheckConstraint('temperature >= 0 AND temperature <= 2', name='check_temperature'),
        sa.CheckConstraint('top_p > 0 AND top_p <= 1', name='check_top_p'),
        sa.CheckConstraint("output_type IN ('text', 'markdown', 'json')", name='check_output_type'),
        sa.CheckConstraint('frequency_penalty >= 0 AND frequency_penalty <= 2', name='check_frequency_penalty'),
        sa.CheckConstraint('presence_penalty >= 0 AND presence_penalty <= 2', name='check_presence_penalty'),
        sa.CheckConstraint('priority >= 0 AND priority <= 9', name='check_priority'),
        sa.CheckConstraint("processing_mode IN ('single_pass', 'iterative')", name='check_processing_mode'),
        sa.CheckConstraint('max_failover_depth >= 1 AND max_failover_depth <= 10', name='check_max_failover_depth'),
    )
    # Add self-reference check constraints after table creation (using raw SQL)
    op.execute("""
        ALTER TABLE service_flavors
        ADD CONSTRAINT check_no_self_fallback
        CHECK (fallback_flavor_id IS NULL OR fallback_flavor_id != id)
    """)
    op.execute("""
        ALTER TABLE service_flavors
        ADD CONSTRAINT check_no_self_failover
        CHECK (failover_flavor_id IS NULL OR failover_flavor_id != id)
    """)
    op.create_index('ix_service_flavors_service_id', 'service_flavors', ['service_id'])
    op.create_index('ix_service_flavors_model_id', 'service_flavors', ['model_id'])
    op.create_index('ix_service_flavors_is_active', 'service_flavors', ['is_active'])
    op.create_index('ix_service_flavors_priority', 'service_flavors', ['priority'])
    op.create_index('idx_flavors_service', 'service_flavors', ['service_id'])
    op.create_index('idx_flavors_model', 'service_flavors', ['model_id'])
    op.create_index('idx_flavors_system_prompt', 'service_flavors', ['system_prompt_id'])
    op.create_index('idx_flavors_user_prompt', 'service_flavors', ['user_prompt_template_id'])
    op.create_index('idx_flavors_reduce_prompt', 'service_flavors', ['reduce_prompt_id'])
    op.create_index('idx_flavors_placeholder_prompt', 'service_flavors', ['placeholder_extraction_prompt_id'])
    op.create_index('idx_flavors_categorization_prompt', 'service_flavors', ['categorization_prompt_id'])
    op.create_index('idx_flavors_active', 'service_flavors', ['is_active'])
    op.create_index('idx_flavors_fallback', 'service_flavors', ['fallback_flavor_id'])
    op.create_index('idx_flavors_failover', 'service_flavors', ['failover_flavor_id'])

    # Self-referencing FK for fallback flavor
    op.create_foreign_key(
        'fk_service_flavors_fallback',
        'service_flavors',
        'service_flavors',
        ['fallback_flavor_id'],
        ['id'],
        ondelete='SET NULL'
    )
    # Self-referencing FK for failover flavor
    op.create_foreign_key(
        'fk_service_flavors_failover',
        'service_flavors',
        'service_flavors',
        ['failover_flavor_id'],
        ['id'],
        ondelete='SET NULL'
    )
    # Unique partial index for is_default (only one default per service)
    op.execute("""
        CREATE UNIQUE INDEX idx_service_flavors_default
        ON service_flavors (service_id)
        WHERE is_default = true;
    """)
    # Priority descending index
    op.execute("""
        CREATE INDEX idx_flavors_priority ON service_flavors (priority DESC);
    """)

    op.execute("""
        CREATE TRIGGER update_service_flavors_updated_at
            BEFORE UPDATE ON service_flavors
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)

    # ==========================================================================
    # 11. jobs - Job execution tracking
    #     Note: organization_id is VARCHAR(100), not UUID FK
    # ==========================================================================
    op.create_table(
        'jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('service_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('services.id', ondelete='CASCADE'), nullable=False),
        sa.Column('flavor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('service_flavors.id', ondelete='SET NULL'), nullable=True),
        sa.Column('organization_id', sa.String(100), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, default='queued'),
        sa.Column('celery_task_id', sa.String(255), unique=True, nullable=False),
        sa.Column('input_file_name', sa.String(255), nullable=True),
        sa.Column('input_content_preview', sa.Text, nullable=True),
        sa.Column('result', postgresql.JSONB, nullable=True),
        sa.Column('error', sa.Text, nullable=True),
        sa.Column('progress', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        # Version tracking for inline editing
        sa.Column('current_version', sa.Integer, nullable=False, default=1),
        sa.Column('last_edited_at', sa.DateTime(timezone=True), nullable=True),
        # Fallback tracking (when job switches flavor due to context overflow)
        sa.Column('fallback_applied', sa.String(5), nullable=False, server_default='false'),
        sa.Column('original_flavor_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('original_flavor_name', sa.String(50), nullable=True),
        sa.Column('fallback_reason', sa.Text, nullable=True),
        sa.Column('fallback_input_tokens', sa.Integer, nullable=True),
        sa.Column('fallback_context_available', sa.Integer, nullable=True),
        sa.CheckConstraint("status IN ('queued', 'started', 'processing', 'completed', 'failed')", name='valid_status'),
    )
    op.create_index('ix_jobs_service_id', 'jobs', ['service_id'])
    op.create_index('ix_jobs_flavor_id', 'jobs', ['flavor_id'])
    op.create_index('ix_jobs_organization_id', 'jobs', ['organization_id'])
    op.create_index('ix_jobs_status', 'jobs', ['status'])
    op.create_index('ix_jobs_created_at', 'jobs', ['created_at'])
    op.create_index('idx_jobs_organization_id', 'jobs', ['organization_id'])

    # ==========================================================================
    # 12. job_result_versions - Version history for job results
    # ==========================================================================
    op.create_table(
        'job_result_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('jobs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version_number', sa.Integer, nullable=False),
        sa.Column('diff', sa.Text, nullable=False),
        sa.Column('full_content', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.UniqueConstraint('job_id', 'version_number', name='unique_job_version'),
    )
    op.create_index('ix_job_result_versions_job_id', 'job_result_versions', ['job_id'])

    # ==========================================================================
    # 13. flavor_usage - Usage tracking for service flavor executions
    # ==========================================================================
    op.create_table(
        'flavor_usage',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('flavor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('service_flavors.id', ondelete='CASCADE'), nullable=False),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('jobs.id', ondelete='SET NULL'), nullable=True),
        sa.Column('input_tokens', sa.Integer, nullable=False),
        sa.Column('output_tokens', sa.Integer, nullable=False),
        sa.Column('total_tokens', sa.Integer, nullable=False),
        sa.Column('latency_ms', sa.Integer, nullable=False),
        sa.Column('estimated_cost', sa.Float, nullable=True),
        sa.Column('success', sa.Boolean, nullable=False, default=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('executed_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    )
    op.create_index('ix_flavor_usage_flavor_id', 'flavor_usage', ['flavor_id'])
    op.create_index('ix_flavor_usage_job_id', 'flavor_usage', ['job_id'])
    op.create_index('ix_flavor_usage_executed_at', 'flavor_usage', ['executed_at'])
    op.create_index('idx_flavor_usage_flavor', 'flavor_usage', ['flavor_id'])
    op.create_index('idx_flavor_usage_job', 'flavor_usage', ['job_id'])
    op.create_index('idx_flavor_usage_executed_at', 'flavor_usage', ['executed_at'])
    op.create_index('idx_flavor_usage_success', 'flavor_usage', ['success'])

    # ==========================================================================
    # 14. flavor_presets - Pre-configured flavor settings
    # ==========================================================================
    op.create_table(
        'flavor_presets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('service_type', sa.String(50), nullable=False, default='summary'),
        sa.Column('description_en', sa.Text, nullable=True),
        sa.Column('description_fr', sa.Text, nullable=True),
        sa.Column('is_system', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('config', postgresql.JSONB, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    )
    op.create_index('ix_flavor_presets_service_type', 'flavor_presets', ['service_type'])
    op.create_index('idx_flavor_presets_service_type', 'flavor_presets', ['service_type'])

    op.execute("""
        CREATE TRIGGER update_flavor_presets_updated_at
            BEFORE UPDATE ON flavor_presets
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)


def downgrade() -> None:
    # Drop triggers first
    op.execute("DROP TRIGGER IF EXISTS update_flavor_presets_updated_at ON flavor_presets;")
    op.execute("DROP TRIGGER IF EXISTS update_service_flavors_updated_at ON service_flavors;")
    op.execute("DROP TRIGGER IF EXISTS update_services_updated_at ON services;")
    op.execute("DROP TRIGGER IF EXISTS update_document_templates_updated_at ON document_templates;")
    op.execute("DROP TRIGGER IF EXISTS update_service_templates_updated_at ON service_templates;")
    op.execute("DROP TRIGGER IF EXISTS update_prompts_updated_at ON prompts;")
    op.execute("DROP TRIGGER IF EXISTS update_models_updated_at ON models;")
    op.execute("DROP TRIGGER IF EXISTS update_providers_updated_at ON providers;")
    op.execute("DROP TRIGGER IF EXISTS update_prompt_types_updated_at ON prompt_types;")
    op.execute("DROP TRIGGER IF EXISTS update_service_types_updated_at ON service_types;")
    op.execute("DROP TRIGGER IF EXISTS update_organizations_updated_at ON organizations;")

    # Drop trigger function
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column();")

    # Drop tables in reverse order of creation (respecting FK dependencies)
    op.drop_table('flavor_presets')
    op.drop_table('flavor_usage')
    op.drop_table('job_result_versions')
    op.drop_table('jobs')

    # Drop self-referencing FK before dropping service_flavors
    op.drop_constraint('fk_service_flavors_fallback', 'service_flavors', type_='foreignkey')
    op.drop_constraint('fk_service_flavors_failover', 'service_flavors', type_='foreignkey')
    op.drop_table('service_flavors')

    op.drop_table('services')
    op.drop_table('document_templates')
    op.drop_table('service_templates')
    op.drop_table('prompts')
    op.drop_table('models')
    op.drop_table('providers')
    op.drop_table('prompt_types')
    op.drop_table('service_types')
    op.drop_table('organizations')
