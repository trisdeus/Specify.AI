"""
Comprehensive tests for specify.context.registry module.

This module contains unit tests for:
- EntityRegistry initialization
- register() entity registration
- duplicate registration handling
- get() by ID
- get_by_name() case-insensitive lookup
- get_by_type() filtering
- add_relationship() and get_related()
- remove() with cleanup
- clear() functionality
- to_dict() and from_dict() serialization
- Thread-safety (basic concurrent access test)
"""

import pytest

from specify.context.registry import EntityRegistry
from specify.context.models import (
    EntityType,
    FeatureEntity,
    UserPersonaEntity,
)


# =============================================================================
# A. Initialization Tests
# =============================================================================


class TestEntityRegistryInit:
    """Tests for EntityRegistry initialization."""

    def test_registry_initialization(self) -> None:
        """Test registry initialization."""
        registry = EntityRegistry()
        assert registry is not None

    def test_initial_count_is_zero(self) -> None:
        """Test initial count is zero."""
        registry = EntityRegistry()
        assert len(registry) == 0


# =============================================================================
# B. Registration Tests
# =============================================================================


class TestRegistration:
    """Tests for entity registration."""

    def test_register_single_entity(self) -> None:
        """Test registering a single entity."""
        registry = EntityRegistry()

        entity = UserPersonaEntity(
            id="user_persona_admin",
            name="Administrator",
            description="System admin",
            source_text="Admin",
            confidence=0.9,
            role="Administrator",
        )

        entity_id = registry.register(entity)
        assert entity_id == "user_persona_admin"
        assert len(registry) == 1

    def test_register_multiple_entities(self) -> None:
        """Test registering multiple entities."""
        registry = EntityRegistry()

        entity1 = UserPersonaEntity(
            id="user_persona_admin",
            name="Administrator",
            description="Admin",
            source_text="Admin",
            confidence=0.9,
        )
        entity2 = FeatureEntity(
            id="feature_auth",
            name="Authentication",
            description="Auth",
            source_text="Auth",
            confidence=0.9,
        )

        registry.register(entity1)
        registry.register(entity2)

        assert len(registry) == 2

    def test_duplicate_registration_returns_existing(self) -> None:
        """Test that duplicate registration returns existing ID."""
        registry = EntityRegistry()

        entity1 = UserPersonaEntity(
            id="user_persona_admin",
            name="Administrator",
            description="Admin 1",
            source_text="Admin",
            confidence=0.9,
        )
        entity2 = UserPersonaEntity(
            id="user_persona_admin",
            name="Administrator",
            description="Admin 2",
            source_text="Admin",
            confidence=0.8,
        )

        id1 = registry.register(entity1)
        id2 = registry.register(entity2)

        # Should return existing ID, not create new one
        assert id1 == id2
        assert len(registry) == 1

    def test_duplicate_by_name_and_type(self) -> None:
        """Test duplicate detection by name and type."""
        registry = EntityRegistry()

        entity1 = UserPersonaEntity(
            id="user_persona_admin",
            name="Administrator",
            description="Admin 1",
            source_text="Admin",
            confidence=0.9,
        )
        entity2 = UserPersonaEntity(
            id="user_persona_different_id",
            name="Administrator",
            description="Admin 2",
            source_text="Admin",
            confidence=0.8,
        )

        registry.register(entity1)
        registry.register(entity2)

        # Should detect duplicate by name and type
        assert len(registry) == 1


# =============================================================================
# C. Lookup Tests
# =============================================================================


