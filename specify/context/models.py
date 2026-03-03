"""
Pydantic models for context extraction in Specify.AI.

This module defines the data models for entities extracted from user prompts
during the document generation process. These models support the Shared Context
Pipeline that ensures consistency across all generated documents.

Entity Types:
- USER_PERSONA: Users, customers, administrators who interact with the system
- FEATURE: Functional capabilities and features of the product
- TECHNICAL_CONSTRAINT: Performance, security, budget constraints
- SUCCESS_METRIC: KPIs, targets, and measurement methods
- NON_FUNCTIONAL_REQ: Quality attributes like availability, scalability
- BUSINESS_GOAL: Business outcomes and objectives
- INTEGRATION: External systems, APIs, services to integrate with
- DATA_ENTITY: Core data objects (users, orders, products, etc.)
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class EntityType(str, Enum):
    """Enumeration of supported entity types for context extraction.

    Each entity type represents a category of information that can be
    extracted from user prompts to ensure consistent document generation.
    """

    USER_PERSONA = "user_persona"
    FEATURE = "feature"
    TECHNICAL_CONSTRAINT = "technical_constraint"
    SUCCESS_METRIC = "success_metric"
    NON_FUNCTIONAL_REQ = "non_functional_req"
    BUSINESS_GOAL = "business_goal"
    INTEGRATION = "integration"
    DATA_ENTITY = "data_entity"


class Entity(BaseModel):
    """Base model for all extracted entities.

    This is the foundational model that all specialized entity types extend.
    It contains the common fields that every entity must have, including
    unique identification, type classification, naming, and metadata.

    Attributes:
        id: Unique identifier for the entity, typically formatted as
            {entity_type}_{normalized_name}
        entity_type: The category of this entity
        name: Normalized, consistent name for the entity
        description: Human-readable description of the entity
        source_text: Original text from the user prompt where this entity
            was mentioned
        confidence: Extraction confidence score between 0.0 and 1.0
        aliases: Alternative names or variations found for this entity
    """

    id: str = Field(..., description="Unique identifier for the entity")
    entity_type: EntityType = Field(..., description="Type of entity")
    name: str = Field(..., description="Normalized name of the entity")
    description: str = Field(..., description="Detailed description of the entity")
    source_text: str = Field(..., description="Original text from the source prompt")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence score")
    aliases: list[str] = Field(
        default_factory=list,
        description="Alternative names found for this entity"
    )

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Ensure confidence is between 0.0 and 1.0."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v


class UserPersonaEntity(Entity):
    """Entity representing a user persona.

    A user persona describes a type of user who will interact with the system,
    including their role, characteristics, and goals. This information is
    crucial for generating user-centered documentation like BDD scenarios
    and feature requirements.

    Example:
        >>> persona = UserPersonaEntity(
        ...     id="user_persona_admin",
        ...     name="Admin User",
        ...     description="System administrator with full access",
        ...     source_text="Admin users should be able to manage all settings",
        ...     confidence=0.9,
        ...     role="Administrator",
        ...     characteristics=["Technical", "Full system access", "Security conscious"],
        ...     goals=["Manage users", "Configure system settings", "View reports"]
        ... )
    """

    entity_type: EntityType = EntityType.USER_PERSONA
    role: Optional[str] = Field(default=None, description="The role title of the persona")
    characteristics: list[str] = Field(
        default_factory=list,
        description="Key characteristics and attributes of this persona"
    )
    goals: list[str] = Field(
        default_factory=list,
        description="Goals and objectives this persona wants to achieve"
    )


class FeatureEntity(Entity):
    """Entity representing a product feature or capability.

    A feature describes a functional capability of the product that needs
    to be implemented. It includes priority, dependencies on other features,
    and associated user stories for agile documentation.

    Example:
        >>> feature = FeatureEntity(
        ...     id="feature_user_authentication",
        ...     name="User Authentication",
        ...     description="Secure login and registration system",
        ...     source_text="The system must support user login and registration",
        ...     confidence=0.95,
        ...     priority="must",
        ...     dependencies=["feature_password_reset"],
        ...     user_stories=[
        ...         "As a user, I want to register with email",
        ...         "As a user, I want to log in securely"
        ...     ]
        ... )
    """

    entity_type: EntityType = EntityType.FEATURE
    priority: Optional[str] = Field(
        default=None,
        description="Priority level: must, should, could, or wont"
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="IDs of features this feature depends on"
    )
    user_stories: list[str] = Field(
        default_factory=list,
        description="User stories associated with this feature"
    )


class TechnicalConstraintEntity(Entity):
    """Entity representing a technical constraint.

    A technical constraint describes a limitation or requirement that affects
    the technical implementation, such as performance targets, budget limits,
    or uptime requirements.

    Example:
        >>> constraint = TechnicalConstraintEntity(
        ...     id="technical_constraint_response_time",
        ...     name="Response Time",
        ...     description="Maximum allowed response time for API calls",
        ...     source_text="API response time must be under 200ms",
        ...     confidence=0.85,
        ...     constraint_type="performance",
        ...     value="200",
        ...     unit="ms"
        ... )
    """

    entity_type: EntityType = EntityType.TECHNICAL_CONSTRAINT
    constraint_type: str = Field(
        ...,
        description="Type of constraint: performance, security, budget, etc."
    )
    value: str = Field(..., description="The constraint value or threshold")
    unit: Optional[str] = Field(
        default=None,
        description="Unit of measurement (e.g., ms, seconds, $, %)"
    )


class SuccessMetricEntity(Entity):
    """Entity representing a success metric or KPI.

    A success metric defines a measurable target that indicates the success
    of the product or feature. It includes the metric name, target value,
    and how it should be measured.

    Example:
        >>> metric = SuccessMetricEntity(
        ...     id="success_metric_page_load",
        ...     name="Page Load Time",
        ...     description="Average time to load a page",
        ...     source_text="Pages should load in under 2 seconds",
        ...     confidence=0.8,
        ...     metric_name="page_load_time",
        ...     target_value="2",
        ...     measurement_method="Average of 1000 page loads via RUM"
        ... )
    """

    entity_type: EntityType = EntityType.SUCCESS_METRIC
    metric_name: str = Field(..., description="Technical name of the metric")
    target_value: str = Field(..., description="Target value to achieve")
    measurement_method: Optional[str] = Field(
        default=None,
        description="How this metric should be measured"
    )


class NonFunctionalReqEntity(Entity):
    """Entity representing a non-functional requirement.

    Non-functional requirements define quality attributes of the system
    such as availability, scalability, security, usability, and reliability.

    Example:
        >>> nfr = NonFunctionalReqEntity(
        ...     id="non_functional_req_99_9_uptime",
        ...     name="System Availability",
        ...     description="System should be available 99.9% of the time",
        ...     source_text="The system must have 99.9% uptime",
        ...     confidence=0.9,
        ...     requirement_type="availability",
        ...     target="99.9",
        ...     unit="%"
        ... )
    """

    entity_type: EntityType = EntityType.NON_FUNCTIONAL_REQ
    requirement_type: str = Field(
        ...,
        description="Type: availability, scalability, security, usability, etc."
    )
    target: str = Field(..., description="Target value or threshold")
    unit: Optional[str] = Field(default=None, description="Unit of measurement")


class BusinessGoalEntity(Entity):
    """Entity representing a business goal or objective.

    Business goals define the outcomes that the business wants to achieve
    with the product. They provide strategic context for decision-making
    during document generation.

    Example:
        >>> goal = BusinessGoalEntity(
        ...     id="business_goal_increase_retention",
        ...     name="Increase Customer Retention",
        ...     description="Improve customer retention rate by 20%",
        ...     source_text="We want to increase customer retention by 20%",
        ...     confidence=0.85,
        ...     outcome="Customer retention rate improvement",
        ...     target_value="20",
        ...     unit="%"
        ... )
    """

    entity_type: EntityType = EntityType.BUSINESS_GOAL
    outcome: str = Field(..., description="The business outcome being targeted")
    target_value: Optional[str] = Field(
        default=None,
        description="Target value for the outcome"
    )
    unit: Optional[str] = Field(default=None, description="Unit of measurement")


class IntegrationEntity(Entity):
    """Entity representing an external integration.

    Integration entities describe external systems, APIs, services,
    or platforms that the product needs to integrate with.

    Example:
        >>> integration = IntegrationEntity(
        ...     id="integration_stripe",
        ...     name="Stripe Payment",
        ...     description="Payment processing via Stripe API",
        ...     source_text="Integrate with Stripe for payments",
        ...     confidence=0.95,
        ...     integration_type="api",
        ...     provider="Stripe",
        ...     connection_details={"api_version": "2023-10-16"}
        ... )
    """

    entity_type: EntityType = EntityType.INTEGRATION
    integration_type: str = Field(
        ...,
        description="Type: api, service, platform, library, etc."
    )
    provider: Optional[str] = Field(
        default=None,
        description="Name of the integration provider"
    )
    connection_details: Optional[dict] = Field(
        default=None,
        description="Connection configuration details"
    )


class DataEntity(Entity):
    """Entity representing a data object or domain entity.

    Data entities represent the core data objects in the system, such as
    users, orders, products, or other domain-specific objects that are
    central to the application's functionality.

    Example:
        >>> data = DataEntity(
        ...     id="data_entity_order",
        ...     name="Order",
        ...     description="Customer order containing items and totals",
        ...     source_text="Users can place orders for products",
        ...     confidence=0.9,
        ...     attributes=["order_id", "customer_id", "items", "total", "status"],
        ...     relationships=["belongs_to Customer", "contains OrderItems"]
        ... )
    """

    entity_type: EntityType = EntityType.DATA_ENTITY
    attributes: list[str] = Field(
        default_factory=list,
        description="Key attributes or fields of this data entity"
    )
    relationships: list[str] = Field(
        default_factory=list,
        description="Relationships to other data entities"
    )


class EntityContext(BaseModel):
    """Container for all extracted entities with metadata.

    EntityContext serves as the main container that holds all entities
    extracted from a user prompt. It provides organized access to entities
    by type and includes metadata about the extraction process.

    The context can be converted to a prompt section for inclusion in
    generator prompts, ensuring all document generators have access to
    the same consistent context.

    Example:
        >>> context = EntityContext(
        ...     source_prompt="Build an admin dashboard with user management...",
        ...     user_personas=[persona],
        ...     features=[feature],
        ...     technical_constraints=[constraint],
        ...     success_metrics=[metric]
        ... )
        >>> prompt_section = context.to_prompt_section()
    """

    # Metadata
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this context"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when context was created"
    )
    source_prompt: str = Field(..., description="Original user prompt")

    # Extracted Entities
    user_personas: list[UserPersonaEntity] = Field(
        default_factory=list,
        description="Extracted user personas"
    )
    features: list[FeatureEntity] = Field(
        default_factory=list,
        description="Extracted features"
    )
    technical_constraints: list[TechnicalConstraintEntity] = Field(
        default_factory=list,
        description="Extracted technical constraints"
    )
    success_metrics: list[SuccessMetricEntity] = Field(
        default_factory=list,
        description="Extracted success metrics"
    )
    non_functional_reqs: list[NonFunctionalReqEntity] = Field(
        default_factory=list,
        description="Extracted non-functional requirements"
    )
    business_goals: list[BusinessGoalEntity] = Field(
        default_factory=list,
        description="Extracted business goals"
    )
    integrations: list[IntegrationEntity] = Field(
        default_factory=list,
        description="Extracted integrations"
    )
    data_entities: list[DataEntity] = Field(
        default_factory=list,
        description="Extracted data entities"
    )

    # Derived Context
    product_name: Optional[str] = Field(
        default=None,
        description="Name of the product being built"
    )
    product_type: Optional[str] = Field(
        default=None,
        description="Type of product: web app, mobile app, API, etc."
    )
    target_platform: list[str] = Field(
        default_factory=list,
        description="Target platforms for deployment"
    )

    # Normalization Metadata
    entity_registry: dict[str, str] = Field(
        default_factory=dict,
        description="Maps original text to normalized entity IDs"
    )

    def to_prompt_section(self) -> str:
        """Generate a markdown section for inclusion in generator prompts.

        This method creates a formatted markdown section that can be appended
        to generator prompts, ensuring all document generators see the same
        consistent context extracted from the user prompt.

        Returns:
            Formatted markdown string with all extracted context
        """
        sections = [
            "## SHARED CONTEXT",
            "",
            "The following context has been extracted from your prompt and should be used consistently across all documents.",
            "",
            "### Product Overview",
            f"- **Product Name**: {self.product_name or 'Not specified'}",
            f"- **Product Type**: {self.product_type or 'Not specified'}",
            f"- **Target Platforms**: {', '.join(self.target_platform) or 'Not specified'}",
            "",
            "### User Personas",
            self._format_user_personas(),
            "",
            "### Features",
            self._format_features(),
            "",
            "### Technical Constraints",
            self._format_technical_constraints(),
            "",
            "### Success Metrics",
            self._format_success_metrics(),
            "",
            "### Non-Functional Requirements",
            self._format_non_functional_reqs(),
            "",
            "### Business Goals",
            self._format_business_goals(),
            "",
            "### Integrations",
            self._format_integrations(),
            "",
            "### Data Entities",
            self._format_data_entities(),
            "",
            "---",
            "*Use these normalized entity names consistently throughout your document.*",
        ]
        return "\n".join(sections)

    def _format_user_personas(self) -> str:
        """Format user personas for the prompt section."""
        if not self.user_personas:
            return "No user personas specified."
        lines = []
        for persona in self.user_personas:
            lines.append(f"- **{persona.name}** ({persona.role or 'User'})")
            if persona.characteristics:
                lines.append(f"  - Characteristics: {', '.join(persona.characteristics)}")
            if persona.goals:
                lines.append(f"  - Goals: {', '.join(persona.goals)}")
        return "\n".join(lines)

    def _format_features(self) -> str:
        """Format features for the prompt section."""
        if not self.features:
            return "No features specified."
        lines = []
        for feature in self.features:
            priority_str = f" [{feature.priority}]" if feature.priority else ""
            lines.append(f"- **{feature.name}**{priority_str}")
            if feature.description:
                lines.append(f"  - {feature.description}")
            if feature.user_stories:
                lines.append(f"  - User Stories: {len(feature.user_stories)} stories")
        return "\n".join(lines)

    def _format_technical_constraints(self) -> str:
        """Format technical constraints for the prompt section."""
        if not self.technical_constraints:
            return "No technical constraints specified."
        lines = []
        for constraint in self.technical_constraints:
            unit_str = f" {constraint.unit}" if constraint.unit else ""
            lines.append(f"- **{constraint.name}**: {constraint.value}{unit_str} ({constraint.constraint_type})")
        return "\n".join(lines)

    def _format_success_metrics(self) -> str:
        """Format success metrics for the prompt section."""
        if not self.success_metrics:
            return "No success metrics specified."
        lines = []
        for metric in self.success_metrics:
            lines.append(f"- **{metric.name}**: Target {metric.target_value}")
            if metric.measurement_method:
                lines.append(f"  - Measurement: {metric.measurement_method}")
        return "\n".join(lines)

    def _format_non_functional_reqs(self) -> str:
        """Format non-functional requirements for the prompt section."""
        if not self.non_functional_reqs:
            return "No non-functional requirements specified."
        lines = []
        for req in self.non_functional_reqs:
            unit_str = f" {req.unit}" if req.unit else ""
            lines.append(f"- **{req.name}**: {req.target}{unit_str} ({req.requirement_type})")
        return "\n".join(lines)

    def _format_business_goals(self) -> str:
        """Format business goals for the prompt section."""
        if not self.business_goals:
            return "No business goals specified."
        lines = []
        for goal in self.business_goals:
            lines.append(f"- **{goal.name}**: {goal.outcome}")
            if goal.target_value:
                unit_str = f" {goal.unit}" if goal.unit else ""
                lines.append(f"  - Target: {goal.target_value}{unit_str}")
        return "\n".join(lines)

    def _format_integrations(self) -> str:
        """Format integrations for the prompt section."""
        if not self.integrations:
            return "No integrations specified."
        lines = []
        for integration in self.integrations:
            provider_str = f" ({integration.provider})" if integration.provider else ""
            lines.append(f"- **{integration.name}**{provider_str}: {integration.integration_type}")
        return "\n".join(lines)

    def _format_data_entities(self) -> str:
        """Format data entities for the prompt section."""
        if not self.data_entities:
            return "No data entities specified."
        lines = []
        for entity in self.data_entities:
            lines.append(f"- **{entity.name}**")
            if entity.attributes:
                lines.append(f"  - Attributes: {', '.join(entity.attributes)}")
            if entity.relationships:
                lines.append(f"  - Relationships: {', '.join(entity.relationships)}")
        return "\n".join(lines)

    def get_entities_by_type(self, entity_type: EntityType) -> list[Entity]:
        """Get all entities of a specific type.

        Args:
            entity_type: The type of entities to retrieve

        Returns:
            List of entities matching the specified type
        """
        entities_map = {
            EntityType.USER_PERSONA: self.user_personas,
            EntityType.FEATURE: self.features,
            EntityType.TECHNICAL_CONSTRAINT: self.technical_constraints,
            EntityType.SUCCESS_METRIC: self.success_metrics,
            EntityType.NON_FUNCTIONAL_REQ: self.non_functional_reqs,
            EntityType.BUSINESS_GOAL: self.business_goals,
            EntityType.INTEGRATION: self.integrations,
            EntityType.DATA_ENTITY: self.data_entities,
        }
        return entities_map.get(entity_type, [])

    def get_all_entities(self) -> list[Entity]:
        """Get all extracted entities regardless of type.

        Returns:
            List of all entities in the context
        """
        all_entities: list[Entity] = []
        all_entities.extend(self.user_personas)
        all_entities.extend(self.features)
        all_entities.extend(self.technical_constraints)
        all_entities.extend(self.success_metrics)
        all_entities.extend(self.non_functional_reqs)
        all_entities.extend(self.business_goals)
        all_entities.extend(self.integrations)
        all_entities.extend(self.data_entities)
        return all_entities

    def to_json(self) -> str:
        """Export the context as a JSON string for serialization.

        This method converts the entire EntityContext to a JSON string,
        making it suitable for storage, transmission, or caching.

        Returns:
            JSON string representation of the context
        """
        return self.model_dump_json(indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> EntityContext:
        """Create an EntityContext from a JSON string.

        This method deserializes a JSON string back into an EntityContext
        instance, enabling restoration of cached or stored contexts.

        Args:
            json_str: JSON string to deserialize

        Returns:
            EntityContext instance
        """
        return cls.model_validate_json(json_str)

    def get_summary(self) -> str:
        """Generate a brief text summary of the context.

        Creates a concise summary (1-2 sentences per entity type) suitable
        for quick overview or logging purposes.

        Returns:
            Formatted summary string
        """
        parts = []

        # Product overview
        if self.product_name:
            parts.append(f"Product: {self.product_name}")
        if self.product_type:
            parts.append(f"Type: {self.product_type}")

        # Entity counts
        entity_counts = self.get_entity_count()
        counts_summary = [
            f"{count} {entity_type.value.replace('_', ' ')}(s)"
            for entity_type, count in entity_counts.items()
            if count > 0
        ]
        if counts_summary:
            parts.append(", ".join(counts_summary))

        # Key features summary
        if self.features:
            feature_names = [f.name for f in self.features[:3]]
            features_str = ", ".join(feature_names)
            if len(self.features) > 3:
                features_str += f" and {len(self.features) - 3} more"
            parts.append(f"Features: {features_str}")

        # Key integrations
        if self.integrations:
            integration_names = [i.name for i in self.integrations]
            parts.append(f"Integrations: {', '.join(integration_names)}")

        return " | ".join(parts) if parts else "No context available"

    def get_entity_count(self) -> dict[EntityType, int]:
        """Get the count of entities grouped by type.

        Returns:
            Dictionary mapping entity types to their counts
        """
        return {
            EntityType.USER_PERSONA: len(self.user_personas),
            EntityType.FEATURE: len(self.features),
            EntityType.TECHNICAL_CONSTRAINT: len(self.technical_constraints),
            EntityType.SUCCESS_METRIC: len(self.success_metrics),
            EntityType.NON_FUNCTIONAL_REQ: len(self.non_functional_reqs),
            EntityType.BUSINESS_GOAL: len(self.business_goals),
            EntityType.INTEGRATION: len(self.integrations),
            EntityType.DATA_ENTITY: len(self.data_entities),
        }

    def validate_completeness(self) -> dict[str, bool | list[str]]:
        """Validate that minimum required entities exist.

        Checks whether the context contains sufficient information for
        document generation. Returns a validation report with status
        and any missing required entity types.

        Returns:
            Dictionary with validation results:
                - 'is_valid': bool indicating if context is complete
                - 'missing_types': list of missing required entity types
                - 'warnings': list of warning messages
        """
        warnings: list[str] = []
        missing_types: list[str] = []

        # Required entity types for basic context
        required_types = {
            EntityType.FEATURE: self.features,
            EntityType.USER_PERSONA: self.user_personas,
        }

        for entity_type, entities in required_types.items():
            if not entities:
                missing_types.append(entity_type.value)
                warnings.append(f"Missing required entity type: {entity_type.value}")

        # Check for product information
        if not self.product_name:
            warnings.append("Product name not specified")

        # Optional but recommended checks
        if not self.data_entities and self.features:
            warnings.append("No data entities defined despite features being specified")

        if not self.business_goals and self.features:
            warnings.append("No business goals defined despite features being specified")

        if not self.technical_constraints and self.features:
            warnings.append("No technical constraints defined despite features being specified")

        return {
            "is_valid": len(missing_types) == 0,
            "missing_types": missing_types,
            "warnings": warnings,
        }
