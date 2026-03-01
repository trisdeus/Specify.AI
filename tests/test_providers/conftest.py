"""
Pytest configuration and fixtures for provider tests.

This module provides shared fixtures for testing the provider abstraction layer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from specify.providers import BaseProvider, ProviderConfig

if TYPE_CHECKING:
    from typing import AsyncIterator


class MockProvider(BaseProvider):
    """Mock implementation of BaseProvider for testing."""

    async def generate(self, prompt: str, rules: str) -> str:
        """Return a generated response based on the prompt."""
        return f"Generated: {prompt}"

    async def stream(self, prompt: str, rules: str) -> AsyncIterator[str]:
        """Yield streamed response chunks."""
        yield f"Streamed: {prompt}"

    async def validate_connection(self) -> bool:
        """Always return True for mock provider."""
        return True


@pytest.fixture
def provider_config() -> ProviderConfig:
    """Create a test provider configuration.

    Returns:
        A ProviderConfig instance with test values.
    """
    return ProviderConfig(
        model="test-model",
        api_key="test-key",
        timeout=30,
        max_retries=3,
    )


@pytest.fixture
def mock_provider(provider_config: ProviderConfig) -> MockProvider:
    """Create a mock provider instance.

    Args:
        provider_config: The provider configuration fixture.

    Returns:
        A MockProvider instance for testing.
    """
    return MockProvider(provider_config)
