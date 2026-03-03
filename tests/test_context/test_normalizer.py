"""
Comprehensive tests for specify.context.normalizer module.

This module contains unit tests for:
- EntityNormalizer initialization
- normalize_name() with various inputs
- generate_id() format and consistency
- normalize_entity() returns correct copy
- add_term_mapping() custom mappings
- remove_term_mapping() functionality
- TERM_MAPPINGS dictionary lookups
"""

import pytest

from specify.context.normalizer import EntityNormalizer
from specify.context.models import (
    Entity,
    EntityType,
    FeatureEntity,
    UserPersonaEntity,
)


# =============================================================================
# A. Initialization Tests
# =============================================================================


class TestEntityNormalizerInit:
    """Tests for EntityNormalizer initialization."""

    def test_normalizer_initialization(self) -> None:
        """Test normalizer initialization."""
        normalizer = EntityNormalizer()
        assert normalizer is not None

    def test_default_term_mappings(self) -> None:
        """Test that default term mappings are loaded."""
        normalizer = EntityNormalizer()
        mappings = normalizer.get_term_mappings()
        assert len(mappings) > 0

    def test_term_mappings_contain_admin(self) -> None:
        """Test that admin term is mapped."""
        normalizer = EntityNormalizer()
        mappings = normalizer.get_term_mappings()
        assert "admin" in mappings


# =============================================================================
# B. normalize_name Tests
# =============================================================================


class TestNormalizeName:
    """Tests for normalize_name method."""

    def test_normalize_admin(self) -> None:
        """Test normalization of 'admin'."""
        normalizer = EntityNormalizer()
        result = normalizer.normalize_name("admin")
        assert result == "Administrator"

    def test_normalize_customer(self) -> None:
        """Test normalization of 'customer'."""
        normalizer = EntityNormalizer()
        result = normalizer.normalize_name("customer")
        assert result == "User"

    def test_normalize_uppercase(self) -> None:
        """Test normalization handles uppercase."""
        normalizer = EntityNormalizer()
        result = normalizer.normalize_name("ADMIN")
        assert result == "Administrator"

    def test_normalize_mixed_case(self) -> None:
        """Test normalization handles mixed case."""
        normalizer = EntityNormalizer()
        result = normalizer.normalize_name("AdMiN")
        assert result == "Administrator"

    def test_normalize_with_whitespace(self) -> None:
        """Test normalization strips whitespace."""
        normalizer = EntityNormalizer()
        result = normalizer.normalize_name("  admin  ")
        assert result == "Administrator"

    def test_normalize_empty_string(self) -> None:
        """Test normalization of empty string."""
        normalizer = EntityNormalizer()
        result = normalizer.normalize_name("")
        assert result == ""

    def test_normalize_developer(self) -> None:
        """Test normalization of 'developer'."""
        normalizer = EntityNormalizer()
        result = normalizer.normalize_name("developer")
        assert result == "Developer"

    def test_normalize_end_user(self) -> None:
        """Test normalization of 'end user'."""
        normalizer = EntityNormalizer()
        result = normalizer.normalize_name("end user")
        assert result == "User"

    def test_normalize_superuser(self) -> None:
        """Test normalization of 'superuser'."""
        normalizer = EntityNormalizer()
        result = normalizer.normalize_name("superuser")
        assert result == "Administrator"

    def test_normalize_hyphenated(self) -> None:
        """Test normalization of hyphenated terms."""
        normalizer = EntityNormalizer()
        result = normalizer.normalize_name("end-user")
        assert result == "User"

    def test_normalize_api(self) -> None:
        """Test normalization of 'API'."""
        normalizer = EntityNormalizer()
        result = normalizer.normalize_name("api")
        assert result == "API"


# =============================================================================
# C. generate_id Tests
# =============================================================================


class TestGenerateId:
    """Tests for generate_id method."""

    def test_generate_id_user_persona(self) -> None:
        """Test ID generation for user persona."""
        normalizer = EntityNormalizer()
        result = normalizer.generate_id("Admin User", EntityType.USER_PERSONA)
        assert result == "user_persona_admin_user"

    def test_generate_id_feature(self) -> None:
        """Test ID generation for feature."""
        normalizer = EntityNormalizer()
        result = normalizer.generate_id("User Authentication", EntityType.FEATURE)
        assert result == "feature_user_authentication"

    def test_generate_id_with_spaces(self) -> None:
        """Test ID generation replaces spaces with underscores."""
        normalizer = EntityNormalizer()
        result = normalizer.generate_id("Test Feature", EntityType.FEATURE)
        assert " " not in result

    def test_generate_id_with_special_chars(self) -> None:
        """Test ID generation removes special characters."""
        normalizer = EntityNormalizer()
        result = normalizer.generate_id("Test-Feature@123", EntityType.FEATURE)
        assert "@" not in result

    def test_generate_id_empty_name(self) -> None:
        """Test ID generation with empty name."""
        normalizer = EntityNormalizer()
        result = normalizer.generate_id("", EntityType.USER_PERSONA)
        assert "unknown" in result

    def test_generate_id_lowercase(self) -> None:
        """Test ID generation converts to lowercase."""
        normalizer = EntityNormalizer()
        result = normalizer.generate_id("ADMIN", EntityType.USER_PERSONA)
        assert result == result.lower()

    def test_generate_id_multiple_underscores(self) -> None:
        """Test ID generation handles multiple spaces."""
        normalizer = EntityNormalizer()
        result = normalizer.generate_id("Test   Feature", EntityType.FEATURE)
        assert "__" not in result

    def test_generate_id_leading_underscore(self) -> None:
        """Test ID generation removes leading underscores."""
        normalizer = EntityNormalizer()
        result = normalizer.generate_id("  Test", EntityType.FEATURE)
        assert not result.startswith("_")


