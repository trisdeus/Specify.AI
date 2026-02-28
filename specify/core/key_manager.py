"""
API Key Manager for Specify.AI.

This module provides the KeyManager class for storing, retrieving, listing,
and deleting API keys for LLM providers (Ollama, OpenAI, Anthropic).

Keys are stored in a JSON file at ~/.specify/keys.json (or a custom directory
if specified). This is Sprint 2 implementation - keys are stored in plain text
without encryption. Encryption will be added in a future sprint.

Environment variable support is provided as a fallback for API keys.
If a key is not found in the local store, the manager will check for
environment variables (e.g., OPENAI_API_KEY).

Example usage:
    >>> from specify.core import KeyManager
    >>> km = KeyManager()
    >>> km.store_key("openai", "sk-test123")
    >>> km.get_key("openai")
    'sk-test123'
    >>> km.list_keys()
    {'openai': 'sk-...123'}
    >>> km.delete_key("openai")
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from typing import Final

# Allowed LLM providers
VALID_PROVIDERS: Final[set[str]] = {"ollama", "openai", "anthropic"}

# Mapping of providers to their environment variable names
ENV_VAR_MAPPING: Final[dict[str, str]] = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "ollama": "OLLAMA_HOST",
}

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
    a key that doesn't exist in the local store or environment.
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
    Environment variables are checked as a fallback source.

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

    def get_key(self, provider: str) -> str:
        """Retrieve an API key for a provider.

        Checks the local JSON file first. If the key is not found there,
        it falls back to checking environment variables (e.g., OPENAI_API_KEY).

        Args:
            provider: The provider name to look up.

        Returns:
            The API key.

        Raises:
            KeyNotFoundError: If no key is found for the provider in the
                              local store or environment variables.

        Example:
            >>> km = KeyManager()
            >>> km.store_key("openai", "sk-test123")
            >>> key = km.get_key("openai")
            >>> print(key)
            sk-test123
        """
        provider_lower = provider.lower()
        
        # 1. Check local store (JSON file)
        keys = self._load_keys()
        if provider_lower in keys:
            return keys[provider_lower]

        # 2. Check environment variables
        env_var_name = ENV_VAR_MAPPING.get(provider_lower)
        if env_var_name:
            env_value = os.environ.get(env_var_name)
            if env_value:
                return env_value

        # 3. Not found anywhere
        raise KeyNotFoundError(provider_lower)

    def list_keys(self) -> dict[str, str]:
        """List all stored API keys with masked values.

        Returns a dictionary mapping provider names to masked keys.
        Keys are masked for security - only first 3 and last 3 characters
        are shown (e.g., "sk-...abc").

        This method aggregates keys from both the local JSON file and
        environment variables. Local keys take precedence.

        Returns:
            Dictionary mapping provider names to masked API keys.

        Example:
            >>> km = KeyManager()
            >>> km.store_key("openai", "sk-proj-abc123")
            >>> km.list_keys()
            {'openai': 'sk-...123'}
        """
        keys = self._load_keys()

        # Add keys from environment variables if not already in file
        for provider, env_var in ENV_VAR_MAPPING.items():
            if provider not in keys:
                env_value = os.environ.get(env_var)
                if env_value:
                    keys[provider] = env_value

        # Mask all keys for display
        masked_keys = {provider: self._mask_key(key) for provider, key in keys.items()}
        return masked_keys

    def delete_key(self, provider: str) -> None:
        """Delete a stored API key.

        Note: This only deletes keys from the local JSON store.
        It does not modify environment variables.

        Args:
            provider: The provider name to delete the key for.

        Raises:
            KeyNotFoundError: If no key is found for the provider in the
                              local store.

        Example:
            >>> km = KeyManager()
            >>> km.store_key("openai", "sk-test")
            >>> km.delete_key("openai")
        """
        keys = self._load_keys()
        provider_lower = provider.lower()

        if provider_lower not in keys:
            raise KeyNotFoundError(provider_lower)

        # Remove the key
        del keys[provider_lower]

        # Save keys to file
        self._save_keys(keys)

    def key_exists(self, provider: str) -> bool:
        """Check if a key exists for a provider.

        Checks both the local JSON store and environment variables.

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
        provider_lower = provider.lower()
        
        # Check local store
        keys = self._load_keys()
        if provider_lower in keys:
            return True

        # Check environment variables
        env_var_name = ENV_VAR_MAPPING.get(provider_lower)
        if env_var_name:
            return os.environ.get(env_var_name) is not None

        return False

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
            # Set restrictive permissions: owner read/write only (0600)
            os.chmod(self.keys_file, stat.S_IRUSR | stat.S_IWUSR)
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
