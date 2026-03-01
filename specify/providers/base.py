"""
Base provider interface for LLM providers in Specify.AI.

This module provides the abstract base class and configuration models for
LLM provider clients (Ollama, OpenAI, Anthropic).

Example usage:
    >>> from specify.providers import ProviderConfig, get_default_factory
    >>> config = ProviderConfig.from_env("openai", "gpt-4")
    >>> factory = get_default_factory()
    >>> provider = factory.create("openai", config)
    >>> response = await provider.generate("Hello", "Be concise.")
"""

from __future__ import annotations

import os
import threading
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, field_validator

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


# Mapping of provider names to their environment variable names
_PROVIDER_ENV_VAR_MAPPING: dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "ollama": "OLLAMA_HOST",
}


# =============================================================================
# Provider Exceptions
# =============================================================================


class ProviderError(Exception):
    """Base exception for all provider-related errors.

    This exception is raised when:
    - Any generic provider error occurs that doesn't fit a specific category
    - Unexpected errors during provider operations
    """

    pass


class ProviderConnectionError(ProviderError):
    """Raised when network connectivity issues occur.

    This exception is raised when:
    - The API endpoint is unreachable
    - Connection timeout occurs
    - DNS resolution fails
    - Network is unavailable
    """

    pass


class ProviderAuthError(ProviderError):
    """Raised when authentication fails.

    This exception is raised when:
    - API key is invalid
    - API key is expired
    - Missing authentication credentials
    - Unauthorized access attempt
    """

    pass


class ProviderResponseError(ProviderError):
    """Raised when the provider returns an invalid or error response.

    This exception is raised when:
    - Server returns HTTP 5xx error
    - Response JSON is malformed
    - Response body is empty or unexpected format
    - API returns an error message in the response
    """

    pass


class ProviderConfigError(ProviderError):
    """Raised when provider configuration is invalid or missing.

    This exception is raised when:
    - Required environment variable is not set
    - Configuration value is invalid
    - Provider is not registered with the factory
    - Missing required configuration fields
    """

    pass


class ProviderRateLimitError(ProviderResponseError):
    """Raised when rate limit or quota is exceeded.

    This exception is raised when:
    - Too many requests in a given time period
    - Monthly API quota is exceeded
    - Request count limit is reached
    """

    pass


class ProviderContentFilterError(ProviderResponseError):
    """Raised when content policy violation occurs.

    This exception is raised when:
    - Prompt violates content safety policy
    - Response is filtered by safety system
    - Content policy violation detected
    """

    pass


# =============================================================================
# Provider Configuration
# =============================================================================


class ProviderConfig(BaseModel):
    """Configuration for LLM provider clients.

    This model holds all configuration needed to connect to and use
    an LLM provider.

    Attributes:
        model: The model identifier to use (e.g., "gpt-4", "claude-3-opus")
        api_key: Optional API key for authentication
        base_url: Optional base URL for the API endpoint
        timeout: Request timeout in seconds (1-300)
        max_retries: Maximum number of retry attempts (0-10)

    Example:
        >>> config = ProviderConfig(
        ...     model="gpt-4",
        ...     api_key="sk-...",
        ...     timeout=60,
        ...     max_retries=3
        ... )
    """

    model: str = Field(..., description="The model identifier to use")
    api_key: str | None = Field(default=None, description="Optional API key for authentication")
    base_url: str | None = Field(default=None, description="Optional base URL for the API endpoint")
    timeout: int = Field(default=60, ge=1, le=300, description="Request timeout in seconds (1-300)")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum number of retry attempts (0-10)")

    model_config = ConfigDict(frozen=False, extra="forbid")

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        """Validate that model name is not empty."""
        if not v or not v.strip():
            raise ValueError("model cannot be empty")
        return v.strip()

    @classmethod
    def from_env(cls, provider_name: str, model: str) -> ProviderConfig:
        """Create ProviderConfig from environment variables.

        Reads configuration from environment variables based on the provider name.

        Args:
            provider_name: Name of the provider ("openai", "anthropic", "ollama")
            model: The model identifier to use

        Returns:
            ProviderConfig instance with values from environment

        Raises:
            ProviderConfigError: If required environment variable is not set

        Example:
            >>> config = ProviderConfig.from_env("openai", "gpt-4")
            >>> # Reads OPENAI_API_KEY from environment
        """
        env_var_name = _PROVIDER_ENV_VAR_MAPPING.get(provider_name.lower())

        if env_var_name is None:
            raise ProviderConfigError(
                f"Unknown provider: {provider_name}. "
                f"Valid providers: {list(_PROVIDER_ENV_VAR_MAPPING.keys())}"
            )

        # For ollama, we use OLLAMA_HOST as the base URL, not api_key
        if provider_name.lower() == "ollama":
            base_url = os.environ.get(env_var_name, "http://localhost:11434")
            return cls(model=model, base_url=base_url, timeout=60, max_retries=3)

        api_key = os.environ.get(env_var_name)
        if api_key is None:
            raise ProviderConfigError(
                f"Environment variable {env_var_name} is not set. "
                f"Please set it with your {provider_name.title()} API key."
            )

        return cls(model=model, api_key=api_key, timeout=60, max_retries=3)


