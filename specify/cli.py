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
from collections.abc import Sequence

import click
import requests

from specify import __version__
from specify.core import KeyManager, KeyNotFoundError, KeyValidationError


# Default Ollama URL
DEFAULT_OLLAMA_HOST = "http://localhost:11434"


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

    # Handle string input - reject it (strings are Sequences but not valid args)
    if isinstance(args, str):
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


def _check_first_run() -> bool:
    """
    Check if this is a first-run (no API keys configured).

    Returns:
        True if no keys are configured, False otherwise.
    """
    try:
        key_manager = KeyManager()
        keys = key_manager.list_keys()
        return len(keys) == 0
    except Exception:
        # If there's an error checking keys, assume first run
        return True


def _should_skip_onboarding(ctx: click.Context) -> bool:
    """
    Determine if onboarding should be skipped based on context.

    Checks if:
    - A subcommand was explicitly invoked
    - Provider/key flags were provided on generate command

    Args:
        ctx: Click context

    Returns:
        True if onboarding should be skipped, False otherwise.
    """
    # If a subcommand was explicitly invoked, skip onboarding
    if ctx.invoked_subcommand is not None:
        return True

    # Check if args indicate explicit configuration (e.g., --provider, --key)
    # Use a set for O(1) lookup of flags that indicate explicit configuration
    skip_flags = {
        "--provider", "-p",      # Provider selection
        "--key", "-k",           # API key input
        "--model", "-m",         # Model selection
        "--help", "-h",          # Help flag
        "--version",             # Version flag
        "--verbose", "-v",       # Verbose flag
    }

    if ctx.args:
        for arg in ctx.args:
            # Check for exact match or flag with value (e.g., --provider=openai)
            if arg in skip_flags:
                return True
            # Handle flags with = syntax (e.g., --provider=openai)
            if "=" in arg:
                flag_part = arg.split("=")[0]
                if flag_part in skip_flags:
                    return True

    return False


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

    # First-run detection: Check if onboarding should be triggered
    # Only trigger if no keys are configured AND no explicit subcommand/flags provided
    if _check_first_run() and not _should_skip_onboarding(ctx):
        try:
            run_onboarding_wizard()
            # After wizard completes, show help or exit
            click.echo("\nSetup complete! Run 'specify --help' to get started.")
            ctx.exit(0)
        except KeyboardInterrupt:
            click.echo("\n\nOnboarding cancelled.", err=True)
            ctx.exit(1)
        except Exception as e:
            # If onboarding fails, show error and continue to show help
            click.echo(f"Onboarding error: {e}", err=True)
            # Continue to show help


# ─────────────────────────────────────────────────────────────────────────────
# Onboarding Wizard Functions
# ─────────────────────────────────────────────────────────────────────────────


def run_onboarding_wizard() -> None:
    """
    Main orchestrator for the interactive onboarding wizard.

    This function guides the user through:
    1. Selecting a provider (Ollama, OpenAI, or Anthropic)
    2. Entering the API key or base URL
    3. Selecting or entering a model
    4. Saving the configuration

    The wizard handles errors gracefully and provides fallbacks
    when API calls fail.
    """
    click.echo("\n" + "=" * 60)
    click.echo("  Welcome to Specify.AI! Let's get you set up.")
    click.echo("=" * 60)
    click.echo("")

    # Step 1: Select provider
    provider = prompt_provider_selection()

    # Step 2: Get API key or base URL
    key = prompt_key_input(provider)

    # Step 3: Select model
    model = prompt_model_selection(provider, key)

    # Step 4: Save configuration
    save_provider_config(provider, key, model)

    click.echo("")
    click.echo("[OK] Configuration saved successfully!")
    click.echo(f"  Provider: {provider}")
    click.echo(f"  Model: {model}")

    # Show main menu after onboarding completes
    show_main_menu()


def prompt_provider_selection() -> str:
    """
    Prompt user to select a LLM provider.

    Displays a numbered menu with options for Ollama, OpenAI, and Anthropic.
    Returns the selected provider name.

    Returns:
        Selected provider name (ollama, openai, or anthropic).

    Raises:
        click.Abort: If user cancels the selection.
    """
    click.echo("Select a provider:")
    click.echo("")
    click.echo("  1. Ollama (local)")
    click.echo("  2. OpenAI")
    click.echo("  3. Anthropic")
    click.echo("")

    while True:
        try:
            choice = click.prompt(
                "Enter choice [1-3]",
                type=int,
                default=1,
                show_default=False,
            )

            if choice == 1:
                return "ollama"
            elif choice == 2:
                return "openai"
            elif choice == 3:
                return "anthropic"
            else:
                click.echo("Please enter a number between 1 and 3.")
        except click.Abort:
            raise click.Abort()
        except Exception as e:
            click.echo(f"Invalid input: {e}. Please enter a number between 1 and 3.")


