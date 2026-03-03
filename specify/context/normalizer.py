"""
Entity Normalizer for Specify.AI.

This module provides the EntityNormalizer class that normalizes entity names
and descriptions for consistency across all generated documents.

The normalizer ensures that:
- Entity names follow consistent formatting rules
- Common terms are mapped to canonical forms
- Entity IDs are generated consistently based on normalized names
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from specify.context.models import Entity, EntityType

# Configure module logger
logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from typing import Any


class EntityNormalizer:
    """Normalizes entity names and descriptions for consistency.
    
    This class provides normalization utilities that ensure entity names
    and identifiers are consistent across all generated documents. It
    applies term mappings, generates deterministic IDs, and supports
    custom term mappings for domain-specific terminology.
    
    Attributes:
        TERM_MAPPINGS: Dictionary mapping variant terms to canonical forms.
    
    Example:
        >>> normalizer = EntityNormalizer()
        >>> normalizer.normalize_name("admin user")
        'Administrator'
        >>> normalizer.generate_id("Admin User", EntityType.USER_PERSONA)
        'user_persona_administrator'
    """
    
    # Standard term mappings for consistency
    # Maps variant forms to canonical entity names
    TERM_MAPPINGS: dict[str, str] = {
        # User persona terms
        "user": "user",
        "customer": "user",
        "end user": "user",
        "end-user": "user",
        "client": "user",
        "buyer": "user",
        "subscriber": "user",
        "member": "user",
        
        # Administrator terms
        "admin": "administrator",
        "administrator": "administrator",
        "admin user": "administrator",
        "admin-user": "administrator",
        "superuser": "administrator",
        "super user": "administrator",
        "sysadmin": "administrator",
        "system administrator": "administrator",
        
        # Manager terms
        "manager": "manager",
        "admin manager": "manager",
        "project manager": "manager",
        
        # Developer terms
        "developer": "developer",
        "dev": "developer",
        "programmer": "developer",
        "engineer": "developer",
        "software developer": "developer",
        
        # Feature terms
        "functionality": "feature",
        "capability": "feature",
        "function": "feature",
        
        # Integration terms
        "api": "api",
        "service": "service",
        "integration": "integration",
        "third party": "third party",
        "third-party": "third party",
        "external": "external",
    }
    
    def __init__(self) -> None:
        """Initialize the EntityNormalizer."""
        self._term_mappings = self.TERM_MAPPINGS.copy()
        logger.debug("EntityNormalizer initialized with %d term mappings", 
                    len(self._term_mappings))
    
    def normalize_name(self, name: str) -> str:
        """Normalize entity name to consistent format.
        
        Applies the following normalization rules:
        1. Convert to lowercase and strip whitespace
        2. Apply term mappings for variant synonyms
        3. Convert to title case for display
        
        Args:
            name: The original entity name to normalize.
            
        Returns:
            Normalized entity name in title case.
            
        Example:
            >>> normalizer.normalize_name("ADMIN USER")
            'Administrator'
            >>> normalizer.normalize_name("end-user")
            'User'
        """
        if not name:
            return ""
        
        # Lowercase and strip whitespace
        normalized = name.lower().strip()
        
        # Apply term mappings (try exact match first, then partial)
        if normalized in self._term_mappings:
            normalized = self._term_mappings[normalized]
        else:
            # Try to find partial matches
            for variant, canonical in self._term_mappings.items():
                if variant in normalized or normalized in variant:
                    normalized = canonical
                    break
        
        # Convert to title case for display
        # Handle special cases like acronyms and hyphenated words
        normalized = self._to_title_case(normalized)
        
        logger.debug("Normalized name '%s' to '%s'", name, normalized)
        return normalized
    
    def _to_title_case(self, text: str) -> str:
        """Convert text to title case with special handling.
        
        Handles hyphenated words and common acronyms.
        
        Args:
            text: Text to convert to title case.
            
        Returns:
            Title-cased text.
        """
        # Split on hyphens to handle hyphenated words
        parts = text.split('-')
        title_parts = []
        
        for part in parts:
            # Skip common prepositions/articles in certain contexts
            if part in ('a', 'an', 'the', 'and', 'but', 'or', 'for', 'nor', 
                       'on', 'at', 'to', 'from', 'by'):
                title_parts.append(part)
            else:
                title_parts.append(part.title())
        
        result = '-'.join(title_parts)
        
        # Ensure common acronyms are uppercase
        acronyms = ['API', 'ID', 'SSO', 'REST', 'JSON', 'XML', 'SQL', 'HTTP', 'HTTPS']
        for acronym in acronyms:
            if result.lower() == acronym.lower():
                return acronym
        
        return result
    
    def generate_id(self, name: str, entity_type: EntityType) -> str:
        """Generate a unique, consistent ID for an entity.
        
        Generates an ID by:
        1. Normalizing the name (lowercase, remove special chars)
        2. Replacing spaces with underscores
        3. Prepending the entity type
        
        Args:
            name: The entity name to generate an ID from.
            entity_type: The type of entity.
            
        Returns:
            A unique identifier string in the format: {entity_type}_{normalized_name}
            
        Example:
            >>> normalizer.generate_id("Admin User", EntityType.USER_PERSONA)
            'user_persona_administrator'
            >>> normalizer.generate_id("User Authentication", EntityType.FEATURE)
            'feature_user_authentication'
        """
        if not name:
            return f"{entity_type.value}_unknown"
        
        # Normalize: lowercase and strip
        normalized = name.lower().strip()
        
        # Remove special characters (keep only alphanumeric and spaces)
        normalized = re.sub(r'[^a-z0-9\s]', '', normalized)
        
        # Replace spaces with underscores
        normalized = re.sub(r'\s+', '_', normalized)
        
        # Remove multiple underscores
        normalized = re.sub(r'_+', '_', normalized)
        
        # Strip leading/trailing underscores
        normalized = normalized.strip('_')
        
        # Handle empty result
        if not normalized:
            return f"{entity_type.value}_unknown"
        
        entity_id = f"{entity_type.value}_{normalized}"
        
        logger.debug("Generated ID '%s' for name '%s' and type '%s'", 
                    entity_id, name, entity_type.value)
        return entity_id
    
    def normalize_entity(self, entity: Entity) -> Entity:
        """Normalize an entity in place (return a copy).
        
        Creates a normalized copy of the entity with:
        - Normalized name
        - Updated ID based on normalized name
        
        Args:
            entity: The entity to normalize.
            
        Returns:
            A new Entity with normalized name and ID.
            
        Example:
            >>> entity = Entity(
            ...     id="user_persona_admin",
            ...     entity_type=EntityType.USER_PERSONA,
            ...     name="Admin User",
            ...     description="System admin",
            ...     source_text="admin users should...",
            ...     confidence=0.9
            ... )
            >>> normalized = normalizer.normalize_entity(entity)
            >>> normalized.name
            'Administrator'
            >>> normalized.id
            'user_persona_administrator'
        """
        # Create a copy to avoid mutating the original
        normalized_entity = entity.model_copy(deep=True)
        
        # Normalize the name
        normalized_name = self.normalize_name(entity.name)
        normalized_entity.name = normalized_name
        
        # Generate new ID based on normalized name
        normalized_entity.id = self.generate_id(normalized_name, entity.entity_type)
        
        logger.info("Normalized entity '%s' (ID: %s) to name '%s' (ID: %s)",
                   entity.name, entity.id, normalized_entity.name, normalized_entity.id)
        
        return normalized_entity
    
    def add_term_mapping(self, variant: str, canonical: str) -> None:
        """Add a custom term mapping.
        
        Allows adding domain-specific term mappings for normalization.
        
        Args:
            variant: The variant term to map from (e.g., "end user").
            canonical: The canonical term to map to (e.g., "user").
            
        Example:
            >>> normalizer.add_term_mapping("purchaser", "user")
            >>> normalizer.normalize_name("purchaser")
            'User'
        """
        variant_normalized = variant.lower().strip()
        canonical_normalized = canonical.lower().strip()
        
        self._term_mappings[variant_normalized] = canonical_normalized
        
        logger.info("Added term mapping: '%s' -> '%s'", 
                   variant_normalized, canonical_normalized)
    
    def remove_term_mapping(self, variant: str) -> bool:
        """Remove a custom term mapping.
        
        Args:
            variant: The variant term to remove.
            
        Returns:
            True if the mapping was removed, False if it wasn't found.
        """
        variant_normalized = variant.lower().strip()
        
        if variant_normalized in self._term_mappings:
            del self._term_mappings[variant_normalized]
            logger.info("Removed term mapping for '%s'", variant_normalized)
            return True
        
        return False
    
    def get_term_mappings(self) -> dict[str, str]:
        """Get a copy of all current term mappings.
        
        Returns:
            Dictionary of current term mappings.
        """
        return self._term_mappings.copy()
    
    def clear_custom_mappings(self) -> None:
        """Clear all custom term mappings, restoring defaults."""
        self._term_mappings = self.TERM_MAPPINGS.copy()
        logger.info("Cleared all custom term mappings, restored defaults")