# =============================================================================
# D. normalize_entity Tests
# =============================================================================


class TestNormalizeEntity:
    """Tests for normalize_entity method."""

    def test_normalize_entity_basic(self) -> None:
        """Test basic entity normalization."""
        normalizer = EntityNormalizer()

        entity = UserPersonaEntity(
            id="user_persona_admin",
            name="Admin User",
            description="Admin user description",
            source_text="Admin users",
            confidence=0.9,
            role="Admin",
        )

        normalized = normalizer.normalize_entity(entity)

        # Should create a new entity, not modify original
        assert normalized is not entity
        assert normalized.name == "Administrator"

    def test_normalize_entity_preserves_other_fields(self) -> None:
        """Test that other fields are preserved."""
        normalizer = EntityNormalizer()

        entity = UserPersonaEntity(
            id="user_persona_admin",
            name="Admin",
            description="Admin user",
            source_text="Admin users",
            confidence=0.9,
            role="Administrator",
            characteristics=["Technical"],
            goals=["Manage users"],
        )

        normalized = normalizer.normalize_entity(entity)

        assert normalized.description == "Admin user"
        assert normalized.role == "Administrator"
        assert normalized.characteristics == ["Technical"]
        assert normalized.goals == ["Manage users"]

    def test_normalize_entity_updates_id(self) -> None:
        """Test that ID is updated based on normalized name."""
        normalizer = EntityNormalizer()

        entity = UserPersonaEntity(
            id="user_persona_old",
            name="admin",
            description="Admin",
            source_text="Admin",
            confidence=0.9,
        )

        normalized = normalizer.normalize_entity(entity)

        assert "administrator" in normalized.id.lower()

    def test_normalize_entity_does_not_mutate_original(self) -> None:
        """Test that original entity is not mutated."""
        normalizer = EntityNormalizer()

        entity = UserPersonaEntity(
            id="user_persona_admin",
            name="Admin",
            description="Admin",
            source_text="Admin",
            confidence=0.9,
        )

        original_name = entity.name
        normalized = normalizer.normalize_entity(entity)

        assert entity.name == original_name


# =============================================================================
# E. Term Mapping Tests
# =============================================================================


class TestTermMappings:
    """Tests for term mapping management."""

    def test_add_term_mapping(self) -> None:
        """Test adding custom term mapping."""
        normalizer = EntityNormalizer()
        normalizer.add_term_mapping("purchaser", "user")

        result = normalizer.normalize_name("purchaser")
        assert result == "User"

    def test_add_term_mapping_case_insensitive(self) -> None:
        """Test adding term mapping is case insensitive."""
        normalizer = EntityNormalizer()
        normalizer.add_term_mapping("PURCHASER", "user")

        result = normalizer.normalize_name("purchaser")
        assert result == "User"

    def test_remove_term_mapping_existing(self) -> None:
        """Test removing existing term mapping."""
        normalizer = EntityNormalizer()
        # Add then remove
        normalizer.add_term_mapping("test_term", "user")
        result = normalizer.remove_term_mapping("test_term")
        assert result is True

    def test_remove_term_mapping_non_existing(self) -> None:
        """Test removing non-existing term mapping."""
        normalizer = EntityNormalizer()
        result = normalizer.remove_term_mapping("non_existing_term_xyz")
        assert result is False

    def test_get_term_mappings_returns_copy(self) -> None:
        """Test that get_term_mappings returns a copy."""
        normalizer = EntityNormalizer()
        mappings = normalizer.get_term_mappings()
        mappings["new_term"] = "new_value"

        # Original should be unchanged
        assert "new_term" not in normalizer.get_term_mappings()

    def test_clear_custom_mappings(self) -> None:
        """Test clearing custom mappings."""
        normalizer = EntityNormalizer()
        normalizer.add_term_mapping("custom_term", "user")
        normalizer.clear_custom_mappings()

        # Custom mapping should be removed
        result = normalizer.normalize_name("custom_term")
        assert result != "User"


# =============================================================================
# F. Title Case Tests
# =============================================================================


class TestTitleCase:
    """Tests for title case conversion."""

    def test_title_case_simple(self) -> None:
        """Test simple title case."""
        normalizer = EntityNormalizer()
        # "admin user" maps to "administrator"
        result = normalizer.normalize_name("admin user")
        assert result == "Administrator"

    def test_title_case_acronyms(self) -> None:
        """Test that common acronyms are handled."""
        normalizer = EntityNormalizer()
        # Test that API stays uppercase
        assert normalizer.normalize_name("api") == "API"

    def test_title_case_hyphenated(self) -> None:
        """Test title case with hyphens."""
        normalizer = EntityNormalizer()
        result = normalizer.normalize_name("end-user")
        assert result == "User"


# =============================================================================
# G. Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases."""

    def test_unknown_term(self) -> None:
        """Test handling of unknown terms."""
        normalizer = EntityNormalizer()
        result = normalizer.normalize_name("xyz_unknown_term")
        # Should still title-case unknown terms
        assert result is not None
        assert len(result) > 0

    def test_numeric_name(self) -> None:
        """Test handling of numeric names."""
        normalizer = EntityNormalizer()
        result = normalizer.normalize_name("user123")
        assert result is not None

    def test_very_long_name(self) -> None:
        """Test handling of very long names."""
        normalizer = EntityNormalizer()
        long_name = "a" * 200
        result = normalizer.normalize_name(long_name)
        assert result is not None
