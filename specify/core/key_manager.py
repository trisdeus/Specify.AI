"""
API Key Manager for Specify.AI.

This module provides the KeyManager class for storing, retrieving, listing,
and deleting API keys for LLM providers (Ollama, OpenAI, Anthropic).

Keys are stored in an encrypted JSON file at ~/.specify/keys.json (or a custom
directory if specified). Encryption uses Fernet (AES-128-CBC with HMAC) with
a machine-specific key derived from the system's unique identifier.

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

import base64
import json
import os
import platform
import socket
import stat
import subprocess
import warnings
from pathlib import Path
from typing import Any, Final

from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

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


class EncryptionError(Exception):
    """Raised when encryption operations fail.

    This exception is raised when:
    - Key derivation fails
    - Fernet encryption fails
    - File operations for salt storage fail
    """

    pass


class DecryptionError(Exception):
    """Raised when decryption fails due to corrupted data or missing salt.

    This exception is raised when:
    - The salt file is missing or corrupted
    - The ciphertext is corrupted
    - The machine ID has changed (keys from a different machine)
    - Key derivation or decryption fails for any reason
    """

    pass


class MachineIdError(Exception):
    """Raised when unable to get machine-specific identifier.

    This exception is raised when:
    - Cannot read machine-id on Linux
    - Cannot get IOPlatformUUID on macOS
    - Cannot read MachineGuid from Windows registry
    - Fallback (hostname + username) also fails
    """

    pass


class CryptoManager:
    """Manages encryption and decryption of sensitive data using Fernet.

    This class provides symmetric encryption using Fernet (AES-128-CBC with HMAC)
    for secure storage of API keys. The encryption key is derived from:
    1. A machine-specific identifier (machine-id, IOPlatformUUID, or MachineGuid)
    2. A randomly generated salt stored in ~/.specify/.salt

    Key derivation uses PBKDF2HMAC with SHA-256 and 1,200,000 iterations
    (OWASP recommended minimum).

    Attributes:
        config_dir: Path to the configuration directory.
    """

    SALT_FILE_NAME: str = ".salt"
    PBKDF2_ITERATIONS: int = 1_200_000  # OWASP recommended minimum

    def __init__(self, config_dir: Path) -> None:
        """Initialize CryptoManager with the config directory.

        Args:
            config_dir: Path to the configuration directory (e.g., ~/.specify).
        """
        self.config_dir = config_dir
        self._fernet: Fernet | None = None

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a plaintext string and return base64-encoded ciphertext.

        Args:
            plaintext: The string to encrypt.

        Returns:
            Base64-encoded ciphertext string.

        Raises:
            EncryptionError: If encryption fails.
        """
        try:
            fernet = self._get_fernet()
            ciphertext = fernet.encrypt(plaintext.encode("utf-8"))
            return base64.urlsafe_b64encode(ciphertext).decode("utf-8")
        except Exception as e:
            raise EncryptionError(
                f"Failed to encrypt data: {e}"
            ) from e

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a ciphertext string and return plaintext.

        Args:
            ciphertext: Base64-encoded ciphertext string.

        Returns:
            Decrypted plaintext string.

        Raises:
            DecryptionError: If decryption fails (corrupted data, wrong key, etc.).
        """
        try:
            fernet = self._get_fernet()
            # Decode from base64
            decoded = base64.urlsafe_b64decode(ciphertext.encode("utf-8"))
            plaintext = fernet.decrypt(decoded)
            return plaintext.decode("utf-8")
        except DecryptionError:
            raise
        except Exception as e:
            raise DecryptionError(
                f"Failed to decrypt data: {e}. "
                "This can happen if:\n"
                "1. The keys were encrypted on a different machine\n"
                "2. The .salt file was corrupted or deleted\n"
                "3. The keys.json file is corrupted\n\n"
                "You may need to re-store your API keys."
            ) from e

    def _get_fernet(self) -> Fernet:
        """Get or create the Fernet instance with derived key.

        Returns:
            Fernet instance for encryption/decryption.

        Raises:
            EncryptionError: If key derivation fails.
        """
        if self._fernet is None:
            key = self._derive_key()
            self._fernet = Fernet(key)
        return self._fernet

    def _get_machine_id(self) -> bytes:
        """Get a machine-specific identifier for key derivation.

        Cross-platform implementation:
        - Linux: /etc/machine-id or /var/lib/dbus/machine-id
        - macOS: IOPlatformUUID via ioreg command
        - Windows: MachineGuid from registry
        - Fallback: hostname + username

        Returns:
            Machine-specific identifier as bytes.

        Raises:
            MachineIdError: If no machine identifier can be determined.
        """
        system = platform.system()

        if system == "Linux":
            return self._get_linux_machine_id()
        elif system == "Darwin":
            return self._get_macos_machine_id()
        elif system == "Windows":
            return self._get_windows_machine_id()
        else:
            return self._get_fallback_machine_id()

    def _get_linux_machine_id(self) -> bytes:
        """Get machine-id from Linux systems.

        Tries /etc/machine-id first, then /var/lib/dbus/machine-id.

        Returns:
            Machine ID as bytes.

        Raises:
            MachineIdError: If machine-id cannot be read.
        """
        # Try /etc/machine-id first (primary location)
        machine_id_paths = ["/etc/machine-id", "/var/lib/dbus/machine-id"]

        for path in machine_id_paths:
            try:
                machine_id_file = Path(path)
                if machine_id_file.exists():
                    machine_id = machine_id_file.read_text(encoding="utf-8").strip()
                    if machine_id:
                        return machine_id.encode("utf-8")
            except OSError:
                continue

        raise MachineIdError(
            "Could not read machine-id from any of: " + ", ".join(machine_id_paths)
        )

    def _get_macos_machine_id(self) -> bytes:
        """Get IOPlatformUUID from macOS using ioreg.

        Returns:
            IOPlatformUUID as bytes.

        Raises:
            MachineIdError: If ioreg command fails.
        """
        try:
            result = subprocess.run(
                ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            )

            for line in result.stdout.split("\n"):
                if "IOPlatformUUID" in line:
                    # Extract UUID from the line
                    uuid = line.split("=")[-1].strip('" \n')
                    if uuid:
                        return uuid.encode("utf-8")

            raise MachineIdError("Could not find IOPlatformUUID in ioreg output")
        except subprocess.TimeoutExpired as e:
            raise MachineIdError(f"ioreg command timed out: {e}") from e
        except subprocess.CalledProcessError as e:
            raise MachineIdError(f"ioreg command failed: {e}") from e
        except FileNotFoundError:
            raise MachineIdError("ioreg command not found (not running macOS?)") from None

    def _get_windows_machine_id(self) -> bytes:
        """Get MachineGuid from Windows registry.

        Returns:
            MachineGuid as bytes.

        Raises:
            MachineIdError: If registry key cannot be read.
        """
        try:
            import winreg

            key_path = r"SOFTWARE\Microsoft\Cryptography"
            value_name = "MachineGuid"

            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                key_path,
                0,
                winreg.KEY_READ,
            ) as key:
                machine_guid: str = winreg.QueryValueEx(key, value_name)[0]
                if machine_guid:
                    return machine_guid.encode("utf-8")

            raise MachineIdError("MachineGuid registry value is empty")
        except FileNotFoundError:
            raise MachineIdError(
                "MachineGuid not found in registry at HKLM\\SOFTWARE\\Microsoft\\Cryptography"
            ) from None
        except OSError as e:
            raise MachineIdError(f"Failed to read registry: {e}") from e
        except ImportError:
            # Fallback if winreg is not available
            return self._get_fallback_machine_id()

    def _get_fallback_machine_id(self) -> bytes:
        """Get fallback machine identifier from hostname + username.

        This is less secure but works across all platforms. A warning is
        emitted when this fallback is used, as the combination of hostname
        and username is more easily guessable than platform-specific IDs.

        Returns:
            Combined hostname + username as bytes.

        Raises:
            MachineIdError: If even fallback fails.
        """
        warnings.warn(
            "Using insecure fallback machine ID (hostname + username). "
            "Platform-specific machine ID could not be determined. "
            "This may result in weaker encryption. "
            "Consider ensuring platform-specific identifiers are accessible.",
            UserWarning,
            stacklevel=3,
        )
        try:
            hostname = socket.gethostname()
            username = os.environ.get("USERNAME") or os.environ.get("USER") or "unknown"
            fallback_id = f"{hostname}-{username}"
            return fallback_id.encode("utf-8")
        except Exception as e:
            raise MachineIdError(
                f"Could not determine fallback machine ID: {e}"
            ) from e

    def _derive_key(self) -> bytes:
        """Derive a Fernet key from machine ID and salt using PBKDF2HMAC.

        Uses PBKDF2HMAC with SHA-256 and 1,200,000 iterations
        to derive a 32-byte key, then encodes it for Fernet usage.

        Returns:
            32-byte key suitable for Fernet encryption.

        Raises:
            EncryptionError: If key derivation fails.
        """
        try:
            salt = self._load_or_create_salt()
            machine_id = self._get_machine_id()

            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=self.PBKDF2_ITERATIONS,
                backend=default_backend(),
            )

            key = kdf.derive(machine_id)
            # Encode to URL-safe base64 for Fernet
            return base64.urlsafe_b64encode(key)
        except MachineIdError:
            raise
        except Exception as e:
            raise EncryptionError(f"Failed to derive encryption key: {e}") from e

    def _load_or_create_salt(self) -> bytes:
        """Load existing salt or create and store a new one.

        The salt file is stored at ~/.specify/.salt with permissions 0600.
        If the file doesn't exist, a new 16-byte random salt is generated
        and saved.

        Returns:
            16-byte salt.

        Raises:
            EncryptionError: If salt file operations fail.
        """
        import secrets

        salt_file = self.config_dir / self.SALT_FILE_NAME

        # Ensure config directory exists
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError as e:
            raise EncryptionError(
                f"Permission denied creating config directory {self.config_dir}: {e}"
            ) from e

        # Try to load existing salt
        if salt_file.exists():
            try:
                salt_data = salt_file.read_bytes()
                # Salt should be exactly 16 bytes
                if len(salt_data) == 16:
                    return salt_data
                else:
                    # Invalid salt length - will recreate
                    pass
            except OSError:
                # Can't read - will recreate
                pass

        # Create new salt
        try:
            new_salt = secrets.token_bytes(16)
            salt_file.write_bytes(new_salt)
            # Set restrictive permissions: owner read/write only (0600)
            salt_file.chmod(stat.S_IRUSR | stat.S_IWUSR)
            return new_salt
        except OSError as e:
            raise EncryptionError(
                f"Failed to create salt file at {salt_file}: {e}"
            ) from e


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
                       If None, uses SPECIFY_CONFIG_DIR env var or ~/.specify

        Raises:
            KeyValidationError: If SPECIFY_CONFIG_DIR is not an absolute path.
        """
        if config_dir is None:
            # Check for environment variable first
            config_dir_env = os.environ.get("SPECIFY_CONFIG_DIR")
            if config_dir_env:
                config_path = Path(config_dir_env).resolve()
                if not config_path.is_absolute():
                    raise KeyValidationError(
                        f"SPECIFY_CONFIG_DIR must be an absolute path, got: {config_dir_env}"
                    )
                self.config_dir: Path = config_path
            else:
                self.config_dir = Path.home() / CONFIG_DIR_NAME
        else:
            self.config_dir = config_dir

        self.keys_file: Path = self.config_dir / KEYS_FILE_NAME

        # Initialize CryptoManager for encryption/decryption
        self._crypto_manager = CryptoManager(self.config_dir)

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

        Handles both encrypted and plain-text formats for backward compatibility.
        If keys are stored in plain-text format, they are migrated to encrypted
        format on next save.

        Returns:
            Dictionary of provider -> key mappings (always decrypted).
            Returns empty dict if file doesn't exist or is empty.

        Raises:
            KeyValidationError: If the keys file contains invalid JSON.
            DecryptionError: If decryption fails (corrupted data, wrong key, etc.).
        """
        if not self.keys_file.exists():
            return {}

        try:
            with self.keys_file.open(encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                # Invalid format - return empty dict
                return {}

            # Check if keys are encrypted
            is_encrypted = data.get("_encrypted", False)

            result: dict[str, str] = {}
            needs_migration = False

            for key, value in data.items():
                # Skip metadata keys (starting with underscore)
                if key.startswith("_"):
                    continue

                if is_encrypted:
                    # Decrypt the encrypted value
                    try:
                        result[key] = self._crypto_manager.decrypt(value)
                    except DecryptionError as e:
                        # Re-raise with context about which provider failed
                        raise DecryptionError(
                            f"Cannot decrypt API key for '{key}': {e}\n\n"
                            "This typically happens when:\n"
                            "1. The keys were encrypted on a different machine\n"
                            "2. The .salt file was corrupted or deleted\n"
                            "3. The keys.json file is corrupted\n\n"
                            "You may need to re-store your API keys."
                        ) from e
                else:
                    # Plain text - needs migration to encrypted format
                    result[key] = value
                    needs_migration = True

            # Migrate plain-text keys to encrypted format on next save
            # This happens transparently when keys are saved again
            if needs_migration and result:
                # Schedule migration by re-saving with encryption
                self._save_keys(result)

            return result
        except json.JSONDecodeError as e:
            raise KeyValidationError(
                f"Invalid keys file format: {e}. "
                "The keys.json file appears to be corrupted.\n\n"
                "Recovery options:\n"
                "1. If you have a backup, restore ~/.specify/keys.json\n"
                "2. Otherwise, delete the corrupted file and re-store your keys:\n"
                "   rm ~/.specify/keys.json\n"
                "   specify store-key openai YOUR_API_KEY\n\n"
                f"File location: {self.keys_file}"
            ) from e
        except DecryptionError:
            # Re-raise DecryptionError without wrapping
            raise

    def _save_keys(self, keys: dict[str, str]) -> None:
        """Save keys to the JSON file in encrypted format.

        Args:
            keys: Dictionary of provider -> key mappings to save.

        Raises:
            PermissionError: If unable to write to the keys file.
            EncryptionError: If encryption fails.
        """
        try:
            # Encrypt each key value before storing
            encrypted_keys: dict[str, Any] = {
                "_version": 2,
                "_encrypted": True,
            }

            for provider, key in keys.items():
                try:
                    encrypted_keys[provider] = self._crypto_manager.encrypt(key)
                except EncryptionError as e:
                    raise EncryptionError(
                        f"Failed to encrypt key for '{provider}': {e}"
                    ) from e

            with self.keys_file.open("w", encoding="utf-8") as f:
                json.dump(encrypted_keys, f, indent=2, sort_keys=True)
            # Set restrictive permissions: owner read/write only (0600)
            self.keys_file.chmod(stat.S_IRUSR | stat.S_IWUSR)
        except PermissionError as e:
            raise KeyValidationError(
                f"Permission denied when writing to {self.keys_file}: {e}"
            ) from e
        except EncryptionError:
            # Re-raise EncryptionError without wrapping
            raise

    def _ensure_config_dir(self) -> None:
        """Ensure the config directory exists with restrictive permissions.

        Creates the directory if it doesn't exist and sets permissions to 0700
        (owner read, write, execute only) to prevent access by other users.

        Raises:
            PermissionError: If unable to create the directory.
        """
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            # Set restrictive permissions: owner read/write/execute only (0700)
            self.config_dir.chmod(stat.S_IRWXU)
        except PermissionError as e:
            raise KeyValidationError(
                f"Permission denied when creating config directory {self.config_dir}: {e}"
            ) from e