class TestLookup:
    """Tests for entity lookup methods."""

    def test_get_by_id(self) -> None:
        """Test get by ID."""
        registry = EntityRegistry()

        entity = UserPersonaEntity(
            id="user_persona_admin",
            name="Administrator",
            description="Admin",
            source_text="Admin",
            confidence=0.9,
        )
        registry.register(entity)

        retrieved = registry.get("user_persona_admin")
        assert retrieved is not None
        assert retrieved.name == "Administrator"

    def test_get_by_id_not_found(self) -> None:
        """Test get by non-existent ID."""
        registry = EntityRegistry()
        retrieved = registry.get("non_existent_id")
        assert retrieved is None

    def test_get_by_name_exact(self) -> None:
        """Test get by exact name."""
        registry = EntityRegistry()

        entity = UserPersonaEntity(
            id="user_persona_admin",
            name="Administrator",
            description="Admin",
            source_text="Admin",
            confidence=0.9,
        )
        registry.register(entity)

        retrieved = registry.get_by_name("Administrator")
        assert retrieved is not None
        assert retrieved.name == "Administrator"

    def test_get_by_name_case_insensitive(self) -> None:
        """Test get by name is case insensitive."""
        registry = EntityRegistry()

        entity = UserPersonaEntity(
            id="user_persona_admin",
            name="Administrator",
            description="Admin",
            source_text="Admin",
            confidence=0.9,
        )
        registry.register(entity)

        retrieved = registry.get_by_name("administrator")
        assert retrieved is not None

    def test_get_by_name_not_found(self) -> None:
        """Test get by non-existent name."""
        registry = EntityRegistry()
        retrieved = registry.get_by_name("NonExistent")
        assert retrieved is None

    def test_get_by_type(self) -> None:
        """Test get by entity type."""
        registry = EntityRegistry()

        persona = UserPersonaEntity(
            id="user_persona_admin",
            name="Administrator",
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

        registry.register(persona)
        registry.register(feature)

        personas = registry.get_by_type(EntityType.USER_PERSONA)
        assert len(personas) == 1
        assert personas[0].name == "Administrator"

    def test_get_by_type_empty(self) -> None:
        """Test get by type returns empty list."""
        registry = EntityRegistry()
        entities = registry.get_by_type(EntityType.USER_PERSONA)
        assert entities == []


# =============================================================================
# D. Relationship Tests
# =============================================================================


class TestRelationships:
    """Tests for entity relationships."""

    def test_add_relationship(self) -> None:
        """Test adding relationship between entities."""
        registry = EntityRegistry()

        entity1 = UserPersonaEntity(
            id="user_persona_admin",
            name="Administrator",
            description="Admin",
            source_text="Admin",
            confidence=0.9,
        )
        entity2 = FeatureEntity(
            id="feature_auth",
            name="Authentication",
            description="Auth",
            source_text="Auth",
            confidence=0.9,
        )

        registry.register(entity1)
        registry.register(entity2)
        registry.add_relationship("user_persona_admin", "feature_auth")

        # Check bidirectional relationship
        related1 = registry.get_related("user_persona_admin")
        related2 = registry.get_related("feature_auth")

        assert len(related1) == 1
        assert len(related2) == 1

    def test_add_relationship_invalid_entity(self) -> None:
        """Test adding relationship with invalid entity."""
        registry = EntityRegistry()

        entity = UserPersonaEntity(
            id="user_persona_admin",
            name="Administrator",
            description="Admin",
            source_text="Admin",
            confidence=0.9,
        )
        registry.register(entity)

        with pytest.raises(ValueError):
            registry.add_relationship("user_persona_admin", "non_existent")

    def test_get_related_invalid_entity(self) -> None:
        """Test get related with invalid entity."""
        registry = EntityRegistry()

        with pytest.raises(ValueError):
            registry.get_related("non_existent_id")


# =============================================================================
# E. Removal Tests
# =============================================================================


class TestRemoval:
    """Tests for entity removal."""

    def test_remove_existing_entity(self) -> None:
        """Test removing existing entity."""
        registry = EntityRegistry()

        entity = UserPersonaEntity(
            id="user_persona_admin",
            name="Administrator",
            description="Admin",
            source_text="Admin",
            confidence=0.9,
        )
        registry.register(entity)

        result = registry.remove("user_persona_admin")
        assert result is True
        assert len(registry) == 0

    def test_remove_non_existent_entity(self) -> None:
        """Test removing non-existent entity."""
        registry = EntityRegistry()
        result = registry.remove("non_existent_id")
        assert result is False

    def test_remove_cleans_up_aliases(self) -> None:
        """Test that removal cleans up aliases."""
        registry = EntityRegistry()

        entity = UserPersonaEntity(
            id="user_persona_admin",
            name="Administrator",
            description="Admin",
            source_text="Admin",
            confidence=0.9,
            aliases=["admin", "superuser"],
        )
        registry.register(entity)
        registry.remove("user_persona_admin")

        # Should not be able to find by alias
        retrieved = registry.get_by_name("admin")
        assert retrieved is None


# =============================================================================
# F. Clear Tests
# =============================================================================


class TestClear:
    """Tests for clearing registry."""

    def test_clear_removes_all(self) -> None:
        """Test clear removes all entities."""
        registry = EntityRegistry()

        entity1 = UserPersonaEntity(
            id="user_persona_admin",
            name="Administrator",
            description="Admin",
            source_text="Admin",
            confidence=0.9,
        )
        entity2 = FeatureEntity(
            id="feature_auth",
            name="Authentication",
            description="Auth",
            source_text="Auth",
            confidence=0.9,
        )

        registry.register(entity1)
        registry.register(entity2)
        assert len(registry) == 2

        registry.clear()
        assert len(registry) == 0


# =============================================================================
# G. Count Tests
# =============================================================================


class TestCount:
    """Tests for counting methods."""

    def test_count_total(self) -> None:
        """Test total count."""
        registry = EntityRegistry()

        entity1 = UserPersonaEntity(
            id="user_persona_admin",
            name="Administrator",
            description="Admin",
            source_text="Admin",
            confidence=0.9,
        )
        entity2 = FeatureEntity(
            id="feature_auth",
            name="Authentication",
            description="Auth",
            source_text="Auth",
            confidence=0.9,
        )

        registry.register(entity1)
        registry.register(entity2)

        assert registry.count() == 2

    def test_count_by_type(self) -> None:
        """Test count by type."""
        registry = EntityRegistry()

        persona = UserPersonaEntity(
            id="user_persona_admin",
            name="Administrator",
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

        registry.register(persona)
        registry.register(feature)

        assert registry.count_by_type(EntityType.USER_PERSONA) == 1
        assert registry.count_by_type(EntityType.FEATURE) == 1


# =============================================================================
# H. Serialization Tests
# =============================================================================


class TestSerialization:
    """Tests for serialization methods."""

    def test_to_dict(self) -> None:
        """Test to_dict serialization."""
        registry = EntityRegistry()

        entity = UserPersonaEntity(
            id="user_persona_admin",
            name="Administrator",
            description="Admin",
            source_text="Admin",
            confidence=0.9,
        )
        registry.register(entity)

        data = registry.to_dict()
        assert "entities" in data
        assert "relationships" in data
        assert "metadata" in data
        assert len(data["entities"]) == 1

    def test_from_dict(self) -> None:
        """Test from_dict deserialization."""
        registry = EntityRegistry()

        entity = UserPersonaEntity(
            id="user_persona_admin",
            name="Administrator",
            description="Admin",
            source_text="Admin",
            confidence=0.9,
        )
        registry.register(entity)

        data = registry.to_dict()
        new_registry = EntityRegistry.from_dict(data)

        assert len(new_registry) == 1
        retrieved = new_registry.get("user_persona_admin")
        assert retrieved is not None
        assert retrieved.name == "Administrator"

    def test_roundtrip_with_relationships(self) -> None:
        """Test roundtrip with relationships."""
        registry = EntityRegistry()

        entity1 = UserPersonaEntity(
            id="user_persona_admin",
            name="Administrator",
            description="Admin",
            source_text="Admin",
            confidence=0.9,
        )
        entity2 = FeatureEntity(
            id="feature_auth",
            name="Authentication",
            description="Auth",
            source_text="Auth",
            confidence=0.9,
        )

        registry.register(entity1)
        registry.register(entity2)
        registry.add_relationship("user_persona_admin", "feature_auth")

        data = registry.to_dict()
        new_registry = EntityRegistry.from_dict(data)

        # Check relationship preserved
        related = new_registry.get_related("user_persona_admin")
        assert len(related) == 1


# =============================================================================
# I. Iterator and Contains Tests
# =============================================================================


class TestIteratorAndContains:
    """Tests for iterator and contains methods."""

    def test_iteration(self) -> None:
        """Test iteration over registry."""
        registry = EntityRegistry()

        entity1 = UserPersonaEntity(
            id="user_persona_admin",
            name="Administrator",
            description="Admin",
            source_text="Admin",
            confidence=0.9,
        )
        entity2 = FeatureEntity(
            id="feature_auth",
            name="Authentication",
            description="Auth",
            source_text="Auth",
            confidence=0.9,
        )

        registry.register(entity1)
        registry.register(entity2)

        entities = list(registry)
        assert len(entities) == 2

    def test_contains_true(self) -> None:
        """Test contains returns true."""
        registry = EntityRegistry()

        entity = UserPersonaEntity(
            id="user_persona_admin",
            name="Administrator",
            description="Admin",
            source_text="Admin",
            confidence=0.9,
        )
        registry.register(entity)

        assert "user_persona_admin" in registry

    def test_contains_false(self) -> None:
        """Test contains returns false."""
        registry = EntityRegistry()
        assert "non_existent" not in registry


# =============================================================================
# J. Thread Safety Tests
# =============================================================================


class TestThreadSafety:
    """Basic thread safety tests."""

    def test_concurrent_registration(self) -> None:
        """Test concurrent registration doesn't crash."""
        import threading

        registry = EntityRegistry()
        errors = []

        def register_entity(entity_id: str) -> None:
            try:
                entity = UserPersonaEntity(
                    id=entity_id,
                    name=f"User {entity_id}",
                    description="Test",
                    source_text="Test",
                    confidence=0.9,
                )
                registry.register(entity)
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(10):
            thread = threading.Thread(target=register_entity, args=(f"user_persona_{i}",))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Should have all entities registered
        assert len(registry) == 10
        assert len(errors) == 0


# =============================================================================
# K. Get All Test
# =============================================================================


class TestGetAll:
    """Tests for get_all method."""

    def test_get_all_returns_all(self) -> None:
        """Test get_all returns all entities."""
        registry = EntityRegistry()

        entity1 = UserPersonaEntity(
            id="user_persona_admin",
            name="Administrator",
            description="Admin",
            source_text="Admin",
            confidence=0.9,
        )
        entity2 = FeatureEntity(
            id="feature_auth",
            name="Authentication",
            description="Auth",
            source_text="Auth",
            confidence=0.9,
        )

        registry.register(entity1)
        registry.register(entity2)

        all_entities = registry.get_all()
        assert len(all_entities) == 2
