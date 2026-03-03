"""
Comprehensive tests for specify.context.models module.

This module contains unit tests for:
- EntityType enum values
- Entity base model
- All entity subclasses (UserPersonaEntity, FeatureEntity, etc.)
- EntityContext creation and manipulation
- to_prompt_section() output format
- to_json() and from_json() serialization
- get_summary() output
- get_entity_count() accuracy
- validate_completeness() with various scenarios
"""

import json
from datetime import datetime

import pytest

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


# =============================================================================
# A. EntityType Tests
# =============================================================================


class TestEntityType:
    """Tests for EntityType enum."""

    def test_entity_type_values(self) -> None:
        """Test that all expected entity type values exist."""
        assert EntityType.USER_PERSONA.value == "user_persona"
        assert EntityType.FEATURE.value == "feature"
        assert EntityType.TECHNICAL_CONSTRAINT.value == "technical_constraint"
        assert EntityType.SUCCESS_METRIC.value == "success_metric"
        assert EntityType.NON_FUNCTIONAL_REQ.value == "non_functional_req"
        assert EntityType.BUSINESS_GOAL.value == "business_goal"
        assert EntityType.INTEGRATION.value == "integration"
        assert EntityType.DATA_ENTITY.value == "data_entity"

    def test_entity_type_count(self) -> None:
        """Test that EntityType has exactly 8 values."""
        assert len(EntityType) == 8

    def test_entity_type_is_string_enum(self) -> None:
        """Test that EntityType inherits from str."""
        assert issubclass(EntityType, str)


# =============================================================================
# B. Entity Base Model Tests
# =============================================================================


class TestEntity:
    """Tests for Entity base model."""

    def test_entity_creation(self) -> None:
        """Test basic entity creation."""
        entity = Entity(
            id="test_entity",
            entity_type=EntityType.FEATURE,
            name="Test Feature",
            description="A test feature",
            source_text="This is a test feature",
            confidence=0.9,
        )
        assert entity.id == "test_entity"
        assert entity.entity_type == EntityType.FEATURE
        assert entity.name == "Test Feature"
        assert entity.confidence == 0.9
        assert entity.aliases == []

    def test_entity_with_aliases(self) -> None:
        """Test entity creation with aliases."""
        entity = Entity(
            id="test_entity",
            entity_type=EntityType.FEATURE,
            name="Test Feature",
            description="A test feature",
            source_text="This is a test feature",
            confidence=0.9,
            aliases=["test", "testing"],
        )
        assert entity.aliases == ["test", "testing"]

    def test_entity_confidence_validation_min(self) -> None:
        """Test that confidence below 0.0 raises error."""
        with pytest.raises(Exception):  # Pydantic validation error
            Entity(
                id="test",
                entity_type=EntityType.FEATURE,
                name="Test",
                description="Test",
                source_text="Test",
                confidence=-0.1,
            )

    def test_entity_confidence_validation_max(self) -> None:
        """Test that confidence above 1.0 raises error."""
        with pytest.raises(Exception):  # Pydantic validation error
            Entity(
                id="test",
                entity_type=EntityType.FEATURE,
                name="Test",
                description="Test",
                source_text="Test",
                confidence=1.1,
            )

    def test_entity_confidence_boundary_min(self) -> None:
        """Test that confidence of 0.0 is valid."""
        entity = Entity(
            id="test",
            entity_type=EntityType.FEATURE,
            name="Test",
            description="Test",
            source_text="Test",
            confidence=0.0,
        )
        assert entity.confidence == 0.0

    def test_entity_confidence_boundary_max(self) -> None:
        """Test that confidence of 1.0 is valid."""
        entity = Entity(
            id="test",
            entity_type=EntityType.FEATURE,
            name="Test",
            description="Test",
            source_text="Test",
            confidence=1.0,
        )
        assert entity.confidence == 1.0


# =============================================================================
# C. Entity Subclass Tests
# =============================================================================


