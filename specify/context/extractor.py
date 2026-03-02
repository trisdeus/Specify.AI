"""
Hybrid Context Extractor for Specify.AI.

This module provides hybrid entity extraction that combines deterministic
(pattern-based) extraction with LLM-based extraction. It uses a two-phase
approach:
1. Fast, free deterministic extraction first
2. LLM fallback for missing or low-confidence entities

This hybrid approach optimizes for both cost (minimizing LLM calls) and
quality (ensuring comprehensive entity extraction).

Example:
    >>> from specify.context.extractor import HybridContextExtractor
    >>> from specify.providers.ollama import OllamaProvider
    >>> from specify.providers.base import ProviderConfig
    >>>
    >>> # With LLM fallback available
    >>> config = ProviderConfig(model="llama2", base_url="http://localhost:11434")
    >>> provider = OllamaProvider(config)
    >>> extractor = HybridContextExtractor(provider=provider)
    >>>
    >>> # Extract entities
    >>> context = extractor.extract("Build an admin dashboard for managing users...")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from specify.context.deterministic import DeterministicExtractor
from specify.context.llm_extractor import LLMEntityExtractor
from specify.context.models import (
    Entity,
    EntityContext,
    EntityType,
    FeatureEntity,
    UserPersonaEntity,
)
from specify.providers.base import BaseProvider

logger = logging.getLogger(__name__)


# Source tracking for entities
class ExtractionSource:
    """Source of entity extraction."""
    DETERMINISTIC = "deterministic"
    LLM = "llm"


@dataclass
class ExtractionAnalysis:
    """Analysis of extraction results to determine if LLM fallback is needed.
    
    This dataclass holds the results of analyzing deterministic extraction
    results and determines whether LLM fallback should be triggered.
    
    Attributes:
        needs_llm_fallback: Whether LLM extraction is needed for missing/low-confidence entities
        missing_types: List of entity types that have no entities extracted
        low_confidence_entities: List of entity names with confidence below threshold
        coverage_score: Percentage of expected entities found (0.0 to 1.0)
    """
    needs_llm_fallback: bool = False
    missing_types: list[str] = field(default_factory=list)
    low_confidence_entities: list[str] = field(default_factory=list)
    coverage_score: float = 0.0


class HybridContextExtractor:
    """Hybrid entity extraction: deterministic first, LLM fallback for ambiguity.
    
    This extractor combines the speed of deterministic extraction with the
    comprehensiveness of LLM extraction. It first attempts to extract entities
    using pattern matching, then analyzes the results to determine if LLM
    fallback is needed.
    
    The decision to use LLM fallback is based on:
    - Missing required entity types (user_persona, feature)
    - Entities with confidence below the threshold
    - Overall coverage score
    
    Example:
        >>> # Basic usage with LLM provider
        >>> extractor = HybridContextExtractor(provider=ollama_provider)
        >>> context = extractor.extract("Build a user authentication system...")
        >>>
        >>> # Deterministic-only (no LLM fallback)
        >>> extractor = HybridContextExtractor()
        >>> context = extractor.extract("Build a login feature...")
    """
    
    # Confidence threshold below which entities trigger LLM fallback
    CONFIDENCE_THRESHOLD: float = 0.7
    
    # Minimum number of entities required per type for successful extraction
    # Types not listed here can be empty
    MIN_ENTITIES_PER_TYPE: dict[str, int] = {
        "user_persona": 1,
        "feature": 1,
    }
    
    def __init__(self, provider: Optional[BaseProvider] = None) -> None:
        """Initialize with optional LLM provider for fallback.
        
        Args:
            provider: Optional LLM provider instance (e.g., OllamaProvider,
                     OpenAIProvider) for fallback extraction. If not provided,
                     extraction will use deterministic-only mode.
        
        Example:
            >>> # With LLM fallback
            >>> extractor = HybridContextExtractor(provider=ollama_provider)
            >>>
            >>> # Deterministic only
            >>> extractor = HybridContextExtractor()
        """
        self._deterministic_extractor = DeterministicExtractor()
        self._llm_extractor = LLMEntityExtractor(provider) if provider else None
        self._provider = provider
        
        if provider:
            logger.info("HybridContextExtractor initialized with LLM provider")
        else:
            logger.info("HybridContextExtractor initialized in deterministic-only mode")
    
    def extract(self, prompt: str) -> EntityContext:
        """Extract entities using hybrid approach.
        
        This method performs the two-phase extraction:
        1. First runs deterministic (pattern-based) extraction
        2. Analyzes results to determine if LLM fallback is needed
        3. If needed and provider available, runs LLM for missing types
        4. Merges results with deterministic taking priority for conflicts
        
        Args:
            prompt: The user prompt to extract entities from.
            
        Returns:
            EntityContext containing all extracted entities from both
            deterministic and LLM extraction (if used).
        
        Example:
            >>> extractor = HybridContextExtractor(provider=provider)
            >>> context = extractor.extract("Build an admin dashboard...")
            >>> for persona in context.user_personas:
            ...     print(f"Persona: {persona.name}")
        """
        if not prompt or not prompt.strip():
            logger.warning("Empty prompt provided to hybrid extractor")
            return EntityContext(source_prompt=prompt)
        
        # Phase 1: Deterministic extraction (fast, free)
        logger.info("Starting deterministic extraction...")
        deterministic_entities = self._deterministic_extractor.extract(prompt)
        
        # Convert to EntityContext for analysis
        deterministic_context = self._entities_to_context(deterministic_entities, prompt)
        
        # Phase 2: Analyze results
        analysis = self._analyze_extraction(deterministic_entities)
        
        # Phase 3: LLM fallback if needed
        if analysis.needs_llm_fallback and self._llm_extractor is not None:
            logger.info(
                f"LLM fallback needed. Missing types: {analysis.missing_types}, "
                f"Low confidence: {analysis.low_confidence_entities}"
            )
            
            try:
                llm_context = self._llm_extractor.extract(
                    prompt=prompt,
                    missing_types=analysis.missing_types
                )
                
                # Phase 4: Merge results
                merged_context = self._merge_entities(deterministic_context, llm_context)
                
                logger.info(
                    f"Hybrid extraction complete: "
                    f"{len(merged_context.user_personas)} personas, "
                    f"{len(merged_context.features)} features, "
                    f"coverage: {analysis.coverage_score:.1%}"
                )
                
                return merged_context
                
            except Exception as e:
                logger.error(f"LLM fallback failed: {e}. Using deterministic results only.")
                return deterministic_context
        else:
            if analysis.needs_llm_fallback:
                logger.warning(
                    "LLM fallback needed but no provider available. "
                    f"Missing types: {analysis.missing_types}"
                )
            else:
                logger.info(
                    f"Deterministic-only extraction complete: "
                    f"{len(deterministic_context.user_personas)} personas, "
                    f"{len(deterministic_context.features)} features, "
                    f"coverage: {analysis.coverage_score:.1%}"
                )
            
            return deterministic_context
    
    def _analyze_extraction(self, entities: list[Entity]) -> ExtractionAnalysis:
        """Analyze extraction results to determine if LLM fallback is needed.
        
        This method checks:
        - Required entity types (user_persona, feature) have at least 1 entity
        - Any entities have confidence below CONFIDENCE_THRESHOLD
        - Overall coverage score (% of expected entities found)
        
        Args:
            entities: List of entities extracted by deterministic method.
            
        Returns:
            ExtractionAnalysis with findings and recommendation.
        
        Example:
            >>> analysis = extractor._analyze_extraction(entities)
            >>> if analysis.needs_llm_fallback:
            ...     print(f"Missing: {analysis.missing_types}")
        """
        # Group entities by type
        entities_by_type: dict[str, list[Entity]] = {}
        for entity in entities:
            entity_type = entity.entity_type.value
            if entity_type not in entities_by_type:
                entities_by_type[entity_type] = []
            entities_by_type[entity_type].append(entity)
        
        # Check for missing required types
        missing_types: list[str] = []
        for entity_type, min_count in self.MIN_ENTITIES_PER_TYPE.items():
            count = len(entities_by_type.get(entity_type, []))
            if count < min_count:
                missing_types.append(entity_type)
        
        # Check for low confidence entities
        low_confidence: list[str] = []
        for entity in entities:
            if entity.confidence < self.CONFIDENCE_THRESHOLD:
                low_confidence.append(f"{entity.entity_type.value}:{entity.name}")
        
        # Calculate coverage score
        total_expected = sum(self.MIN_ENTITIES_PER_TYPE.values())
        total_found = sum(
            min(len(entities_by_type.get(et, [])), mc)
            for et, mc in self.MIN_ENTITIES_PER_TYPE.items()
        )
        coverage_score = total_found / total_expected if total_expected > 0 else 1.0
        
        # Determine if LLM fallback is needed
        needs_llm = len(missing_types) > 0 or len(low_confidence) > 0
        
        return ExtractionAnalysis(
            needs_llm_fallback=needs_llm,
            missing_types=missing_types,
            low_confidence_entities=low_confidence,
            coverage_score=coverage_score,
        )
    
    def _merge_entities(
        self,
        deterministic: EntityContext,
        llm_context: EntityContext
    ) -> EntityContext:
        """Merge deterministic and LLM extractions.
        
        Merge strategy:
        - For same entity (same name/type), keep the one with higher confidence
        - Add LLM-only entities to the result
        - Preserve source_text from both sources for traceability
        
        Args:
            deterministic: EntityContext from deterministic extraction.
            llm_context: EntityContext from LLM extraction.
            
        Returns:
            Merged EntityContext with combined entities.
        
        Example:
            >>> merged = extractor._merge_entities(det_context, llm_context)
        """
        # Start with a copy of deterministic context
        merged = EntityContext(source_prompt=deterministic.source_prompt)
        
        # Merge each entity type
        merged.user_personas = self._merge_entity_lists(
            deterministic.user_personas,
            llm_context.user_personas
        )
        merged.features = self._merge_entity_lists(
            deterministic.features,
            llm_context.features
        )
        merged.technical_constraints = self._merge_entity_lists(
            deterministic.technical_constraints,
            llm_context.technical_constraints
        )
        merged.success_metrics = self._merge_entity_lists(
            deterministic.success_metrics,
            llm_context.success_metrics
        )
        merged.non_functional_reqs = self._merge_entity_lists(
            deterministic.non_functional_reqs,
            llm_context.non_functional_reqs
        )
        merged.business_goals = self._merge_entity_lists(
            deterministic.business_goals,
            llm_context.business_goals
        )
        merged.integrations = self._merge_entity_lists(
            deterministic.integrations,
            llm_context.integrations
        )
        merged.data_entities = self._merge_entity_lists(
            deterministic.data_entities,
            llm_context.data_entities
        )
        
        # Copy other metadata
        merged.product_name = deterministic.product_name or llm_context.product_name
        merged.product_type = deterministic.product_type or llm_context.product_type
        merged.target_platform = deterministic.target_platform or llm_context.target_platform
        
        # Merge entity registry (deterministic takes priority)
        merged.entity_registry = {**llm_context.entity_registry, **deterministic.entity_registry}
        
        return merged
    
    def _merge_entity_lists(
        self,
        deterministic_list: list[Entity],
        llm_list: list[Entity]
    ) -> list[Entity]:
        """Merge two lists of entities, keeping highest confidence for duplicates.
        
        Args:
            deterministic_list: Entities from deterministic extraction.
            llm_list: Entities from LLM extraction.
            
        Returns:
            Merged list with duplicates resolved.
        """
        # Create a mapping of (entity_type, normalized_name) -> Entity
        entity_map: dict[tuple[str, str], Entity] = {}
        
        # Add deterministic entities first (they take priority)
        for entity in deterministic_list:
            key = (entity.entity_type.value, entity.name.lower())
            if key not in entity_map:
                entity_map[key] = entity
            elif entity.confidence > entity_map[key].confidence:
                # Keep the higher confidence one
                entity_map[key] = entity
        
        # Add LLM entities, but don't override deterministic if present
        for entity in llm_list:
            key = (entity.entity_type.value, entity.name.lower())
            if key not in entity_map:
                entity_map[key] = entity
            # If both exist, deterministic already has priority (added first)
        
        # Convert back to list and deduplicate further
        entities = list(entity_map.values())
        return self._deduplicate_entities(entities)
    
    def _deduplicate_entities(self, entities: list[Entity]) -> list[Entity]:
        """Remove duplicate entities, keeping highest confidence.
        
        This method performs final deduplication by checking for entities
        with the same name and type, keeping only the one with highest
        confidence.
        
        Args:
            entities: List of entities to deduplicate.
            
        Returns:
            Deduplicated list of entities.
        
        Example:
            >>> unique = extractor._deduplicate_entities(all_entities)
        """
        # Use a dict to track best entity per name+type combination
        seen: dict[str, Entity] = {}
        
        for entity in entities:
            # Create a unique key based on type and name
            key = f"{entity.entity_type.value}:{entity.name.lower()}"
            
            if key not in seen:
                seen[key] = entity
            elif entity.confidence > seen[key].confidence:
                # Replace with higher confidence version
                seen[key] = entity
            elif entity.confidence == seen[key].confidence:
                # If same confidence, merge source_text for traceability
                existing = seen[key]
                combined_sources = f"{existing.source_text} | {entity.source_text}"
                seen[key].source_text = combined_sources
        
        return list(seen.values())
    
    def _entities_to_context(
        self,
        entities: list[Entity],
        prompt: str
    ) -> EntityContext:
        """Convert a list of entities to an EntityContext.
        
        Args:
            entities: List of Entity objects.
            prompt: Source prompt string.
            
        Returns:
            EntityContext with entities organized by type.
        """
        context = EntityContext(source_prompt=prompt)
        
        for entity in entities:
            entity_type = entity.entity_type
            
            if entity_type == EntityType.USER_PERSONA:
                context.user_personas.append(entity)  # type: ignore
            elif entity_type == EntityType.FEATURE:
                context.features.append(entity)  # type: ignore
            elif entity_type == EntityType.TECHNICAL_CONSTRAINT:
                context.technical_constraints.append(entity)  # type: ignore
            elif entity_type == EntityType.SUCCESS_METRIC:
                context.success_metrics.append(entity)  # type: ignore
            elif entity_type == EntityType.NON_FUNCTIONAL_REQ:
                context.non_functional_reqs.append(entity)  # type: ignore
            elif entity_type == EntityType.BUSINESS_GOAL:
                context.business_goals.append(entity)  # type: ignore
            elif entity_type == EntityType.INTEGRATION:
                context.integrations.append(entity)  # type: ignore
            elif entity_type == EntityType.DATA_ENTITY:
                context.data_entities.append(entity)  # type: ignore
        
        return context
