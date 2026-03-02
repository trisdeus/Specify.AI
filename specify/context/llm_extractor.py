"""
LLM-based Entity Extractor for Specify.AI.

This module provides LLM-based entity extraction for cases where deterministic
extraction yields low confidence or missing entities. It uses an LLM provider
to analyze user prompts and extract structured entity information.

This is the fallback extractor used when the DeterministicExtractor cannot
sufficiently extract entities from a prompt.

Entity Types Extracted:
- User Personas: Who are the users? Include roles, characteristics, goals.
- Features: What features/capabilities are mentioned? Include priorities if stated.
- Technical Constraints: Performance targets, budget limits, uptime requirements.
- Success Metrics: KPIs, targets, measurement methods.
- Business Goals: What outcomes does the business want?
- Integrations: External systems, APIs, services mentioned.
- Data Entities: Core data objects (users, orders, products, etc.)
"""

import json
import logging
from typing import Optional

from specify.context.models import (
    BusinessGoalEntity,
    DataEntity,
    Entity,
    EntityContext,
    EntityType,
    FeatureEntity,
    IntegrationEntity,
    SuccessMetricEntity,
    TechnicalConstraintEntity,
    UserPersonaEntity,
)
from specify.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class LLMEntityExtractor:
    """LLM-based entity extraction for ambiguous cases.
    
    This extractor uses an LLM provider to analyze user prompts and extract
    structured entity information. It's used as a fallback when deterministic
    extraction yields low confidence or missing entities.
    
    The extractor sends a carefully crafted prompt to the LLM that specifies
    the entity schema and extraction guidelines, then parses the JSON response
    into structured Entity objects.
    
    Example:
        >>> from specify.providers.ollama import OllamaProvider
        >>> from specify.providers.base import ProviderConfig
        >>> 
        >>> config = ProviderConfig(model="llama2", base_url="http://localhost:11434")
        >>> provider = OllamaProvider(config)
        >>> extractor = LLMEntityExtractor(provider)
        >>> 
        >>> # Extract entities for missing types
        >>> context = await extractor.extract(
        ...     prompt="Build a dashboard for managing customer orders...",
        ...     missing_types=["user_persona", "feature"]
        ... )
    """

    # Prompt template for entity extraction
    EXTRACTION_PROMPT: str = """You are an Entity Extraction Specialist. Extract the following entity types from the user prompt:

1. **User Personas**: Who are the users? Include roles, characteristics, goals.
2. **Features**: What features/capabilities are mentioned? Include priorities if stated.
3. **Technical Constraints**: Performance targets, budget limits, uptime requirements.
4. **Success Metrics**: KPIs, targets, measurement methods.
5. **Business Goals**: What outcomes does the business want?
6. **Integrations**: External systems, APIs, services mentioned.
7. **Data Entities**: Core data objects (users, orders, products, etc.)

For each entity, provide:
- Normalized name (consistent naming)
- Description
- Original text from prompt
- Confidence level (high/medium/low)

Output as JSON following this schema:
{schema}

USER PROMPT:
{prompt}"""

    def __init__(self, provider: BaseProvider) -> None:
        """Initialize with an LLM provider.
        
        Args:
            provider: An LLM provider instance (e.g., OllamaProvider, OpenAIProvider)
                     that implements the BaseProvider interface.
        
        Example:
            >>> from specify.providers.ollama import OllamaProvider
            >>> from specify.providers.base import ProviderConfig
            >>> config = ProviderConfig(model="llama2")
            >>> provider = OllamaProvider(config)
            >>> extractor = LLMEntityExtractor(provider)
        """
        self._provider = provider

    def extract(self, prompt: str, missing_types: list[str]) -> EntityContext:
        """Extract entities using LLM for specified missing types.
        
        This method sends the user prompt to the LLM with the extraction schema
        and parses the response into an EntityContext object.
        
        Args:
            prompt: The user prompt to extract entities from.
            missing_types: List of entity types that need LLM extraction.
                          These are the types that the deterministic extractor
                          couldn't extract or had low confidence on.
        
        Returns:
            EntityContext containing all extracted entities from the LLM.
        
        Raises:
            LLMExtractionError: If the LLM call fails or response parsing fails.
        
        Example:
            >>> extractor = LLMEntityExtractor(provider)
            >>> context = await extractor.extract(
            ...     prompt="Build an e-commerce platform with user auth...",
            ...     missing_types=["user_persona", "feature", "integration"]
            ... )
            >>> for persona in context.user_personas:
            ...     print(f"Persona: {persona.name}, Role: {persona.role}")
        """
        if not prompt or not prompt.strip():
            logger.warning("Empty prompt provided to LLM extractor")
            return EntityContext(source_prompt=prompt)

        # Build the extraction prompt with schema
        schema = self._get_schema()
        extraction_prompt = self.EXTRACTION_PROMPT.format(
            schema=schema,
            prompt=prompt
        )

        logger.info(
            f"Extracting entities via LLM for types: {missing_types}"
        )

        try:
            # Call the LLM provider
            response = self._provider.generate(
                prompt=extraction_prompt,
                rules="You are a precise entity extraction system. Output ONLY valid JSON, no additional text."
            )

            # Parse the response into EntityContext
            context = self._parse_response(response)
            context.source_prompt = prompt

            logger.info(
                f"LLM extraction complete: "
                f"{len(context.user_personas)} personas, "
                f"{len(context.features)} features, "
                f"{len(context.data_entities)} data entities"
            )

            return context

        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            raise LLMExtractionError(
                f"Failed to extract entities via LLM: {e}"
            ) from e

    def _get_schema(self) -> str:
        """Return JSON schema for entity extraction response.
        
        This method provides the detailed JSON schema that the LLM should
        use for its response. It defines all the fields required for each
        entity type.
        
        Returns:
            JSON schema string defining the expected response format.
        
        Example:
            >>> schema = extractor._get_schema()
            >>> print(schema)
            {
              "user_personas": [...],
              "features": [...],
              ...
            }
        """
        schema = {
            "user_personas": [
                {
                    "name": "string - normalized name",
                    "role": "string - role title",
                    "characteristics": ["list of characteristic strings"],
                    "goals": ["list of goal strings"],
                    "source_text": "original text from prompt",
                    "confidence": "high/medium/low"
                }
            ],
            "features": [
                {
                    "name": "string - normalized feature name",
                    "description": "string - feature description",
                    "priority": "string - must/should/could/wont",
                    "dependencies": ["list of dependency feature names"],
                    "source_text": "original text from prompt",
                    "confidence": "high/medium/low"
                }
            ],
            "technical_constraints": [
                {
                    "name": "string - constraint name",
                    "constraint_type": "string - performance/security/budget/etc",
                    "value": "string - constraint value",
                    "unit": "string - unit of measurement (optional)",
                    "source_text": "original text from prompt",
                    "confidence": "high/medium/low"
                }
            ],
            "success_metrics": [
                {
                    "name": "string - metric name",
                    "metric_name": "string - technical metric name",
                    "target_value": "string - target value",
                    "measurement_method": "string - how to measure",
                    "source_text": "original text from prompt",
                    "confidence": "high/medium/low"
                }
            ],
            "business_goals": [
                {
                    "name": "string - goal name",
                    "description": "string - goal description",
                    "outcome": "string - business outcome",
                    "source_text": "original text from prompt",
                    "confidence": "high/medium/low"
                }
            ],
            "integrations": [
                {
                    "name": "string - integration name",
                    "integration_type": "string - api/service/platform/library",
                    "provider": "string - provider name (optional)",
                    "source_text": "original text from prompt",
                    "confidence": "high/medium/low"
                }
            ],
            "data_entities": [
                {
                    "name": "string - entity name",
                    "attributes": ["list of attribute names"],
                    "relationships": ["list of relationship descriptions"],
                    "source_text": "original text from prompt",
                    "confidence": "high/medium/low"
                }
            ]
        }
        return json.dumps(schema, indent=2)

    def _parse_response(self, response: str) -> EntityContext:
        """Parse LLM JSON response into EntityContext.
        
        This method extracts the JSON from the LLM response and converts it
        into Entity objects. It handles various response formats and errors
        gracefully.
        
        Args:
            response: The raw text response from the LLM provider.
        
        Returns:
            EntityContext populated with entities parsed from the response.
        
        Raises:
            LLMExtractionError: If JSON parsing fails or response is invalid.
        """
        # Try to extract JSON from response (handle markdown code blocks)
        json_str = self._extract_json(response)

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            raise LLMExtractionError(
                f"Invalid JSON response from LLM: {e}"
            ) from e

        # Validate response structure
        if not isinstance(data, dict):
            raise LLMExtractionError(
                "Expected JSON object in LLM response, got other type"
            )

        # Extract and validate entities by type
        entities = {
            "user_personas": data.get("user_personas", []),
            "features": data.get("features", []),
            "technical_constraints": data.get("technical_constraints", []),
            "success_metrics": data.get("success_metrics", []),
            "business_goals": data.get("business_goals", []),
            "integrations": data.get("integrations", []),
            "data_entities": data.get("data_entities", []),
        }

        # Validate and convert each entity type
        validated = self._validate_entities(entities)

        # Create EntityContext with validated entities
        return EntityContext(
            source_prompt="",
            user_personas=validated.get("user_personas", []),
            features=validated.get("features", []),
            technical_constraints=validated.get("technical_constraints", []),
            success_metrics=validated.get("success_metrics", []),
            business_goals=validated.get("business_goals", []),
            integrations=validated.get("integrations", []),
            data_entities=validated.get("data_entities", []),
        )

    def _extract_json(self, response: str) -> str:
        """Extract JSON from LLM response, handling markdown code blocks.
        
        The LLM may wrap JSON in markdown code blocks (```json ... ```).
        This method extracts the JSON portion from such responses.
        
        Args:
            response: Raw response text from LLM.
        
        Returns:
            Cleaned JSON string ready for parsing.
        """
        # Remove markdown code blocks if present
        response = response.strip()
        
        # Check for markdown code block
        if response.startswith("```"):
            # Find the closing ```
            lines = response.split("\n")
            json_lines = []
            in_json_block = False
            
            for line in lines:
                if line.strip().startswith("```"):
                    in_json_block = not in_json_block
                    continue
                if in_json_block:
                    json_lines.append(line)
            
            if json_lines:
                response = "\n".join(json_lines)
        
        return response.strip()

    def _validate_entities(self, entities: dict[str, list[dict]]) -> dict[str, list[Entity]]:
        """Validate and convert dict entities to Entity objects.
        
        This method takes the raw dictionary entities from the LLM response
        and validates each one before converting to the appropriate Entity
        subclass. Invalid entities are logged and skipped.
        
        Args:
            entities: Dictionary mapping entity type to list of entity dicts.
        
        Returns:
            Dictionary mapping entity type to list of validated Entity objects.
        
        Example:
            >>> validated = extractor._validate_entities({
            ...     "user_personas": [{"name": "Admin", "role": "Administrator", ...}]
            ... })
            >>> print(type(validated["user_personas"][0]))
            <class 'UserPersonaEntity'>
        """
        validated: dict[str, list[Entity]] = {
            "user_personas": [],
            "features": [],
            "technical_constraints": [],
            "success_metrics": [],
            "business_goals": [],
            "integrations": [],
            "data_entities": [],
        }

        # Validate user personas
        for item in entities.get("user_personas", []):
            entity = self._create_user_persona(item)
            if entity:
                validated["user_personas"].append(entity)

        # Validate features
        for item in entities.get("features", []):
            entity = self._create_feature(item)
            if entity:
                validated["features"].append(entity)

        # Validate technical constraints
        for item in entities.get("technical_constraints", []):
            entity = self._create_technical_constraint(item)
            if entity:
                validated["technical_constraints"].append(entity)

        # Validate success metrics
        for item in entities.get("success_metrics", []):
            entity = self._create_success_metric(item)
            if entity:
                validated["success_metrics"].append(entity)

        # Validate business goals
        for item in entities.get("business_goals", []):
            entity = self._create_business_goal(item)
            if entity:
                validated["business_goals"].append(entity)

        # Validate integrations
        for item in entities.get("integrations", []):
            entity = self._create_integration(item)
            if entity:
                validated["integrations"].append(entity)

        # Validate data entities
        for item in entities.get("data_entities", []):
            entity = self._create_data_entity(item)
            if entity:
                validated["data_entities"].append(entity)

        return validated

    def _create_user_persona(self, data: dict) -> Optional[UserPersonaEntity]:
        """Create a UserPersonaEntity from dictionary data.
        
        Args:
            data: Dictionary with user persona fields.
        
        Returns:
            UserPersonaEntity or None if validation fails.
        """
        # Validate required fields
        if not data.get("name"):
            logger.warning("UserPersona missing required 'name' field, skipping")
            return None

        try:
            confidence = self._parse_confidence(data.get("confidence", "medium"))
            
            return UserPersonaEntity(
                id=f"user_persona_{data['name'].lower().replace(' ', '_')}",
                name=data["name"],
                description=data.get("description", ""),
                source_text=data.get("source_text", ""),
                confidence=confidence,
                role=data.get("role"),
                characteristics=data.get("characteristics", []),
                goals=data.get("goals", []),
            )
        except Exception as e:
            logger.warning(f"Failed to create UserPersonaEntity: {e}")
            return None

    def _create_feature(self, data: dict) -> Optional[FeatureEntity]:
        """Create a FeatureEntity from dictionary data.
        
        Args:
            data: Dictionary with feature fields.
        
        Returns:
            FeatureEntity or None if validation fails.
        """
        # Validate required fields
        if not data.get("name"):
            logger.warning("Feature missing required 'name' field, skipping")
            return None

        try:
            confidence = self._parse_confidence(data.get("confidence", "medium"))
            
            return FeatureEntity(
                id=f"feature_{data['name'].lower().replace(' ', '_')}",
                name=data["name"],
                description=data.get("description", ""),
                source_text=data.get("source_text", ""),
                confidence=confidence,
                priority=data.get("priority"),
                dependencies=data.get("dependencies", []),
            )
        except Exception as e:
            logger.warning(f"Failed to create FeatureEntity: {e}")
            return None

    def _create_technical_constraint(self, data: dict) -> Optional[TechnicalConstraintEntity]:
        """Create a TechnicalConstraintEntity from dictionary data.
        
        Args:
            data: Dictionary with technical constraint fields.
        
        Returns:
            TechnicalConstraintEntity or None if validation fails.
        """
        # Validate required fields
        if not data.get("name"):
            logger.warning("TechnicalConstraint missing required 'name' field, skipping")
            return None

        try:
            confidence = self._parse_confidence(data.get("confidence", "medium"))
            
            return TechnicalConstraintEntity(
                id=f"technical_constraint_{data['name'].lower().replace(' ', '_')}",
                name=data["name"],
                description=data.get("description", ""),
                source_text=data.get("source_text", ""),
                confidence=confidence,
                constraint_type=data.get("constraint_type", "other"),
                value=data.get("value", ""),
                unit=data.get("unit"),
            )
        except Exception as e:
            logger.warning(f"Failed to create TechnicalConstraintEntity: {e}")
            return None

    def _create_success_metric(self, data: dict) -> Optional[SuccessMetricEntity]:
        """Create a SuccessMetricEntity from dictionary data.
        
        Args:
            data: Dictionary with success metric fields.
        
        Returns:
            SuccessMetricEntity or None if validation fails.
        """
        # Validate required fields
        if not data.get("name"):
            logger.warning("SuccessMetric missing required 'name' field, skipping")
            return None

        try:
            confidence = self._parse_confidence(data.get("confidence", "medium"))
            
            return SuccessMetricEntity(
                id=f"success_metric_{data['name'].lower().replace(' ', '_')}",
                name=data["name"],
                description=data.get("description", ""),
                source_text=data.get("source_text", ""),
                confidence=confidence,
                metric_name=data.get("metric_name", data["name"]),
                target_value=data.get("target_value", ""),
                measurement_method=data.get("measurement_method"),
            )
        except Exception as e:
            logger.warning(f"Failed to create SuccessMetricEntity: {e}")
            return None

    def _create_business_goal(self, data: dict) -> Optional[BusinessGoalEntity]:
        """Create a BusinessGoalEntity from dictionary data.
        
        Args:
            data: Dictionary with business goal fields.
        
        Returns:
            BusinessGoalEntity or None if validation fails.
        """
        # Validate required fields
        if not data.get("name"):
            logger.warning("BusinessGoal missing required 'name' field, skipping")
            return None

        try:
            confidence = self._parse_confidence(data.get("confidence", "medium"))
            
            return BusinessGoalEntity(
                id=f"business_goal_{data['name'].lower().replace(' ', '_')}",
                name=data["name"],
                description=data.get("description", ""),
                source_text=data.get("source_text", ""),
                confidence=confidence,
                outcome=data.get("outcome", ""),
            )
        except Exception as e:
            logger.warning(f"Failed to create BusinessGoalEntity: {e}")
            return None

    def _create_integration(self, data: dict) -> Optional[IntegrationEntity]:
        """Create an IntegrationEntity from dictionary data.
        
        Args:
            data: Dictionary with integration fields.
        
        Returns:
            IntegrationEntity or None if validation fails.
        """
        # Validate required fields
        if not data.get("name"):
            logger.warning("Integration missing required 'name' field, skipping")
            return None

        try:
            confidence = self._parse_confidence(data.get("confidence", "medium"))
            
            return IntegrationEntity(
                id=f"integration_{data['name'].lower().replace(' ', '_')}",
                name=data["name"],
                description=data.get("description", ""),
                source_text=data.get("source_text", ""),
                confidence=confidence,
                integration_type=data.get("integration_type", "api"),
                provider=data.get("provider"),
            )
        except Exception as e:
            logger.warning(f"Failed to create IntegrationEntity: {e}")
            return None

    def _create_data_entity(self, data: dict) -> Optional[DataEntity]:
        """Create a DataEntity from dictionary data.
        
        Args:
            data: Dictionary with data entity fields.
        
        Returns:
            DataEntity or None if validation fails.
        """
        # Validate required fields
        if not data.get("name"):
            logger.warning("DataEntity missing required 'name' field, skipping")
            return None

        try:
            confidence = self._parse_confidence(data.get("confidence", "medium"))
            
            return DataEntity(
                id=f"data_entity_{data['name'].lower().replace(' ', '_')}",
                name=data["name"],
                description=data.get("description", ""),
                source_text=data.get("source_text", ""),
                confidence=confidence,
                attributes=data.get("attributes", []),
                relationships=data.get("relationships", []),
            )
        except Exception as e:
            logger.warning(f"Failed to create DataEntity: {e}")
            return None

    def _parse_confidence(self, confidence_str: str) -> float:
        """Parse confidence string to float value.
        
        Args:
            confidence_str: Confidence string (high/medium/low or numeric string).
        
        Returns:
            Confidence value between 0.0 and 1.0.
        """
        if not confidence_str:
            return 0.5

        confidence_str = str(confidence_str).lower().strip()

        # Handle string confidence levels
        confidence_map = {
            "high": 0.9,
            "medium": 0.6,
            "low": 0.3,
        }

        if confidence_str in confidence_map:
            return confidence_map[confidence_str]

        # Try to parse as numeric
        try:
            value = float(confidence_str)
            return max(0.0, min(1.0, value))
        except (ValueError, TypeError):
            return 0.5


class LLMExtractionError(Exception):
    """Exception raised when LLM entity extraction fails.
    
    This exception is raised when:
    - The LLM provider fails to generate a response
    - The response cannot be parsed as valid JSON
    - The response structure is invalid
    - Entity validation fails
    
    Attributes:
        message: Human-readable error message
    """
    
    def __init__(self, message: str) -> None:
        """Initialize the exception with a message.
        
        Args:
            message: Error message describing what went wrong.
        """
        self.message = message
        super().__init__(self.message)
