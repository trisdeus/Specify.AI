"""
LLM Provider module for Specify.AI.

This module contains LLM provider clients:
- base.py: Abstract provider interface, exceptions, and factory
- ollama.py: Ollama client (local LLM)
- openai.py: OpenAI client
- anthropic.py: Anthropic client

Example usage:
    >>> from specify.providers import ProviderConfig, get_default_factory
    >>> config = ProviderConfig.from_env("openai", "gpt-4")
    >>> factory = get_default_factory()
    >>> provider = factory.create("openai", config)
"""

from __future__ import annotations

from specify.providers.base import (
    BaseProvider,
    ProviderAuthError,
    ProviderConfig,
    ProviderConfigError,
    ProviderConnectionError,
    ProviderContentFilterError,
    ProviderError,
    ProviderFactory,
    ProviderRateLimitError,
    ProviderResponseError,
    get_default_factory,
)

from specify.providers.ollama import OllamaProvider

# Explicitly register providers with the default factory
# This ensures importing the submodule is side-effect-free
get_default_factory().register("ollama", OllamaProvider)

__all__ = [
    "BaseProvider",
    "OllamaProvider",
    "ProviderAuthError",
    "ProviderConfig",
    "ProviderConfigError",
    "ProviderConnectionError",
    "ProviderContentFilterError",
    "ProviderError",
    "ProviderFactory",
    "ProviderRateLimitError",
    "ProviderResponseError",
    "get_default_factory",
]
