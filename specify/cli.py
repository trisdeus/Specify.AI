"""
Specify.AI CLI - Command Line Interface for AI-powered documentation generation.

This module provides the main entry point for the Specify.AI CLI tool.
It uses Click for command parsing and provides the following commands:

- generate: Generate documentation from a prompt
- config: Manage API keys and configuration
- check-consistency: Check consistency between generated documents
- fix-inconsistencies: Automatically fix inconsistencies in documents

Example usage:
    $ specify --version
    specify-ai, version 0.1.0

    $ specify --help
    Usage: specify [OPTIONS] COMMAND [ARGS]...

    $ specify generate --prompt "Build a task app" --type all
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from collections.abc import Sequence

from specify import __version__


def main(args: Sequence[str] | None = None) -> int:
    """
    Main entry point for the Specify.AI CLI.

    This function serves as the primary entry point for the CLI application.
    It can be called programmatically or used as a console script entry point.

    Args:
        args: Command line arguments. If None, sys.argv[1:] is used.

    Returns:
        Exit code (0 for success, non-zero for failure).

    Raises:
        TypeError: If args is not a Sequence or None.

    Example:
        >>> from specify.cli import main
        >>> exit_code = main(["--version"])
        specify-ai, version 0.1.0
        >>> exit_code
        0
    """
    if args is not None and not isinstance(args, Sequence):
        raise TypeError(f"args must be a Sequence or None, got {type(args).__name__}")

    try:
        return cli.main(args=args, standalone_mode=False)  # type: ignore[no-any-return]
    except click.exceptions.Exit as e:
        # Click raises Exit with the exit code
        return int(e.exit_code)
    except click.exceptions.ClickException as e:
        # Handle Click exceptions (usage errors, etc.)
        e.show()
        return e.exit_code if e.exit_code is not None else 1
    except Exception as e:
        # Handle unexpected errors
        click.echo(f"Error: {e}", err=True)
        return 1


@click.group()
@click.version_option(version=__version__, prog_name="specify-ai")
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging output.",
)
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    """
    Specify.AI - Generate documentation from AI.

    A local-first CLI tool that transforms a single prompt into five
    production-ready documents: App Flow, BDD, Design Doc, PRD, and
    Technical Architecture.

    \b
    Quick Start:
        1. Configure your API key: specify config set-key --provider ollama
        2. Generate documents: specify generate --prompt "Your idea" --type all

    \b
    For more information:
        specify --help
        specify generate --help
        specify config --help
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose


# ─────────────────────────────────────────────────────────────────────────────
# Generate Command Group
# ─────────────────────────────────────────────────────────────────────────────


