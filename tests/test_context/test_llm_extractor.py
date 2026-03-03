"""
Comprehensive tests for specify.context.llm_extractor module.

This module contains unit tests for:
- LLMEntityExtractor initialization
- Mock provider responses for testing
- JSON response parsing
- Markdown code block handling
- Error handling for malformed responses
- Entity extraction from mock LLM output
"""

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from specify.context.llm_extractor import LLMEntityExtractor, LLMExtractionError
from specify.context.models import (
    EntityContext,
    EntityType,
    UserPersonaEntity,
)
from specify.providers.base import BaseProvider, ProviderConfig


# Create a mock provider for testing
class MockProvider(BaseProvider):
    """Mock provider for testing."""

    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config)
        self._mock_response: str = ""

    def generate(self, prompt: str, rules: str | None = None) -> str:
        return self._mock_response

    def stream(self, prompt: str, rules: str | None = None):
        yield self._mock_response

    def validate_connection(self) -> bool:
        return True


# =============================================================================
# A. Initialization Tests
# =============================================================================


class TestLLMEntityExtractorInit:
    """Tests for LLMEntityExtractor initialization."""

    def test_extractor_initialization(self) -> None:
        """Test that extractor initializes correctly."""
        config = ProviderConfig(model="test-model")
        provider = MockProvider(config)
        extractor = LLMEntityExtractor(provider)
        assert extractor is not None

    def test_extractor_has_provider(self) -> None:
        """Test that extractor has provider."""
        config = ProviderConfig(model="test-model")
        provider = MockProvider(config)
        extractor = LLMEntityExtractor(provider)
        assert extractor._provider is provider


# =============================================================================
# B. JSON Response Parsing Tests
# =============================================================================


class TestJSONResponseParsing:
    """Tests for JSON response parsing."""

    def test_parse_valid_json(self) -> None:
        """Test parsing valid JSON response."""
        config = ProviderConfig(model="test-model")
        provider = MockProvider(config)
        provider._mock_response = json.dumps({
            "user_personas": [
                {
                    "name": "Administrator",
                    "role": "Admin",
                    "description": "System admin",
                    "source_text": "Admin users",
                    "confidence": "high",
                }
            ],
            "features": [],
            "technical_constraints": [],
            "success_metrics": [],
            "business_goals": [],
            "integrations": [],
            "data_entities": [],
        })

        extractor = LLMEntityExtractor(provider)
        context = extractor.extract("Test prompt", missing_types=["user_persona"])

        assert len(context.user_personas) == 1
        assert context.user_personas[0].name == "Administrator"

    def test_parse_json_with_features(self) -> None:
        """Test parsing JSON with features."""
        config = ProviderConfig(model="test-model")
        provider = MockProvider(config)
        provider._mock_response = json.dumps({
            "user_personas": [],
            "features": [
                {
                    "name": "User Authentication",
                    "description": "Login system",
                    "source_text": "Auth",
                    "confidence": "high",
                    "priority": "must",
                }
            ],
            "technical_constraints": [],
            "success_metrics": [],
            "business_goals": [],
            "integrations": [],
            "data_entities": [],
        })

        extractor = LLMEntityExtractor(provider)
        context = extractor.extract("Test prompt", missing_types=["feature"])

        assert len(context.features) == 1
        assert context.features[0].name == "User Authentication"


# =============================================================================
# C. Markdown Code Block Handling Tests
# =============================================================================