class TestUserPersonaEntity:
    """Tests for UserPersonaEntity."""

    def test_user_persona_creation(self) -> None:
        """Test UserPersonaEntity creation."""
        persona = UserPersonaEntity(
            id="user_persona_admin",
            name="Administrator",
            description="System administrator with full access",
            source_text="Admin users should be able to manage all settings",
            confidence=0.9,
            role="Administrator",
            characteristics=["Technical", "Full system access", "Security conscious"],
            goals=["Manage users", "Configure system settings", "View reports"],
        )
        assert persona.entity_type == EntityType.USER_PERSONA
        assert persona.role == "Administrator"
        assert len(persona.characteristics) == 3
        assert len(persona.goals) == 3

    def test_user_persona_defaults(self) -> None:
        """Test UserPersonaEntity default values."""
        persona = UserPersonaEntity(
            id="user_persona_test",
            name="Test User",
            description="Test description",
            source_text="Test source",
            confidence=0.8,
        )
        assert persona.role is None
        assert persona.characteristics == []
        assert persona.goals == []


class TestFeatureEntity:
    """Tests for FeatureEntity."""

    def test_feature_creation(self) -> None:
        """Test FeatureEntity creation."""
        feature = FeatureEntity(
            id="feature_user_authentication",
            name="User Authentication",
            description="Secure login and registration system",
            source_text="The system must support user login and registration",
            confidence=0.95,
            priority="must",
            dependencies=["feature_password_reset"],
            user_stories=[
                "As a user, I want to register with email",
                "As a user, I want to log in securely",
            ],
        )
        assert feature.entity_type == EntityType.FEATURE
        assert feature.priority == "must"
        assert len(feature.dependencies) == 1
        assert len(feature.user_stories) == 2

    def test_feature_defaults(self) -> None:
        """Test FeatureEntity default values."""
        feature = FeatureEntity(
            id="feature_test",
            name="Test Feature",
            description="Test description",
            source_text="Test source",
            confidence=0.8,
        )
        assert feature.priority is None
        assert feature.dependencies == []
        assert feature.user_stories == []


class TestTechnicalConstraintEntity:
    """Tests for TechnicalConstraintEntity."""

    def test_technical_constraint_creation(self) -> None:
        """Test TechnicalConstraintEntity creation."""
        constraint = TechnicalConstraintEntity(
            id="technical_constraint_response_time",
            name="Response Time",
            description="Maximum allowed response time for API calls",
            source_text="API response time must be under 200ms",
            confidence=0.85,
            constraint_type="performance",
            value="200",
            unit="ms",
        )
        assert constraint.entity_type == EntityType.TECHNICAL_CONSTRAINT
        assert constraint.constraint_type == "performance"
        assert constraint.value == "200"
        assert constraint.unit == "ms"

    def test_technical_constraint_no_unit(self) -> None:
        """Test TechnicalConstraintEntity without unit."""
        constraint = TechnicalConstraintEntity(
            id="technical_constraint_test",
            name="Test Constraint",
            description="Test description",
            source_text="Test source",
            confidence=0.8,
            constraint_type="security",
            value="AES256",
        )
        assert constraint.unit is None


class TestSuccessMetricEntity:
    """Tests for SuccessMetricEntity."""

    def test_success_metric_creation(self) -> None:
        """Test SuccessMetricEntity creation."""
        metric = SuccessMetricEntity(
            id="success_metric_page_load",
            name="Page Load Time",
            description="Average time to load a page",
            source_text="Pages should load in under 2 seconds",
            confidence=0.8,
            metric_name="page_load_time",
            target_value="2",
            measurement_method="Average of 1000 page loads via RUM",
        )
        assert metric.entity_type == EntityType.SUCCESS_METRIC
        assert metric.metric_name == "page_load_time"
        assert metric.target_value == "2"
        assert metric.measurement_method == "Average of 1000 page loads via RUM"


