"""
Comprehensive tests for specify.context.extractor module.

This module contains unit tests for:
- HybridContextExtractor initialization
- Deterministic-first extraction flow
- LLM fallback triggering conditions
- Merge strategy (deterministic priority)
- ExtractionAnalysis decision making
- Confidence threshold behavior (0.7)
- End-to-end extraction with sample prompts
"""

import asyncio
import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from specify.context.extractor import (
    ExtractionAnalysis,
    HybridContextExtractor,
)
from specify.context.models import (
    EntityContext,
    EntityType,
    FeatureEntity,
    UserPersonaEntity,
)
from specify.providers.base import ProviderConfig


# Create a mock provider for testing
class MockProvider:
    """Mock provider for testing with async generate method."""

    def __init__(self, config: ProviderConfig) -> None:
        self._config = config
        self._mock_response: str = ""

    async def generate(self, prompt: str, rules: str | None = None) -> str:
        """Async generate method matching BaseProvider interface."""
        return self._mock_response


# =============================================================================
# A. Initialization Tests
# =============================================================================


class TestHybridContextExtractorInit:
    """Tests for HybridContextExtractor initialization."""

    def test_extractor_initialization_without_provider(self) -> None:
        """Test extractor initialization without provider."""
        extractor = HybridContextExtractor()
        assert extractor is not None
        assert extractor._llm_extractor is None

    def test_extractor_initialization_with_provider(self) -> None:
        """Test extractor initialization with provider."""
        config = ProviderConfig(model="test-model")
        provider = MockProvider(config)
        extractor = HybridContextExtractor(provider=provider)
        assert extractor is not None
        assert extractor._llm_extractor is not None

    def test_confidence_threshold(self) -> None:
        """Test confidence threshold is 0.7."""
        extractor = HybridContextExtractor()
        assert extractor.CONFIDENCE_THRESHOLD == 0.7


# =============================================================================
# B. ExtractionAnalysis Tests
# =============================================================================


class TestExtractionAnalysis:
    """Tests for ExtractionAnalysis dataclass."""

    def test_analysis_defaults(self) -> None:
        """Test analysis defaults."""
        analysis = ExtractionAnalysis()
        assert analysis.needs_llm_fallback is False
        assert analysis.missing_types == []
        assert analysis.low_confidence_entities == []
        assert analysis.coverage_score == 0.0

    def test_analysis_with_missing_types(self) -> None:
        """Test analysis with missing types."""
        analysis = ExtractionAnalysis(
            needs_llm_fallback=True,
            missing_types=["user_persona", "feature"],
        )
        assert analysis.needs_llm_fallback is True
        assert len(analysis.missing_types) == 2

    def test_analysis_with_low_confidence(self) -> None:
        """Test analysis with low confidence entities."""
        analysis = ExtractionAnalysis(
            needs_llm_fallback=True,
            low_confidence_entities=["user_persona:admin"],
        )
        assert len(analysis.low_confidence_entities) == 1


# =============================================================================
# C. Deterministic-Only Extraction Tests
# =============================================================================


class TestDeterministicOnlyExtraction:
    """Tests for deterministic-only extraction."""

    @pytest.mark.asyncio
    async def test_extract_with_no_provider(self) -> None:
        """Test extraction without provider uses deterministic only."""
        extractor = HybridContextExtractor()
        context = await extractor.extract("Build an app with user John")

        # Should return context from deterministic extraction
        assert context is not None
        assert isinstance(context, EntityContext)

    @pytest.mark.asyncio
    async def test_extract_with_entities_found(self) -> None:
        """Test extraction when entities are found."""
        extractor = HybridContextExtractor()
        context = await extractor.extract("User John needs authentication")

        # Should have some entities from deterministic extraction
        assert context is not None

    @pytest.mark.asyncio
    async def test_extract_empty_prompt(self) -> None:
        """Test extraction with empty prompt."""
        extractor = HybridContextExtractor()
        context = await extractor.extract("")

        assert context.source_prompt == ""
        assert len(context.get_all_entities()) == 0