def prompt_key_input(provider: str) -> str:
    """
    Prompt user for API key or base URL based on provider.

    For Ollama: Prompts for base URL (with default)
    For OpenAI/Anthropic: Prompts for API key (hidden input)

    Args:
        provider: The selected provider name.

    Returns:
        The API key or base URL entered by the user.

    Raises:
        click.Abort: If user cancels the input.
    """
    if provider == "ollama":
        click.echo("")
        click.echo("Enter your Ollama base URL:")
        click.echo("(Press Enter to use the default)")
        base_url = click.prompt(
            "Base URL",
            type=str,
            default=DEFAULT_OLLAMA_HOST,
            show_default=True,
        )
        return base_url.strip()
    else:
        # OpenAI or Anthropic - need API key
        if provider == "openai":
            click.echo("")
            click.echo("Enter your OpenAI API key:")
            click.echo("(Get your key from https://platform.openai.com/api-keys)")
        else:  # anthropic
            click.echo("")
            click.echo("Enter your Anthropic API key:")
            click.echo("(Get your key from https://console.anthropic.com/settings/keys)")

        while True:
            try:
                api_key = click.prompt(
                    "API Key",
                    type=str,
                    hide_input=True,
                )
                if api_key.strip():
                    return api_key.strip()
                click.echo("API key cannot be empty. Please enter a valid key.")
            except click.Abort:
                raise click.Abort()


def prompt_model_selection(provider: str, key: str) -> str:
    """
    Prompt user to select a model from available models or enter custom.

    First attempts to fetch models from the provider's API.
    If that fails, falls back to manual model entry.

    Args:
        provider: The selected provider name.
        key: The API key or base URL for the provider.

    Returns:
        The selected model name.

    Raises:
        click.Abort: If user cancels the selection.
    """
    click.echo("")
    click.echo("Fetching available models...")

    # Try to fetch models from the provider
    models: list[str] = []
    fetch_error: str | None = None

    try:
        if provider == "ollama":
            models = fetch_ollama_models(key)
        elif provider == "openai":
            models = fetch_openai_models(key)
        elif provider == "anthropic":
            models = fetch_anthropic_models(key)
    except Exception as e:
        fetch_error = str(e)

    # If models were fetched successfully, show selection menu
    if models:
        click.echo(f"Found {len(models)} models:")
        click.echo("")

        # Show numbered list (max 20 to avoid overwhelming)
        display_models = models[:20]
        for i, model in enumerate(display_models, 1):
            click.echo(f"  {i}. {model}")

        if len(models) > 20:
            click.echo(f"  ... and {len(models) - 20} more models")

        click.echo("")
        click.echo("  0. Enter custom model name")

        while True:
            try:
                choice = click.prompt(
                    "Select model [0-{0}]".format(len(display_models)),
                    type=int,
                    default=1,
                    show_default=False,
                )

                if choice == 0:
                    # Custom model entry
                    model = click.prompt(
                        "Enter custom model name",
                        type=str,
                    )
                    return model.strip()
                elif 1 <= choice <= len(display_models):
                    return display_models[choice - 1]
                else:
                    click.echo(f"Please enter a number between 0 and {len(display_models)}.")
            except click.Abort:
                raise click.Abort()
            except Exception:
                click.echo(f"Please enter a valid number between 0 and {len(display_models)}.")
    else:
        # Fallback to manual entry
        if fetch_error:
            click.echo(f"Could not fetch models: {fetch_error}")
        click.echo("Please enter a model name manually.")
        click.echo("")

        # Provide some common defaults based on provider
        if provider == "ollama":
            click.echo("Common models: llama2, llama3, mistral, codellama, etc.")
        elif provider == "openai":
            click.echo("Common models: gpt-4o, gpt-4-turbo, gpt-3.5-turbo, etc.")
        else:  # anthropic
            click.echo("Common models: claude-3-opus, claude-3-sonnet, claude-3-haiku, etc.")

        while True:
            try:
                model = click.prompt("Model name", type=str)
                if model.strip():
                    return model.strip()
                click.echo("Model name cannot be empty.")
            except click.Abort:
                raise click.Abort()