# =============================================================================
# Abstract Base Provider
# =============================================================================


class BaseProvider(ABC):
    """Abstract base class for LLM provider clients.

    This class defines the interface that all LLM provider implementations
    must follow. It provides async methods for generating text and streaming
    responses.

    Attributes:
        _config: The provider configuration instance

    Example:
        >>> class OpenAIProvider(BaseProvider):
        ...     async def generate(self, prompt: str, rules: str) -> str:
        ...         # Implementation here
        ...         pass
        ...
        ...     async def stream(self, prompt: str, rules: str) -> AsyncIterator[str]:
        ...         # Implementation here
        ...         pass
        ...
        ...     async def validate_connection(self) -> bool:
        ...         # Implementation here
        ...         return True
    """

    def __init__(self, config: ProviderConfig) -> None:
        """Initialize the provider with configuration.

        Args:
            config: Provider configuration instance
        """
        self._config = config

    @property
    def config(self) -> ProviderConfig:
        """Get the provider configuration.

        Returns:
            The ProviderConfig instance
        """
        return self._config

    @abstractmethod
    async def generate(self, prompt: str, rules: str) -> str:
        """Generate a response from the LLM.

        Args:
            prompt: The user prompt to send to the LLM
            rules: Additional rules or instructions for the LLM

        Returns:
            The generated text response from the LLM

        Raises:
            ProviderError: If an error occurs during generation
        """
        ...

    @abstractmethod
    async def stream(self, prompt: str, rules: str) -> AsyncIterator[str]:
        """Stream a response from the LLM token by token.

        Args:
            prompt: The user prompt to send to the LLM
            rules: Additional rules or instructions for the LLM

        Yields:
            Individual tokens/chunks of the generated response

        Raises:
            ProviderError: If an error occurs during streaming
        """
        ...

    @abstractmethod
    async def validate_connection(self) -> bool:
        """Validate that the provider connection is working.

        This method should attempt to connect to the provider and
        verify that authentication and connectivity are working.

        Returns:
            True if connection is valid, False otherwise

        Raises:
            ProviderError: If an error occurs during validation
        """
        ...

    def _build_request(self, prompt: str, rules: str) -> dict:
        """Build the request payload for the LLM API.

        This is a protected method that constructs the common request
        structure. Subclasses can override or extend this method.

        Args:
            prompt: The user prompt
            rules: Additional rules or instructions

        Returns:
            Dictionary containing the request payload

        Example:
            >>> request = self._build_request("Hello", "Be concise")
            >>> # Returns: {"prompt": "Hello", "rules": "Be concise", ...}
        """
        return {
            "model": self._config.model,
            "prompt": prompt,
            "rules": rules,
            "timeout": self._config.timeout,
            "max_retries": self._config.max_retries,
        }


