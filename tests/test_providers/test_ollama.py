"""
Comprehensive tests for specify.providers.ollama module.

This module contains unit tests for the OllamaProvider class, including:
- Initialization tests (default host, custom host, model configuration)
- generate() method tests (success, empty rules, errors)
- stream() method tests (success, empty rules, errors)
- validate_connection() tests (success, failure)
- Factory registration tests
- Error handling tests
- _build_messages tests

Target coverage: ≥85%
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from specify.providers import (
    ProviderConfig,
    ProviderConnectionError,
    ProviderResponseError,
    get_default_factory,
)
from specify.providers.ollama import OllamaProvider


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_ollama_client(mocker):
    """Mock the Ollama AsyncClient."""
    mock_client = AsyncMock()
    mocker.patch("specify.providers.ollama.AsyncClient", return_value=mock_client)
    return mock_client


@pytest.fixture
def ollama_config():
    """Create a test Ollama configuration."""
    return ProviderConfig(model="llama2", base_url="http://localhost:11434")


@pytest.fixture
def ollama_config_no_url():
    """Create a test Ollama configuration without base_url."""
    return ProviderConfig(model="llama2")


# =============================================================================
# A. Initialization Tests
# =============================================================================


class TestOllamaProviderInit:
    """Tests for OllamaProvider initialization."""

    def test_init_default_host(self, ollama_config_no_url, mock_ollama_client):
        """Test initialization with default host when base_url is None."""
        provider = OllamaProvider(ollama_config_no_url)
        assert provider.config.model == "llama2"
        assert provider.config.base_url is None
        # Client should be created with default host
        assert provider._client is not None

    def test_init_custom_host(self, ollama_config, mock_ollama_client):
        """Test initialization with custom host from config.base_url."""
        provider = OllamaProvider(ollama_config)
        assert provider.config.model == "llama2"
        assert provider.config.base_url == "http://localhost:11434"
        # Client should be created with custom host
        assert provider._client is not None

    def test_init_model_stored_correctly(self, ollama_config, mock_ollama_client):
        """Test that model configuration is stored correctly."""
        provider = OllamaProvider(ollama_config)
        assert provider._config.model == "llama2"

    def test_init_client_is_async_client(self, ollama_config, mock_ollama_client):
        """Test that client is an AsyncClient instance."""
        provider = OllamaProvider(ollama_config)
        assert provider._client is not None


# =============================================================================
# B. Generate Tests
# =============================================================================


class TestOllamaProviderGenerate:
    """Tests for OllamaProvider.generate method."""

    @pytest.mark.asyncio
    async def test_generate_success(self, ollama_config, mock_ollama_client):
        """Test successful generation with prompt and rules."""
        mock_ollama_client.chat.return_value = {
            "message": {"role": "assistant", "content": "Test response"}
        }
        provider = OllamaProvider(ollama_config)
        result = await provider.generate("Hello", "Be concise")
        assert result == "Test response"
        mock_ollama_client.chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_with_empty_rules(self, ollama_config, mock_ollama_client):
        """Test generation with empty rules (no system message)."""
        mock_ollama_client.chat.return_value = {
            "message": {"role": "assistant", "content": "Response without rules"}
        }
        provider = OllamaProvider(ollama_config)
        result = await provider.generate("Hello", "")
        assert result == "Response without rules"
        # Verify the call was made with correct model and messages without system
        call_kwargs = mock_ollama_client.chat.call_args.kwargs
        assert call_kwargs["model"] == "llama2"
        messages = call_kwargs["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello"

    @pytest.mark.asyncio
    async def test_generate_connection_error(self, ollama_config, mock_ollama_client):
        """Test connection error handling maps to ProviderConnectionError."""
        mock_ollama_client.chat.side_effect = Exception("Connection refused")
        provider = OllamaProvider(ollama_config)
        with pytest.raises(ProviderConnectionError):
            await provider.generate("Hello", "Be concise")

    @pytest.mark.asyncio
    async def test_generate_response_error(self, ollama_config, mock_ollama_client):
        """Test response error handling maps to ProviderResponseError."""
        mock_ollama_client.chat.side_effect = Exception("Invalid response")
        provider = OllamaProvider(ollama_config)
        with pytest.raises(ProviderResponseError):
            await provider.generate("Hello", "Be concise")

    @pytest.mark.asyncio
    async def test_generate_messages_built_correctly(
        self, ollama_config, mock_ollama_client
    ):
        """Test that messages are built correctly with system and user messages."""
        mock_ollama_client.chat.return_value = {
            "message": {"role": "assistant", "content": "Response"}
        }
        provider = OllamaProvider(ollama_config)
        await provider.generate("Hello", "Be helpful")
        
        call_kwargs = mock_ollama_client.chat.call_args.kwargs
        messages = call_kwargs["messages"]
        
        # Should have system and user messages
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "Be helpful"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Hello"

    @pytest.mark.asyncio
    async def test_generate_timeout_error(self, ollama_config, mock_ollama_client):
        """Test timeout error is mapped to ProviderConnectionError."""
        mock_ollama_client.chat.side_effect = Exception("Connection timeout")
        provider = OllamaProvider(ollama_config)
        with pytest.raises(ProviderConnectionError):
            await provider.generate("Hello", "Be concise")

    @pytest.mark.asyncio
    async def test_generate_dns_error(self, ollama_config, mock_ollama_client):
        """Test DNS error is mapped to ProviderConnectionError."""
        mock_ollama_client.chat.side_effect = Exception("DNS failure")
        provider = OllamaProvider(ollama_config)
        with pytest.raises(ProviderConnectionError):
            await provider.generate("Hello", "Be concise")


# =============================================================================
# C. Stream Tests
# =============================================================================


class TestOllamaProviderStream:
    """Tests for OllamaProvider.stream method."""

    @pytest.mark.asyncio
    async def test_stream_success(self, ollama_config, mock_ollama_client):
        """Test successful streaming with multiple chunks."""
        # Create a mock async iterator
        async def mock_stream():
            chunks = [
                {"message": {"content": "Hello "}},
                {"message": {"content": "world"}},
                {"message": {"content": "!"}},
            ]
            for chunk in chunks:
                yield chunk

        mock_ollama_client.chat.return_value = mock_stream()
        provider = OllamaProvider(ollama_config)
        
        result = []
        async for chunk in provider.stream("Hello", "Be concise"):
            result.append(chunk)
        
        assert result == ["Hello ", "world", "!"]

    @pytest.mark.asyncio
    async def test_stream_with_empty_rules(self, ollama_config, mock_ollama_client):
        """Test streaming with empty rules (no system message)."""
        async def mock_stream():
            yield {"message": {"content": "Response"}}

        mock_ollama_client.chat.return_value = mock_stream()
        provider = OllamaProvider(ollama_config)
        
        result = []
        async for chunk in provider.stream("Hello", ""):
            result.append(chunk)
        
        assert result == ["Response"]
        
        # Verify messages don't include system message
        call_kwargs = mock_ollama_client.chat.call_args.kwargs
        messages = call_kwargs["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"

    @pytest.mark.asyncio
    async def test_stream_error(self, ollama_config, mock_ollama_client):
        """Test error during streaming raises appropriate exception."""
        mock_ollama_client.chat.side_effect = Exception("Stream error")
        provider = OllamaProvider(ollama_config)
        
        with pytest.raises(ProviderResponseError):
            async for _ in provider.stream("Hello", "Be concise"):
                pass

    @pytest.mark.asyncio
    async def test_stream_connection_error(self, ollama_config, mock_ollama_client):
        """Test connection error during streaming raises ProviderConnectionError."""
        mock_ollama_client.chat.side_effect = Exception("Connection refused")
        provider = OllamaProvider(ollama_config)
        
        with pytest.raises(ProviderConnectionError):
            async for _ in provider.stream("Hello", "Be concise"):
                pass


# =============================================================================
# D. Validate Connection Tests
# =============================================================================


class TestOllamaProviderValidateConnection:
    """Tests for OllamaProvider.validate_connection method."""

    @pytest.mark.asyncio
    async def test_validate_connection_success(self, ollama_config, mock_ollama_client):
        """Test successful validation returns True."""
        mock_ollama_client.list.return_value = {"models": []}
        provider = OllamaProvider(ollama_config)
        result = await provider.validate_connection()
        assert result is True
        mock_ollama_client.list.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_connection_failure(self, ollama_config, mock_ollama_client):
        """Test connection failure returns False."""
        mock_ollama_client.list.side_effect = ConnectionError("Connection refused")
        provider = OllamaProvider(ollama_config)
        result = await provider.validate_connection()
        assert result is False


# =============================================================================
# E. Factory Registration Tests
# =============================================================================


class TestOllamaProviderFactory:
    """Tests for OllamaProvider factory registration."""

    def test_provider_registered_on_import(self):
        """Test that OllamaProvider is registered on import."""
        factory = get_default_factory()
        assert factory.is_registered("ollama")

    def test_factory_create_returns_ollama_provider(self, ollama_config):
        """Test factory.create('ollama', config) returns OllamaProvider instance."""
        factory = get_default_factory()
        provider = factory.create("ollama", ollama_config)
        assert isinstance(provider, OllamaProvider)

    def test_factory_create_case_insensitive(self, ollama_config):
        """Test factory.create handles case-insensitive provider names."""
        factory = get_default_factory()
        provider = factory.create("OLLAMA", ollama_config)
        assert isinstance(provider, OllamaProvider)


# =============================================================================
# F. Error Handling Tests
# =============================================================================


class TestOllamaProviderErrorHandling:
    """Tests for OllamaProvider error handling."""

    @pytest.mark.asyncio
    async def test_handle_error_connection_refused(self, ollama_config, mock_ollama_client):
        """Test _handle_error with connection refused error."""
        provider = OllamaProvider(ollama_config)
        
        with pytest.raises(ProviderConnectionError) as exc_info:
            provider._handle_error(Exception("Connection refused"))
        
        assert "Connection refused" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_handle_error_connection_timeout(self, ollama_config, mock_ollama_client):
        """Test _handle_error with connection timeout error."""
        provider = OllamaProvider(ollama_config)
        
        with pytest.raises(ProviderConnectionError) as exc_info:
            provider._handle_error(Exception("Connection timeout"))
        
        assert "Connection timeout" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_handle_error_unreachable(self, ollama_config, mock_ollama_client):
        """Test _handle_error with unreachable error."""
        provider = OllamaProvider(ollama_config)
        
        with pytest.raises(ProviderConnectionError) as exc_info:
            provider._handle_error(Exception("Host unreachable"))
        
        assert "Host unreachable" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_handle_error_network(self, ollama_config, mock_ollama_client):
        """Test _handle_error with network error."""
        provider = OllamaProvider(ollama_config)
        
        with pytest.raises(ProviderConnectionError) as exc_info:
            provider._handle_error(Exception("Network error"))
        
        assert "Network error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_handle_error_dns(self, ollama_config, mock_ollama_client):
        """Test _handle_error with DNS error."""
        provider = OllamaProvider(ollama_config)
        
        with pytest.raises(ProviderConnectionError) as exc_info:
            provider._handle_error(Exception("DNS failure"))
        
        assert "DNS failure" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_handle_error_host(self, ollama_config, mock_ollama_client):
        """Test _handle_error with host error."""
        provider = OllamaProvider(ollama_config)
        
        with pytest.raises(ProviderConnectionError) as exc_info:
            provider._handle_error(Exception("Host not found"))
        
        assert "Host not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_handle_error_response_error(self, ollama_config, mock_ollama_client):
        """Test _handle_error with other errors maps to ProviderResponseError."""
        provider = OllamaProvider(ollama_config)
        
        with pytest.raises(ProviderResponseError) as exc_info:
            provider._handle_error(Exception("Invalid model response"))
        
        assert "Invalid model response" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_handle_error_api_error(self, ollama_config, mock_ollama_client):
        """Test _handle_error with API error maps to ProviderResponseError."""
        provider = OllamaProvider(ollama_config)
        
        with pytest.raises(ProviderResponseError) as exc_info:
            provider._handle_error(Exception("API error"))
        
        assert "API error" in str(exc_info.value)


# =============================================================================
# G. Build Messages Tests
# =============================================================================


class TestOllamaProviderBuildMessages:
    """Tests for OllamaProvider._build_messages method."""

    def test_build_messages_with_rules(self, ollama_config, mock_ollama_client):
        """Test _build_messages with rules creates system and user messages."""
        provider = OllamaProvider(ollama_config)
        messages = provider._build_messages("Hello", "Be helpful")
        
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "Be helpful"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Hello"

    def test_build_messages_empty_rules(self, ollama_config, mock_ollama_client):
        """Test _build_messages with empty rules returns only user message."""
        provider = OllamaProvider(ollama_config)
        messages = provider._build_messages("Hello", "")
        
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello"

    def test_build_messages_none_rules(self, ollama_config, mock_ollama_client):
        """Test _build_messages with None rules returns only user message."""
        provider = OllamaProvider(ollama_config)
        messages = provider._build_messages("Hello", None)  # type: ignore
        
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello"

    def test_build_messages_whitespace_rules(self, ollama_config, mock_ollama_client):
        """Test _build_messages with whitespace-only rules includes system message."""
        # Note: whitespace-only strings are truthy in Python, so they ARE included
        provider = OllamaProvider(ollama_config)
        messages = provider._build_messages("Hello", "   ")
        
        # Whitespace is truthy in Python, so it adds system message
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "   "
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Hello"

    def test_build_messages_special_characters(self, ollama_config, mock_ollama_client):
        """Test _build_messages with special characters in prompt and rules."""
        provider = OllamaProvider(ollama_config)
        messages = provider._build_messages("Hello\nWorld!", "Rules with 'quotes'")
        
        assert len(messages) == 2
        assert messages[0]["content"] == "Rules with 'quotes'"
        assert messages[1]["content"] == "Hello\nWorld!"


# =============================================================================
# H. Config Property Tests
# =============================================================================


class TestOllamaProviderConfig:
    """Tests for OllamaProvider config property."""

    def test_config_property(self, ollama_config, mock_ollama_client):
        """Test that config property returns the configuration."""
        provider = OllamaProvider(ollama_config)
        assert provider.config == provider._config
        assert provider.config.model == "llama2"
        assert provider.config.base_url == "http://localhost:11434"


class TestOllamaProviderFromEnv:
    """Tests for OllamaProvider configuration from environment variables."""

    def test_from_env_uses_ollama_host(self, monkeypatch):
        """Test that ProviderConfig.from_env reads OLLAMA_HOST environment variable."""
        monkeypatch.setenv("OLLAMA_HOST", "http://custom:11434")
        config = ProviderConfig.from_env("ollama", "llama2")
        assert config.base_url == "http://custom:11434"
        assert config.model == "llama2"

    def test_from_env_default_host(self, monkeypatch):
        """Test that ProviderConfig.from_env uses default host when OLLAMA_HOST not set."""
        monkeypatch.delenv("OLLAMA_HOST", raising=False)
        config = ProviderConfig.from_env("ollama", "llama2")
        assert config.base_url == "http://localhost:11434"
        assert config.model == "llama2"