def save_provider_config(provider: str, key: str, model: str) -> None:
    """
    Save the provider configuration (API key and default model).

    Stores the API key using KeyManager and saves the model preference.

    Args:
        provider: The provider name.
        key: The API key or base URL.
        model: The selected model name.
    """
    try:
        key_manager = KeyManager()
        key_manager.store_key(provider, key)

        # Store model preference in a simple config file
        _save_model_preference(provider, model)

    except KeyValidationError as e:
        raise click.ClickException(f"Failed to save configuration: {e}") from e
    except Exception as e:
        raise click.ClickException(f"Failed to save configuration: {e}") from e


def _save_model_preference(provider: str, model: str) -> None:
    """
    Save the model preference to a config file.

    Args:
        provider: The provider name.
        model: The selected model name.
    """
    import json
    from pathlib import Path

    config_dir = Path.home() / ".specify"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "models.json"

    # Load existing config
    config: dict[str, str] = {}
    if config_file.exists():
        try:
            config = json.loads(config_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Update with new model preference
    config[provider] = model

    # Save config
    config_file.write_text(json.dumps(config, indent=2), encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# Main Menu Functions
# ─────────────────────────────────────────────────────────────────────────────


def get_model_preference(provider: str) -> str | None:
    """
    Get the model preference for a provider.

    Args:
        provider: The provider name.

    Returns:
        The model name if found, None otherwise.
    """
    import json
    from pathlib import Path

    config_dir = Path.home() / ".specify"
    config_file = config_dir / "models.json"

    if not config_file.exists():
        return None

    try:
        config = json.loads(config_file.read_text(encoding="utf-8"))
        return config.get(provider)
    except Exception:
        return None


def show_main_menu() -> None:
    """
    Display the main menu and handle user selection.

    Shows a numbered menu with options for:
    1. Generate documents
    2. Add another provider
    3. List configured providers
    4. Delete a provider
    5. Exit

    The menu loops until the user selects Exit.
    """
    while True:
        click.echo("")
        click.echo("╭────────────────────────────────────╮")
        click.echo("│         Specify.AI Main Menu        │")
        click.echo("├────────────────────────────────────┤")
        click.echo("│ 1. Generate documents               │")
        click.echo("│ 2. Add another provider             │")
        click.echo("│ 3. List configured providers        │")
        click.echo("│ 4. Delete a provider                │")
        click.echo("│ 5. Exit                             │")
        click.echo("╰────────────────────────────────────╯")

        try:
            choice = click.prompt(
                "Enter choice [1-5]",
                type=int,
                default=1,
                show_default=False,
            )

            if choice == 1:
                handle_generate_flow()
            elif choice == 2:
                handle_add_provider()
            elif choice == 3:
                handle_list_providers()
            elif choice == 4:
                handle_delete_provider()
            elif choice == 5:
                click.echo("Goodbye!")
                break
            else:
                click.echo("Please enter a number between 1 and 5.")
        except click.Abort:
            click.echo("\nGoodbye!")
            break


def handle_generate_flow() -> None:
    """
    Handle the generate documents menu option.

    Prompts the user for:
    1. Document type selection
    2. Product description prompt
    3. Provider selection (optional, uses default if only one)

    Then calls the generate command programmatically.
    """
    # Document type selection
    doc_types = ["app-flow", "bdd", "design-doc", "prd", "tech-arch", "all"]

    click.echo("\nSelect document type:")
    for i, dt in enumerate(doc_types, 1):
        click.echo(f"  {i}. {dt}")

    try:
        type_choice = click.prompt(
            "Enter choice [1-6]",
            type=int,
            default=6,  # default to "all"
            show_default=False,
        )

        if not 1 <= type_choice <= len(doc_types):
            click.echo("Invalid choice.")
            return

        doc_type = doc_types[type_choice - 1]

        # Provider selection
        key_manager = KeyManager()
        keys = key_manager.list_keys()

        if not keys:
            click.echo("No providers configured.")
            return

        provider_list = list(keys.keys())

        if len(provider_list) == 1:
            # Only one provider, use it
            provider = provider_list[0]
            click.echo(f"\nUsing provider: {provider}")
        else:
            click.echo("\nSelect provider:")
            for i, prov in enumerate(provider_list, 1):
                model = get_model_preference(prov)
                if model:
                    click.echo(f"  {i}. {prov} (model: {model})")
                else:
                    click.echo(f"  {i}. {prov}")

            prov_choice = click.prompt(
                f"Enter choice [1-{len(provider_list)}]",
                type=int,
                default=1,
                show_default=False,
            )

            if not 1 <= prov_choice <= len(provider_list):
                click.echo("Invalid choice.")
                return

            provider = provider_list[prov_choice - 1]

        # Output directory
        output_dir = click.prompt(
            "Output directory",
            type=str,
            default="./output",
        )

        # Product description prompt
        prompt_text = click.prompt(
            "\nEnter your product description",
            type=str,
        )

        # Call generate command programmatically
        click.echo(f"\nGenerating {doc_type} document(s)...")

        # Import and call the generate function
        from click.testing import CliRunner

        # Create a simple mock context
        class MockContext:
            def __init__(self):
                self.obj = {"verbose": False}

        # Call the generate command directly
        from specify.cli import generate

        runner = CliRunner()
        result = runner.invoke(
            generate,
            [
                "--prompt", prompt_text,
                "--type", doc_type,
                "--provider", provider,
                "--output", output_dir,
            ],
        )

        if result.exit_code != 0:
            click.echo(f"Error: {result.output}", err=True)
            return

        click.echo(result.output)

    except click.Abort:
        return


def handle_add_provider() -> None:
    """
    Handle the add another provider menu option.

    Runs the onboarding wizard for an additional provider.
    """
    click.echo("\n" + "=" * 60)
    click.echo("  Adding a new provider")
    click.echo("=" * 60)

    try:
        # Run the onboarding wizard
        run_onboarding_wizard()
    except click.Abort:
        click.echo("\nProvider addition cancelled.")
    except Exception as e:
        click.echo(f"\nError adding provider: {e}", err=True)


def handle_list_providers() -> None:
    """
    Handle the list providers menu option.

    Displays all configured providers with their masked API keys
    and selected models.
    """
    key_manager = KeyManager()
    keys = key_manager.list_keys()

    if not keys:
        click.echo("\nNo providers configured.")
        return

    click.echo("\nConfigured Providers:")
    click.echo("─" * 40)

    for provider, masked_key in keys.items():
        model = get_model_preference(provider)
        click.echo(f"  {provider}: {masked_key}")
        if model:
            click.echo(f"    Model: {model}")


def handle_delete_provider() -> None:
    """
    Handle the delete provider menu option with interactive selection.

    Shows a numbered list of providers and allows the user to select
    which one to delete.
    """
    key_manager = KeyManager()
    keys = key_manager.list_keys()

    if not keys:
        click.echo("\nNo providers configured.")
        return

    provider_list = list(keys.keys())

    click.echo("\nSelect provider to delete:")
    for i, provider in enumerate(provider_list, 1):
        masked_key = keys[provider]
        model = get_model_preference(provider)
        if model:
            click.echo(f"  {i}. {provider} (model: {model}) - {masked_key}")
        else:
            click.echo(f"  {i}. {provider} - {masked_key}")

    try:
        choice = click.prompt(
            f"Enter choice [1-{len(provider_list)}, or q to quit]",
            type=str,
            default="q",
        )

        if choice.lower() == "q":
            return

        choice_num = int(choice)

        if not 1 <= choice_num <= len(provider_list):
            click.echo("Invalid choice.")
            return

        provider = provider_list[choice_num - 1]

        # Confirm deletion
        confirm = click.confirm(
            f"Are you sure you want to delete the {provider} provider?",
            default=False,
        )

        if not confirm:
            click.echo("Deletion cancelled.")
            return

        key_manager.delete_key(provider)
        click.echo(f"[OK] Provider '{provider}' deleted.")

    except click.Abort:
        return
    except ValueError:
        click.echo("Invalid input. Please enter a number.")


# ─────────────────────────────────────────────────────────────────────────────
# Model Fetching Functions
# ─────────────────────────────────────────────────────────────────────────────


def fetch_ollama_models(base_url: str) -> list[str]:
    """
    Fetch available models from a local Ollama instance.

    Calls the Ollama API at /api/tags to list available models.

    Args:
        base_url: The base URL of the Ollama instance.

    Returns:
        List of model names available on the Ollama server.

    Raises:
        Exception: If the API call fails.
    """
    # Normalize URL (ensure no trailing slash)
    base_url = base_url.rstrip("/")

    try:
        response = requests.get(
            f"{base_url}/api/tags",
            timeout=10,
        )
        response.raise_for_status()

        data = response.json()
        models = [model["name"] for model in data.get("models", [])]
        return sorted(models)

    except requests.exceptions.ConnectionError as e:
        raise Exception(f"Could not connect to Ollama at {base_url}. Is Ollama running?") from e
    except requests.exceptions.Timeout as e:
        raise Exception(f"Connection to Ollama timed out: {e}") from e
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to fetch Ollama models: {e}") from e
    except (KeyError, ValueError) as e:
        raise Exception(f"Invalid response from Ollama: {e}") from e


def fetch_openai_models(api_key: str) -> list[str]:
    """
    Fetch available models from OpenAI API.

    Calls the OpenAI API to list available models.
    Note: This requires an API key with model listing permissions.

    Args:
        api_key: The OpenAI API key.

    Returns:
        List of model names available for the account.

    Raises:
        Exception: If the API call fails.
    """
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
        }

        response = requests.get(
            "https://api.openai.com/v1/models",
            headers=headers,
            timeout=15,
        )
        response.raise_for_status()

        data = response.json()
        # Filter to only chat completion models (most useful)
        models = [
            model["id"]
            for model in data.get("data", [])
            if "gpt" in model["id"] or "chat" in model.get("id", "")
        ]
        return sorted(set(models))  # Remove duplicates and sort

    except requests.exceptions.ConnectionError as e:
        raise Exception("Could not connect to OpenAI API. Check your internet connection.") from e
    except requests.exceptions.Timeout as e:
        raise Exception("Request to OpenAI API timed out.") from e
    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        if response.status_code == 401:
            raise Exception("Invalid OpenAI API key.") from e
        elif response.status_code == 403:
            raise Exception("Access forbidden. Check your API key permissions.") from e
        else:
            raise Exception(f"Failed to fetch OpenAI models: {error_msg}") from e
    except (KeyError, ValueError) as e:
        raise Exception(f"Invalid response from OpenAI: {e}") from e


def fetch_anthropic_models(api_key: str) -> list[str]:
    """
    Return common Anthropic models.

    Note: Anthropic's API doesn't have a direct "list models" endpoint,
    so this returns common Anthropic models without making an API call.
    The API key is accepted for interface consistency but not used.
    Key validation happens naturally when the user attempts to generate
    documents, avoiding unnecessary API credit consumption.

    Args:
        api_key: The Anthropic API key (not used, for interface consistency).

    Returns:
        List of common Anthropic model names.
    """
    # Common Anthropic models - returned without API validation
    # to avoid consuming user credits
    common_models = [
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
        "claude-3-5-sonnet-20241022",
        "claude-3-5-sonnet-20240620",
        "claude-3-5-haiku-20241022",
    ]

    return common_models


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
@click.option(
    "--no-consistency-check",
    is_flag=True,
    help="Skip post-generation consistency check prompt.",
)
@click.option(
    "--auto-fix",
    is_flag=True,
    help="Automatically fix inconsistencies without prompting.",
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
    no_consistency_check: bool,
    auto_fix: bool,
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
        specify generate -p "Build a task app" -t all --no-consistency-check
        specify generate -p "Build a task app" -t all --auto-fix
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
    click.echo(f"Would generate {doc_type} document(s) using {provider}.")
    click.echo(
        f"Prompt: {prompt[:100]}..." if len(prompt) > 100 else f"Prompt: {prompt}"
    )

    # Run consistency check loop after generation by default
    # Skip if --no-consistency-check is provided
    # If --auto-fix is provided, run consistency check with auto-fix enabled
    if not no_consistency_check:
        consistency_check_loop(output, auto_fix=auto_fix)


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

    API keys are stored locally in the user's home directory.
    For Ollama, the key can be the base URL of your Ollama instance.

    \b
    Examples:
        specify config set-key --provider openai --key sk-xxx
        specify config set-key --provider anthropic --key sk-ant-xxx
        specify config set-key --provider ollama --key http://localhost:11434
    """
    try:
        key_manager = KeyManager()
        key_manager.store_key(provider, key)
        click.echo(f"[OK] API key stored for {provider}")
    except KeyValidationError as e:
        raise click.ClickException(str(e)) from e


@config.command(name="list-keys")
def list_keys() -> None:
    """
    List all configured providers.

    Shows which LLM providers have API keys configured.
    Keys are displayed in masked format (e.g., sk-...abc).
    Keys are sourced from both the local store and environment variables.

    \b
    Example:
        specify config list-keys
    """
    key_manager = KeyManager()
    keys = key_manager.list_keys()

    if not keys:
        click.echo("No API keys configured.")
        return

    # Print formatted output
    click.echo("Configured API Keys:")
    click.echo("-" * 40)
    for provider, masked_key in keys.items():
        click.echo(f"  {provider}: {masked_key}")


@config.command(name="delete-key")
@click.option(
    "--provider",
    "-p",
    required=False,
    type=click.Choice(["ollama", "openai", "anthropic"], case_sensitive=False),
    help="Provider to delete the key for. If not specified, shows interactive selection.",
)
def delete_key(provider: str | None) -> None:
    """
    Delete a stored API key.

    Removes the API key for the specified provider from local storage.
    If --provider is not specified, shows an interactive list of
    configured providers to select from.

    Note: This does not affect environment variables.

    \b
    Examples:
        specify config delete-key --provider openai
        specify config delete-key
    """
    key_manager = KeyManager()
    keys = key_manager.list_keys()

    # If provider is specified, use non-interactive mode (backward compatibility)
    if provider:
        try:
            key_manager.delete_key(provider)
            click.echo(f"[OK] API key deleted for {provider}")
        except KeyNotFoundError as e:
            raise click.ClickException(str(e)) from e
        return

    # No provider specified - show interactive selection
    # Check if any keys are configured
    if not keys:
        click.echo("No API keys configured.")
        return

    # Run interactive deletion
    run_interactive_delete(key_manager, keys)


def run_interactive_delete(key_manager: KeyManager, keys: dict[str, str]) -> None:
    """
    Run interactive provider selection for deletion.

    Args:
        key_manager: KeyManager instance.
        keys: Dictionary of provider -> masked_key.
    """
    click.echo("\nConfigured API Keys:")

    # Create numbered list
    providers = list(keys.keys())
    for i, prov in enumerate(providers, 1):
        click.echo(f"  {i}. {prov}: {keys[prov]}")

    click.echo("")

    while True:
        try:
            choice = click.prompt(
                "Select provider to delete [1-{0}] or 'q' to quit:".format(len(providers)),
                type=str,
                default="q"
            )

            # Check for quit
            if choice.lower() == "q":
                click.echo("Cancelled.")
                return

            # Parse as number
            try:
                choice_num = int(choice)
                if 1 <= choice_num <= len(providers):
                    selected_provider = providers[choice_num - 1]
                    break
                else:
                    click.echo(
                        "Please enter a number between 1 and {0}, or 'q' to quit.".format(
                            len(providers)
                        )
                    )
            except ValueError:
                click.echo("Invalid input. Enter a number or 'q' to quit.")

        except click.Abort:
            click.echo("\nCancelled.")
            return

    # Confirm deletion
    try:
        confirm = click.confirm(
            f"Delete API key for {selected_provider}?",
            default=False,
        )
    except click.Abort:
        click.echo("\nCancelled.")
        return

    if not confirm:
        click.echo("Cancelled.")
        return

    # Perform deletion
    try:
        key_manager.delete_key(selected_provider)
        click.echo(f"[OK] API key deleted for {selected_provider}")
    except KeyNotFoundError as e:
        raise click.ClickException(str(e)) from e


# ─────────────────────────────────────────────────────────────────────────────
# Post-Generation Consistency Check Loop Functions
# ─────────────────────────────────────────────────────────────────────────────


def prompt_consistency_check(output_dir: str) -> bool:
    """
    Ask user if they want to check for inconsistencies.

    Args:
        output_dir: Directory containing generated documents.

    Returns:
        True if user wants to check, False otherwise.
    """
    try:
        return click.confirm(
            "\nCheck for inconsistencies?",
            default=True,
        )
    except click.Abort:
        return False


def run_consistency_check(output_dir: str) -> list[dict]:
    """
    Run consistency check and display results.

    Args:
        output_dir: Directory containing generated documents.

    Returns:
        List of inconsistency dictionaries with severity, description, etc.
    """
    click.echo("Checking...")

    # TODO: Implement actual consistency checking logic
    # This is a stub that simulates finding inconsistencies
    # Real implementation will analyze generated documents for conflicts

    # Simulated inconsistencies for demonstration
    inconsistencies = [
        {
            "severity": "HIGH",
            "description": "PRD and Tech Arch have conflicting API versions",
            "documents": ["PRD", "Technical Architecture"],
            "suggestion": "Align API versions across documents",
        },
        {
            "severity": "MEDIUM",
            "description": "BDD missing endpoint defined in App Flow",
            "documents": ["BDD", "App Flow"],
            "suggestion": "Add missing endpoint to BDD scenarios",
        },
        {
            "severity": "LOW",
            "description": "Design Doc uses different terminology",
            "documents": ["Design Doc"],
            "suggestion": "Standardize terminology with other documents",
        },
    ]

    return inconsistencies


def display_inconsistency_report(inconsistencies: list[dict]) -> None:
    """
    Display a formatted inconsistency report.

    Args:
        inconsistencies: List of inconsistency dictionaries.
    """
    click.echo(f"Found {len(inconsistencies)} inconsistencies:")

    for inc in inconsistencies:
        severity = inc.get("severity", "UNKNOWN")
        description = inc.get("description", "No description")

        # Format severity with brackets
        severity_str = f"[{severity}]"

        click.echo(f"  - {severity_str} {description}")


def prompt_fix_inconsistencies() -> bool:
    """
    Ask user if they want to fix inconsistencies.

    Returns:
        True if user wants to fix, False otherwise.
    """
    try:
        return click.confirm(
            "Fix them?",
            default=True,
        )
    except click.Abort:
        return False


def run_fix_inconsistencies(output_dir: str) -> list[dict]:
    """
    Apply fixes to resolve inconsistencies.

    Args:
        output_dir: Directory containing generated documents.

    Returns:
        List of fix results with document, change, and success status.
    """
    click.echo("Fixing...")

    # TODO: Implement actual inconsistency fixing logic
    # This is a stub that simulates fixing inconsistencies
    # Real implementation will modify documents to resolve conflicts

    # Simulated fix results
    fix_results = [
        {
            "document": "PRD",
            "change": "Updated API version to match Technical Architecture",
            "success": True,
        },
        {
            "document": "BDD",
            "change": "Added missing endpoint /api/users to scenarios",
            "success": True,
        },
        {
            "document": "Design Doc",
            "change": "Updated terminology to match other documents",
            "success": True,
        },
    ]

    return fix_results


def display_fix_results(fix_results: list[dict]) -> None:
    """
    Display the results of automatic fixes.

    Args:
        fix_results: List of fix result dictionaries.
    """
    for result in fix_results:
        document = result.get("document", "Unknown")
        success = result.get("success", False)

        if success:
            click.echo(f"  ✓ Updated {document}")
        else:
            click.echo(f"  ✗ Failed to update {document}")


def consistency_check_loop(output_dir: str, auto_fix: bool = False) -> None:
    """
    Main loop for post-generation consistency checking.

    This function runs the consistency check flow:
    1. Ask user if they want to check for inconsistencies
    2. If yes, run consistency check
    3. If inconsistencies found, ask if user wants to fix
    4. If yes, apply fixes
    5. Loop back to check again (until user says no)

    Args:
        output_dir: Directory containing generated documents.
        auto_fix: If True, automatically fix inconsistencies without prompting.
    """
    while True:
        # Ask if user wants to check for inconsistencies
        # If auto_fix is enabled, skip the prompt and check automatically
        if auto_fix:
            should_check = True
        else:
            should_check = prompt_consistency_check(output_dir)

        if not should_check:
            click.echo("\nReturning to main menu...")
            break

        # Run consistency check
        inconsistencies = run_consistency_check(output_dir)

        if not inconsistencies:
            click.echo("No inconsistencies found.")
            # Loop continues - ask again if user wants to check
        else:
            # Display inconsistency report
            display_inconsistency_report(inconsistencies)

            # Ask if user wants to fix
            # If auto_fix is enabled, fix automatically without prompting
            should_fix = auto_fix or prompt_fix_inconsistencies()

            if should_fix:
                # Apply fixes
                fix_results = run_fix_inconsistencies(output_dir)
                display_fix_results(fix_results)
                click.echo("[complete]")
            else:
                # Don't fix, but continue loop to check again
                pass


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
