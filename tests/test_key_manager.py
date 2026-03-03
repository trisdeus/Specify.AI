"""
Tests for the KeyManager class in specify.core.key_manager.

This module contains comprehensive unit tests for:
- Storing API keys
- Retrieving API keys
- Listing keys with masking
- Deleting keys
- Key validation
- Error handling
- Encryption and decryption

Tests use the temp_config_dir fixture from conftest.py for isolated testing.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify.core import CryptoManager, KeyManager, KeyNotFoundError, KeyValidationError

# ─────────────────────────────────────────────────────────────────────────────
# Test Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def key_manager(temp_config_dir: Path) -> KeyManager:
    """Create a KeyManager instance with a temporary config directory.

    Args:
        temp_config_dir: Temporary config directory fixture.

    Returns:
        A KeyManager instance configured for testing.
    """
    return KeyManager(config_dir=temp_config_dir)


@pytest.fixture
def key_manager_with_keys(temp_config_dir: Path) -> KeyManager:
    """Create a KeyManager with pre-stored keys.

    Args:
        temp_config_dir: Temporary config directory fixture.

    Returns:
        A KeyManager instance with two stored keys.
    """
    km = KeyManager(config_dir=temp_config_dir)
    km.store_key("openai", "sk-proj-abc123")
    km.store_key("anthropic", "sk-ant-xyz789")
    return km


# ─────────────────────────────────────────────────────────────────────────────
# Store Key Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestStoreKey:
    """Tests for the store_key method."""

    def test_store_key_new_provider(self, key_manager: KeyManager) -> None:
        """Test storing a key for a new provider."""
        key_manager.store_key("openai", "sk-test123")

        # Verify key was stored
        assert key_manager.get_key("openai") == "sk-test123"
        assert key_manager.key_exists("openai") is True

    def test_store_key_creates_config_dir(self, key_manager: KeyManager) -> None:
        """Test that storing a key creates the config directory."""
        key_manager.store_key("ollama", "http://localhost:11434")

        assert key_manager.config_dir.exists()
        assert key_manager.keys_file.exists()

    def test_store_key_overwrites_existing(self, key_manager: KeyManager) -> None:
        """Test that storing a key overwrites an existing key."""
        key_manager.store_key("openai", "sk-old-key")
        key_manager.store_key("openai", "sk-new-key")

        assert key_manager.get_key("openai") == "sk-new-key"

    def test_store_key_all_providers(self, key_manager: KeyManager) -> None:
        """Test storing keys for all valid providers."""
        providers = ["ollama", "openai", "anthropic"]
        keys = ["http://localhost:11434", "sk-openai-test", "sk-ant-test"]

        for provider, key in zip(providers, keys, strict=False):
            key_manager.store_key(provider, key)
            assert key_manager.get_key(provider) == key

    def test_store_key_case_insensitive_provider(self, key_manager: KeyManager) -> None:
        """Test that provider names are case insensitive."""
        key_manager.store_key("OpenAI", "sk-test")
        key_manager.store_key("OLLAMA", "http://localhost:11434")

        assert key_manager.get_key("openai") == "sk-test"
        assert key_manager.get_key("ollama") == "http://localhost:11434"

    def test_store_key_strips_whitespace(self, key_manager: KeyManager) -> None:
        """Test that key whitespace is stripped."""
        key_manager.store_key("openai", "  sk-test123  ")

        assert key_manager.get_key("openai") == "sk-test123"

    def test_store_key_invalid_provider(self, key_manager: KeyManager) -> None:
        """Test that storing with invalid provider raises error."""
        with pytest.raises(KeyValidationError, match="Invalid provider"):
            key_manager.store_key("invalid", "sk-test")

    def test_store_key_empty_key(self, key_manager: KeyManager) -> None:
        """Test that storing an empty key raises error."""
        with pytest.raises(KeyValidationError, match="API key is required"):
            key_manager.store_key("openai", "")

    def test_store_key_whitespace_only_key(self, key_manager: KeyManager) -> None:
        """Test that storing a whitespace-only key raises error."""
        with pytest.raises(KeyValidationError, match="API key is required"):
            key_manager.store_key("openai", "   ")


# ─────────────────────────────────────────────────────────────────────────────
# Get Key Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestGetKey:
    """Tests for the get_key method."""

    def test_get_stored_key(self, key_manager_with_keys: KeyManager) -> None:
        """Test retrieving a stored key."""
        key = key_manager_with_keys.get_key("openai")
        assert key == "sk-proj-abc123"

    def test_get_nonexistent_key(self, key_manager: KeyManager) -> None:
        """Test that getting a non-existent key raises KeyNotFoundError."""
        with pytest.raises(KeyNotFoundError, match="No key found for provider"):
            key_manager.get_key("nonexistent")

    def test_get_key_case_insensitive(self, key_manager_with_keys: KeyManager) -> None:
        """Test that getting key is case insensitive."""
        assert key_manager_with_keys.get_key("OpenAI") == "sk-proj-abc123"
        assert key_manager_with_keys.get_key("ANTHROPIC") == "sk-ant-xyz789"


# ─────────────────────────────────────────────────────────────────────────────
# List Keys Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestListKeys:
    """Tests for the list_keys method."""

    def test_list_keys_with_data(self, key_manager_with_keys: KeyManager) -> None:
        """Test listing keys returns masked values."""
        keys = key_manager_with_keys.list_keys()

        assert "openai" in keys
        assert "anthropic" in keys
        assert keys["openai"] == "sk-...123"
        assert keys["anthropic"] == "sk-...789"

    def test_list_keys_empty(self, key_manager: KeyManager) -> None:
        """Test listing keys when no keys stored."""
        keys = key_manager.list_keys()

        assert keys == {}

    def test_list_keys_nonexistent_file(self, key_manager: KeyManager) -> None:
        """Test listing keys when file doesn't exist."""
        # keys_file doesn't exist yet
        keys = key_manager.list_keys()

        assert keys == {}