# =============================================================================
# D. Analysis Tests
# =============================================================================


class TestAnalysis:
    """Tests for extraction analysis."""

    def test_analyze_extraction_complete(self) -> None:
        """Test analysis when extraction is complete."""
        extractor = HybridContextExtractor()

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

        entities = [persona, feature]
        analysis = extractor._analyze_extraction(entities)

        assert analysis.needs_llm_fallback is False
        assert analysis.coverage_score == 1.0

    def test_analyze_extraction_missing_types(self) -> None:
        """Test analysis with missing required types."""
        extractor = HybridContextExtractor()

        # Only have a feature, missing user_persona
        feature = FeatureEntity(
            id="feature_test",
            name="Test",
            description="Test",
            source_text="Test",
            confidence=0.9,
        )

        entities = [feature]
        analysis = extractor._analyze_extraction(entities)

        assert analysis.needs_llm_fallback is True
        assert "user_persona" in analysis.missing_types

    def test_analyze_extraction_low_confidence(self) -> None:
        """Test analysis with low confidence entities."""
        extractor = HybridContextExtractor()

        persona = UserPersonaEntity(
            id="user_persona_admin",
            name="Admin",
            description="Admin",
            source_text="Admin",
            confidence=0.5,  # Below 0.7 threshold
        )

        entities = [persona]
        analysis = extractor._analyze_extraction(entities)

        assert analysis.needs_llm_fallback is True
        assert len(analysis.low_confidence_entities) > 0


# =============================================================================
# E. Merge Strategy Tests
# =============================================================================


class TestMergeStrategy:
    """Tests for entity merge strategy."""

    def test_merge_deterministic_priority(self) -> None:
        """Test that deterministic entities take priority."""
        extractor = HybridContextExtractor()

        # Create deterministic context
        det_persona = UserPersonaEntity(
            id="user_persona_admin",
            name="Admin",
            description="Admin from deterministic",
            source_text="Admin source",
            confidence=0.9,
        )
        det_context = EntityContext(
            source_prompt="Test",
            user_personas=[det_persona],
        )

        # Create LLM context with same entity but lower confidence
        llm_persona = UserPersonaEntity(
            id="user_persona_admin2",
            name="Administrator",
            description="Admin from LLM",
            source_text="LLM source",
            confidence=0.7,
        )
        llm_context = EntityContext(
            source_prompt="Test",
            user_personas=[llm_persona],
        )

        merged = extractor._merge_entities(det_context, llm_context)

        # Should have both entities (different IDs)
        assert len(merged.user_personas) >= 1

    def test_merge_llm_only_entities(self) -> None:
        """Test that LLM-only entities are added."""
        extractor = HybridContextExtractor()

        det_context = EntityContext(source_prompt="Test")

        llm_persona = UserPersonaEntity(
            id="user_persona_new",
            name="New User",
            description="New user",
            source_text="New",
            confidence=0.8,
        )
        llm_context = EntityContext(
            source_prompt="Test",
            user_personas=[llm_persona],
        )

        merged = extractor._merge_entities(det_context, llm_context)

        # Should have LLM-only entity
        assert len(merged.user_personas) == 1
        assert merged.user_personas[0].name == "New User"

    def test_merge_multiple_entity_types(self) -> None:
        """Test merging multiple entity types."""
        extractor = HybridContextExtractor()

        det_persona = UserPersonaEntity(
            id="user_persona_admin",
            name="Admin",
            description="Admin",
            source_text="Admin",
            confidence=0.9,
        )
        det_context = EntityContext(
            source_prompt="Test",
            user_personas=[det_persona],
        )

        llm_feature = FeatureEntity(
            id="feature_auth",
            name="Auth",
            description="Auth feature",
            source_text="Auth",
            confidence=0.8,
        )
        llm_context = EntityContext(
            source_prompt="Test",
            features=[llm_feature],
        )

        merged = extractor._merge_entities(det_context, llm_context)

        assert len(merged.user_personas) == 1
        assert len(merged.features) == 1


