"""
Deterministic Entity Extractor for Specify.AI.

This module provides pattern-based entity extraction without LLM calls.
It uses regex patterns to extract entities from user prompts in a fast,
deterministic, and free manner.

Entity Types Extracted:
- user_persona: Users, customers, admins, managers, developers with names/roles
- feature: Features, functionalities, capabilities
- technical_constraint: Latency, budget, uptime, performance targets
- success_metric: KPIs, metrics, goals, targets with percentages/values
"""

import re
from typing import Optional

from .models import (
    Entity,
    EntityType,
    UserPersonaEntity,
    FeatureEntity,
    TechnicalConstraintEntity,
    SuccessMetricEntity,
)


class DeterministicExtractor:
    """Pattern-based entity extraction without LLM calls.
    
    This extractor uses regex patterns to identify and extract entities
    from user prompts. It's fast, deterministic, and doesn't require
    any external API calls.
    
    Example:
        >>> extractor = DeterministicExtractor()
        >>> entities = extractor.extract("Build an admin dashboard with user named John")
        >>> for entity in entities:
        ...     print(f"{entity.name}: {entity.entity_type}")
    """

    # Patterns for entity extraction, organized by entity type
    # Each entity type has multiple patterns for comprehensive matching
    PATTERNS: dict[str, list[str]] = {
        "user_persona": [
            # Pattern: "user named John" or "admin named John"
            r"(?i)(?:user|customer|admin|manager|developer)\s+(?:named\s+)?['\"]?([A-Z][a-z]+)['\"]?",
            # Pattern: "as a developer" or "for the user"
            r"(?i)(?:as\s+a|for\s+(?:the\s+)?)\s*([a-z]+\s+(?:user|customer|admin|manager|developer))",
            # Pattern: "target audience includes..."
            r"(?i)(?:target\s+)?(?:audience|user)s?\s*(?:include|are|is|:)\s*([^.]+)",
            # Pattern: "persona: developer"
            r"(?i)(?:persona|role)[\s:]+([a-z]+)",
        ],
        "feature": [
            # Pattern: "feature called Login" or "functionality named Authentication"
            r"(?i)(?:feature|functionality|capability)(?:\s+called|\s+named)?\s*['\"]?([a-zA-Z\s]+)['\"]?",
            # Pattern: "ability to process payments" or "allow users to upload"
            r"(?i)(?:ability\s+to|allow\s+(?:users?\s+)?to|enable\s+(?:users?\s+)?to)\s+([^.]+)",
            # Pattern: "must have authentication" or "should include reporting"
            r"(?i)(?:must|should|need\s+to)\s+(?:have\s+|include\s+|support\s+)?([^.]+)",
            # Pattern: "the system should support OAuth"
            r"(?i)(?:system|app|application)\s+(?:must|should|needs?\s+to)\s+([^.]+)",
        ],
        "technical_constraint": [
            # Pattern: "latency under 200ms" or "response time less than 2 seconds"
            r"(?i)(?:latency|response\s+time)\s*(?:<|less\s+than|under|below)\s*(\d+\s*(?:ms|seconds?|s))",
            # Pattern: "budget under $10k" or "cost less than 5000 per month"
            r"(?i)(?:budget|cost)\s*(?:<|less\s+than|under|below|max)\s*(\$?\d+(?:k|K|,)?(?:\s*(?:per\s+month|\/month|monthly))?)",
            # Pattern: "uptime above 99.9%" or "availability greater than 99%"
            r"(?i)(?:uptime|availability)\s*(?:>|greater\s+than|above|at\s+least)\s*(\d+(?:\.\d+)?%?)",
            # Pattern: "support 1000 users" or "handle 10k requests"
            r"(?i)(?:support|handle|capacity\s+for)\s*(\d+(?:,\d+)*(?:k|K|m|M)?)\s*(?:users?|requests?|transactions?|concurrent)",
            # Pattern: "max response time of 500ms"
            r"(?i)(?:max|maximum|min|minimum)\s+(?:response\s+)?time\s+(?:of\s+)?(\d+\s*(?:ms|seconds?|s))",
        ],
        "success_metric": [
            # Pattern: "KPI: reduce latency" or "metric: improve conversion"
            r"(?i)(?:KPI|metric|goal|target)\s*(?::|is|should\s+be)\s*([^.]+)",
            # Pattern: "increase conversion by 20%" or "reduce latency by 50%"
            r"(?i)(?:increase|decrease|reduce|improve)\s+([^.]+?)\s+by\s+(\d+%)",
            # Pattern: "achieve 99.9% uptime" or "reach 50ms latency"
            r"(?i)(?:achieve|reach|hit|attain)\s+(\d+(?:\.\d+)?%?)\s+([^.]+)",
            # Pattern: "target conversion rate of 5%"
            r"(?i)(?:target|goal)\s+([^:]+?)\s+of\s+(\d+(?:\.\d+)?%?)",
        ],
    }

    def __init__(self) -> None:
        """Initialize the deterministic extractor."""
        # Compile patterns for better performance
        self._compiled_patterns: dict[str, list[re.Pattern]] = {}
        for entity_type, patterns in self.PATTERNS.items():
            self._compiled_patterns[entity_type] = [
                re.compile(pattern) for pattern in patterns
            ]

    def extract(self, prompt: str) -> list[Entity]:
        """Extract entities from the given prompt using pattern matching.
        
        Args:
            prompt: The user prompt to extract entities from.
            
        Returns:
            List of extracted Entity objects.
        """
        if not prompt or not prompt.strip():
            return []

        entities: list[Entity] = []
        seen_entity_names: set[str] = set()  # Avoid duplicates

        for entity_type, compiled_patterns in self._compiled_patterns.items():
            for pattern in compiled_patterns:
                matches = pattern.finditer(prompt)
                for match in matches:
                    entity = self._create_entity(entity_type, match, prompt)
                    if entity:
                        # Avoid duplicate entities based on name and type
                        entity_key = f"{entity.entity_type.value}:{entity.name.lower()}"
                        if entity_key not in seen_entity_names:
                            seen_entity_names.add(entity_key)
                            entities.append(entity)

        return entities

    def _create_entity(
        self, entity_type: str, match: re.Match, prompt: str
    ) -> Optional[Entity]:
        """Create an entity from a regex match.
        
        Args:
            entity_type: The type of entity to create.
            match: The regex match object.
            prompt: The original prompt for source text extraction.
            
        Returns:
            An Entity object or None if the match is invalid.
        """
        # Extract the matched text groups
        groups = match.groups()
        if not groups or not groups[0]:
            return None

        # Get the primary matched value
        primary_value = groups[0].strip()
        if not primary_value or len(primary_value) < 2:
            return None

        # Get source text (the matched portion from the prompt)
        source_text = match.group(0).strip()
        
        # Determine confidence based on pattern specificity
        confidence = self._calculate_confidence(entity_type, primary_value, groups)

        # Create entity based on type
        if entity_type == "user_persona":
            return self._create_user_persona(primary_value, source_text, confidence, groups)
        elif entity_type == "feature":
            return self._create_feature(primary_value, source_text, confidence, prompt, groups)
        elif entity_type == "technical_constraint":
            return self._create_technical_constraint(primary_value, source_text, confidence, groups)
        elif entity_type == "success_metric":
            return self._create_success_metric(primary_value, source_text, confidence, groups)

        return None

    def _create_user_persona(
        self,
        name: str,
        source_text: str,
        confidence: float,
        groups: tuple,
    ) -> UserPersonaEntity:
        """Create a UserPersonaEntity from extracted data.
        
        Args:
            name: The name or role of the persona.
            source_text: Original text from the prompt.
            confidence: Confidence score.
            groups: Regex match groups.
            
        Returns:
            A UserPersonaEntity object.
        """
        # Determine if this is a name or a role
        role_keywords = ["user", "customer", "admin", "manager", "developer", "administrator"]
        is_role = any(keyword in name.lower() for keyword in role_keywords)
        
        if is_role:
            role = name.title()
            persona_name = "User"
        else:
            role = "User"
            persona_name = name

        # Generate unique ID
        entity_id = f"user_persona_{role.lower().replace(' ', '_')}"

        return UserPersonaEntity(
            id=entity_id,
            name=persona_name,
            description=f"User persona: {name}",
            source_text=source_text,
            confidence=confidence,
            role=role,
            characteristics=[],
            goals=[],
        )

    def _create_feature(
        self,
        name: str,
        source_text: str,
        confidence: float,
        prompt: str,
        groups: tuple,
    ) -> FeatureEntity:
        """Create a FeatureEntity from extracted data.
        
        Args:
            name: The name of the feature.
            source_text: Original text from the prompt.
            confidence: Confidence score.
            prompt: The original prompt to check for priority.
            groups: Regex match groups.
            
        Returns:
            A FeatureEntity object.
        """
        # Clean up the feature name
        feature_name = name.strip()
        if len(feature_name) > 100:
            feature_name = feature_name[:100]

        # Determine priority from context
        priority = self._determine_priority(source_text)
        if not priority:
            # Check surrounding context in the prompt
            priority = self._determine_priority_from_prompt(prompt, match=source_text)

        # Generate unique ID
        entity_id = f"feature_{feature_name.lower().replace(' ', '_').replace('-', '_')}"

        return FeatureEntity(
            id=entity_id,
            name=feature_name.title(),
            description=f"Feature: {feature_name}",
            source_text=source_text,
            confidence=confidence,
            priority=priority,
            dependencies=[],
            user_stories=[],
        )

    def _create_technical_constraint(
        self,
        value: str,
        source_text: str,
        confidence: float,
        groups: tuple,
    ) -> Optional[TechnicalConstraintEntity]:
        """Create a TechnicalConstraintEntity from extracted data.
        
        Args:
            value: The constraint value.
            source_text: Original text from the prompt.
            confidence: Confidence score.
            groups: Regex match groups.
            
        Returns:
            A TechnicalConstraintEntity object or None if invalid.
        """
        # Extract value and unit
        extracted_value, unit = self._extract_value_and_unit(value)
        
        if not extracted_value:
            return None

        # Determine constraint type from source text
        constraint_type = self._determine_constraint_type(source_text)

        # Generate unique ID
        entity_id = f"technical_constraint_{constraint_type}_{extracted_value}"

        return TechnicalConstraintEntity(
            id=entity_id,
            name=f"{constraint_type.title()} Constraint",
            description=f"Technical constraint: {source_text}",
            source_text=source_text,
            confidence=confidence,
            constraint_type=constraint_type,
            value=extracted_value,
            unit=unit,
        )

    def _create_success_metric(
        self,
        value: str,
        source_text: str,
        confidence: float,
        groups: tuple,
    ) -> Optional[SuccessMetricEntity]:
        """Create a SuccessMetricEntity from extracted data.
        
        Args:
            value: The metric value or description.
            source_text: Original text from the prompt.
            confidence: Confidence score.
            groups: Regex match groups.
            
        Returns:
            A SuccessMetricEntity object or None if invalid.
        """
        # Check if we have a percentage in the groups
        target_value = None
        metric_description = value

        # Look for percentage in groups (from patterns like "increase X by 20%")
        for group in groups:
            if group and "%" in group:
                target_value = group.strip()
                break

        if not target_value:
            # Try to extract from value string
            target_value, _ = self._extract_value_and_unit(value)
            if target_value and "%" not in target_value:
                # If we found a number but no %, the metric description might be in groups
                if len(groups) > 1 and groups[1]:
                    metric_description = f"{groups[1].strip()} {value}"

        # Generate unique ID
        metric_name = self._generate_metric_name(source_text)
        entity_id = f"success_metric_{metric_name}"

        return SuccessMetricEntity(
            id=entity_id,
            name=metric_name.replace("_", " ").title(),
            description=f"Success metric: {source_text}",
            source_text=source_text,
            confidence=confidence,
            metric_name=metric_name,
            target_value=target_value or value,
            measurement_method=None,
        )

    def _determine_priority(self, text: str) -> Optional[str]:
        """Determine feature priority from context (must/should/could).
        
        Args:
            text: The text to analyze for priority indicators.
            
        Returns:
            Priority string ('must', 'should', 'could') or None.
        """
        text_lower = text.lower()
        
        if "must" in text_lower or "required" in text_lower or "need to" in text_lower:
            return "must"
        elif "should" in text_lower or "recommended" in text_lower:
            return "should"
        elif "could" in text_lower or "nice to have" in text_lower:
            return "could"
        
        return None

    def _determine_priority_from_prompt(self, prompt: str, match: str) -> Optional[str]:
        """Determine priority from the prompt context around the match.
        
        Args:
            prompt: The full prompt.
            match: The matched text.
            
        Returns:
            Priority string or None.
        """
        # Find the position of the match in the prompt
        match_pos = prompt.find(match)
        if match_pos == -1:
            return None

        # Look at text before the match (up to 50 characters)
        context_start = max(0, match_pos - 50)
        context = prompt[context_start:match_pos]

        return self._determine_priority(context)

    def _extract_value_and_unit(self, text: str) -> tuple[str, Optional[str]]:
        """Extract value and unit from constraint text.
        
        Args:
            text: The text to parse (e.g., "200ms", "$5000", "99.9%").
            
        Returns:
            Tuple of (value, unit).
        """
        # Pattern for number with optional unit
        pattern = r"(\d+(?:\.\d+)?)\s*(%|[a-zA-Z]+)?"
        match = re.search(pattern, text)
        
        if match:
            value = match.group(1)
            unit = match.group(2) if match.group(2) else None
            return value, unit

        return text, None

    def _calculate_confidence(
        self, entity_type: str, primary_value: str, groups: tuple
    ) -> float:
        """Calculate confidence score based on pattern specificity.
        
        Args:
            entity_type: The type of entity.
            primary_value: The primary matched value.
            groups: All regex match groups.
            
        Returns:
            Confidence score between 0.0 and 1.0.
        """
        base_confidence = 0.7

        # Higher confidence for specific patterns
        if entity_type == "user_persona":
            # If we matched a specific name (capitalized), higher confidence
            if primary_value and primary_value[0].isupper():
                return 0.85
            return 0.75

        elif entity_type == "feature":
            # If we have multiple groups captured, higher confidence
            if len([g for g in groups if g]) > 1:
                return 0.85
            return 0.75

        elif entity_type == "technical_constraint":
            # If we have a clear value and unit, higher confidence
            value, unit = self._extract_value_and_unit(primary_value)
            if unit and value:
                return 0.9
            elif value:
                return 0.8
            return 0.7

        elif entity_type == "success_metric":
            # If we have a percentage, higher confidence
            if "%" in primary_value:
                return 0.9
            # If we captured multiple groups (value + description)
            if len([g for g in groups if g and g.strip()]) > 1:
                return 0.85
            return 0.75

        return base_confidence

    def _determine_constraint_type(self, text: str) -> str:
        """Determine the type of technical constraint from the text.
        
        Args:
            text: The source text to analyze.
            
        Returns:
            The constraint type string.
        """
        text_lower = text.lower()

        if "latency" in text_lower or "response time" in text_lower:
            return "performance"
        elif "budget" in text_lower or "cost" in text_lower:
            return "budget"
        elif "uptime" in text_lower or "availability" in text_lower:
            return "availability"
        elif "support" in text_lower or "handle" in text_lower or "capacity" in text_lower:
            return "capacity"
        elif "security" in text_lower:
            return "security"
        elif "scalab" in text_lower:
            return "scalability"

        return "performance"

    def _generate_metric_name(self, text: str) -> str:
        """Generate a metric name from the source text.
        
        Args:
            text: The source text.
            
        Returns:
            A normalized metric name.
        """
        text_lower = text.lower()
        
        # Common metric patterns
        metric_patterns = [
            ("uptime", "uptime"),
            ("availability", "availability"),
            ("latency", "latency"),
            ("response time", "response_time"),
            ("conversion", "conversion"),
            ("retention", "retention"),
            ("engagement", "engagement"),
            ("revenue", "revenue"),
            ("cost", "cost"),
            ("performance", "performance"),
            ("error rate", "error_rate"),
            ("load time", "load_time"),
        ]

        for pattern, name in metric_patterns:
            if pattern in text_lower:
                return name

        # Fallback: extract key words
        words = re.findall(r"[a-z]+", text_lower)
        if words:
            return "_".join(words[:3])

        return "metric"