class TestMarkdownCodeBlockHandling:
    """Tests for markdown code block handling."""

    def test_parse_json_in_code_block(self) -> None:
        """Test parsing JSON inside markdown code block."""
        config = ProviderConfig(model="test-model")
        provider = MockProvider(config)
        provider._mock_response = """```json
{
    "user_personas": [
        {
            "name": "Developer",
            "role": "Dev",
            "description": "Developer user",
            "source_text": "Dev users",
            "confidence": "high"
        }
    ],
    "features": [],
    "technical_constraints": [],
    "success_metrics": [],
    "business_goals": [],
    "integrations": [],
    "data_entities": []
}
```"""

        extractor = LLMEntityExtractor(provider)
        context = extractor.extract("Test prompt", missing_types=["user_persona"])

        assert len(context.user_personas) == 1
        assert context.user_personas[0].name == "Developer"

    def test_parse_json_without_code_block(self) -> None:
        """Test parsing JSON without code block."""
        config = ProviderConfig(model="test-model")
        provider = MockProvider(config)
        # Provide just the JSON part since the parser expects clean JSON
        provider._mock_response = json.dumps({
            "user_personas": [
                {
                    "name": "Manager",
                    "role": "Manager",
                    "description": "Project manager",
                    "source_text": "Managers",
                    "confidence": "medium"
                }
            ],
            "features": [],
            "technical_constraints": [],
            "success_metrics": [],
            "business_goals": [],
            "integrations": [],
            "data_entities": [],
        })

        extractor = LLMEntityExtractor(provider)
        context = extractor.extract("Test prompt", missing_types=["user_persona"])

        assert len(context.user_personas) == 1
        assert context.user_personas[0].name == "Manager"


# =============================================================================
# D. Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Tests for error handling."""

    def test_parse_invalid_json(self) -> None:
        """Test handling of invalid JSON."""
        config = ProviderConfig(model="test-model")
        provider = MockProvider(config)
        provider._mock_response = "This is not valid JSON"

        extractor = LLMEntityExtractor(provider)
        with pytest.raises(LLMExtractionError):
            extractor.extract("Test prompt", missing_types=["user_persona"])

    def test_empty_response(self) -> None:
        """Test handling of empty response."""
        config = ProviderConfig(model="test-model")
        provider = MockProvider(config)
        provider._mock_response = ""

        extractor = LLMEntityExtractor(provider)
        with pytest.raises(LLMExtractionError):
            extractor.extract("Test prompt", missing_types=["user_persona"])

    def test_empty_prompt(self) -> None:
        """Test handling of empty prompt."""
        config = ProviderConfig(model="test-model")
        provider = MockProvider(config)

        extractor = LLMEntityExtractor(provider)
        context = extractor.extract("", missing_types=["user_persona"])
        assert context.source_prompt == ""

    def test_whitespace_only_prompt(self) -> None:
        """Test handling of whitespace-only prompt."""
        config = ProviderConfig(model="test-model")
        provider = MockProvider(config)

        extractor = LLMEntityExtractor(provider)
        context = extractor.extract("   ", missing_types=["user_persona"])
        assert context.source_prompt == "   "

    def test_malformed_entity_data(self) -> None:
        """Test handling of malformed entity data."""
        config = ProviderConfig(model="test-model")
        provider = MockProvider(config)
        provider._mock_response = json.dumps({
            "user_personas": [
                {
                    # Missing required 'name' field
                    "role": "Admin",
                    "description": "Admin user",
                }
            ],
            "features": [],
            "technical_constraints": [],
            "success_metrics": [],
            "business_goals": [],
            "integrations": [],
            "data_entities": [],
        })

        extractor = LLMEntityExtractor(provider)
        context = extractor.extract("Test prompt", missing_types=["user_persona"])
        # Should skip invalid entity and return empty
        assert len(context.user_personas) == 0


# =============================================================================
# E. Entity Extraction Tests
# =============================================================================