class TestNonFunctionalReqEntity:
    """Tests for NonFunctionalReqEntity."""

    def test_non_functional_req_creation(self) -> None:
        """Test NonFunctionalReqEntity creation."""
        nfr = NonFunctionalReqEntity(
            id="non_functional_req_99_9_uptime",
            name="System Availability",
            description="System should be available 99.9% of the time",
            source_text="The system must have 99.9% uptime",
            confidence=0.9,
            requirement_type="availability",
            target="99.9",
            unit="%",
        )
        assert nfr.entity_type == EntityType.NON_FUNCTIONAL_REQ
        assert nfr.requirement_type == "availability"
        assert nfr.target == "99.9"
        assert nfr.unit == "%"


class TestBusinessGoalEntity:
    """Tests for BusinessGoalEntity."""

    def test_business_goal_creation(self) -> None:
        """Test BusinessGoalEntity creation."""
        goal = BusinessGoalEntity(
            id="business_goal_increase_retention",
            name="Increase Customer Retention",
            description="Improve customer retention rate by 20%",
            source_text="We want to increase customer retention by 20%",
            confidence=0.85,
            outcome="Customer retention rate improvement",
            target_value="20",
            unit="%",
        )
        assert goal.entity_type == EntityType.BUSINESS_GOAL
        assert goal.outcome == "Customer retention rate improvement"
        assert goal.target_value == "20"
        assert goal.unit == "%"


class TestIntegrationEntity:
    """Tests for IntegrationEntity."""

    def test_integration_creation(self) -> None:
        """Test IntegrationEntity creation."""
        integration = IntegrationEntity(
            id="integration_stripe",
            name="Stripe Payment",
            description="Payment processing via Stripe API",
            source_text="Integrate with Stripe for payments",
            confidence=0.95,
            integration_type="api",
            provider="Stripe",
            connection_details={"api_version": "2023-10-16"},
        )
        assert integration.entity_type == EntityType.INTEGRATION
        assert integration.integration_type == "api"
        assert integration.provider == "Stripe"
        assert integration.connection_details == {"api_version": "2023-10-16"}


class TestDataEntity:
    """Tests for DataEntity."""

    def test_data_entity_creation(self) -> None:
        """Test DataEntity creation."""
        data = DataEntity(
            id="data_entity_order",
            name="Order",
            description="Customer order containing items and totals",
            source_text="Users can place orders for products",
            confidence=0.9,
            attributes=["order_id", "customer_id", "items", "total", "status"],
            relationships=["belongs_to Customer", "contains OrderItems"],
        )
        assert data.entity_type == EntityType.DATA_ENTITY
        assert len(data.attributes) == 5
        assert len(data.relationships) == 2


# =============================================================================
# D. EntityContext Tests
# =============================================================================