# ─────────────────────────────────────────────────────────────────────────────
# Delete Key Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestDeleteKey:
    """Tests for the delete_key method."""

    def test_delete_existing_key(self, key_manager: KeyManager) -> None:
        """Test deleting an existing key."""
        key_manager.store_key("openai", "sk-test")
        # delete_key returns None on success
        result = key_manager.delete_key("openai")

        assert result is None
        with pytest.raises(KeyNotFoundError):
            key_manager.get_key("openai")
        assert key_manager.key_exists("openai") is False

    def test_delete_nonexistent_key(self, key_manager: KeyManager) -> None:
        """Test deleting a non-existent key raises KeyNotFoundError."""
        with pytest.raises(KeyNotFoundError, match="No key found for provider"):
            key_manager.delete_key("nonexistent")

    def test_delete_key_case_insensitive(self, key_manager: KeyManager) -> None:
        """Test that deleting key is case insensitive."""
        key_manager.store_key("openai", "sk-test")
        result = key_manager.delete_key("OpenAI")

        assert result is None
        with pytest.raises(KeyNotFoundError):
            key_manager.get_key("openai")


# ─────────────────────────────────────────────────────────────────────────────
# Key Exists Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestKeyExists:
    """Tests for the key_exists method."""

    def test_key_exists_true(self, key_manager_with_keys: KeyManager) -> None:
        """Test that key_exists returns True for stored keys."""
        assert key_manager_with_keys.key_exists("openai") is True
        assert key_manager_with_keys.key_exists("anthropic") is True

    def test_key_exists_false(self, key_manager: KeyManager) -> None:
        """Test that key_exists returns False for non-existent keys."""
        assert key_manager.key_exists("openai") is False

    def test_key_exists_case_insensitive(
        self, key_manager_with_keys: KeyManager
    ) -> None:
        """Test that key_exists is case insensitive."""
        assert key_manager_with_keys.key_exists("OpenAI") is True
        assert key_manager_with_keys.key_exists("ANTHROPIC") is True


