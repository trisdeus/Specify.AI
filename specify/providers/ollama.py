"""
Ollama provider for local LLM inference.

This module provides the OllamaProvider class that implements the BaseProvider
interface for connecting to local Ollama instances.

Example usage:
    >>> from specify.providers import ProviderConfig, get_default_factory
    >>> config = ProviderConfig.from_env("ollama", "llama2")
    >>> factory = get_default_factory()
    >>> provider = factory.create("ollama", config)
    >>> response = await provider.generate("Hello", "Be concise.")
"""

from __future__ import annotations

from typing import TYPE_CHECKING

# Default host for local Ollama instance
DEFAULT_OLLAMA_HOST = "http://localhost:11434"

from ollama import AsyncClient

from specify.providers.base import (
    BaseProvider,
    ProviderConfig,
    ProviderConnectionError,
    ProviderResponseError,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


class OllamaProvider(BaseProvider):
    """Ollama provider for local LLM inference.

    This class implements the BaseProvider interface to connect to a local
    Ollama instance and generate text using local language models.

    Attributes:
        _config: The provider configuration instance
        _client: The Ollama AsyncClient instance

    Example:
        >>> from specify.providers import ProviderConfig
        >>> from specify.providers.ollama import OllamaProvider
        >>>
        >>> config = ProviderConfig(
        ...     model="llama2",
        ...     base_url="http://localhost:11434"
        ... )
        >>> provider = OllamaProvider(config)
        >>> response = await provider.generate("Hello", "Be helpful.")
    """

    def __init__(self, config: ProviderConfig) -> None:
        """Initialize the Ollama provider with configuration.

        Args:
            config: Provider configuration instance containing model and base_url.

        Example:
            >>> config = ProviderConfig(model="llama2", base_url="http://localhost:11434")
            >>> provider = OllamaProvider(config)
        """
        super().__init__(config)
        host = config.base_url or DEFAULT_OLLAMA_HOST
        self._client = AsyncClient(host=host)

    async def generate(self, prompt: str, rules: str) -> str:
        """Generate a response from the Ollama model.

        Args:
            prompt: The user prompt to send to the LLM.
            rules: Additional rules or instructions for the LLM (used as system message).

        Returns:
            The generated text response from the LLM.

        Raises:
            ProviderConnectionError: If the Ollama server is unreachable.
            ProviderResponseError: If the model returns an error response.

        Example:
            >>> provider = OllamaProvider(ProviderConfig(model="llama2"))
            >>> response = await provider.generate("Hello", "Be concise.")
        """
        messages = self._build_messages(prompt, rules)
        try:
            response = await self._client.chat(
                model=self._config.model,
                messages=messages,
            )
            # Use dict access for compatibility with both mocked dicts and real ChatResponse
            content: str = response["message"]["content"]
            return content or ""
        except Exception as e:
            self._handle_error(e)
            raise

    async def stream(self, prompt: str, rules: str) -> AsyncIterator[str]:  # type: ignore[override,misc]
        """Stream a response from the Ollama model token by token.

        Args:
            prompt: The user prompt to send to the LLM.
            rules: Additional rules or instructions for the LLM (used as system message).

        Yields:
            Individual chunks of the generated response.

        Raises:
            ProviderConnectionError: If the Ollama server is unreachable.
            ProviderResponseError: If the model returns an error response.

        Example:
            >>> provider = OllamaProvider(ProviderConfig(model="llama2"))
            >>> async for chunk in provider.stream("Hello", "Be concise."):
            ...     print(chunk, end="")
        """
        messages = self._build_messages(prompt, rules)
        try:
            response = await self._client.chat(
                model=self._config.model,
                messages=messages,
                stream=True,
            )
            async for chunk in response:
                yield chunk["message"]["content"]
        except Exception as e:
            self._handle_error(e)
            raise

    async def validate_connection(self) -> bool:
        """Validate that the Ollama connection is working.

        This method attempts to list available models to verify that
        the Ollama server is accessible.

        Returns:
            True if connection is valid, False otherwise.

        Example:
            >>> provider = OllamaProvider(ProviderConfig(model="llama2"))
            >>> is_valid = await provider.validate_connection()
        """
        try:
            await self._client.list()
            return True
        except Exception:
            return False

    def _build_messages(self, prompt: str, rules: str) -> list[dict]:
        """Build the messages list for the Ollama API.

        Constructs a message list with an optional system message for rules
        and a required user message for the prompt.

        Args:
            prompt: The user prompt.
            rules: Additional rules or instructions (becomes system message if non-empty).

        Returns:
            List of message dictionaries for the Ollama API.

        Example:
            >>> provider = OllamaProvider(ProviderConfig(model="llama2"))
            >>> messages = provider._build_messages("Hello", "Be helpful.")
            >>> # Returns: [{'role': 'system', 'content': 'Be helpful.'}, {'role': 'user', 'content': 'Hello'}]
        """
        messages: list[dict] = []
        if rules:
            messages.append({"role": "system", "content": rules})
        messages.append({"role": "user", "content": prompt})
        return messages

    def _handle_error(self, error: Exception) -> None:
        """Handle errors from the Ollama client.

        Maps generic exceptions to appropriate provider-specific exceptions.

        Args:
            error: The exception raised by the Ollama client.

        Raises:
            ProviderConnectionError: For connection-related errors.
            ProviderResponseError: For response-related errors.
        """
        error_message = str(error).lower()

        # Check for common connection errors
        connection_keywords = [
            "connection",
            "refused",
            "timeout",
            "unreachable",
            "network",
            "dns",
            "host not found",
            "name or service not known",
        ]
        if any(keyword in error_message for keyword in connection_keywords):
            raise ProviderConnectionError(
                f"Failed to connect to Ollama at {self._config.base_url}: {error}"
            ) from error

        # For all other errors, raise as response error
        raise ProviderResponseError(
            f"Ollama API error: {error}"
        ) from error