class TestEntityContext:
    """Tests for EntityContext."""

    def test_entity_context_creation(self) -> None:
        """Test basic EntityContext creation."""
        context = EntityContext(source_prompt="Build an admin dashboard")
        assert context.source_prompt == "Build an admin dashboard"
        assert context.id is not None
        assert context.created_at is not None
        assert context.user_personas == []
        assert context.features == []
        assert context.technical_constraints == []
        assert context.success_metrics == []
        assert context.non_functional_reqs == []
        assert context.business_goals == []
        assert context.integrations == []
        assert context.data_entities == []

    def test_entity_context_with_entities(self) -> None:
        """Test EntityContext with entities."""
        persona = UserPersonaEntity(
            id="user_persona_admin",
            name="Administrator",
            description="Admin user",
            source_text="Admin users",
            confidence=0.9,
            role="Administrator",
        )
        feature = FeatureEntity(
            id="feature_auth",
            name="Authentication",
            description="User auth",
            source_text="User authentication",
            confidence=0.95,
        )
        context = EntityContext(
            source_prompt="Build admin dashboard",
            user_personas=[persona],
            features=[feature],
        )
        assert len(context.user_personas) == 1
        assert len(context.features) == 1

    def test_entity_context_product_info(self) -> None:
        """Test EntityContext with product info."""
        context = EntityContext(
            source_prompt="Test prompt",
            product_name="My App",
            product_type="Web Application",
            target_platform=["Web", "Mobile"],
        )
        assert context.product_name == "My App"
        assert context.product_type == "Web Application"
        assert context.target_platform == ["Web", "Mobile"]

    def test_entity_context_entity_registry(self) -> None:
        """Test EntityContext with entity registry."""
        context = EntityContext(
            source_prompt="Test prompt",
            entity_registry={"admin": "user_persona_admin", "auth": "feature_auth"},
        )
        assert context.entity_registry == {
            "admin": "user_persona_admin",
            "auth": "feature_auth",
        }

    def test_entity_context_with_all_entity_types(self) -> None:
        """Test EntityContext with all entity types."""
        persona = UserPersonaEntity(
            id="user_persona_admin",
            name="Admin",
            description="Admin",
            source_text="Admin",
            confidence=0.9,
        )
        feature = FeatureEntity(
            id="feature_test",
            name="Test",
            description="Test",
            source_text="Test",
            confidence=0.9,
        )
        constraint = TechnicalConstraintEntity(
            id="technical_constraint_perf",
            name="Performance",
            description="Perf",
            source_text="Perf",
            confidence=0.9,
            constraint_type="performance",
            value="100",
        )
        metric = SuccessMetricEntity(
            id="success_metric_test",
            name="Test",
            description="Test",
            source_text="Test",
            confidence=0.9,
            metric_name="test",
            target_value="10",
        )
        nfr = NonFunctionalReqEntity(
            id="nfr_test",
            name="Test",
            description="Test",
            source_text="Test",
            confidence=0.9,
            requirement_type="availability",
            target="99",
        )
        goal = BusinessGoalEntity(
            id="goal_test",
            name="Test",
            description="Test",
            source_text="Test",
            confidence=0.9,
            outcome="Test",
        )
        integration = IntegrationEntity(
            id="integration_test",
            name="Test",
            description="Test",
            source_text="Test",
            confidence=0.9,
            integration_type="api",
        )
        data_entity = DataEntity(
            id="data_entity_user",
            name="User",
            description="User data",
            source_text="User",
            confidence=0.9,
        )

        context = EntityContext(
            source_prompt="Full test",
            user_personas=[persona],
            features=[feature],
            technical_constraints=[constraint],
            success_metrics=[metric],
            non_functional_reqs=[nfr],
            business_goals=[goal],
            integrations=[integration],
            data_entities=[data_entity],
        )

        assert len(context.user_personas) == 1
        assert len(context.features) == 1
        assert len(context.technical_constraints) == 1
        assert len(context.success_metrics) == 1
        assert len(context.non_functional_reqs) == 1
        assert len(context.business_goals) == 1
        assert len(context.integrations) == 1
        assert len(context.data_entities) == 1


# =============================================================================
# E. Serialization Tests
# =============================================================================


class TestEntityContextSerialization:
    """Tests for EntityContext serialization (to_json/from_json)."""

    def test_entity_context_to_json(self) -> None:
        """Test EntityContext to JSON serialization."""
        context = EntityContext(
            source_prompt="Test prompt",
            product_name="Test App",
        )
        json_str = context.model_dump_json()
        assert "Test prompt" in json_str
        assert "Test App" in json_str

    def test_entity_context_from_json(self) -> None:
        """Test EntityContext from JSON deserialization."""
        original = EntityContext(
            source_prompt="Test prompt",
            product_name="Test App",
            product_type="Web App",
        )
        json_str = original.model_dump_json()
        restored = EntityContext.model_validate_json(json_str)
        assert restored.source_prompt == original.source_prompt
        assert restored.product_name == original.product_name
        assert restored.product_type == original.product_type

    def test_entity_context_roundtrip_with_entities(self) -> None:
        """Test EntityContext roundtrip with entities."""
        persona = UserPersonaEntity(
            id="user_persona_admin",
            name="Administrator",
            description="Admin user",
            source_text="Admin users",
            confidence=0.9,
            role="Administrator",
            characteristics=["Technical"],
            goals=["Manage system"],
        )
        original = EntityContext(
            source_prompt="Test prompt",
            user_personas=[persona],
        )
        json_str = original.model_dump_json()
        restored = EntityContext.model_validate_json(json_str)

        assert len(restored.user_personas) == 1
        assert restored.user_personas[0].name == "Administrator"
        assert restored.user_personas[0].role == "Administrator"
        assert restored.user_personas[0].characteristics == ["Technical"]


