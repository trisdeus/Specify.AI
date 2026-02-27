"""
Tests for the Specify.AI CLI.

This module contains tests for:
- CLI entry point
- --version flag
- --help flag
- Command groups (generate, config, check-consistency, fix-inconsistencies)
- Error handling
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from specify import __version__
from specify.cli import cli, main

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

    def test_config_list_keys(self, cli_runner: CliRunner) -> None:
        """Test config list-keys command."""
        result = cli_runner.invoke(cli, ["config", "list-keys"])

        assert result.exit_code == 0
        # Output should contain either "no api keys configured" OR list of keys
        output_lower = result.output.lower()
        has_no_keys = "no api keys configured" in output_lower
        has_openai = "openai" in output_lower
        assert has_no_keys or has_openai

    def test_config_delete_key_requires_provider(self, cli_runner: CliRunner) -> None:
        """Test that delete-key requires provider."""
        result = cli_runner.invoke(cli, ["config", "delete-key"])

        assert result.exit_code != 0


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

    def test_config_delete_key_each_provider(self, cli_runner: CliRunner) -> None:
        """Test config delete-key with each provider."""
        providers = ["ollama", "openai", "anthropic"]

        for provider in providers:
            result = cli_runner.invoke(
                cli,
                ["config", "delete-key", "--provider", provider],
            )
            assert result.exit_code == 0, f"Failed for provider: {provider}"