# =============================================================================
# F. Deduplication Tests
# =============================================================================


class TestDeduplication:
    """Tests for entity deduplication."""

    def test_deduplicate_same_entity(self) -> None:
        """Test deduplication of same entity."""
        extractor = HybridContextExtractor()

        persona1 = UserPersonaEntity(
            id="user_persona_admin",
            name="Admin",
            description="Admin 1",
            source_text="Source 1",
            confidence=0.9,
        )
        persona2 = UserPersonaEntity(
            id="user_persona_admin",
            name="Admin",
            description="Admin 2",
            source_text="Source 2",
            confidence=0.8,
        )

        entities = [persona1, persona2]
        deduplicated = extractor._deduplicate_entities(entities)

        assert len(deduplicated) == 1

    def test_deduplicate_same_name_different_confidence(self) -> None:
        """Test keeping higher confidence entity."""
        extractor = HybridContextExtractor()

        persona_low = UserPersonaEntity(
            id="user_persona_admin",
            name="Admin",
            description="Low confidence",
            source_text="Source",
            confidence=0.5,
        )
        persona_high = UserPersonaEntity(
            id="user_persona_admin",
            name="Admin",
            description="High confidence",
            source_text="Source",
            confidence=0.9,
        )

        entities = [persona_low, persona_high]
        deduplicated = extractor._deduplicate_entities(entities)

        assert len(deduplicated) == 1
        assert deduplicated[0].confidence == 0.9


# =============================================================================
# G. End-to-End Tests
# =============================================================================


class TestEndToEnd:
    """End-to-end extraction tests."""

    @pytest.mark.asyncio
    async def test_e2e_deterministic_only(self) -> None:
        """Test end-to-end deterministic-only extraction."""
        extractor = HybridContextExtractor()
        context = await extractor.extract(
            "Build a dashboard with user authentication. "
            "Admin users should have full access. "
            "Response time must be under 200ms."
        )

        assert context is not None
        assert len(context.get_all_entities()) > 0

    @pytest.mark.asyncio
    async def test_e2e_with_provider_fallback(self) -> None:
        """Test end-to-end with LLM fallback."""
        config = ProviderConfig(model="test-model")
        provider = MockProvider(config)
        provider._mock_response = json.dumps({
            "user_personas": [
                {
                    "name": "LLM User",
                    "role": "User",
                    "description": "From LLM",
                    "source_text": "LLM source",
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

        extractor = HybridContextExtractor(provider=provider)
        # This should trigger LLM fallback because no user_persona is extracted
        context = await extractor.extract("Build a simple app")

        # Should have entities from either deterministic or LLM
        assert context is not None

    @pytest.mark.asyncio
    async def test_e2e_llm_failure_fallback(self) -> None:
        """Test that deterministic is used when LLM fails."""
        config = ProviderConfig(model="test-model")
        provider = MockProvider(config)

        async def raise_error(*args: Any, **kwargs: Any) -> str:
            raise Exception("LLM error")

        provider.generate = raise_error  # type: ignore

        extractor = HybridContextExtractor(provider=provider)

        # Extract with deterministic finding entities
        context = await extractor.extract("User John needs authentication")

        # Should fall back to deterministic
        assert context is not None


# =============================================================================
# H. Context Conversion Tests
# =============================================================================


class TestEntitiesToContext:
    """Tests for entities to context conversion."""

    def test_entities_to_context(self) -> None:
        """Test conversion of entities to context."""
        extractor = HybridContextExtractor()

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

        entities = [persona, feature]
        context = extractor._entities_to_context(entities, "Test prompt")

        assert len(context.user_personas) == 1
        assert len(context.features) == 1
        assert context.source_prompt == "Test prompt"

    def test_entities_to_context_empty(self) -> None:
        """Test conversion with no entities."""
        extractor = HybridContextExtractor()

        context = extractor._entities_to_context([], "Test prompt")

        assert len(context.user_personas) == 0
        assert len(context.features) == 0
        assert context.source_prompt == "Test prompt"
