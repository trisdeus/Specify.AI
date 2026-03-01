"""
Comprehensive tests for specify.providers.base module.

This module contains unit tests for:
- Provider exceptions (hierarchy, messages, raising)
- ProviderConfig (validation, defaults, from_env)
- BaseProvider (abstract class, config property, _build_request)
- ProviderFactory (registration, creation, management)
- Async provider methods (generate, stream, validate_connection)

Target coverage: ≥90%
"""

from __future__ import annotations

import os
from typing import Type
from unittest.mock import patch

import pytest

from specify.providers import (
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
from tests.test_providers.conftest import MockProvider


# =============================================================================
# A. Exception Tests
# =============================================================================


class TestProviderExceptions:
    """Tests for provider exception classes."""

    def test_provider_error_can_be_raised_and_caught(self) -> None:
        """Test that ProviderError can be raised and caught."""
        with pytest.raises(ProviderError):
            raise ProviderError("Generic provider error")

    def test_provider_error_message_preserved(self) -> None:
        """Test that exception message is preserved."""
        msg = "Test error message"
        with pytest.raises(ProviderError, match=msg):
            raise ProviderError(msg)

    def test_provider_connection_error_inherits_from_provider_error(
        self,
    ) -> None:
        """Test that ProviderConnectionError inherits from ProviderError."""
        assert issubclass(ProviderConnectionError, ProviderError)

    def test_provider_connection_error_can_be_raised_and_caught(self) -> None:
        """Test that ProviderConnectionError can be raised and caught."""
        with pytest.raises(ProviderConnectionError):
            raise ProviderConnectionError("Connection failed")

    def test_provider_connection_error_instance_of_provider_error(
        self,
    ) -> None:
        """Test that ProviderConnectionError instance is also ProviderError."""
        err = ProviderConnectionError("Connection error")
        assert isinstance(err, ProviderError)

    def test_provider_auth_error_inherits_from_provider_error(self) -> None:
        """Test that ProviderAuthError inherits from ProviderError."""
        assert issubclass(ProviderAuthError, ProviderError)

    def test_provider_auth_error_can_be_raised_and_caught(self) -> None:
        """Test that ProviderAuthError can be raised and caught."""
        with pytest.raises(ProviderAuthError):
            raise ProviderAuthError("Authentication failed")

    def test_provider_auth_error_instance_of_provider_error(self) -> None:
        """Test that ProviderAuthError instance is also ProviderError."""
        err = ProviderAuthError("Auth error")
        assert isinstance(err, ProviderError)

    def test_provider_response_error_inherits_from_provider_error(
        self,
    ) -> None:
        """Test that ProviderResponseError inherits from ProviderError."""
        assert issubclass(ProviderResponseError, ProviderError)

    def test_provider_response_error_can_be_raised_and_caught(self) -> None:
        """Test that ProviderResponseError can be raised and caught."""
        with pytest.raises(ProviderResponseError):
            raise ProviderResponseError("Invalid response")

    def test_provider_response_error_instance_of_provider_error(
        self,
    ) -> None:
        """Test that ProviderResponseError instance is also ProviderError."""
        err = ProviderResponseError("Response error")
        assert isinstance(err, ProviderError)

    def test_provider_config_error_inherits_from_provider_error(
        self,
    ) -> None:
        """Test that ProviderConfigError inherits from ProviderError."""
        assert issubclass(ProviderConfigError, ProviderError)

    def test_provider_config_error_can_be_raised_and_caught(self) -> None:
        """Test that ProviderConfigError can be raised and caught."""
        with pytest.raises(ProviderConfigError):
            raise ProviderConfigError("Invalid config")

    def test_provider_config_error_instance_of_provider_error(self) -> None:
        """Test that ProviderConfigError instance is also ProviderError."""
        err = ProviderConfigError("Config error")
        assert isinstance(err, ProviderError)

    def test_provider_rate_limit_error_inherits_from_provider_response_error(
        self,
    ) -> None:
        """Test that ProviderRateLimitError inherits from ProviderResponseError."""
        assert issubclass(ProviderRateLimitError, ProviderResponseError)

    def test_provider_rate_limit_error_inherits_from_provider_error(
        self,
    ) -> None:
        """Test that ProviderRateLimitError inherits from ProviderError."""
        assert issubclass(ProviderRateLimitError, ProviderError)

    def test_provider_rate_limit_error_can_be_raised_and_caught(
        self,
    ) -> None:
        """Test that ProviderRateLimitError can be raised and caught."""
        with pytest.raises(ProviderRateLimitError):
            raise ProviderRateLimitError("Rate limit exceeded")

    def test_provider_rate_limit_error_instance_of_provider_response_error(
        self,
    ) -> None:
        """Test that ProviderRateLimitError instance is also ProviderResponseError."""
        err = ProviderRateLimitError("Rate limit")
        assert isinstance(err, ProviderResponseError)

    def test_provider_rate_limit_error_instance_of_provider_error(
        self,
    ) -> None:
        """Test that ProviderRateLimitError instance is also ProviderError."""
        err = ProviderRateLimitError("Rate limit")
        assert isinstance(err, ProviderError)

    def test_provider_content_filter_error_inherits_from_provider_response_error(
        self,
    ) -> None:
        """Test that ProviderContentFilterError inherits from ProviderResponseError."""
        assert issubclass(ProviderContentFilterError, ProviderResponseError)

    def test_provider_content_filter_error_inherits_from_provider_error(
        self,
    ) -> None:
        """Test that ProviderContentFilterError inherits from ProviderError."""
        assert issubclass(ProviderContentFilterError, ProviderError)

    def test_provider_content_filter_error_can_be_raised_and_caught(
        self,
    ) -> None:
        """Test that ProviderContentFilterError can be raised and caught."""
        with pytest.raises(ProviderContentFilterError):
            raise ProviderContentFilterError("Content filtered")

    def test_provider_content_filter_error_instance_of_provider_response_error(
        self,
    ) -> None:
        """Test that ProviderContentFilterError is also ProviderResponseError."""
        err = ProviderContentFilterError("Content filter")
        assert isinstance(err, ProviderResponseError)

    def test_provider_content_filter_error_instance_of_provider_error(
        self,
    ) -> None:
        """Test that ProviderContentFilterError instance is also ProviderError."""
        err = ProviderContentFilterError("Content filter")
        assert isinstance(err, ProviderError)

    def test_all_exceptions_inherit_from_provider_error(self) -> None:
        """Test that all custom exceptions inherit from ProviderError."""
        exception_classes: list[Type[Exception]] = [
            ProviderConnectionError,
            ProviderAuthError,
            ProviderResponseError,
            ProviderConfigError,
            ProviderRateLimitError,
            ProviderContentFilterError,
        ]
        for exc_class in exception_classes:
            assert issubclass(exc_class, ProviderError)


# =============================================================================
# B. ProviderConfig Tests
# =============================================================================


class TestProviderConfig:
    """Tests for ProviderConfig class."""

    def test_model_field_is_required(self) -> None:
        """Test that model field is required."""
        with pytest.raises(ValueError, match="Field required"):
            ProviderConfig()

    def test_default_api_key_is_none(self) -> None:
        """Test that api_key defaults to None."""
        config = ProviderConfig(model="test-model")
        assert config.api_key is None

    def test_default_base_url_is_none(self) -> None:
        """Test that base_url defaults to None."""
        config = ProviderConfig(model="test-model")
        assert config.base_url is None

    def test_default_timeout_is_60(self) -> None:
        """Test that timeout defaults to 60."""
        config = ProviderConfig(model="test-model")
        assert config.timeout == 60

    def test_default_max_retries_is_3(self) -> None:
        """Test that max_retries defaults to 3."""
        config = ProviderConfig(model="test-model")
        assert config.max_retries == 3

    def test_timeout_validation_zero_raises_error(self) -> None:
        """Test that timeout=0 raises validation error."""
        with pytest.raises(ValueError, match="greater than or equal to 1"):
            ProviderConfig(model="test-model", timeout=0)

    def test_timeout_validation_one_is_valid(self) -> None:
        """Test that timeout=1 is valid."""
        config = ProviderConfig(model="test-model", timeout=1)
        assert config.timeout == 1

    def test_timeout_validation_300_is_valid(self) -> None:
        """Test that timeout=300 is valid."""
        config = ProviderConfig(model="test-model", timeout=300)
        assert config.timeout == 300

    def test_timeout_validation_301_raises_error(self) -> None:
        """Test that timeout=301 raises validation error."""
        with pytest.raises(ValueError, match="less than or equal to 300"):
            ProviderConfig(model="test-model", timeout=301)

    def test_max_retries_validation_negative_raises_error(self) -> None:
        """Test that max_retries=-1 raises validation error."""
        with pytest.raises(ValueError, match="greater than or equal to 0"):
            ProviderConfig(model="test-model", max_retries=-1)

    def test_max_retries_validation_zero_is_valid(self) -> None:
        """Test that max_retries=0 is valid."""
        config = ProviderConfig(model="test-model", max_retries=0)
        assert config.max_retries == 0

    def test_max_retries_validation_ten_is_valid(self) -> None:
        """Test that max_retries=10 is valid."""
        config = ProviderConfig(model="test-model", max_retries=10)
        assert config.max_retries == 10

    def test_max_retries_validation_11_raises_error(self) -> None:
        """Test that max_retries=11 raises validation error."""
        with pytest.raises(ValueError, match="less than or equal to 10"):
            ProviderConfig(model="test-model", max_retries=11)

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields raise validation error."""
        with pytest.raises(ValueError):
            ProviderConfig(model="test-model", unknown_field="value")

    def test_model_validator_empty_string_raises_error(self) -> None:
        """Test that empty model string raises validation error."""
        with pytest.raises(ValueError, match="model cannot be empty"):
            ProviderConfig(model="")

    def test_model_validator_whitespace_only_raises_error(self) -> None:
        """Test that whitespace-only model string raises validation error."""
        with pytest.raises(ValueError, match="model cannot be empty"):
            ProviderConfig(model="   ")

    def test_model_validator_strips_whitespace(self) -> None:
        """Test that model string whitespace is stripped."""
        config = ProviderConfig(model="  gpt-4  ")
        assert config.model == "gpt-4"

    def test_from_env_with_valid_openai_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test from_env creates config with API key from environment."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-123")
        config = ProviderConfig.from_env("openai", "gpt-4")

        assert config.model == "gpt-4"
        assert config.api_key == "sk-test-key-123"
        assert config.timeout == 60
        assert config.max_retries == 3

    def test_from_env_with_valid_anthropic_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test from_env creates config for Anthropic from environment."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
        config = ProviderConfig.from_env("anthropic", "claude-3")

        assert config.model == "claude-3"
        assert config.api_key == "sk-ant-test-key"

    def test_from_env_with_ollama_uses_base_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test from_env for Ollama uses base_url instead of api_key."""
        monkeypatch.setenv("OLLAMA_HOST", "http://localhost:11434")
        config = ProviderConfig.from_env("ollama", "llama2")

        assert config.model == "llama2"
        assert config.base_url == "http://localhost:11434"
        assert config.api_key is None

    def test_from_env_ollama_defaults_to_localhost(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test from_env for Ollama defaults to localhost when env var not set."""
        monkeypatch.delenv("OLLAMA_HOST", raising=False)
        config = ProviderConfig.from_env("ollama", "llama2")

        assert config.model == "llama2"
        assert config.base_url == "http://localhost:11434"

    def test_from_env_missing_api_key_raises_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test from_env raises error when API key is not set."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(ProviderConfigError, match="is not set"):
            ProviderConfig.from_env("openai", "gpt-4")

    def test_from_env_unknown_provider_raises_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test from_env raises error for unknown provider."""
        with pytest.raises(ProviderConfigError, match="Unknown provider"):
            ProviderConfig.from_env("unknown", "some-model")

    def test_from_env_case_insensitive_provider_name(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test from_env handles case-insensitive provider names."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        config = ProviderConfig.from_env("OPENAI", "gpt-4")

        assert config.model == "gpt-4"
        assert config.api_key == "sk-test"


# =============================================================================
# C. BaseProvider Tests
# =============================================================================


class TestBaseProvider:
    """Tests for BaseProvider class."""

    def test_base_provider_is_abstract_cannot_instantiate(self) -> None:
        """Test that BaseProvider cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseProvider(ProviderConfig(model="test"))

    def test_concrete_implementation_can_be_instantiated(
        self, provider_config: ProviderConfig
    ) -> None:
        """Test that concrete implementation can be instantiated."""
        provider = MockProvider(provider_config)
        assert provider is not None

    def test_config_property_returns_configuration(
        self, mock_provider: MockProvider
    ) -> None:
        """Test that config property returns the configuration."""
        assert mock_provider.config == mock_provider._config

    def test_config_property_returns_correct_config(
        self, provider_config: ProviderConfig, mock_provider: MockProvider
    ) -> None:
        """Test that config property returns the correct config instance."""
        assert mock_provider.config.model == "test-model"
        assert mock_provider.config.api_key == "test-key"

    def test_build_request_returns_correct_structure(
        self, mock_provider: MockProvider
    ) -> None:
        """Test that _build_request returns correct structure."""
        request = mock_provider._build_request("test prompt", "test rules")

        assert request["model"] == "test-model"
        assert request["prompt"] == "test prompt"
        assert request["rules"] == "test rules"
        assert request["timeout"] == 30
        assert request["max_retries"] == 3

    def test_build_request_with_different_values(
        self, provider_config: ProviderConfig
    ) -> None:
        """Test _build_request with different configuration values."""
        config = ProviderConfig(
            model="custom-model",
            timeout=120,
            max_retries=5,
        )
        provider = MockProvider(config)
        request = provider._build_request("prompt", "rules")

        assert request["model"] == "custom-model"
        assert request["timeout"] == 120
        assert request["max_retries"] == 5


# =============================================================================
# D. ProviderFactory Tests
# =============================================================================


class TestProviderFactory:
    """Tests for ProviderFactory class."""

    def test_factory_register_adds_provider(self) -> None:
        """Test that register adds provider to registry."""
        factory = ProviderFactory()
        factory.register("test", MockProvider)

        assert factory.is_registered("test")

    def test_factory_register_duplicate_raises_error(self) -> None:
        """Test that registering duplicate provider raises error."""
        factory = ProviderFactory()
        factory.register("test", MockProvider)

        with pytest.raises(ProviderConfigError, match="already registered"):
            factory.register("test", MockProvider)

    def test_factory_register_non_base_provider_raises_error(self) -> None:
        """Test that registering non-BaseProvider raises error."""
        factory = ProviderFactory()

        class NotAProvider:
            pass

        with pytest.raises(ProviderConfigError, match="must be a subclass of BaseProvider"):
            factory.register("notaprovider", NotAProvider)

    def test_factory_create_returns_provider_instance(
        self, provider_config: ProviderConfig
    ) -> None:
        """Test that create returns provider instance."""
        factory = ProviderFactory()
        factory.register("mock", MockProvider)
        provider = factory.create("mock", provider_config)

        assert isinstance(provider, MockProvider)

    def test_factory_create_case_insensitive(self, provider_config: ProviderConfig) -> None:
        """Test that create handles case-insensitive provider names."""
        factory = ProviderFactory()
        factory.register("mock", MockProvider)
        provider = factory.create("MOCK", provider_config)

        assert isinstance(provider, MockProvider)

    def test_factory_create_unregistered_raises_error(
        self, provider_config: ProviderConfig
    ) -> None:
        """Test that create raises error for unregistered provider."""
        factory = ProviderFactory()

        with pytest.raises(ProviderConfigError, match="is not registered"):
            factory.create("unregistered", provider_config)

    def test_factory_get_available_providers(self) -> None:
        """Test that get_available_providers returns list of registered names."""
        factory = ProviderFactory()
        factory.register("provider1", MockProvider)
        factory.register("provider2", MockProvider)

        providers = factory.get_available_providers()
        assert "provider1" in providers
        assert "provider2" in providers
        assert len(providers) == 2

    def test_factory_get_available_providers_empty(self) -> None:
        """Test that get_available_providers returns empty list when no providers."""
        factory = ProviderFactory()
        providers = factory.get_available_providers()

        assert providers == []

    def test_factory_is_registered_returns_true(self) -> None:
        """Test that is_registered returns True for registered provider."""
        factory = ProviderFactory()
        factory.register("test", MockProvider)

        assert factory.is_registered("test") is True

    def test_factory_is_registered_returns_false(self) -> None:
        """Test that is_registered returns False for unregistered provider."""
        factory = ProviderFactory()

        assert factory.is_registered("nonexistent") is False

    def test_factory_is_registered_case_insensitive(self) -> None:
        """Test that is_registered handles case-insensitive names."""
        factory = ProviderFactory()
        factory.register("test", MockProvider)

        assert factory.is_registered("TEST") is True
        assert factory.is_registered("Test") is True


class TestProviderFactorySingleton:
    """Tests for the default factory singleton."""

    def test_get_default_factory_returns_singleton(self) -> None:
        """Test that get_default_factory returns singleton instance."""
        factory1 = get_default_factory()
        factory2 = get_default_factory()

        assert factory1 is factory2

    def test_get_default_factory_returns_provider_factory_instance(
        self,
    ) -> None:
        """Test that get_default_factory returns ProviderFactory instance."""
        factory = get_default_factory()
        assert isinstance(factory, ProviderFactory)


# =============================================================================
# E. Async Tests
# =============================================================================


class TestMockProviderAsync:
    """Tests for async methods in MockProvider."""

    @pytest.mark.asyncio
    async def test_generate_returns_expected_string(
        self, mock_provider: MockProvider
    ) -> None:
        """Test that generate returns expected string."""
        result = await mock_provider.generate("test prompt", "test rules")

        assert result == "Generated: test prompt"

    @pytest.mark.asyncio
    async def test_stream_yields_expected_chunks(
        self, mock_provider: MockProvider
    ) -> None:
        """Test that stream yields expected chunks."""
        chunks = [chunk async for chunk in mock_provider.stream("test prompt", "test rules")]

        assert len(chunks) == 1
        assert chunks[0] == "Streamed: test prompt"

    @pytest.mark.asyncio
    async def test_validate_connection_returns_true(
        self, mock_provider: MockProvider
    ) -> None:
        """Test that validate_connection returns True."""
        result = await mock_provider.validate_connection()

        assert result is True

    @pytest.mark.asyncio
    async def test_generate_with_empty_prompt(
        self, mock_provider: MockProvider
    ) -> None:
        """Test generate handles empty prompt."""
        result = await mock_provider.generate("", "rules")

        assert result == "Generated: "

    @pytest.mark.asyncio
    async def test_stream_multiple_chunks(self, provider_config: ProviderConfig
    ) -> None:
        """Test stream with a custom provider yielding multiple chunks."""

        class MultiChunkProvider(MockProvider):
            async def stream(
                self, prompt: str, rules: str
            ):
                yield "chunk1"
                yield "chunk2"
                yield "chunk3"

        provider = MultiChunkProvider(provider_config)
        chunks = [chunk async for chunk in provider.stream("prompt", "rules")]

        assert len(chunks) == 3
        assert chunks[0] == "chunk1"
        assert chunks[1] == "chunk2"
        assert chunks[2] == "chunk3"


# =============================================================================
# Integration Tests
# =============================================================================


class TestProviderIntegration:
    """Integration tests for complete provider workflows."""

    def test_factory_and_config_workflow(self, provider_config: ProviderConfig) -> None:
        """Test complete workflow: register factory and create provider."""
        factory = ProviderFactory()
        factory.register("mock", MockProvider)

        provider = factory.create("mock", provider_config)
        assert provider.config.model == "test-model"

    def test_multiple_providers_registered(self, provider_config: ProviderConfig) -> None:
        """Test registering multiple providers."""
        factory = ProviderFactory()
        factory.register("mock1", MockProvider)
        factory.register("mock2", MockProvider)

        assert factory.is_registered("mock1")
        assert factory.is_registered("mock2")
        assert len(factory.get_available_providers()) == 2
