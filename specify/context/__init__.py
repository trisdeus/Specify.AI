"""
Context extraction module for Specify.AI.

This module provides entity extraction models and utilities for extracting
structured information from user prompts. It forms the foundation of the
Shared Context Pipeline that ensures consistency across all generated documents.

Key components:
- EntityType: Enumeration of supported entity types
- Entity: Base model for all extracted entities
- Specialized entity models for each entity type
- EntityContext: Container for all extracted entities

Example usage:
    >>> from specify.context import EntityContext, EntityType
    >>> from specify.context.models import UserPersonaEntity
    >>> 
    >>> # Create entities
    >>> persona = UserPersonaEntity(
    ...     id="user_persona_admin",
    ...     name="Admin User",
    ...     description="System administrator with full access",
    ...     source_text="Admin users should be able to manage all settings",
    ...     confidence=0.9,
    ...     role="Administrator",
    ...     characteristics=["Technical", "Full system access"],
    ...     goals=["Manage users", "Configure settings"]
    ... )
    >>> 
    >>> # Create context container
    >>> context = EntityContext(
    ...     source_prompt="Build an admin dashboard...",
    ...     user_personas=[persona]
    ... )
"""

from specify.context.models import (
    BusinessGoalEntity,
    DataEntity,
    Entity,
    EntityContext,
    EntityType,
    FeatureEntity,
    IntegrationEntity,
    NonFunctionalReqEntity,
    SuccessMetricEntity,
    TechnicalConstraintEntity,
    UserPersonaEntity,
)

from specify.context.llm_extractor import (
    LLMEntityExtractor,
    LLMExtractionError,
)

from specify.context.extractor import (
    ExtractionAnalysis,
    HybridContextExtractor,
)

from specify.context.normalizer import EntityNormalizer

from specify.context.registry import EntityRegistry

__all__ = [
    # Entity types
    "EntityType",
    "Entity",
    "UserPersonaEntity",
    "FeatureEntity",
    "TechnicalConstraintEntity",
    "SuccessMetricEntity",
    "NonFunctionalReqEntity",
    "BusinessGoalEntity",
    "IntegrationEntity",
    "DataEntity",
    "EntityContext",
    # LLM extractor
    "LLMEntityExtractor",
    "LLMExtractionError",
    # Hybrid extractor
    "HybridContextExtractor",
    "ExtractionAnalysis",
    # Normalizer
    "EntityNormalizer",
    # Registry
    "EntityRegistry",
]