@cli.command()
@click.option(
    "--prompt",
    "-p",
    required=True,
    help="Product description prompt for document generation.",
)
@click.option(
    "--type",
    "-t",
    "doc_type",
    type=click.Choice(
        ["app-flow", "bdd", "design-doc", "prd", "tech-arch", "all"],
        case_sensitive=False,
    ),
    default="all",
    show_default=True,
    help="Type of document to generate.",
)
@click.option(
    "--provider",
    type=click.Choice(["ollama", "openai", "anthropic"], case_sensitive=False),
    default="ollama",
    show_default=True,
    help="LLM provider to use for generation.",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(file_okay=False, dir_okay=True, writable=True),
    default="./output",
    show_default=True,
    help="Output directory for generated documents.",
)
@click.option(
    "--model",
    "-m",
    default=None,
    help="Specific model to use (provider-specific).",
)
@click.option(
    "--no-recommendations",
    is_flag=True,
    help="Skip clarification questions for missing information.",
)
@click.pass_context
def generate(
    ctx: click.Context,
    prompt: str,
    doc_type: str,
    provider: str,
    output: str,
    model: str | None,
    no_recommendations: bool,
) -> None:
    """
    Generate documentation from a product description prompt.

    This command generates one or more documents based on the provided
    prompt. Documents follow the rules defined in the plan/rules/ directory.

    \b
    Document Types:
        - app-flow: App Flow Document (user flow specification)
        - bdd: Backend Design Document
        - design-doc: Design Document (design system specification)
        - prd: Product Requirements Document
        - tech-arch: Technical Architecture Document
        - all: Generate all 5 documents

    \b
    Examples:
        specify generate -p "Build a task app" -t all
        specify generate -p "Build a task app" -t prd --provider openai
        specify generate -p "Build a task app" -t all -o ./my-docs
    """
    verbose = ctx.obj.get("verbose", False)

    if verbose:
        click.echo(f"Generating {doc_type} document(s)...")
        click.echo(f"Provider: {provider}")
        click.echo(f"Output directory: {output}")

    # TODO: Implement document generation (Sprint 2-3)
    click.echo(
        "[PLACEHOLDER] Document generation is not yet implemented. "
        "This is a stub that will be fully implemented in Sprint 2-3."
    )
    click.echo(
        f"Would generate {doc_type} document(s) using {provider}."
    )
    click.echo(
        f"Prompt: {prompt[:100]}..." if len(prompt) > 100 else f"Prompt: {prompt}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Config Command Group
# ─────────────────────────────────────────────────────────────────────────────


@cli.group()
def config() -> None:
    """
    Manage configuration and API keys.

    Commands for storing, listing, and deleting API keys for
    LLM providers (Ollama, OpenAI, Anthropic).

    \b
    Examples:
        specify config set-key --provider ollama --key "your-key"
        specify config list-keys
        specify config delete-key --provider ollama
    """
    pass


@config.command(name="set-key")
@click.option(
    "--provider",
    "-p",
    required=True,
    type=click.Choice(["ollama", "openai", "anthropic"], case_sensitive=False),
    help="LLM provider for the API key.",
)
@click.option(
    "--key",
    "-k",
    required=True,
    help="API key or URL (for Ollama).",
)
def set_key(provider: str, key: str) -> None:
    """
    Store an API key for a provider.

    API keys are encrypted and stored locally in the user's home directory.
    For Ollama, the key can be the base URL of your Ollama instance.

    \b
    Examples:
        specify config set-key --provider openai --key sk-xxx
        specify config set-key --provider anthropic --key sk-ant-xxx
        specify config set-key --provider ollama --key http://localhost:11434
    """
    # TODO: Implement key storage (Sprint 2)
    click.echo("API key storage is not yet implemented.")
    click.echo(f"Would store key for {provider}.")


@config.command(name="list-keys")
def list_keys() -> None:
    """
    List all configured providers.

    Shows which LLM providers have API keys configured.
    Keys are displayed in masked format (e.g., sk-...abc).

    \b
    Example:
        specify config list-keys
    """
    # TODO: Implement key listing (Sprint 2)
    click.echo("API key listing is not yet implemented.")
    click.echo("Configured providers: (none)")


@config.command(name="delete-key")
@click.option(
    "--provider",
    "-p",
    required=True,
    type=click.Choice(["ollama", "openai", "anthropic"], case_sensitive=False),
    help="Provider to delete the key for.",
)
def delete_key(provider: str) -> None:
    """
    Delete a stored API key.

    Removes the API key for the specified provider from local storage.

    \b
    Example:
        specify config delete-key --provider openai
    """
    # TODO: Implement key deletion (Sprint 2)
    click.echo("API key deletion is not yet implemented.")
    click.echo(f"Would delete key for {provider}.")


# ─────────────────────────────────────────────────────────────────────────────
# Consistency Commands
# ─────────────────────────────────────────────────────────────────────────────


@cli.command(name="check-consistency")
@click.option(
    "--dir",
    "-d",
    "directory",
    type=click.Path(file_okay=False, dir_okay=True),
    default="./output",
    show_default=True,
    help="Directory containing generated documents.",
)
@click.pass_context
def check_consistency(ctx: click.Context, directory: str) -> None:
    """
    Check consistency between generated documents.

    Analyzes all generated documents in the specified directory
    and reports any inconsistencies or conflicts.

    \b
    Example:
        specify check-consistency --dir ./my-docs
    """
    verbose = ctx.obj.get("verbose", False)

    if verbose:
        click.echo(f"Checking consistency in: {directory}")

    # TODO: Implement consistency checking (Sprint 3)
    click.echo("Consistency checking is not yet implemented.")
    click.echo(f"Would check documents in: {directory}")


@cli.command(name="fix-inconsistencies")
@click.option(
    "--dir",
    "-d",
    "directory",
    type=click.Path(file_okay=False, dir_okay=True),
    default="./output",
    show_default=True,
    help="Directory containing generated documents.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be changed without making changes.",
)
@click.pass_context
def fix_inconsistencies(ctx: click.Context, directory: str, dry_run: bool) -> None:
    """
    Automatically fix inconsistencies in generated documents.

    Attempts to resolve conflicts between documents automatically.
    Use --dry-run to preview changes without modifying files.

    \b
    Examples:
        specify fix-inconsistencies --dir ./my-docs
        specify fix-inconsistencies --dir ./my-docs --dry-run
    """
    verbose = ctx.obj.get("verbose", False)

    if verbose:
        click.echo(f"Fixing inconsistencies in: {directory}")
        if dry_run:
            click.echo("Dry run mode: no changes will be made.")

    # TODO: Implement inconsistency fixing (Sprint 3)
    click.echo("Inconsistency fixing is not yet implemented.")
    click.echo(f"Would fix documents in: {directory}")


# ─────────────────────────────────────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    sys.exit(main())