class TestEntityExtraction:
    """Tests for entity extraction from LLM output."""

    def test_extract_user_personas(self) -> None:
        """Test extraction of user personas."""
        config = ProviderConfig(model="test-model")
        provider = MockProvider(config)
        provider._mock_response = json.dumps({
            "user_personas": [
                {
                    "name": "Admin User",
                    "role": "Administrator",
                    "description": "System administrator",
                    "source_text": "Admin users manage the system",
                    "confidence": "high",
                    "characteristics": ["Technical", "Security conscious"],
                    "goals": ["Manage users", "Configure settings"],
                },
                {
                    "name": "Regular User",
                    "role": "User",
                    "description": "Standard user",
                    "source_text": "Regular users access the app",
                    "confidence": "medium",
                }
            ],
            "features": [],
            "technical_constraints": [],
            "success_metrics": [],
            "business_goals": [],
            "integrations": [],
            "data_entities": [],
        })

        extractor = LLMEntityExtractor(provider)
        context = extractor.extract("Test prompt", missing_types=["user_persona"])

        assert len(context.user_personas) == 2
        assert context.user_personas[0].name == "Admin User"
        assert context.user_personas[0].role == "Administrator"
        assert context.user_personas[0].characteristics == ["Technical", "Security conscious"]
        assert context.user_personas[1].name == "Regular User"

    def test_extract_features(self) -> None:
        """Test extraction of features."""
        config = ProviderConfig(model="test-model")
        provider = MockProvider(config)
        provider._mock_response = json.dumps({
            "user_personas": [],
            "features": [
                {
                    "name": "User Authentication",
                    "description": "Login and registration",
                    "source_text": "User auth",
                    "confidence": "high",
                    "priority": "must",
                    "dependencies": ["feature_password_reset"],
                }
            ],
            "technical_constraints": [],
            "success_metrics": [],
            "business_goals": [],
            "integrations": [],
            "data_entities": [],
        })

        extractor = LLMEntityExtractor(provider)
        context = extractor.extract("Test prompt", missing_types=["feature"])

        assert len(context.features) == 1
        assert context.features[0].name == "User Authentication"
        assert context.features[0].priority == "must"
        assert context.features[0].dependencies == ["feature_password_reset"]

    def test_extract_technical_constraints(self) -> None:
        """Test extraction of technical constraints."""
        config = ProviderConfig(model="test-model")
        provider = MockProvider(config)
        provider._mock_response = json.dumps({
            "user_personas": [],
            "features": [],
            "technical_constraints": [
                {
                    "name": "Response Time",
                    "constraint_type": "performance",
                    "value": "200",
                    "unit": "ms",
                    "source_text": "Response time under 200ms",
                    "confidence": "high",
                }
            ],
            "success_metrics": [],
            "business_goals": [],
            "integrations": [],
            "data_entities": [],
        })

        extractor = LLMEntityExtractor(provider)
        context = extractor.extract("Test prompt", missing_types=["technical_constraint"])

        assert len(context.technical_constraints) == 1
        assert context.technical_constraints[0].value == "200"
        assert context.technical_constraints[0].unit == "ms"

    def test_extract_success_metrics(self) -> None:
        """Test extraction of success metrics."""
        config = ProviderConfig(model="test-model")
        provider = MockProvider(config)
        provider._mock_response = json.dumps({
            "user_personas": [],
            "features": [],
            "technical_constraints": [],
            "success_metrics": [
                {
                    "name": "Page Load Time",
                    "metric_name": "page_load_time",
                    "target_value": "2",
                    "measurement_method": "RUM",
                    "source_text": "Pages load in 2 seconds",
                    "confidence": "medium",
                }
            ],
            "business_goals": [],
            "integrations": [],
            "data_entities": [],
        })

        extractor = LLMEntityExtractor(provider)
        context = extractor.extract("Test prompt", missing_types=["success_metric"])

        assert len(context.success_metrics) == 1
        assert context.success_metrics[0].target_value == "2"

    def test_extract_integrations(self) -> None:
        """Test extraction of integrations."""
        config = ProviderConfig(model="test-model")
        provider = MockProvider(config)
        provider._mock_response = json.dumps({
            "user_personas": [],
            "features": [],
            "technical_constraints": [],
            "success_metrics": [],
            "business_goals": [],
            "integrations": [
                {
                    "name": "Stripe Payment",
                    "integration_type": "api",
                    "provider": "Stripe",
                    "source_text": "Stripe integration",
                    "confidence": "high",
                }
            ],
            "data_entities": [],
        })

        extractor = LLMEntityExtractor(provider)
        context = extractor.extract("Test prompt", missing_types=["integration"])

        assert len(context.integrations) == 1
        assert context.integrations[0].provider == "Stripe"

    def test_extract_data_entities(self) -> None:
        """Test extraction of data entities."""
        config = ProviderConfig(model="test-model")
        provider = MockProvider(config)
        provider._mock_response = json.dumps({
            "user_personas": [],
            "features": [],
            "technical_constraints": [],
            "success_metrics": [],
            "business_goals": [],
            "integrations": [],
            "data_entities": [
                {
                    "name": "Order",
                    "attributes": ["order_id", "customer_id", "total"],
                    "relationships": ["belongs_to Customer"],
                    "source_text": "Order entity",
                    "confidence": "high",
                }
            ],
        })

        extractor = LLMEntityExtractor(provider)
        context = extractor.extract("Test prompt", missing_types=["data_entity"])

        assert len(context.data_entities) == 1
        assert context.data_entities[0].attributes == ["order_id", "customer_id", "total"]


