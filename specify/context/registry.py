"""
Entity Registry for Specify.AI.

This module provides the EntityRegistry class that serves as a central
registry for all extracted entities. It provides lookup, deduplication,
relationship tracking, and serialization capabilities.

The registry ensures:
- Unique entity registration with deduplication
- Fast lookups by ID, name, or type
- Case-insensitive name/alias matching
- Thread-safe operations
- Entity relationship tracking
"""

from __future__ import annotations

import logging
import threading
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Optional

from specify.context.models import Entity, EntityType

# Configure module logger
logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from typing import Iterator


class EntityRegistry:
    """Central registry for all extracted entities.
    
    This class provides a thread-safe, deduplicated storage mechanism for
    entities extracted from user prompts. It supports fast lookups by ID,
    name, or type, and tracks relationships between entities.
    
    Attributes:
        _entities: Dictionary mapping entity IDs to Entity objects.
        _by_type: Dictionary mapping EntityType to lists of entity IDs.
        _aliases: Dictionary mapping lowercase aliases to entity IDs.
        _relationships: Dictionary mapping entity IDs to lists of related entity IDs.
        _lock: Threading lock for thread-safe operations.
    
    Example:
        >>> registry = EntityRegistry()
        >>> entity = UserPersonaEntity(
        ...     id="user_persona_admin",
        ...     name="Administrator",
        ...     description="System admin with full access",
        ...     source_text="Admin users should...",
        ...     confidence=0.9,
        ...     role="Administrator"
        ... )
        >>> entity_id = registry.register(entity)
        >>> retrieved = registry.get(entity_id)
        >>> retrieved.name
        'Administrator'
    """
    
    def __init__(self) -> None:
        """Initialize the EntityRegistry."""
        self._entities: dict[str, Entity] = {}
        self._by_type: dict[EntityType, list[str]] = defaultdict(list)
        self._aliases: dict[str, str] = {}  # lowercase alias -> entity_id
        self._relationships: dict[str, list[str]] = defaultdict(list)
        self._lock = threading.RLock()
        
        logger.debug("EntityRegistry initialized")
    
    def register(self, entity: Entity, update_existing: bool = False) -> str:
        """Register an entity and return its ID.
        
        Handles duplicate registration by either updating existing entities
        or returning the existing entity's ID based on the update_existing flag.
        
        Args:
            entity: The entity to register.
            update_existing: If True, update existing entities with the same 
                           ID. If False (default), return the existing ID.
                           
        Returns:
            The entity ID (either the new one or existing if duplicate).
        """
        with self._lock:
            # Check for duplicates
            existing = self._find_duplicate(entity)
            if existing:
                if update_existing:
                    # Update the existing entity
                    logger.info("Updating existing entity '%s' with new data", 
                               existing.id)
                    self._update_entity(existing, entity)
                else:
                    logger.debug("Duplicate entity found, returning existing ID '%s'",
                               existing.id)
                return existing.id
            
            # Register new entity
            self._entities[entity.id] = entity
            self._by_type[entity.entity_type].append(entity.id)
            
            # Register aliases (case-insensitive)
            for alias in entity.aliases:
                alias_lower = alias.lower().strip()
                if alias_lower:
                    self._aliases[alias_lower] = entity.id
            
            # Also register the entity name as an alias
            name_lower = entity.name.lower().strip()
            if name_lower and name_lower not in self._aliases:
                self._aliases[name_lower] = entity.id
            
            logger.info("Registered entity '%s' (type: %s)", 
                       entity.id, entity.entity_type.value)
            
            return entity.id
    
    def _find_duplicate(self, entity: Entity) -> Optional[Entity]:
        """Check if a similar entity already exists.
        
        Checks for duplicates by:
        1. Exact ID match
        2. Same name and entity type
        
        Args:
            entity: The entity to check for duplicates.
            
        Returns:
            The existing entity if found, None otherwise.
        """
        # Check by ID
        if entity.id in self._entities:
            return self._entities[entity.id]
        
        # Check by name and type
        name_lower = entity.name.lower().strip()
        for existing in self._entities.values():
            if (existing.name.lower().strip() == name_lower and 
                existing.entity_type == entity.entity_type):
                return existing
        
        return None
    
    def _update_entity(self, existing: Entity, new_data: Entity) -> None:
        """Update an existing entity with new data.
        
        Merges new data into the existing entity, preserving the original ID.
        
        Args:
            existing: The existing entity to update.
            new_data: The new entity data to merge.
        """
        # Update fields if new data provides better information
        if new_data.description and new_data.description != existing.description:
            existing.description = new_data.description
        
        if (new_data.confidence > existing.confidence and 
            new_data.source_text != existing.source_text):
            existing.source_text = new_data.source_text
            existing.confidence = new_data.confidence
        
        # Merge aliases
        for alias in new_data.aliases:
            alias_lower = alias.lower().strip()
            if alias_lower and alias_lower not in [a.lower() for a in existing.aliases]:
                existing.aliases.append(alias)
    
    def get(self, entity_id: str) -> Optional[Entity]:
        """Get entity by ID.
        
        Args:
            entity_id: The unique identifier of the entity.
            
        Returns:
            The Entity if found, None otherwise.
        """
        with self._lock:
            return self._entities.get(entity_id)
    
    def get_by_name(self, name: str) -> Optional[Entity]:
        """Get entity by name or alias.
        
        Performs case-insensitive lookup by:
        1. Trying exact name match
        2. Trying alias lookup
        
        Args:
            name: The name or alias to look up.
            
        Returns:
            The Entity if found, None otherwise.
        """
        with self._lock:
            name_lower = name.lower().strip()
            
            # Try exact name match first
            for entity in self._entities.values():
                if entity.name.lower() == name_lower:
                    return entity
            
            # Try aliases
            entity_id = self._aliases.get(name_lower)
            if entity_id:
                return self._entities.get(entity_id)
            
            return None
    
    def get_by_type(self, entity_type: EntityType) -> list[Entity]:
        """Get all entities of a specific type.
        
        Args:
            entity_type: The type of entities to retrieve.
            
        Returns:
            List of entities of the specified type.
        """
        with self._lock:
            entity_ids = self._by_type.get(entity_type, [])
            return [
                self._entities[eid] 
                for eid in entity_ids 
                if eid in self._entities
            ]
    
    def get_all(self) -> list[Entity]:
        """Get all registered entities.
        
        Returns:
            List of all entities in the registry.
        """
        with self._lock:
            return list(self._entities.values())
    
    def add_relationship(self, entity1_id: str, entity2_id: str) -> None:
        """Record a relationship between two entities.
        
        Creates a bidirectional relationship between two entities.
        
        Args:
            entity1_id: ID of the first entity.
            entity2_id: ID of the second entity.
            
        Raises:
            ValueError: If either entity ID doesn't exist in the registry.
        """
        with self._lock:
            # Validate that both entities exist
            if entity1_id not in self._entities:
                raise ValueError(f"Entity '{entity1_id}' not found in registry")
            if entity2_id not in self._entities:
                raise ValueError(f"Entity '{entity2_id}' not found in registry")
            
            # Add bidirectional relationships
            if entity2_id not in self._relationships[entity1_id]:
                self._relationships[entity1_id].append(entity2_id)
            if entity1_id not in self._relationships[entity2_id]:
                self._relationships[entity2_id].append(entity1_id)
            
            logger.debug("Added relationship: %s <-> %s", entity1_id, entity2_id)
    
    def get_related(self, entity_id: str) -> list[Entity]:
        """Get all entities related to the given entity.
        
        Args:
            entity_id: The ID of the entity to find related entities for.
            
        Returns:
            List of related entities.
            
        Raises:
            ValueError: If the entity ID doesn't exist in the registry.
        """
        with self._lock:
            if entity_id not in self._entities:
                raise ValueError(f"Entity '{entity_id}' not found in registry")
            
            related_ids = self._relationships.get(entity_id, [])
            return [
                self._entities[rid] 
                for rid in related_ids 
                if rid in self._entities
            ]
    
    def remove(self, entity_id: str) -> bool:
        """Remove an entity from the registry.
        
        Also removes all aliases and relationships associated with the entity.
        
        Args:
            entity_id: The ID of the entity to remove.
            
        Returns:
            True if the entity was removed, False if it wasn't found.
        """
        with self._lock:
            if entity_id not in self._entities:
                return False
            
            entity = self._entities[entity_id]
            
            # Remove from type index
            if entity.entity_type in self._by_type:
                self._by_type[entity.entity_type] = [
                    eid for eid in self._by_type[entity.entity_type]
                    if eid != entity_id
                ]
            
            # Remove aliases
            for alias in entity.aliases:
                alias_lower = alias.lower().strip()
                if alias_lower in self._aliases:
                    del self._aliases[alias_lower]
            
            # Remove name alias
            name_lower = entity.name.lower().strip()
            if name_lower in self._aliases:
                del self._aliases[name_lower]
            
            # Remove relationships
            related_ids = self._relationships.pop(entity_id, [])
            for rid in related_ids:
                if rid in self._relationships:
                    self._relationships[rid] = [
                        eid for eid in self._relationships[rid]
                        if eid != entity_id
                    ]
            
            # Remove entity
            del self._entities[entity_id]
            
            logger.info("Removed entity '%s'", entity_id)
            return True
    
    def clear(self) -> None:
        """Clear all registered entities.
        
        Removes all entities, aliases, and relationships from the registry.
        """
        with self._lock:
            count = len(self._entities)
            self._entities.clear()
            self._by_type.clear()
            self._aliases.clear()
            self._relationships.clear()
            
            logger.info("Cleared registry (removed %d entities)", count)
    
    def count(self) -> int:
        """Get the total number of registered entities.
        
        Returns:
            Number of entities in the registry.
        """
        with self._lock:
            return len(self._entities)
    
    def count_by_type(self, entity_type: EntityType) -> int:
        """Get the number of entities of a specific type.
        
        Args:
            entity_type: The type to count.
            
        Returns:
            Number of entities of the specified type.
        """
        with self._lock:
            return len(self._by_type.get(entity_type, []))
    
    def __iter__(self) -> Iterator[Entity]:
        """Iterate over all entities in the registry.
        
        Returns:
            Iterator over all entities.
        """
        with self._lock:
            return iter(list(self._entities.values()))
    
    def __len__(self) -> int:
        """Get the number of entities in the registry.
        
        Returns:
            Number of entities.
        """
        with self._lock:
            return len(self._entities)
    
    def __contains__(self, entity_id: str) -> bool:
        """Check if an entity exists in the registry.
        
        Args:
            entity_id: The entity ID to check.
            
        Returns:
            True if the entity exists, False otherwise.
        """
        with self._lock:
            return entity_id in self._entities
    
    def to_dict(self) -> dict[str, Any]:
        """Export registry to dictionary for serialization.
        
        Creates a dictionary representation of the entire registry
        that can be serialized to JSON.
        
        Returns:
            Dictionary containing all registry data.
        """
        with self._lock:
            return {
                "entities": [
                    entity.model_dump() for entity in self._entities.values()
                ],
                "relationships": dict(self._relationships),
                "metadata": {
                    "total_count": len(self._entities),
                    "type_counts": {
                        et.value: len(eids) 
                        for et, eids in self._by_type.items()
                    }
                }
            }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EntityRegistry:
        """Create registry from dictionary.
        
        Reconstructs a registry from a serialized dictionary.
        
        Args:
            data: Dictionary containing registry data (from to_dict).
            
        Returns:
            A new EntityRegistry instance populated with the data.
            
        Example:
            >>> data = registry.to_dict()
            >>> new_registry = EntityRegistry.from_dict(data)
        """
        registry = cls()
        
        # Restore entities
        entities_data = data.get("entities", [])
        for entity_data in entities_data:
            entity_type = EntityType(entity_data.get("entity_type", ""))
            
            # Create entity based on type
            if entity_type == EntityType.USER_PERSONA:
                from specify.context.models import UserPersonaEntity
                entity = UserPersonaEntity(**entity_data)
            elif entity_type == EntityType.FEATURE:
                from specify.context.models import FeatureEntity
                entity = FeatureEntity(**entity_data)
            elif entity_type == EntityType.TECHNICAL_CONSTRAINT:
                from specify.context.models import TechnicalConstraintEntity
                entity = TechnicalConstraintEntity(**entity_data)
            elif entity_type == EntityType.SUCCESS_METRIC:
                from specify.context.models import SuccessMetricEntity
                entity = SuccessMetricEntity(**entity_data)
            elif entity_type == EntityType.NON_FUNCTIONAL_REQ:
                from specify.context.models import NonFunctionalReqEntity
                entity = NonFunctionalReqEntity(**entity_data)
            elif entity_type == EntityType.BUSINESS_GOAL:
                from specify.context.models import BusinessGoalEntity
                entity = BusinessGoalEntity(**entity_data)
            elif entity_type == EntityType.INTEGRATION:
                from specify.context.models import IntegrationEntity
                entity = IntegrationEntity(**entity_data)
            elif entity_type == EntityType.DATA_ENTITY:
                from specify.context.models import DataEntity
                entity = DataEntity(**entity_data)
            else:
                entity = Entity(**entity_data)
            
            # Register without updating
            registry._entities[entity.id] = entity
            registry._by_type[entity.entity_type].append(entity.id)
            
            # Register aliases
            for alias in entity.aliases:
                alias_lower = alias.lower().strip()
                if alias_lower:
                    registry._aliases[alias_lower] = entity.id
            
            name_lower = entity.name.lower().strip()
            if name_lower and name_lower not in registry._aliases:
                registry._aliases[name_lower] = entity.id
        
        # Restore relationships with validation
        relationships = data.get("relationships", {})
        for entity_id, related_ids in relationships.items():
            # Only restore relationships if the source entity exists
            if entity_id not in registry._entities:
                logger.warning(
                    "Skipping relationships for non-existent entity '%s'", 
                    entity_id
                )
                continue
            
            # Validate and filter related IDs to only include existing entities
            valid_related_ids = [
                rid for rid in related_ids 
                if rid in registry._entities
            ]
            
            # Log if some relationships were invalid
            if len(valid_related_ids) != len(related_ids):
                invalid_ids = set(related_ids) - set(valid_related_ids)
                logger.warning(
                    "Skipping relationships to non-existent entities: %s", 
                    invalid_ids
                )
            
            # Store relationships for this entity
            if valid_related_ids:
                registry._relationships[entity_id] = valid_related_ids
                
                # Ensure bidirectional relationships are established
                # This is needed because to_dict stores both directions,
                # but we validate each direction independently
                for related_id in valid_related_ids:
                    if entity_id not in registry._relationships[related_id]:
                        registry._relationships[related_id].append(entity_id)
        
        logger.info("Created registry from dict with %d entities", 
                   len(registry._entities))
        
        return registry
