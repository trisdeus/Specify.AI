"""
API Key Manager for Specify.AI.

This module provides the KeyManager class for storing, retrieving, listing,
and deleting API keys for LLM providers (Ollama, OpenAI, Anthropic).

Keys are stored in a JSON file at ~/.specify/keys.json (or a custom directory
if specified). This is Sprint 2 implementation - keys are stored in plain text
without encryption. Encryption will be added in a future sprint.

Example usage:
    >>> from specify.core import KeyManager
    >>> km = KeyManager()
    >>> km.store_key("openai", "sk-test123")
    >>> km.get_key("openai")
    'sk-test123'
    >>> km.list_keys()
    {'openai': 'sk-...123'}
    >>> km.delete_key("openai")
    True
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final

# Allowed LLM providers
VALID_PROVIDERS: Final[set[str]] = {"ollama", "openai", "anthropic"}

# Default config directory name in user's home directory
CONFIG_DIR_NAME: Final[str] = ".specify"
KEYS_FILE_NAME: Final[str] = "keys.json"


class KeyValidationError(Exception):
    """Raised when API key validation fails.

    This exception is raised when:
    - The provider name is not valid (not in VALID_PROVIDERS)
    - The API key is empty or invalid
    """

    pass


class KeyNotFoundError(Exception):
    """Raised when a key is not found for a provider.

    This exception is raised when attempting to retrieve or delete
    a key that doesn't exist.
    """

    def __init__(self, provider: str) -> None:
        """Initialize the exception with the provider name.

        Args:
            provider: The provider name that was not found.
        """
        self.provider = provider
        super().__init__(f"No key found for provider: {provider}")


class KeyManager:
    """Manager for storing and retrieving API keys.

    This class provides methods for managing API keys for LLM providers.
    Keys are stored in a JSON file at ~/.specify/keys.json by default.

    Attributes:
        config_dir: Path to the configuration directory.
        keys_file: Path to the keys JSON file.

    Example:
        >>> km = KeyManager()
        >>> km.store_key("openai", "sk-test123")
        >>> keys = km.list_keys()
        >>> print(keys)
        {'openai': 'sk-...123'}
    """

    def __init__(self, config_dir: Path | None = None) -> None:
        """Initialize the KeyManager.

        Args:
            config_dir: Optional custom directory for storing keys.
                       If None, uses ~/.specify
        """
        if config_dir is None:
            self.config_dir: Path = Path.home() / CONFIG_DIR_NAME
        else:
            self.config_dir = config_dir

        self.keys_file: Path = self.config_dir / KEYS_FILE_NAME

    def store_key(self, provider: str, key: str) -> None:
        """Store an API key for a provider.

        Validates that the provider is valid and the key is not empty.
        Creates the config directory if it doesn't exist.

        Args:
            provider: The provider name (must be one of: ollama, openai, anthropic).
            key: The API key to store.

        Raises:
            KeyValidationError: If the provider is invalid or key is empty.

        Example:
            >>> km = KeyManager()
            >>> km.store_key("openai", "sk-proj-abc123")
        """
        # Validate provider
        provider_lower = provider.lower()
        if provider_lower not in VALID_PROVIDERS:
            raise KeyValidationError(
                f"Invalid provider: {provider}. "
                f"Must be one of: {', '.join(sorted(VALID_PROVIDERS))}"
            )

        # Validate key is not empty
        if not key or not key.strip():
            raise KeyValidationError("API key cannot be empty")

        # Ensure config directory exists
        self._ensure_config_dir()

        # Load existing keys
        keys = self._load_keys()

        # Store/update the key
        keys[provider_lower] = key.strip()

        # Save keys to file
        self._save_keys(keys)

    def get_key(self, provider: str) -> str | None:
        """Retrieve an API key for a provider.

        Args:
            provider: The provider name to look up.

        Returns:
            The API key if found, None otherwise.

        Example:
            >>> km = KeyManager()
            >>> key = km.get_key("openai")
            >>> print(key)
            sk-test123
        """
        keys = self._load_keys()
        return keys.get(provider.lower())

    def list_keys(self) -> dict[str, str]:
        """List all stored API keys with masked values.

        Returns a dictionary mapping provider names to masked keys.
        Keys are masked for security - only first 3 and last 3 characters
        are shown (e.g., "sk-...abc").

        Returns:
            Dictionary mapping provider names to masked API keys.

        Example:
            >>> km = KeyManager()
            >>> km.store_key("openai", "sk-proj-abc123")
            >>> km.list_keys()
            {'openai': 'sk-...123'}
        """
        keys = self._load_keys()
        # Mask all keys for display
        masked_keys = {provider: self._mask_key(key) for provider, key in keys.items()}
        return masked_keys

    def delete_key(self, provider: str) -> bool:
        """Delete a stored API key.

        Args:
            provider: The provider name to delete the key for.

        Returns:
            True if the key was deleted, False if it didn't exist.

        Example:
            >>> km = KeyManager()
            >>> km.store_key("openai", "sk-test")
            >>> km.delete_key("openai")
            True
            >>> km.delete_key("openai")
            False
        """
        keys = self._load_keys()
        provider_lower = provider.lower()

        if provider_lower not in keys:
            return False

        # Remove the key
        del keys[provider_lower]

        # Save keys to file
        self._save_keys(keys)

        return True

    def key_exists(self, provider: str) -> bool:
        """Check if a key exists for a provider.

        Args:
            provider: The provider name to check.

        Returns:
            True if a key exists for the provider, False otherwise.

        Example:
            >>> km = KeyManager()
            >>> km.store_key("openai", "sk-test")
            >>> km.key_exists("openai")
            True
            >>> km.key_exists("anthropic")
            False
        """
        keys = self._load_keys()
        return provider.lower() in keys

    def _mask_key(self, key: str) -> str:
        """Mask a key for secure display.

        Keys with length >= 6 show first 3 chars + "..." + last 3 chars.
        Keys with length < 6 are shown as "***".

        Args:
            key: The API key to mask.

        Returns:
            The masked key string.

        Example:
            >>> km = KeyManager()
            >>> km._mask_key("sk-proj-abc123")
            'sk-...123'
            >>> km._mask_key("abc")
            '***'
        """
        if len(key) < 6:
            return "***"

        return f"{key[:3]}...{key[-3:]}"

    def _load_keys(self) -> dict[str, str]:
        """Load keys from the JSON file.

        Returns:
            Dictionary of provider -> key mappings.
            Returns empty dict if file doesn't exist or is empty.

        Raises:
            json.JSONDecodeError: If the keys file contains invalid JSON.
        """
        if not self.keys_file.exists():
            return {}

        try:
            with self.keys_file.open(encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                # Invalid format - return empty dict
                return {}

            return data
        except json.JSONDecodeError as e:
            raise KeyValidationError(
                f"Invalid keys file format: {e}. "
                "Please fix or delete the file at " + str(self.keys_file)
            ) from e

    def _save_keys(self, keys: dict[str, str]) -> None:
        """Save keys to the JSON file.

        Args:
            keys: Dictionary of provider -> key mappings to save.

        Raises:
            PermissionError: If unable to write to the keys file.
        """
        try:
            with self.keys_file.open("w", encoding="utf-8") as f:
                json.dump(keys, f, indent=2, sort_keys=True)
        except PermissionError as e:
            raise KeyValidationError(
                f"Permission denied when writing to {self.keys_file}: {e}"
            ) from e

    def _ensure_config_dir(self) -> None:
        """Ensure the config directory exists.

        Creates the directory if it doesn't exist.

        Raises:
            PermissionError: If unable to create the directory.
        """
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError as e:
            raise KeyValidationError(
                f"Permission denied when creating config directory {self.config_dir}: {e}"
            ) from e