# ─────────────────────────────────────────────────────────────────────────────
# Mask Key Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestMaskKey:
    """Tests for the _mask_key method."""

    def test_mask_normal_key(self, key_manager: KeyManager) -> None:
        """Test masking a normal length key."""
        masked = key_manager._mask_key("sk-proj-abc123")
        assert masked == "sk-...123"

    def test_mask_short_key(self, key_manager: KeyManager) -> None:
        """Test masking a short key."""
        masked = key_manager._mask_key("abc")
        assert masked == "***"

    def test_mask_exactly_six_char_key(self, key_manager: KeyManager) -> None:
        """Test masking a key with exactly 6 characters."""
        masked = key_manager._mask_key("abcdef")
        assert masked == "abc...def"

    def test_mask_five_char_key(self, key_manager: KeyManager) -> None:
        """Test masking a key with 5 characters."""
        masked = key_manager._mask_key("abcde")
        assert masked == "***"

    def test_mask_url_key(self, key_manager: KeyManager) -> None:
        """Test masking a URL key (Ollama)."""
        masked = key_manager._mask_key("http://localhost:11434")
        assert masked == "htt...434"


# ─────────────────────────────────────────────────────────────────────────────
# CryptoManager Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestCryptoManager:
    """Tests for the CryptoManager class."""

    def test_encrypt_decrypt_roundtrip(self, temp_config_dir: Path) -> None:
        """Test that encrypt/decrypt returns original value."""
        crypto = CryptoManager(temp_config_dir)
        original = "sk-test-secret-key-123"
        encrypted = crypto.encrypt(original)
        decrypted = crypto.decrypt(encrypted)

        assert decrypted == original
        assert encrypted != original

    def test_salt_persistence(self, temp_config_dir: Path) -> None:
        """Test that salt is saved and reused."""
        crypto1 = CryptoManager(temp_config_dir)
        encrypted1 = crypto1.encrypt("test")  # Trigger salt creation

        crypto2 = CryptoManager(temp_config_dir)
        encrypted2 = crypto2.encrypt("test")

        # Should use same salt, so encrypted values should be identical
        # (since Fernet uses random IV, they may differ - but both should decrypt)
        assert crypto2.decrypt(encrypted1) == "test"
        assert crypto2.decrypt(encrypted2) == "test"

    def test_keys_are_encrypted_in_file(self, key_manager: KeyManager) -> None:
        """Test that keys stored in file are not plain-text."""
        key_manager.store_key("openai", "sk-secret-key-12345")

        # Read raw file
        with key_manager.keys_file.open(encoding="utf-8") as f:
            content = f.read()

        # The secret should NOT appear in plain text
        assert "sk-secret-key-12345" not in content


# ─────────────────────────────────────────────────────────────────────────────
# Integration Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestKeyManagerIntegration:
    """Integration tests for complete workflows."""

    def test_full_workflow(self, key_manager: KeyManager) -> None:
        """Test a complete workflow: store, get, list, delete."""
        # Store keys
        key_manager.store_key("openai", "sk-proj-abc123")
        key_manager.store_key("anthropic", "sk-ant-xyz789")

        # Verify keys exist
        assert key_manager.key_exists("openai")
        assert key_manager.key_exists("anthropic")

        # Get keys
        assert key_manager.get_key("openai") == "sk-proj-abc123"

        # List keys
        keys = key_manager.list_keys()
        assert len(keys) == 2

        # Delete one key - returns None on success
        result = key_manager.delete_key("openai")
        assert result is None

        # Verify deletion
        assert not key_manager.key_exists("openai")
        assert key_manager.key_exists("anthropic")

        # List after deletion
        keys = key_manager.list_keys()
        assert len(keys) == 1

    def test_keys_persisted_to_file(self, temp_config_dir: Path) -> None:
        """Test that keys are persisted to the JSON file."""
        # Create first manager and store key
        km1 = KeyManager(config_dir=temp_config_dir)
        km1.store_key("openai", "sk-test123")

        # Create second manager and verify key is accessible
        km2 = KeyManager(config_dir=temp_config_dir)
        assert km2.get_key("openai") == "sk-test123"

    def test_json_format(self, key_manager: KeyManager) -> None:
        """Test that keys are stored in encrypted JSON format."""
        key_manager.store_key("openai", "sk-test123")

        keys_file = key_manager.keys_file
        with keys_file.open(encoding="utf-8") as f:
            data = json.load(f)

        assert isinstance(data, dict)
        assert data.get("_encrypted") is True
        assert data.get("_version") == 3
        # The actual key should be encrypted in nested format
        assert data.get("openai") is not None
        assert isinstance(data.get("openai"), dict)
        # Check nested structure with api_key, base_url, model
        assert "api_key" in data.get("openai")
        assert "base_url" in data.get("openai")
        assert "model" in data.get("openai")
        # The api_key should be encrypted (not plain-text)
        assert data.get("openai").get("api_key") != "sk-test123"
        # Encrypted tokens are base64-encoded (starts with 'Z' due to double encoding)
        assert data.get("openai").get("api_key").startswith("Z")