# =============================================================================
# F. Prompt Section Tests
# =============================================================================


class TestEntityContextToPromptSection:
    """Tests for EntityContext.to_prompt_section()."""

    def test_to_prompt_section_empty(self) -> None:
        """Test to_prompt_section with empty context."""
        context = EntityContext(source_prompt="Test")
        section = context.to_prompt_section()
        assert "## SHARED CONTEXT" in section
        assert "### User Personas" in section
        assert "No user personas specified" in section
        assert "### Features" in section
        assert "No features specified" in section

    def test_to_prompt_section_with_product_info(self) -> None:
        """Test to_prompt_section with product info."""
        context = EntityContext(
            source_prompt="Test",
            product_name="Test App",
            product_type="Web Application",
            target_platform=["Web", "Mobile"],
        )
        section = context.to_prompt_section()
        assert "**Product Name**: Test App" in section
        assert "**Product Type**: Web Application" in section
        assert "**Target Platforms**: Web, Mobile" in section

    def test_to_prompt_section_with_personas(self) -> None:
        """Test to_prompt_section with user personas."""
        persona = UserPersonaEntity(
            id="user_persona_admin",
            name="Administrator",
            description="Admin user",
            source_text="Admin",
            confidence=0.9,
            role="Administrator",
            characteristics=["Technical", "Security"],
            goals=["Manage users"],
        )
        context = EntityContext(
            source_prompt="Test",
            user_personas=[persona],
        )
        section = context.to_prompt_section()
        assert "### User Personas" in section
        assert "**Administrator**" in section
        assert "Administrator" in section
        assert "Technical" in section or "Characteristics" in section

    def test_to_prompt_section_with_features(self) -> None:
        """Test to_prompt_section with features."""
        feature = FeatureEntity(
            id="feature_auth",
            name="Authentication",
            description="User authentication",
            source_text="Auth",
            confidence=0.9,
            priority="must",
            user_stories=["Story 1", "Story 2"],
        )
        context = EntityContext(
            source_prompt="Test",
            features=[feature],
        )
        section = context.to_prompt_section()
        assert "### Features" in section
        assert "**Authentication**" in section
        assert "[must]" in section

    def test_to_prompt_section_all_sections_present(self) -> None:
        """Test that all expected sections are present."""
        context = EntityContext(source_prompt="Test")
        section = context.to_prompt_section()
        assert "### Product Overview" in section
        assert "### User Personas" in section
        assert "### Features" in section
        assert "### Technical Constraints" in section
        assert "### Success Metrics" in section
        assert "### Non-Functional Requirements" in section
        assert "### Business Goals" in section
        assert "### Integrations" in section
        assert "### Data Entities" in section


# =============================================================================
# G. Helper Method Tests
# =============================================================================