# =============================================================================
# Provider Factory
# =============================================================================


class ProviderFactory:
    """Factory for creating and managing LLM provider instances.

    This class implements a registry pattern for providers, allowing
    dynamic registration and creation of provider clients.

    Attributes:
        _registry: Dictionary mapping provider names to provider classes

    Example:
        >>> from specify.providers import ProviderFactory, ProviderConfig
        >>> from specify.providers.ollama import OllamaProvider
        >>>
        >>> factory = ProviderFactory()
        >>> factory.register("ollama", OllamaProvider)
        >>> config = ProviderConfig.from_env("ollama", "llama2")
        >>> provider = factory.create("ollama", config)
    """

    def __init__(self) -> None:
        """Initialize the provider factory with an empty registry."""
        self._registry: dict[str, type[BaseProvider]] = {}

    def register(self, name: str, provider_class: type[BaseProvider]) -> None:
        """Register a provider class with the factory.

        Args:
            name: Provider name (e.g., "openai", "anthropic", "ollama")
            provider_class: Provider class to register

        Raises:
            ProviderConfigError: If a provider with this name is already registered

        Example:
            >>> factory.register("openai", OpenAIProvider)
        """
        name_lower = name.lower()
        if name_lower in self._registry:
            raise ProviderConfigError(
                f"Provider '{name}' is already registered. "
                f"Use a different name or unregister first."
            )

        if not issubclass(provider_class, BaseProvider):
            raise ProviderConfigError(
                f"Provider class must be a subclass of BaseProvider, "
                f"got {provider_class.__name__}"
            )

        self._registry[name_lower] = provider_class

    def unregister(self, name: str) -> None:
        """Unregister a provider from the factory.

        Args:
            name: Provider name to unregister (e.g., "openai")

        Raises:
            ProviderConfigError: If provider is not registered

        Example:
            >>> factory.unregister("openai")
        """
        name_lower = name.lower()
        if name_lower not in self._registry:
            raise ProviderConfigError(f"Provider '{name}' is not registered")
        del self._registry[name_lower]

    def create(self, name: str, config: ProviderConfig) -> BaseProvider:
        """Create a provider instance.

        Args:
            name: Provider name (e.g., "openai", "anthropic", "ollama")
            config: Provider configuration

        Returns:
            Instance of the requested provider

        Raises:
            ProviderConfigError: If provider is not registered

        Example:
            >>> config = ProviderConfig(model="gpt-4", api_key="sk-...")
            >>> provider = factory.create("openai", config)
        """
        name_lower = name.lower()
        if name_lower not in self._registry:
            available = self.get_available_providers()
            raise ProviderConfigError(
                f"Provider '{name}' is not registered. "
                f"Available providers: {available}"
            )

        provider_class = self._registry[name_lower]
        return provider_class(config)

    def get_available_providers(self) -> list[str]:
        """Get list of registered provider names.

        Returns:
            List of provider names

        Example:
            >>> factory.get_available_providers()
            ['openai', 'anthropic', 'ollama']
        """
        return list(self._registry.keys())

    def is_registered(self, name: str) -> bool:
        """Check if a provider is registered.

        Args:
            name: Provider name to check

        Returns:
            True if registered, False otherwise

        Example:
            >>> factory.is_registered("openai")
            True
        """
        return name.lower() in self._registry


# =============================================================================
# Global Factory Singleton
# =============================================================================

_default_factory: ProviderFactory | None = None
_factory_lock = threading.Lock()


def get_default_factory() -> ProviderFactory:
    """Get the default global provider factory instance.

    This function implements a singleton pattern, returning the same
    factory instance across all calls.

    Returns:
        The global ProviderFactory instance

    Example:
        >>> factory = get_default_factory()
        >>> factory.register("openai", OpenAIProvider)
    """
    global _default_factory
    if _default_factory is None:
        with _factory_lock:
            if _default_factory is None:
                _default_factory = ProviderFactory()
    return _default_factory