# ─────────────────────────────────────────────────────────────────────────────
# Backward Compatibility Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestBackwardCompatibility:
    """Tests for backward compatibility with plain-text keys."""

    def test_backward_compatibility_plain_text_migration(
        self, temp_config_dir: Path
    ) -> None:
        """Test that plain-text keys are migrated to encrypted format."""
        # Create a plain-text keys file (old format)
        keys_file = temp_config_dir / "keys.json"
        plain_text_data = {"openai": "sk-plain-text-key"}
        with keys_file.open("w", encoding="utf-8") as f:
            json.dump(plain_text_data, f)

        # Load with KeyManager - should migrate automatically
        km = KeyManager(config_dir=temp_config_dir)
        key = km.get_key("openai")

        # Key should be retrievable
        assert key == "sk-plain-text-key"

        # File should now be encrypted
        with keys_file.open(encoding="utf-8") as f:
            data = json.load(f)
        assert data.get("_encrypted") is True


# ─────────────────────────────────────────────────────────────────────────────
# Error Handling Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestErrorHandling:
    """Tests for error handling scenarios."""

    def test_corrupted_json_file(self, temp_config_dir: Path) -> None:
        """Test handling of corrupted JSON file."""
        # Create corrupted keys file in the correct location (config_dir/keys.json)
        keys_file = temp_config_dir / "keys.json"
        keys_file.write_text("{ invalid json", encoding="utf-8")

        km = KeyManager(config_dir=temp_config_dir)

        with pytest.raises(KeyValidationError, match="Invalid keys file format"):
            km.list_keys()

    def test_invalid_json_type(self, temp_config_dir: Path) -> None:
        """Test handling of non-dict JSON."""
        keys_file = temp_config_dir / ".specify" / "keys.json"
        keys_file.parent.mkdir(parents=True, exist_ok=True)
        keys_file.write_text('"not a dict"', encoding="utf-8")

        km = KeyManager(config_dir=temp_config_dir)

        # Should return empty dict, not crash
        keys = km.list_keys()
        assert keys == {}


# ─────────────────────────────────────────────────────────────────────────────
# New Method Tests: any_keys_configured
# ─────────────────────────────────────────────────────────────────────────────