# =============================================================================
# F. Confidence Parsing Tests
# =============================================================================


class TestConfidenceParsing:
    """Tests for confidence level parsing."""

    def test_confidence_high(self) -> None:
        """Test parsing high confidence."""
        config = ProviderConfig(model="test-model")
        provider = MockProvider(config)
        provider._mock_response = json.dumps({
            "user_personas": [
                {
                    "name": "Test",
                    "description": "Test",
                    "source_text": "Test",
                    "confidence": "high",
                }
            ],
            "features": [],
            "technical_constraints": [],
            "success_metrics": [],
            "business_goals": [],
            "integrations": [],
            "data_entities": [],
        })

        extractor = LLMEntityExtractor(provider)
        context = extractor.extract("Test", missing_types=["user_persona"])

        assert context.user_personas[0].confidence == 0.9

    def test_confidence_medium(self) -> None:
        """Test parsing medium confidence."""
        config = ProviderConfig(model="test-model")
        provider = MockProvider(config)
        provider._mock_response = json.dumps({
            "user_personas": [
                {
                    "name": "Test",
                    "description": "Test",
                    "source_text": "Test",
                    "confidence": "medium",
                }
            ],
            "features": [],
            "technical_constraints": [],
            "success_metrics": [],
            "business_goals": [],
            "integrations": [],
            "data_entities": [],
        })

        extractor = LLMEntityExtractor(provider)
        context = extractor.extract("Test", missing_types=["user_persona"])

        assert context.user_personas[0].confidence == 0.6

    def test_confidence_low(self) -> None:
        """Test parsing low confidence."""
        config = ProviderConfig(model="test-model")
        provider = MockProvider(config)
        provider._mock_response = json.dumps({
            "user_personas": [
                {
                    "name": "Test",
                    "description": "Test",
                    "source_text": "Test",
                    "confidence": "low",
                }
            ],
            "features": [],
            "technical_constraints": [],
            "success_metrics": [],
            "business_goals": [],
            "integrations": [],
            "data_entities": [],
        })

        extractor = LLMEntityExtractor(provider)
        context = extractor.extract("Test", missing_types=["user_persona"])

        assert context.user_personas[0].confidence == 0.3

    def test_confidence_default(self) -> None:
        """Test default confidence when not specified."""
        config = ProviderConfig(model="test-model")
        provider = MockProvider(config)
        provider._mock_response = json.dumps({
            "user_personas": [
                {
                    "name": "Test",
                    "description": "Test",
                    "source_text": "Test",
                    # No confidence specified
                }
            ],
            "features": [],
            "technical_constraints": [],
            "success_metrics": [],
            "business_goals": [],
            "integrations": [],
            "data_entities": [],
        })

        extractor = LLMEntityExtractor(provider)
        context = extractor.extract("Test", missing_types=["user_persona"])

        # Default is medium (0.6)
        assert context.user_personas[0].confidence == 0.6
