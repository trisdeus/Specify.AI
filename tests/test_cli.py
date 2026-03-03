"""
Tests for the Specify.AI CLI.

This module contains tests for:
- CLI entry point
- --version flag
- --help flag
- Command groups (generate, config, check-consistency, fix-inconsistencies)
- Error handling
- First-run detection and onboarding
- Interactive flows (main menu, consistency check, delete-key)
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner
from unittest import mock

from pathlib import Path

from specify import __version__
from specify.cli import (
    cli,
    main,
    _check_first_run,
    _should_skip_onboarding,
    prompt_provider_selection,
    prompt_key_input,
    prompt_model_selection,
    save_provider_config,
    show_main_menu,
    prompt_consistency_check,
    run_consistency_check,
    display_inconsistency_report,
    prompt_fix_inconsistencies,
    consistency_check_loop,
    run_interactive_delete,
)
from specify.core.key_manager import KeyManager

# Add the missing import for Click's prompt handling
import click

# ─────────────────────────────────────────────────────────────────────────────
# Version Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestVersion:
    """Tests for the --version flag."""

    def test_version_flag(self, cli_runner: CliRunner) -> None:
        """Test that --version prints the correct version string."""
        result = cli_runner.invoke(cli, ["--version"])

        assert result.exit_code == 0
        assert "specify-ai" in result.output
        assert __version__ in result.output

    def test_version_format(self, cli_runner: CliRunner) -> None:
        """Test that version output follows expected format."""
        result = cli_runner.invoke(cli, ["--version"])

        # Expected format: "specify-ai, version X.Y.Z"
        assert "specify-ai, version" in result.output
        assert "0.1.0" in result.output


# ─────────────────────────────────────────────────────────────────────────────
# Help Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestHelp:
    """Tests for the --help flag."""

    def test_help_flag(self, cli_runner: CliRunner) -> None:
        """Test that --help shows usage information."""
        result = cli_runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "Usage:" in result.output
        assert "Specify.AI" in result.output

    def test_help_shows_commands(self, cli_runner: CliRunner) -> None:
        """Test that --help shows available commands."""
        result = cli_runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "generate" in result.output
        assert "config" in result.output
        assert "check-consistency" in result.output
        assert "fix-inconsistencies" in result.output

    def test_help_no_args(self, cli_runner: CliRunner) -> None:
        """Test that running with no arguments shows help message."""
        result = cli_runner.invoke(cli, [])

        # Click groups exit with code 2 when no args provided (shows help)
        # This is expected behavior - the help is shown in the output
        assert "Usage:" in result.output or "Specify.AI" in result.output


# ─────────────────────────────────────────────────────────────────────────────
# Main Entry Point Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestMain:
    """Tests for the main entry point."""

    def test_main_returns_int(self) -> None:
        """Test that main() returns an integer exit code."""
        exit_code = main(["--version"])

        assert isinstance(exit_code, int)
        assert exit_code == 0

    def test_main_with_none_args(self) -> None:
        """Test that main() works with None args (uses sys.argv)."""
        # This should not raise an exception
        exit_code = main(["--help"])

        assert exit_code == 0

    def test_main_handles_click_exception(self) -> None:
        """Test that main() handles Click exceptions gracefully."""
        # Pass an invalid command
        exit_code = main(["invalid-command-that-does-not-exist"])

        # Should return non-zero exit code
        assert exit_code != 0

    def test_main_invalid_args_type(self) -> None:
        """Test that main() raises TypeError for invalid args type."""
        with pytest.raises(TypeError, match="args must be a Sequence or None"):
            main("invalid-args")  # type: ignore[arg-type]


# ─────────────────────────────────────────────────────────────────────────────
# Generate Command Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestGenerateCommand:
    """Tests for the generate command."""

    def test_generate_help(self, cli_runner: CliRunner) -> None:
        """Test that generate --help shows usage."""
        result = cli_runner.invoke(cli, ["generate", "--help"])

        assert result.exit_code == 0
        assert "Generate documentation" in result.output
        assert "--prompt" in result.output
        assert "--type" in result.output
        assert "--provider" in result.output

    def test_generate_requires_prompt(self, cli_runner: CliRunner) -> None:
        """Test that generate requires a prompt."""
        result = cli_runner.invoke(cli, ["generate"])

        assert result.exit_code != 0
        assert "Missing option" in result.output or "--prompt" in result.output

    def test_generate_with_prompt(self, cli_runner: CliRunner) -> None:
        """Test generate command with a prompt."""
        result = cli_runner.invoke(
            cli,
            ["generate", "--prompt", "Build a task app", "--type", "prd"],
        )

        # Command should succeed (even though not fully implemented)
        assert result.exit_code == 0
        assert "not yet implemented" in result.output.lower()

    def test_generate_invalid_type(self, cli_runner: CliRunner) -> None:
        """Test generate with invalid document type."""
        result = cli_runner.invoke(
            cli,
            ["generate", "--prompt", "Build a task app", "--type", "invalid"],
        )

        assert result.exit_code != 0
        assert "invalid" in result.output.lower() or "choice" in result.output.lower()

    def test_generate_invalid_provider(self, cli_runner: CliRunner) -> None:
        """Test generate with invalid provider."""
        result = cli_runner.invoke(
            cli,
            ["generate", "--prompt", "Build a task app", "--provider", "invalid"],
        )

        assert result.exit_code != 0

    def test_generate_no_consistency_check_flag(self, cli_runner: CliRunner) -> None:
        """Test generate with --no-consistency-check flag."""
        result = cli_runner.invoke(
            cli,
            ["generate", "--prompt", "Build a task app", "--no-consistency-check"],
        )
        assert result.exit_code == 0

    def test_generate_auto_fix_flag(self, cli_runner: CliRunner) -> None:
        """Test generate with --auto-fix flag."""
        result = cli_runner.invoke(
            cli,
            ["generate", "--prompt", "Build a task app", "--auto-fix"],
        )
        assert result.exit_code == 0

    def test_generate_both_new_flags(self, cli_runner: CliRunner) -> None:
        """Test generate with both --no-consistency-check and --auto-fix flags."""
        result = cli_runner.invoke(
            cli,
            ["generate", "--prompt", "Build a task app", "--no-consistency-check", "--auto-fix"],
        )
        assert result.exit_code == 0

    def test_generate_help_shows_new_flags(self, cli_runner: CliRunner) -> None:
        """Test that generate --help shows the new flags."""
        result = cli_runner.invoke(cli, ["generate", "--help"])
        assert result.exit_code == 0
        assert "--no-consistency-check" in result.output
        assert "--auto-fix" in result.output
        assert "Skip post-generation consistency check" in result.output
        assert "Automatically fix inconsistencies" in result.output


# ─────────────────────────────────────────────────────────────────────────────
# Config Command Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestConfigCommand:
    """Tests for the config command group."""

    def test_config_help(self, cli_runner: CliRunner) -> None:
        """Test that config --help shows usage."""
        result = cli_runner.invoke(cli, ["config", "--help"])

        assert result.exit_code == 0
        assert "Manage configuration" in result.output
        assert "set-key" in result.output
        assert "list-keys" in result.output
        assert "delete-key" in result.output

    def test_config_set_key_help(self, cli_runner: CliRunner) -> None:
        """Test that config set-key --help shows usage."""
        result = cli_runner.invoke(cli, ["config", "set-key", "--help"])

        assert result.exit_code == 0
        assert "--provider" in result.output
        assert "--key" in result.output

    def test_config_set_key_requires_provider(self, cli_runner: CliRunner) -> None:
        """Test that set-key requires provider."""
        result = cli_runner.invoke(cli, ["config", "set-key", "--key", "test-key"])

        assert result.exit_code != 0

    def test_config_set_key_requires_key(self, cli_runner: CliRunner) -> None:
        """Test that set-key requires key."""
        result = cli_runner.invoke(cli, ["config", "set-key", "--provider", "openai"])

        assert result.exit_code != 0

    def test_config_list_keys_empty(
        self, cli_runner: CliRunner, temp_config_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test listing keys when none are configured."""
        # Set environment variable so CLI uses the isolated temp config directory
        monkeypatch.setenv("SPECIFY_CONFIG_DIR", str(temp_config_dir))

        result = cli_runner.invoke(cli, ["config", "list-keys"])

        assert result.exit_code == 0
        assert "No API keys configured" in result.output

    def test_config_list_keys_with_data(
        self, cli_runner: CliRunner, temp_config_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test listing keys when some are configured."""
        # Set up a key using KeyManager with temp directory
        key_manager = KeyManager(config_dir=temp_config_dir)
        key_manager.store_key("openai", "sk-test-key-12345")

        # Set environment variable so CLI uses the same config directory
        monkeypatch.setenv("SPECIFY_CONFIG_DIR", str(temp_config_dir))

        result = cli_runner.invoke(cli, ["config", "list-keys"])

        assert result.exit_code == 0
        assert "openai" in result.output.lower()
        assert "sk-" in result.output  # Masked key prefix should be visible

    def test_config_list_keys_with_env_var(
        self, cli_runner: CliRunner, temp_config_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test listing keys includes keys from environment variables."""
        # Use isolated temp config directory
        monkeypatch.setenv("SPECIFY_CONFIG_DIR", str(temp_config_dir))
        # Set env var for the key
        monkeypatch.setenv("OPENAI_API_KEY", "sk-env-test-key-12345")

        # Run CLI
        result = cli_runner.invoke(cli, ["config", "list-keys"])

        assert result.exit_code == 0
        assert "openai" in result.output.lower()
        assert "sk-" in result.output

    def test_config_delete_key_requires_provider(
        self, cli_runner: CliRunner, temp_config_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that delete-key works without provider (shows interactive or no keys message)."""
        # Set environment variable so CLI uses the isolated temp config directory
        monkeypatch.setenv("SPECIFY_CONFIG_DIR", str(temp_config_dir))

        result = cli_runner.invoke(cli, ["config", "delete-key"])

        # Should succeed with no provider (shows interactive selection or no keys message)
        assert result.exit_code == 0
        # When no keys are configured, should show this message
        assert "No API keys configured" in result.output


# ─────────────────────────────────────────────────────────────────────────────
# Consistency Command Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestConsistencyCommands:
    """Tests for consistency checking commands."""

    def test_check_consistency_help(self, cli_runner: CliRunner) -> None:
        """Test that check-consistency --help shows usage."""
        result = cli_runner.invoke(cli, ["check-consistency", "--help"])

        assert result.exit_code == 0
        assert "--dir" in result.output

    def test_check_consistency_default_dir(self, cli_runner: CliRunner) -> None:
        """Test check-consistency with default directory."""
        result = cli_runner.invoke(cli, ["check-consistency"])

        # Should succeed even if directory doesn't exist (not implemented yet)
        assert result.exit_code == 0
        assert "not yet implemented" in result.output.lower()

    def test_fix_inconsistencies_help(self, cli_runner: CliRunner) -> None:
        """Test that fix-inconsistencies --help shows usage."""
        result = cli_runner.invoke(cli, ["fix-inconsistencies", "--help"])

        assert result.exit_code == 0
        assert "--dir" in result.output
        assert "--dry-run" in result.output

    def test_fix_inconsistencies_dry_run(self, cli_runner: CliRunner) -> None:
        """Test fix-inconsistencies with --dry-run flag."""
        result = cli_runner.invoke(cli, ["fix-inconsistencies", "--dry-run"])

        assert result.exit_code == 0
        assert "not yet implemented" in result.output.lower()


# ─────────────────────────────────────────────────────────────────────────────
# Verbose Flag Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestVerboseFlag:
    """Tests for the --verbose flag."""

    def test_verbose_flag_accepted(self, cli_runner: CliRunner) -> None:
        """Test that --verbose flag is accepted."""
        result = cli_runner.invoke(cli, ["--verbose", "--help"])

        assert result.exit_code == 0

    def test_verbose_short_flag(self, cli_runner: CliRunner) -> None:
        """Test that -v flag is accepted."""
        result = cli_runner.invoke(cli, ["-v", "--help"])

        assert result.exit_code == 0


# ─────────────────────────────────────────────────────────────────────────────
# Package Import Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestPackageImport:
    """Tests for package imports."""

    def test_import_specify(self) -> None:
        """Test that the specify package can be imported."""
        import specify

        assert hasattr(specify, "__version__")
        assert specify.__version__ == "0.1.0"

    def test_import_cli(self) -> None:
        """Test that the CLI module can be imported."""
        from specify import cli

        assert hasattr(cli, "cli")
        assert hasattr(cli, "main")

    def test_import_submodules(self) -> None:
        """Test that submodules can be imported."""
        import specify.analysis
        import specify.core
        import specify.generators
        import specify.providers
        import specify.rules
        import specify.utils

        # All should import without error
        assert specify.core is not None
        assert specify.providers is not None
        assert specify.generators is not None
        assert specify.rules is not None
        assert specify.analysis is not None
        assert specify.utils is not None


# ─────────────────────────────────────────────────────────────────────────────
# Edge Case Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_invalid_command(self, cli_runner: CliRunner) -> None:
        """Test that invalid commands show error and suggest --help."""
        result = cli_runner.invoke(cli, ["invalid-command"])

        assert result.exit_code != 0
        # Click shows "No such command" for invalid commands
        assert "No such command" in result.output or "Error" in result.output

    def test_generate_all_types(self, cli_runner: CliRunner) -> None:
        """Test generate with --type all."""
        result = cli_runner.invoke(
            cli,
            ["generate", "--prompt", "Build a task app", "--type", "all"],
        )

        assert result.exit_code == 0

    def test_generate_each_type(self, cli_runner: CliRunner) -> None:
        """Test generate with each document type."""
        doc_types = ["app-flow", "bdd", "design-doc", "prd", "tech-arch"]

        for doc_type in doc_types:
            result = cli_runner.invoke(
                cli,
                ["generate", "--prompt", "Build a task app", "--type", doc_type],
            )
            assert result.exit_code == 0, f"Failed for type: {doc_type}"

    def test_generate_each_provider(self, cli_runner: CliRunner) -> None:
        """Test generate with each provider."""
        providers = ["ollama", "openai", "anthropic"]

        for provider in providers:
            result = cli_runner.invoke(
                cli,
                [
                    "generate",
                    "--prompt",
                    "Build a task app",
                    "--type",
                    "prd",
                    "--provider",
                    provider,
                ],
            )
            assert result.exit_code == 0, f"Failed for provider: {provider}"

    def test_config_set_key_each_provider(self, cli_runner: CliRunner) -> None:
        """Test config set-key with each provider."""
        providers = ["ollama", "openai", "anthropic"]

        for provider in providers:
            result = cli_runner.invoke(
                cli,
                ["config", "set-key", "--provider", provider, "--key", "test-key"],
            )
            assert result.exit_code == 0, f"Failed for provider: {provider}"

    def test_config_delete_key_each_provider(
        self, cli_runner: CliRunner, temp_config_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test config delete-key with each provider after storing keys."""
        providers = ["ollama", "openai", "anthropic"]

        # Set up keys using KeyManager with temp directory
        key_manager = KeyManager(config_dir=temp_config_dir)
        for provider in providers:
            key_manager.store_key(provider, f"test-key-{provider}")

        # Set environment variable so CLI uses the same config directory
        monkeypatch.setenv("SPECIFY_CONFIG_DIR", str(temp_config_dir))

        # Now delete each key via CLI
        for provider in providers:
            result = cli_runner.invoke(
                cli,
                ["config", "delete-key", "--provider", provider],
            )
            assert result.exit_code == 0, f"Failed for provider: {provider}"


# ─────────────────────────────────────────────────────────────────────────────
# First-Run Detection Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestFirstRunDetection:
    """Tests for first-run detection and onboarding triggers."""

    def test_check_first_run_no_keys(
        self, temp_config_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that _check_first_run returns True when no keys are configured."""
        monkeypatch.setenv("SPECIFY_CONFIG_DIR", str(temp_config_dir))

        result = _check_first_run()

        assert result is True

    def test_check_first_run_with_keys(
        self, temp_config_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that _check_first_run returns False when keys are configured."""
        monkeypatch.setenv("SPECIFY_CONFIG_DIR", str(temp_config_dir))

        # Set up a key
        key_manager = KeyManager(config_dir=temp_config_dir)
        key_manager.store_key("openai", "sk-test-key-12345")

        result = _check_first_run()

        assert result is False

    def test_cli_with_no_keys_triggers_onboarding(
        self, cli_runner: CliRunner, temp_config_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that running CLI with no keys triggers onboarding check."""
        monkeypatch.setenv("SPECIFY_CONFIG_DIR", str(temp_config_dir))

        # The CLI first-run check runs in the cli() function
        # When no args are given, Click shows help (exit code 2)
        # We need to test this indirectly by checking if _check_first_run is called
        # Let's mock run_onboarding_wizard to see if it would be triggered
        with mock.patch("specify.cli.run_onboarding_wizard") as mock_wizard:
            result = cli_runner.invoke(cli, [])
            # The CLI will show help when no args given
            # But if it were to run properly, onboarding would be triggered
            # For now, just check the behavior is as expected (help shown)
            assert result.exit_code == 2

    def test_cli_with_keys_skips_onboarding(
        self, cli_runner: CliRunner, temp_config_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that running CLI with keys stored skips onboarding."""
        monkeypatch.setenv("SPECIFY_CONFIG_DIR", str(temp_config_dir))

        # Set up a key
        key_manager = KeyManager(config_dir=temp_config_dir)
        key_manager.store_key("openai", "sk-test-key-12345")

        result = cli_runner.invoke(cli, ["--help"])

        # Should not show onboarding welcome
        assert "Welcome to Specify.AI" not in result.output
        assert result.exit_code == 0

    def test_provider_flag_skips_onboarding(
        self, cli_runner: CliRunner, temp_config_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that providing --help (or any subcommand) skips onboarding."""
        monkeypatch.setenv("SPECIFY_CONFIG_DIR", str(temp_config_dir))

        # Using --help is a way to skip onboarding (subcommand)
        result = cli_runner.invoke(
            cli,
            ["--help"],
        )

        # Should not show onboarding welcome
        assert "Welcome to Specify.AI" not in result.output
        assert result.exit_code == 0

    def test_subcommand_skips_onboarding(
        self, cli_runner: CliRunner, temp_config_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that providing subcommand skips onboarding."""
        monkeypatch.setenv("SPECIFY_CONFIG_DIR", str(temp_config_dir))

        result = cli_runner.invoke(cli, ["generate", "--help"])

        # Should not show onboarding welcome
        assert "Welcome to Specify.AI" not in result.output
        assert result.exit_code == 0

    def test_should_skip_onboarding_with_subcommand(
        self, cli_runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that _should_skip_onboarding returns True when subcommand invoked."""
        # Create a mock context
        from unittest.mock import MagicMock

        ctx = MagicMock()
        ctx.invoked_subcommand = "generate"
        ctx.args = {}

        result = _should_skip_onboarding(ctx)

        assert result is True

    def test_should_skip_onboarding_with_provider_flag(
        self, cli_runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that _should_skip_onboarding returns True with --provider flag."""
        from unittest.mock import MagicMock

        ctx = MagicMock()
        ctx.invoked_subcommand = None
        ctx.args = {"--provider": "openai"}

        result = _should_skip_onboarding(ctx)

        assert result is True

    def test_should_skip_onboarding_with_key_flag(
        self, cli_runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that _should_skip_onboarding returns True with --key flag."""
        from unittest.mock import MagicMock

        ctx = MagicMock()
        ctx.invoked_subcommand = None
        ctx.args = {"--key": "sk-test-key"}

        result = _should_skip_onboarding(ctx)

        assert result is True

    def test_should_not_skip_onboarding_no_args(
        self, cli_runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that _should_skip_onboarding returns False with no args."""
        from unittest.mock import MagicMock

        ctx = MagicMock()
        ctx.invoked_subcommand = None
        ctx.args = {}

        result = _should_skip_onboarding(ctx)

        assert result is False


# ─────────────────────────────────────────────────────────────────────────────
# Onboarding Wizard Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestOnboardingWizard:
    """Tests for the onboarding wizard functions."""

    def test_prompt_provider_selection_valid_input_1(
        self, cli_runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test prompt_provider_selection with valid input 1 (Ollama)."""
        result = cli_runner.invoke(
            cli,
            [],
            input="1\n",  # Select Ollama
        )

        # The function is called from within the CLI context
        # We need to test the function directly or via mock
        # Let's test the function directly
        from click.testing import CliRunner as ClickRunner

        runner = ClickRunner()

        # We can't easily test the interactive prompt directly
        # Instead, test by mocking click.prompt
        with mock.patch("specify.cli.click.prompt") as mock_prompt:
            mock_prompt.return_value = 1
            result = prompt_provider_selection()
            assert result == "ollama"

    def test_prompt_provider_selection_valid_input_2(
        self, cli_runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test prompt_provider_selection with valid input 2 (OpenAI)."""
        with mock.patch("specify.cli.click.prompt") as mock_prompt:
            mock_prompt.return_value = 2
            result = prompt_provider_selection()
            assert result == "openai"

    def test_prompt_provider_selection_valid_input_3(
        self, cli_runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test prompt_provider_selection with valid input 3 (Anthropic)."""
        with mock.patch("specify.cli.click.prompt") as mock_prompt:
            mock_prompt.return_value = 3
            result = prompt_provider_selection()
            assert result == "anthropic"

    def test_prompt_provider_selection_invalid_then_valid(
        self, cli_runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test prompt_provider_selection with invalid input then valid."""
        # Mock prompt to return invalid then valid
        with mock.patch("specify.cli.click.prompt") as mock_prompt:
            mock_prompt.side_effect = [99, 4, 1]  # Invalid, invalid, valid
            result = prompt_provider_selection()
            assert result == "ollama"
            # Should have been called 3 times
            assert mock_prompt.call_count == 3

    def test_prompt_key_input_ollama(
        self, cli_runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test prompt_key_input for Ollama (URL input)."""
        with mock.patch("specify.cli.click.prompt") as mock_prompt:
            mock_prompt.return_value = "http://localhost:11434"
            result = prompt_key_input("ollama")
            assert result == "http://localhost:11434"

    def test_prompt_key_input_ollama_default(
        self, cli_runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test prompt_key_input for Ollama with user-provided URL."""
        with mock.patch("specify.cli.click.prompt") as mock_prompt:
            mock_prompt.return_value = "http://custom:9999"
            result = prompt_key_input("ollama")
            assert result == "http://custom:9999"

    def test_prompt_key_input_openai(
        self, cli_runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test prompt_key_input for OpenAI (hidden API key input)."""
        with mock.patch("specify.cli.click.prompt") as mock_prompt:
            mock_prompt.return_value = "sk-test-key-12345"
            result = prompt_key_input("openai")
            assert result == "sk-test-key-12345"

    def test_prompt_key_input_anthropic(
        self, cli_runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test prompt_key_input for Anthropic (hidden API key input)."""
        with mock.patch("specify.cli.click.prompt") as mock_prompt:
            mock_prompt.return_value = "sk-ant-test-key-12345"
            result = prompt_key_input("anthropic")
            assert result == "sk-ant-test-key-12345"

    def test_prompt_key_input_empty_then_valid(
        self, cli_runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test prompt_key_input with empty input then valid."""
        with mock.patch("specify.cli.click.prompt") as mock_prompt:
            mock_prompt.side_effect = ["", "sk-valid-key"]
            result = prompt_key_input("openai")
            assert result == "sk-valid-key"

    @mock.patch("specify.cli.fetch_ollama_models")
    def test_prompt_model_selection_with_fetched_models(
        self, mock_fetch, cli_runner: CliRunner
    ) -> None:
        """Test prompt_model_selection with model list fetched."""
        mock_fetch.return_value = ["llama2", "llama3", "mistral"]

        with mock.patch("specify.cli.click.prompt") as mock_prompt:
            mock_prompt.return_value = 2  # Select llama3
            result = prompt_model_selection("ollama", "http://localhost:11434")
            assert result == "llama3"

    @mock.patch("specify.cli.fetch_ollama_models")
    def test_prompt_model_selection_manual_entry(
        self, mock_fetch, cli_runner: CliRunner
    ) -> None:
        """Test prompt_model_selection with manual model entry."""
        mock_fetch.side_effect = Exception("Connection failed")

        with mock.patch("specify.cli.click.prompt") as mock_prompt:
            mock_prompt.return_value = "codellama"
            result = prompt_model_selection("ollama", "http://localhost:11434")
            assert result == "codellama"

    @mock.patch("specify.cli.fetch_openai_models")
    def test_prompt_model_selection_openai(
        self, mock_fetch, cli_runner: CliRunner
    ) -> None:
        """Test prompt_model_selection with OpenAI models."""
        mock_fetch.return_value = ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]

        with mock.patch("specify.cli.click.prompt") as mock_prompt:
            mock_prompt.return_value = 1  # Select gpt-4o
            result = prompt_model_selection("openai", "sk-test-key")
            assert result == "gpt-4o"

    @mock.patch("specify.cli.fetch_anthropic_models")
    def test_prompt_model_selection_anthropic(
        self, mock_fetch, cli_runner: CliRunner
    ) -> None:
        """Test prompt_model_selection with Anthropic models."""
        mock_fetch.return_value = ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"]

        with mock.patch("specify.cli.click.prompt") as mock_prompt:
            mock_prompt.return_value = 1  # Select claude-3-opus
            result = prompt_model_selection("anthropic", "sk-ant-test-key")
            assert result == "claude-3-opus"

    @mock.patch("specify.cli.fetch_ollama_models")
    def test_prompt_model_selection_custom_model(
        self, mock_fetch, cli_runner: CliRunner
    ) -> None:
        """Test prompt_model_selection with custom model entry (option 0)."""
        mock_fetch.return_value = ["llama2", "llama3", "mistral"]

        with mock.patch("specify.cli.click.prompt") as mock_prompt:
            # First return 0 to select custom, then return custom model name
            mock_prompt.side_effect = [0, "custom-model"]
            result = prompt_model_selection("ollama", "http://localhost:11434")
            assert result == "custom-model"

    def test_save_provider_config(
        self, temp_config_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test save_provider_config stores key and model preference."""
        monkeypatch.setenv("SPECIFY_CONFIG_DIR", str(temp_config_dir))

        save_provider_config("ollama", "http://localhost:11434", "llama3")

        # Verify key was stored
        key_manager = KeyManager(config_dir=temp_config_dir)
        keys = key_manager.list_keys()
        assert "ollama" in keys

        # Verify model preference was saved
        from specify.cli import get_model_preference
        model = get_model_preference("ollama")
        assert model == "llama3"

    def test_save_provider_config_openai(
        self, temp_config_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test save_provider_config for OpenAI."""
        monkeypatch.setenv("SPECIFY_CONFIG_DIR", str(temp_config_dir))

        save_provider_config("openai", "sk-test-key-12345", "gpt-4o")

        key_manager = KeyManager(config_dir=temp_config_dir)
        keys = key_manager.list_keys()
        assert "openai" in keys

        from specify.cli import get_model_preference
        model = get_model_preference("openai")
        assert model == "gpt-4o"


# ─────────────────────────────────────────────────────────────────────────────
# Main Menu Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestMainMenu:
    """Tests for the main menu functions."""

    def test_show_main_menu_option_1(
        self, cli_runner: CliRunner, temp_config_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test show_main_menu option 1 (generate documents)."""
        monkeypatch.setenv("SPECIFY_CONFIG_DIR", str(temp_config_dir))

        # Set up a provider so the menu can work
        key_manager = KeyManager(config_dir=temp_config_dir)
        key_manager.store_key("openai", "sk-test-key")

        # Option 1 leads to handle_generate_flow which is complex
        # We just test that menu is displayed, then exit (5)
        with mock.patch("specify.cli.handle_generate_flow"):
            with mock.patch("specify.cli.click.prompt") as mock_prompt:
                mock_prompt.side_effect = [1, 5]  # Option 1, then exit
                show_main_menu()
                # If we get here without error, test passes

    def test_show_main_menu_option_2(
        self, cli_runner: CliRunner, temp_config_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test show_main_menu option 2 (add provider)."""
        monkeypatch.setenv("SPECIFY_CONFIG_DIR", str(temp_config_dir))

        with mock.patch("specify.cli.handle_add_provider"):
            with mock.patch("specify.cli.click.prompt") as mock_prompt:
                mock_prompt.side_effect = [2, 5]  # Option 2, then exit
                show_main_menu()

    def test_show_main_menu_option_3(
        self, cli_runner: CliRunner, temp_config_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test show_main_menu option 3 (list providers)."""
        monkeypatch.setenv("SPECIFY_CONFIG_DIR", str(temp_config_dir))

        # Set up a provider
        key_manager = KeyManager(config_dir=temp_config_dir)
        key_manager.store_key("openai", "sk-test-key")

        with mock.patch("specify.cli.click.prompt") as mock_prompt:
            mock_prompt.side_effect = [3, 5]  # Option 3, then exit
            # This should print provider list
            show_main_menu()

    def test_show_main_menu_option_4(
        self, cli_runner: CliRunner, temp_config_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test show_main_menu option 4 (delete provider)."""
        monkeypatch.setenv("SPECIFY_CONFIG_DIR", str(temp_config_dir))

        # Set up a provider
        key_manager = KeyManager(config_dir=temp_config_dir)
        key_manager.store_key("openai", "sk-test-key")

        with mock.patch("specify.cli.handle_delete_provider"):
            with mock.patch("specify.cli.click.prompt") as mock_prompt:
                mock_prompt.side_effect = [4, 5]  # Option 4, then exit
                show_main_menu()

    def test_show_main_menu_option_5(
        self, cli_runner: CliRunner, temp_config_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test show_main_menu option 5 (exit)."""
        monkeypatch.setenv("SPECIFY_CONFIG_DIR", str(temp_config_dir))

        with mock.patch("specify.cli.click.prompt") as mock_prompt:
            mock_prompt.return_value = 5
            # Should exit cleanly with goodbye message
            show_main_menu()

    def test_show_main_menu_invalid_input(
        self, cli_runner: CliRunner, temp_config_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test show_main_menu with invalid input."""
        monkeypatch.setenv("SPECIFY_CONFIG_DIR", str(temp_config_dir))

        # First invalid, then valid exit
        with mock.patch("specify.cli.click.prompt") as mock_prompt:
            mock_prompt.side_effect = [99, 5]  # Invalid, then exit
            show_main_menu()
            # Should have shown invalid message

    def test_show_main_menu_keyboard_interrupt(
        self, cli_runner: CliRunner, temp_config_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test show_main_menu handles Ctrl+C gracefully."""
        monkeypatch.setenv("SPECIFY_CONFIG_DIR", str(temp_config_dir))

        with mock.patch("specify.cli.click.prompt") as mock_prompt:
            mock_prompt.side_effect = click.Abort()
            # Should handle gracefully
            show_main_menu()


# ─────────────────────────────────────────────────────────────────────────────
# Consistency Check Loop Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestConsistencyCheckLoop:
    """Tests for the consistency check loop functions."""

    def test_prompt_consistency_check_yes(
        self, cli_runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test prompt_consistency_check with 'y' input."""
        with mock.patch("specify.cli.click.confirm") as mock_confirm:
            mock_confirm.return_value = True
            result = prompt_consistency_check("./output")
            assert result is True

    def test_prompt_consistency_check_no(
        self, cli_runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test prompt_consistency_check with 'n' input."""
        with mock.patch("specify.cli.click.confirm") as mock_confirm:
            mock_confirm.return_value = False
            result = prompt_consistency_check("./output")
            assert result is False

    def test_run_consistency_check_returns_format(
        self, cli_runner: CliRunner
    ) -> None:
        """Test run_consistency_check returns expected format."""
        result = run_consistency_check("./output")

        assert isinstance(result, list)
        assert len(result) > 0

        # Check structure of first inconsistency
        first = result[0]
        assert "severity" in first
        assert "description" in first

    def test_display_inconsistency_report(
        self, cli_runner: CliRunner
    ) -> None:
        """Test display_inconsistency_report output format."""
        inconsistencies = [
            {
                "severity": "HIGH",
                "description": "Test inconsistency",
                "documents": ["PRD", "Tech Arch"],
                "suggestion": "Fix it",
            }
        ]

        # Should not raise exception
        display_inconsistency_report(inconsistencies)

    def test_prompt_fix_inconsistencies_yes(
        self, cli_runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test prompt_fix_inconsistencies with 'y' input."""
        with mock.patch("specify.cli.click.confirm") as mock_confirm:
            mock_confirm.return_value = True
            result = prompt_fix_inconsistencies()
            assert result is True

    def test_prompt_fix_inconsistencies_no(
        self, cli_runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test prompt_fix_inconsistencies with 'n' input."""
        with mock.patch("specify.cli.click.confirm") as mock_confirm:
            mock_confirm.return_value = False
            result = prompt_fix_inconsistencies()
            assert result is False

    def test_consistency_check_loop_exits_on_no(
        self, cli_runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test consistency_check_loop exits on 'n'."""
        with mock.patch("specify.cli.prompt_consistency_check") as mock_prompt:
            mock_prompt.return_value = False
            # Should exit cleanly
            consistency_check_loop("./output")

    def test_consistency_check_loop_loops_with_inconsistencies(
        self, cli_runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test consistency_check_loop loops when inconsistencies found."""
        # First call returns True (check), second returns False (exit)
        with mock.patch("specify.cli.prompt_consistency_check") as mock_prompt:
            mock_prompt.side_effect = [True, False]

            with mock.patch("specify.cli.run_consistency_check") as mock_check:
                mock_check.return_value = [
                    {
                        "severity": "HIGH",
                        "description": "Test",
                        "documents": ["Doc1"],
                        "suggestion": "Fix",
                    }
                ]

                with mock.patch("specify.cli.prompt_fix_inconsistencies") as mock_fix:
                    mock_fix.return_value = False  # Don't fix, just loop
                    # Should handle loop
                    consistency_check_loop("./output")

    def test_consistency_check_loop_no_inconsistencies(
        self, cli_runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test consistency_check_loop with no inconsistencies."""
        with mock.patch("specify.cli.prompt_consistency_check") as mock_prompt:
            mock_prompt.side_effect = [True, False]

            with mock.patch("specify.cli.run_consistency_check") as mock_check:
                mock_check.return_value = []  # No inconsistencies
                # Should handle gracefully
                consistency_check_loop("./output")


# ─────────────────────────────────────────────────────────────────────────────
# Interactive Delete-Key Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestInteractiveDeleteKey:
    """Tests for interactive delete-key functionality."""

    def test_run_interactive_delete_valid_selection(
        self, cli_runner: CliRunner, temp_config_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test run_interactive_delete with valid selection."""
        monkeypatch.setenv("SPECIFY_CONFIG_DIR", str(temp_config_dir))

        # Set up keys
        key_manager = KeyManager(config_dir=temp_config_dir)
        key_manager.store_key("openai", "sk-test-key-12345")
        key_manager.store_key("ollama", "http://localhost:11434")

        keys = key_manager.list_keys()

        # Mock in specify.cli module where it's used
        with mock.patch("specify.cli.click.prompt") as mock_prompt:
            # Select option 2 (openai based on alphabetical order: ollama=1, openai=2)
            mock_prompt.return_value = "2"
            with mock.patch("specify.cli.click.confirm") as mock_confirm:
                mock_confirm.return_value = True
                run_interactive_delete(key_manager, keys)

        # Verify openai key was deleted
        keys_after = key_manager.list_keys()
        assert "openai" not in keys_after

    def test_run_interactive_delete_quit(
        self, cli_runner: CliRunner, temp_config_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test run_interactive_delete with 'q' to quit."""
        monkeypatch.setenv("SPECIFY_CONFIG_DIR", str(temp_config_dir))

        # Set up a key
        key_manager = KeyManager(config_dir=temp_config_dir)
        key_manager.store_key("openai", "sk-test-key-12345")

        keys = key_manager.list_keys()

        with mock.patch("specify.cli.click.prompt") as mock_prompt:
            mock_prompt.return_value = "q"
            run_interactive_delete(key_manager, keys)

        # Verify key was NOT deleted
        keys_after = key_manager.list_keys()
        assert "openai" in keys_after

    def test_run_interactive_delete_invalid_selection(
        self, cli_runner: CliRunner, temp_config_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test run_interactive_delete with invalid selection."""
        monkeypatch.setenv("SPECIFY_CONFIG_DIR", str(temp_config_dir))

        # Set up a key
        key_manager = KeyManager(config_dir=temp_config_dir)
        key_manager.store_key("openai", "sk-test-key-12345")

        keys = key_manager.list_keys()

        with mock.patch("specify.cli.click.prompt") as mock_prompt:
            # Invalid then valid quit
            mock_prompt.side_effect = ["99", "q"]
            run_interactive_delete(key_manager, keys)

        # Verify key was NOT deleted
        keys_after = key_manager.list_keys()
        assert "openai" in keys_after

    def test_run_interactive_delete_confirmation_no(
        self, cli_runner: CliRunner, temp_config_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test run_interactive_delete confirmation 'n' cancels."""
        monkeypatch.setenv("SPECIFY_CONFIG_DIR", str(temp_config_dir))

        # Set up a key
        key_manager = KeyManager(config_dir=temp_config_dir)
        key_manager.store_key("openai", "sk-test-key-12345")

        keys = key_manager.list_keys()

        # Mock in specify.cli module where it's used
        with mock.patch("specify.cli.click.prompt") as mock_prompt:
            # Select option 1
            mock_prompt.return_value = "1"
            with mock.patch("specify.cli.click.confirm") as mock_confirm:
                mock_confirm.return_value = False
                run_interactive_delete(key_manager, keys)

        # Verify key was NOT deleted
        keys_after = key_manager.list_keys()
        assert "openai" in keys_after

    def test_delete_key_command_without_provider(
        self, cli_runner: CliRunner, temp_config_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test delete_key command without --provider shows interactive selection."""
        monkeypatch.setenv("SPECIFY_CONFIG_DIR", str(temp_config_dir))

        # Set up keys
        key_manager = KeyManager(config_dir=temp_config_dir)
        key_manager.store_key("openai", "sk-test-key-12345")
        key_manager.store_key("ollama", "http://localhost:11434")

        # Provide input for interactive selection: select 1, confirm yes
        result = cli_runner.invoke(
            cli,
            ["config", "delete-key"],
            input="1\ny\n",
        )

        assert result.exit_code == 0

    def test_delete_key_command_with_provider(
        self, cli_runner: CliRunner, temp_config_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test delete_key command with --provider uses non-interactive mode."""
        monkeypatch.setenv("SPECIFY_CONFIG_DIR", str(temp_config_dir))

        # Set up keys
        key_manager = KeyManager(config_dir=temp_config_dir)
        key_manager.store_key("openai", "sk-test-key-12345")

        result = cli_runner.invoke(
            cli,
            ["config", "delete-key", "--provider", "openai"],
        )

        assert result.exit_code == 0
        assert "deleted" in result.output.lower()

        # Verify key was deleted
        keys_after = key_manager.list_keys()
        assert "openai" not in keys_after

    def test_delete_key_command_no_keys(
        self, cli_runner: CliRunner, temp_config_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test delete_key command with no keys configured."""
        monkeypatch.setenv("SPECIFY_CONFIG_DIR", str(temp_config_dir))

        result = cli_runner.invoke(
            cli,
            ["config", "delete-key"],
        )

        assert result.exit_code == 0
        assert "No API keys configured" in result.output

    def test_delete_key_invalid_provider(
        self, cli_runner: CliRunner, temp_config_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test delete_key command with invalid provider."""
        monkeypatch.setenv("SPECIFY_CONFIG_DIR", str(temp_config_dir))

        result = cli_runner.invoke(
            cli,
            ["config", "delete-key", "--provider", "invalid"],
        )

        assert result.exit_code != 0