class TestAnyKeysConfigured:
    """Tests for the any_keys_configured method."""

    def test_no_keys_configured_empty_store(self, key_manager: KeyManager) -> None:
        """Test returns False when no keys are configured."""
        assert key_manager.any_keys_configured() is False

    def test_returns_true_with_stored_key(self, key_manager: KeyManager) -> None:
        """Test returns True when a key is in local store."""
        key_manager.store_key("openai", "sk-proj-abc123")
        assert key_manager.any_keys_configured() is True

    def test_returns_true_with_env_var(self, key_manager: KeyManager, monkeypatch) -> None:
        """Test returns True when key is in environment variable."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-env-key-123")
        assert key_manager.any_keys_configured() is True

    def test_returns_false_with_none_api_key(self, key_manager: KeyManager) -> None:
        """Test returns False when provider has None api_key (like ollama without key)."""
        key_manager.store_key("ollama", None)
        # ollama stored with None key should return False
        assert key_manager.any_keys_configured() is False


# ─────────────────────────────────────────────────────────────────────────────
# New Method Tests: list_providers
# ─────────────────────────────────────────────────────────────────────────────


class TestListProviders:
    """Tests for the list_providers method."""

    def test_empty_store(self, key_manager: KeyManager) -> None:
        """Test returns empty list when no providers configured."""
        assert key_manager.list_providers() == []

    def test_single_provider(self, key_manager: KeyManager) -> None:
        """Test returns list with single provider."""
        key_manager.store_key("openai", "sk-test")
        providers = key_manager.list_providers()
        assert providers == ["openai"]

    def test_multiple_providers_sorted(self, key_manager: KeyManager) -> None:
        """Test returns sorted list of providers."""
        key_manager.store_key("anthropic", "sk-ant")
        key_manager.store_key("openai", "sk-openai")
        key_manager.store_key("ollama", None)

        providers = key_manager.list_providers()
        assert providers == ["anthropic", "ollama", "openai"]

    def test_only_local_store_providers(self, key_manager: KeyManager, monkeypatch) -> None:
        """Test only returns providers from local store, not env vars."""
        # Set env var but don't store any key locally
        monkeypatch.setenv("OPENAI_API_KEY", "sk-env-key")
        # list_providers should only return what's in local store
        assert key_manager.list_providers() == []


# ─────────────────────────────────────────────────────────────────────────────
# New Method Tests: get_model
# ─────────────────────────────────────────────────────────────────────────────


class TestGetModel:
    """Tests for the get_model method."""

    def test_model_set(self, key_manager: KeyManager) -> None:
        """Test returns model when configured."""
        key_manager.store_key("openai", "sk-test", model="gpt-4")
        assert key_manager.get_model("openai") == "gpt-4"

    def test_model_not_set(self, key_manager: KeyManager) -> None:
        """Test returns None when model not configured."""
        key_manager.store_key("openai", "sk-test")
        assert key_manager.get_model("openai") is None

    def test_provider_not_found(self, key_manager: KeyManager) -> None:
        """Test returns None for non-existent provider."""
        assert key_manager.get_model("nonexistent") is None

    def test_case_insensitive(self, key_manager: KeyManager) -> None:
        """Test provider name is case insensitive."""
        key_manager.store_key("OpenAI", "sk-test", model="gpt-4")
        assert key_manager.get_model("openai") == "gpt-4"
        assert key_manager.get_model("OPENAI") == "gpt-4"


# ─────────────────────────────────────────────────────────────────────────────
# New Method Tests: get_base_url
# ─────────────────────────────────────────────────────────────────────────────


class TestGetBaseUrl:
    """Tests for the get_base_url method."""

    def test_base_url_set(self, key_manager: KeyManager) -> None:
        """Test returns base_url when configured."""
        key_manager.store_key("ollama", None, base_url="http://localhost:11434")
        assert key_manager.get_base_url("ollama") == "http://localhost:11434"

    def test_base_url_not_set(self, key_manager: KeyManager) -> None:
        """Test returns None when base_url not configured."""
        key_manager.store_key("openai", "sk-test")
        assert key_manager.get_base_url("openai") is None

    def test_provider_not_found(self, key_manager: KeyManager) -> None:
        """Test returns None for non-existent provider."""
        assert key_manager.get_base_url("nonexistent") is None


# ─────────────────────────────────────────────────────────────────────────────
# New Method Tests: get_provider_config
# ─────────────────────────────────────────────────────────────────────────────


class TestGetProviderConfig:
    """Tests for the get_provider_config method."""

    def test_full_config(self, key_manager: KeyManager) -> None:
        """Test returns full config with all fields."""
        key_manager.store_key("openai", "sk-test123", model="gpt-4", base_url="https://api.openai.com")
        config = key_manager.get_provider_config("openai")

        assert config is not None
        assert config["api_key"] == "sk-test123"
        assert config["model"] == "gpt-4"
        assert config["base_url"] == "https://api.openai.com"

    def test_partial_config(self, key_manager: KeyManager) -> None:
        """Test returns config with some fields None."""
        key_manager.store_key("openai", "sk-test")
        config = key_manager.get_provider_config("openai")

        assert config is not None
        assert config["api_key"] == "sk-test"
        assert config["model"] is None
        assert config["base_url"] is None

    def test_provider_not_found(self, key_manager: KeyManager) -> None:
        """Test returns None for non-existent provider."""
        assert key_manager.get_provider_config("nonexistent") is None

    def test_api_key_decrypted(self, key_manager: KeyManager) -> None:
        """Test that returned api_key is decrypted."""
        key_manager.store_key("openai", "sk-secret-key-12345")
        config = key_manager.get_provider_config("openai")

        assert config is not None
        # Should return decrypted key
        assert config["api_key"] == "sk-secret-key-12345"


# ─────────────────────────────────────────────────────────────────────────────
# New Method Tests: store_key with model and base_url
# ─────────────────────────────────────────────────────────────────────────────


class TestStoreKeyWithModelAndBaseUrl:
    """Tests for the updated store_key method with model and base_url."""

    def test_store_key_with_model(self, key_manager: KeyManager) -> None:
        """Test storing key with model."""
        key_manager.store_key("openai", "sk-test", model="gpt-4")
        assert key_manager.get_key("openai") == "sk-test"
        assert key_manager.get_model("openai") == "gpt-4"

    def test_store_key_with_base_url(self, key_manager: KeyManager) -> None:
        """Test storing key with base_url."""
        key_manager.store_key("openai", "sk-test", base_url="https://custom.openai.com")
        assert key_manager.get_key("openai") == "sk-test"
        assert key_manager.get_base_url("openai") == "https://custom.openai.com"

    def test_store_key_with_all_options(self, key_manager: KeyManager) -> None:
        """Test storing key with model and base_url."""
        key_manager.store_key("openai", "sk-test", model="gpt-4", base_url="https://api.openai.com")

        assert key_manager.get_key("openai") == "sk-test"
        assert key_manager.get_model("openai") == "gpt-4"
        assert key_manager.get_base_url("openai") == "https://api.openai.com"

    def test_ollama_no_key_required(self, key_manager: KeyManager) -> None:
        """Test that ollama can be stored without API key."""
        key_manager.store_key("ollama", None, model="llama3", base_url="http://localhost:11434")

        assert key_manager.get_model("ollama") == "llama3"
        assert key_manager.get_base_url("ollama") == "http://localhost:11434"

    def test_openai_requires_key(self, key_manager: KeyManager) -> None:
        """Test that openai still requires a key."""
        with pytest.raises(KeyValidationError, match="API key is required"):
            key_manager.store_key("openai", None)

    def test_update_model_only(self, key_manager: KeyManager) -> None:
        """Test updating model while preserving existing key."""
        key_manager.store_key("openai", "sk-original")
        key_manager.store_key("openai", "sk-original", model="gpt-4")

        # Key should be preserved
        assert key_manager.get_key("openai") == "sk-original"
        # Model should be updated
        assert key_manager.get_model("openai") == "gpt-4"


# ─────────────────────────────────────────────────────────────────────────────
# New Method Tests: Backward Compatibility Migration
# ─────────────────────────────────────────────────────────────────────────────


class TestBackwardCompatibilityMigration:
    """Tests for backward compatibility with old format."""

    def test_migrate_old_string_format(self, temp_config_dir: Path) -> None:
        """Test that old string format is migrated to new format."""
        # Create an old format keys file (string values instead of nested dicts)
        keys_file = temp_config_dir / "keys.json"
        old_format_data = {"_version": 1, "openai": "sk-plain-text-key", "anthropic": "sk-ant-key"}

        with keys_file.open("w", encoding="utf-8") as f:
            json.dump(old_format_data, f)

        # Load with KeyManager - should migrate automatically
        km = KeyManager(config_dir=temp_config_dir)

        # Keys should be accessible
        assert km.get_key("openai") == "sk-plain-text-key"
        assert km.get_key("anthropic") == "sk-ant-key"

    def test_get_key_after_migration(self, temp_config_dir: Path) -> None:
        """Test that get_key works after migrating old format."""
        keys_file = temp_config_dir / "keys.json"
        old_format_data = {"openai": "sk-old-key"}

        with keys_file.open("w", encoding="utf-8") as f:
            json.dump(old_format_data, f)

        km = KeyManager(config_dir=temp_config_dir)
        key = km.get_key("openai")
        assert key == "sk-old-key"

    def test_list_keys_after_migration(self, temp_config_dir: Path) -> None:
        """Test that list_keys works after migrating old format."""
        keys_file = temp_config_dir / "keys.json"
        old_format_data = {"openai": "sk-proj-abc123", "anthropic": "sk-ant-xyz789"}

        with keys_file.open("w", encoding="utf-8") as f:
            json.dump(old_format_data, f)

        km = KeyManager(config_dir=temp_config_dir)
        keys = km.list_keys()

        assert "openai" in keys
        assert "anthropic" in keys
        assert keys["openai"] == "sk-...123"
        assert keys["anthropic"] == "sk-...789"