class TestEntityContextHelperMethods:
    """Tests for EntityContext helper methods."""

    def test_get_summary_empty(self) -> None:
        """Test get_summary with empty context."""
        context = EntityContext(source_prompt="Test")
        summary = context.get_summary()
        assert summary == "No context available"

    def test_get_summary_with_entities(self) -> None:
        """Test get_summary with entities."""
        persona = UserPersonaEntity(
            id="user_persona_admin",
            name="Admin",
            description="Admin",
            source_text="Admin",
            confidence=0.9,
        )
        feature = FeatureEntity(
            id="feature_auth",
            name="Authentication",
            description="Auth",
            source_text="Auth",
            confidence=0.9,
        )
        context = EntityContext(
            source_prompt="Test",
            product_name="Test App",
            user_personas=[persona],
            features=[feature],
        )
        summary = context.get_summary()
        assert "Test App" in summary
        assert "Authentication" in summary

    def test_get_entity_count_empty(self) -> None:
        """Test get_entity_count with empty context."""
        context = EntityContext(source_prompt="Test")
        counts = context.get_entity_count()
        # All counts should be 0
        assert all(count == 0 for count in counts.values())
        # Total should be 0
        assert sum(counts.values()) == 0

    def test_get_entity_count_with_entities(self) -> None:
        """Test get_entity_count with entities."""
        persona = UserPersonaEntity(
            id="user_persona_admin",
            name="Admin",
            description="Admin",
            source_text="Admin",
            confidence=0.9,
        )
        feature = FeatureEntity(
            id="feature_test",
            name="Test",
            description="Test",
            source_text="Test",
            confidence=0.9,
        )
        context = EntityContext(
            source_prompt="Test",
            user_personas=[persona],
            features=[feature],
        )
        counts = context.get_entity_count()
        assert counts[EntityType.USER_PERSONA] == 1
        assert counts[EntityType.FEATURE] == 1
        assert sum(counts.values()) == 2

    def test_validate_completeness_empty(self) -> None:
        """Test validate_completeness with empty context."""
        context = EntityContext(source_prompt="Test")
        result = context.validate_completeness()
        assert result["is_valid"] is False
        assert "user_persona" in result["missing_types"]
        assert "feature" in result["missing_types"]

    def test_validate_completeness_valid(self) -> None:
        """Test validate_completeness with valid context."""
        persona = UserPersonaEntity(
            id="user_persona_admin",
            name="Admin",
            description="Admin",
            source_text="Admin",
            confidence=0.9,
        )
        feature = FeatureEntity(
            id="feature_test",
            name="Test",
            description="Test",
            source_text="Test",
            confidence=0.9,
        )
        context = EntityContext(
            source_prompt="Test",
            product_name="Test App",
            user_personas=[persona],
            features=[feature],
        )
        result = context.validate_completeness()
        assert result["is_valid"] is True
        assert result["missing_types"] == []

    def test_get_all_entities(self) -> None:
        """Test get_all_entities method."""
        persona = UserPersonaEntity(
            id="user_persona_admin",
            name="Admin",
            description="Admin",
            source_text="Admin",
            confidence=0.9,
        )
        feature = FeatureEntity(
            id="feature_test",
            name="Test",
            description="Test",
            source_text="Test",
            confidence=0.9,
        )
        context = EntityContext(
            source_prompt="Test",
            user_personas=[persona],
            features=[feature],
        )
        all_entities = context.get_all_entities()
        assert len(all_entities) == 2

    def test_get_entities_by_type(self) -> None:
        """Test get_entities_by_type method."""
        persona = UserPersonaEntity(
            id="user_persona_admin",
            name="Admin",
            description="Admin",
            source_text="Admin",
            confidence=0.9,
        )
        context = EntityContext(
            source_prompt="Test",
            user_personas=[persona],
        )
        personas = context.get_entities_by_type(EntityType.USER_PERSONA)
        assert len(personas) == 1
        assert personas[0].name == "Admin"

    def test_to_json_from_json(self) -> None:
        """Test to_json and from_json methods."""
        persona = UserPersonaEntity(
            id="user_persona_admin",
            name="Admin",
            description="Admin",
            source_text="Admin",
            confidence=0.9,
        )
        original = EntityContext(
            source_prompt="Test",
            user_personas=[persona],
        )
        json_str = original.to_json()
        restored = EntityContext.from_json(json_str)
        assert restored.source_prompt == original.source_prompt
        assert len(restored.user_personas) == 1
