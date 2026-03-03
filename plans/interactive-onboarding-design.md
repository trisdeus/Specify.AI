# Technical Design: Interactive Onboarding Flow

## Overview

This document provides detailed technical specifications for implementing the interactive onboarding flow and post-generation consistency check loop in the Specify.AI CLI tool. It is designed to be used by Code mode for implementation.

---

## 1. First-Run Detection Logic

### 1.1 Specification

The CLI must detect when no API keys are configured and automatically trigger the interactive onboarding wizard.

### 1.2 Detection Logic

```
FUNCTION should_trigger_onboarding():
    key_manager = KeyManager()
    stored_keys = key_manager.list_keys()  # Returns dict of provider -> masked_key

    // Check if any keys exist in local storage OR environment variables
    IF stored_keys is empty:
        RETURN True
    ELSE:
        RETURN False
```

### 1.3 Integration Point

The detection should occur in the main `cli()` function BEFORE any subcommand is executed. This requires using Click's `invoke()` method or a pre-command hook.

### 1.4 Pseudocode for CLI Entry Point

```python
@click.group()
@click.version_option(version=__version__, prog_name="specify-ai")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging output.")
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose

    # First-run detection: Check if no subcommand is being invoked
    # and no keys are configured
    if ctx.invoked_subcommand is None:
        key_manager = KeyManager()
        if not key_manager.list_keys():
            # Trigger interactive onboarding
            run_interactive_onboarding(ctx)
            return

        # Show main menu if keys exist
        show_main_menu(ctx)
```

---

## 2. Interactive Onboarding Wizard Flow

### 2.1 Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     START CLI                                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              Check: Any API keys configured?                     │
└─────────────────────────────────────────────────────────────────┘
                    │                    │
                   YES                   NO
                    │                    │
                    ▼                    ▼
┌──────────────────────┐    ┌─────────────────────────────────────┐
│   Show Main Menu     │    │    START INTERACTIVE ONBOARDING     │
└──────────────────────┘    └─────────────────────────────────────┘
                                              │
                                              ▼
                            ┌─────────────────────────────────────┐
                            │  Display welcome message            │
                            │  "Welcome to Specify.AI!            │
                            │   Let's set up your first provider."│
                            └─────────────────────────────────────┘
                                              │
                                              ▼
                            ┌─────────────────────────────────────┐
                            │  STEP 1: Provider Selection         │
                            │  ─────────────────────────────────  │
                            │  Select a provider:                 │
                            │    1. Ollama (local)                │
                            │    2. OpenAI                        │
                            │    3. Anthropic                     │
                            │                                     │
                            │  Enter choice [1-3]:                │
                            └─────────────────────────────────────┘
                                              │
                                              ▼
                            ┌─────────────────────────────────────┐
                            │  STEP 2: Model Selection            │
                            │  ─────────────────────────────────  │
                            │  Fetching available models...       │
                            │                                     │
                            │  Available models:                  │
                            │    1. llama3                        │
                            │    2. mistral                       │
                            │    3. codellama                     │
                            │    4. Enter custom model name       │
                            │                                     │
                            │  Select a model [1-4]:              │
                            └─────────────────────────────────────┘
                                              │
                                    ┌─────────┴─────────┐
                                    │                   │
                              From List            Custom Model
                                    │                   │
                                    ▼                   ▼
                            ┌─────────────┐     ┌─────────────────┐
                            │ Use selected│     │ Prompt for name │
                            │   model     │     │ Validate input  │
                            └─────────────┘     └─────────────────┘
                                    │                   │
                                    └─────────┬─────────┘
                                              │
                                              ▼
                            ┌─────────────────────────────────────┐
                            │  STEP 3: Key/URL Input              │
                            │  ─────────────────────────────────  │
                            │                                     │
                            │  IF provider == "ollama":           │
                            │    Prompt: "Enter Ollama base URL   │
                            │              [default: localhost]" │
                            │  ELSE:                              │
                            │    Prompt: "Enter your API key: "   │
                            │    (Input hidden with echo=False)   │
                            └─────────────────────────────────────┘
                                              │
                                              ▼
                            ┌─────────────────────────────────────┐
                            │  STEP 4: Save Configuration         │
                            │  ─────────────────────────────────  │
                            │  key_manager.store_key(provider, key)│
                            │  save_model_preference(provider, model)│
                            │                                     │
                            │  Display: "Configuration saved!"    │
                            └─────────────────────────────────────┘
                                              │
                                              ▼
                            ┌─────────────────────────────────────┐
                            │        SHOW MAIN MENU               │
                            └─────────────────────────────────────┘
```

### 2.2 Pseudocode for Onboarding Wizard

```python
def run_interactive_onboarding(ctx: click.Context) -> None:
    """Run the interactive onboarding wizard for first-time users."""

    # Welcome message
    click.echo("\n" + "=" * 50)
    click.echo("Welcome to Specify.AI!")
    click.echo("No API keys configured. Let's set up your first provider.")
    click.echo("=" * 50 + "\n")

    # Step 1: Provider Selection
    provider = prompt_provider_selection()
    if provider is None:
        click.echo("Setup cancelled.")
        return

    # Step 2: Model Selection
    model = prompt_model_selection(provider)
    if model is None:
        click.echo("Setup cancelled.")
        return

    # Step 3: Key/URL Input
    key_or_url = prompt_key_or_url(provider)
    if key_or_url is None:
        click.echo("Setup cancelled.")
        return

    # Step 4: Save Configuration
    try:
        key_manager = KeyManager()
        key_manager.store_key(provider, key_or_url)

        # Store model preference (new functionality needed)
        save_model_preference(provider, model)

        click.echo(f"\n✓ Configuration saved successfully!")
        click.echo(f"  Provider: {provider}")
        click.echo(f"  Model: {model}\n")

    except Exception as e:
        click.echo(f"\n✗ Error saving configuration: {e}", err=True)
        return

    # Show main menu after successful setup
    show_main_menu(ctx)


def prompt_provider_selection() -> str | None:
    """Prompt user to select a provider. Returns None if cancelled."""

    providers = [
        ("ollama", "Ollama (local)"),
        ("openai", "OpenAI"),
        ("anthropic", "Anthropic"),
    ]

    click.echo("Select a provider:")
    for i, (_, label) in enumerate(providers, 1):
        click.echo(f"  {i}. {label}")

    while True:
        try:
            choice = click.prompt("Enter choice", type=int, default=1)
            if 1 <= choice <= len(providers):
                return providers[choice - 1][0]
            else:
                click.echo(f"Please enter a number between 1 and {len(providers)}")
        except click.Abort:
            return None


def prompt_model_selection(provider: str) -> str | None:
    """Prompt user to select or enter a model. Returns None if cancelled."""

    click.echo(f"\nFetching available models from {provider}...")

    # Try to fetch models from provider API
    models = fetch_models_from_provider(provider)

    if models:
        click.echo("Available models:")
        for i, model in enumerate(models, 1):
            click.echo(f"  {i}. {model}")
        click.echo(f"  {len(models) + 1}. Enter custom model name")

        while True:
            try:
                choice = click.prompt(
                    "Select a model",
                    type=int,
                    default=1
                )
                if 1 <= choice <= len(models):
                    return models[choice - 1]
                elif choice == len(models) + 1:
                    # Custom model
                    return prompt_custom_model()
                else:
                    click.echo(f"Please enter a number between 1 and {len(models) + 1}")
            except click.Abort:
                return None
    else:
        click.echo("Could not fetch models (provider may not be running).")
        return prompt_custom_model()


def prompt_custom_model() -> str | None:
    """Prompt user to enter a custom model name."""
    try:
        model = click.prompt("Enter model name", type=str)
        if model.strip():
            return model.strip()
        click.echo("Model name cannot be empty.")
        return None
    except click.Abort:
        return None


def prompt_key_or_url(provider: str) -> str | None:
    """Prompt for API key or base URL based on provider type."""

    if provider == "ollama":
        default_url = "http://localhost:11434"
        try:
            url = click.prompt(
                "Enter Ollama base URL",
                default=default_url,
                type=str
            )
            return url
        except click.Abort:
            return None
    else:
        # OpenAI or Anthropic - hide input for security
        try:
            key = click.prompt(
                f"Enter your {provider.capitalize()} API key",
                type=str,
                hide_input=True
            )
            if key.strip():
                return key.strip()
            click.echo("API key cannot be empty.")
            return None
        except click.Abort:
            return None


def fetch_models_from_provider(provider: str) -> list[str]:
    """Fetch available models from the provider's API.

    Returns empty list if fetching fails.
    """
    # This will use the provider clients to fetch models
    # Implementation depends on provider interface
    try:
        if provider == "ollama":
            # Use ollama.list() to get models
            import ollama
            response = ollama.list()
            return [model["model"] for model in response.get("models", [])]
        elif provider == "openai":
            # Use OpenAI API to list models
            # This requires an API key first, so may not work during onboarding
            return ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"]
        elif provider == "anthropic":
            # Anthropic doesn't have a list models endpoint
            return ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"]
    except Exception:
        return []
```

---

## 3. Main Menu Structure

### 3.1 Menu Options

```
Main Menu:
  1. Generate documents
  2. Add another provider
  3. List configured providers
  4. Delete a provider
  5. Exit

Enter choice [1-5]:
```

### 3.2 Pseudocode for Main Menu

```python
def show_main_menu(ctx: click.Context) -> None:
    """Display the main menu and handle user selection."""

    while True:
        click.echo("\n" + "-" * 40)
        click.echo("Main Menu:")
        click.echo("  1. Generate documents")
        click.echo("  2. Add another provider")
        click.echo("  3. List configured providers")
        click.echo("  4. Delete a provider")
        click.echo("  5. Exit")
        click.echo("-" * 40)

        try:
            choice = click.prompt("Enter choice", type=int, default=1)

            if choice == 1:
                # Generate documents - prompt for details
                handle_generate_documents(ctx)
            elif choice == 2:
                # Add another provider - run onboarding again
                run_interactive_onboarding(ctx)
            elif choice == 3:
                # List configured providers
                handle_list_providers()
            elif choice == 4:
                # Delete a provider
                handle_delete_provider_interactive()
            elif choice == 5:
                click.echo("Goodbye!")
                break
            else:
                click.echo("Please enter a number between 1 and 5")

        except click.Abort:
            click.echo("\nGoodbye!")
            break


def handle_generate_documents(ctx: click.Context) -> None:
    """Handle the generate documents menu option."""

    # Prompt for document type
    doc_types = ["app-flow", "bdd", "design-doc", "prd", "tech-arch", "all"]
    click.echo("\nSelect document type:")
    for i, dt in enumerate(doc_types, 1):
        click.echo(f"  {i}. {dt}")

    try:
        type_choice = click.prompt("Enter choice", type=int, default=6)  # default to "all"
        if not 1 <= type_choice <= len(doc_types):
            click.echo("Invalid choice.")
            return

        doc_type = doc_types[type_choice - 1]

        # Prompt for product description
        prompt_text = click.prompt("Enter your product description", type=str)

        # Call generate command
        # This would invoke the generate command programmatically
        click.echo(f"\nGenerating {doc_type} document(s)...")
        # TODO: Call actual generation logic

    except click.Abort:
        return


def handle_list_providers() -> None:
    """Handle the list providers menu option."""
    key_manager = KeyManager()
    keys = key_manager.list_keys()

    if not keys:
        click.echo("\nNo providers configured.")
        return

    click.echo("\nConfigured Providers:")
    click.echo("-" * 40)
    for provider, masked_key in keys.items():
        model = get_model_preference(provider)
        click.echo(f"  {provider}: {masked_key}")
        if model:
            click.echo(f"    Model: {model}")


def handle_delete_provider_interactive() -> None:
    """Handle the delete provider menu option with interactive selection."""
    # See Section 5 for detailed implementation
    run_interactive_delete()
```

---

## 4. Post-Generation Consistency Check Loop

### 4.1 Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│              DOCUMENTS GENERATED SUCCESSFULLY                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  PROMPT: "Would you like to check for inconsistencies? [Y/n]"   │
└─────────────────────────────────────────────────────────────────┘
                    │                    │
                   YES                   NO
                    │                    │
                    ▼                    ▼
┌──────────────────────────┐    ┌─────────────────────────────────┐
│ Run Consistency Checker  │    │ Show Summary Report & Exit      │
└──────────────────────────┘    └─────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│              CHECK: Inconsistencies found?                      │
└─────────────────────────────────────────────────────────────────┘
                    │                    │
                   YES                   NO
                    │                    │
                    ▼                    ▼
┌──────────────────────────┐    ┌─────────────────────────────────┐
│ Display inconsistency    │    │ Display: "All documents are     │
│ report with severity     │    │ consistent"                     │
└──────────────────────────┘    └─────────────────────────────────┘
                    │                    │
                    ▼                    │
┌─────────────────────────────────────────────────────────────────┐
│  PROMPT: "Would you like to fix these? [Y/n]"                   │
└─────────────────────────────────────────────────────────────────┘
                    │                    │
                   YES                   NO
                    │                    │
                    ▼                    ▼
┌──────────────────────────┐    ┌─────────────────────────────────┐
│ Apply automatic fixes    │    │ Show Summary Report & Exit      │
│ Display changes made     │    └─────────────────────────────────┘
└──────────────────────────┘
                    │
                    └──────────────────────────────┐
                                                   │
                                                   ▼
                            ┌─────────────────────────────────────┐
                            │  LOOP BACK to "Check for            │
                            │  inconsistencies?" prompt           │
                            └─────────────────────────────────────┘
```

### 4.2 Pseudocode for Consistency Check Loop

```python
def run_consistency_check_loop(
    output_dir: str,
    auto_fix: bool = False,
    no_check: bool = False
) -> None:
    """Run the post-generation consistency check loop.

    Args:
        output_dir: Directory containing generated documents.
        auto_fix: If True, automatically fix inconsistencies without prompting.
        no_check: If True, skip the entire consistency check flow.
    """
    if no_check:
        return

    while True:
        # Ask if user wants to check for inconsistencies
        if not auto_fix:
            try:
                check = click.confirm(
                    "\nWould you like to check for inconsistencies?",
                    default=True
                )
            except click.Abort:
                break

            if not check:
                break
        else:
            # Auto-fix mode implies we want to check
            pass

        # Run consistency checker
        click.echo("\nChecking consistency...")
        inconsistencies = check_consistency(output_dir)

        if not inconsistencies:
            click.echo("\n✓ All documents are consistent!")
            break

        # Display inconsistency report
        click.echo(f"\nFound {len(inconsistencies)} inconsistencies:")
        display_inconsistency_report(inconsistencies)

        # Ask if user wants to fix
        if auto_fix:
            should_fix = True
        else:
            try:
                should_fix = click.confirm(
                    "\nWould you like to fix these inconsistencies?",
                    default=True
                )
            except click.Abort:
                break

        if not should_fix:
            break

        # Apply fixes
        click.echo("\nFixing inconsistencies...")
        fix_results = fix_inconsistencies(output_dir, inconsistencies)

        # Display fix results
        display_fix_results(fix_results)

        # If auto_fix, only run one iteration
        if auto_fix:
            break

        # Loop continues - ask again if user wants to check
        # This allows verification that fixes worked


def check_consistency(output_dir: str) -> list[dict]:
    """Check consistency between documents in the output directory.

    Returns:
        List of inconsistency dictionaries, each containing:
        - severity: "HIGH", "MEDIUM", or "LOW"
        - description: Human-readable description
        - documents: List of affected document names
        - suggestion: Suggested fix
    """
    # TODO: Implement actual consistency checking logic
    # This will analyze all generated documents for conflicts
    return []


def fix_inconsistencies(output_dir: str, inconsistencies: list[dict]) -> list[dict]:
    """Apply automatic fixes to resolve inconsistencies.

    Returns:
        List of fix results, each containing:
        - document: Document that was modified
        - change: Description of what was changed
        - success: Whether the fix was successful
    """
    # TODO: Implement actual inconsistency fixing logic
    return []


def display_inconsistency_report(inconsistencies: list[dict]) -> None:
    """Display a formatted inconsistency report."""
    for inc in inconsistencies:
        severity = inc.get("severity", "UNKNOWN")
        description = inc.get("description", "No description")

        # Color-code by severity (if terminal supports it)
        if severity == "HIGH":
            severity_str = f"[HIGH]"
        elif severity == "MEDIUM":
            severity_str = f"[MEDIUM]"
        else:
            severity_str = f"[LOW]"

        click.echo(f"  {severity_str} {description}")


def display_fix_results(fix_results: list[dict]) -> None:
    """Display the results of automatic fixes."""
    for result in fix_results:
        document = result.get("document", "Unknown")
        success = result.get("success", False)

        if success:
            click.echo(f"  ✓ Updated {document}")
        else:
            click.echo(f"  ✗ Failed to update {document}")
```

### 4.3 Integration with Generate Command

```python
@cli.command()
@click.option("--prompt", "-p", required=True, ...)
@click.option("--no-consistency-check", is_flag=True, help="Skip post-generation consistency check.")
@click.option("--auto-fix", is_flag=True, help="Automatically fix inconsistencies without prompting.")
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
    """Generate documentation from a product description prompt."""

    # ... existing generation logic ...

    # After generation completes:
    click.echo("\n✓ Document generation complete!")

    # Run consistency check loop
    run_consistency_check_loop(
        output_dir=output,
        auto_fix=auto_fix,
        no_check=no_consistency_check
    )

    # Show final summary
    click.echo("\nSummary: Generation complete.")
```

---

## 5. Delete-Key Interactive Selection

### 5.1 Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│           USER RUNS: specify config delete-key                  │
│                    (no --provider flag)                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              CHECK: Any providers configured?                    │
└─────────────────────────────────────────────────────────────────┘
                    │                    │
                   YES                   NO
                    │                    │
                    ▼                    ▼
┌──────────────────────────┐    ┌─────────────────────────────────┐
│ Display list of          │    │ Display: "No providers          │
│ configured providers     │    │ configured" and exit            │
│ with masked keys         │    └─────────────────────────────────┘
└──────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│  PROMPT: "Select provider to delete [1-N, or q to quit]"        │
└─────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│              USER SELECTS A PROVIDER                            │
└─────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│  PROMPT: "Are you sure you want to delete the key for           │
│           {provider}? [y/N]"                                     │
└─────────────────────────────────────────────────────────────────┘
                    │                    │
                   YES                   NO
                    │                    │
                    ▼                    ▼
┌──────────────────────────┐    ┌─────────────────────────────────┐
│ Delete the key           │    │ Return to selection or exit     │
│ Display success message  │    └─────────────────────────────────┘
└──────────────────────────┘
```

### 5.2 Pseudocode for Interactive Delete

```python
@config.command(name="delete-key")
@click.option(
    "--provider",
    "-p",
    required=False,  # Changed from True to False
    type=click.Choice(["ollama", "openai", "anthropic"], case_sensitive=False),
    help="Provider to delete the key for. If not specified, shows interactive selection.",
)
def delete_key(provider: str | None) -> None:
    """Delete a stored API key.

    If --provider is not specified, shows an interactive list of
    configured providers to select from.
    """
    key_manager = KeyManager()
    keys = key_manager.list_keys()

    if not keys:
        click.echo("No API keys configured.")
        return

    # If provider is specified, use non-interactive mode
    if provider:
        try:
            key_manager.delete_key(provider)
            click.echo(f"[OK] API key deleted for {provider}")
        except KeyNotFoundError as e:
            raise click.ClickException(str(e)) from e
        return

    # Interactive mode
    run_interactive_delete(key_manager, keys)


def run_interactive_delete(
    key_manager: KeyManager,
    keys: dict[str, str]
) -> None:
    """Run interactive provider selection for deletion.

    Args:
        key_manager: KeyManager instance.
        keys: Dictionary of provider -> masked_key.
    """
    click.echo("\nConfigured providers:")

    # Create numbered list
    providers = list(keys.keys())
    for i, prov in enumerate(providers, 1):
        click.echo(f"  {i}. {prov} ({keys[prov]})")

    click.echo(f"  q. Quit without deleting")

    while True:
        try:
            choice = click.prompt(
                "\nSelect provider to delete",
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
                    click.echo(f"Please enter a number between 1 and {len(providers)}, or 'q' to quit.")
            except ValueError:
                click.echo("Invalid input. Enter a number or 'q' to quit.")

        except click.Abort:
            click.echo("\nCancelled.")
            return

    # Confirm deletion
    try:
        confirm = click.confirm(
            f"Are you sure you want to delete the key for {selected_provider}?",
            default=False
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
```

---

## 6. Required Changes to specify/cli.py

### 6.1 Summary of Changes

| Component                              | Change Type | Description                                     |
| -------------------------------------- | ----------- | ----------------------------------------------- |
| `cli()` function                       | Modify      | Add first-run detection and main menu routing   |
| `run_interactive_onboarding()`         | Add         | New function for onboarding wizard              |
| `prompt_provider_selection()`          | Add         | New function for provider selection             |
| `prompt_model_selection()`             | Add         | New function for model selection                |
| `prompt_custom_model()`                | Add         | New function for custom model input             |
| `prompt_key_or_url()`                  | Add         | New function for key/URL input                  |
| `fetch_models_from_provider()`         | Add         | New function to fetch models from provider API  |
| `show_main_menu()`                     | Add         | New function for main menu display              |
| `handle_generate_documents()`          | Add         | New function for menu-driven generation         |
| `handle_list_providers()`              | Add         | New function for menu-driven provider listing   |
| `handle_delete_provider_interactive()` | Add         | New function for menu-driven deletion           |
| `run_consistency_check_loop()`         | Add         | New function for post-generation loop           |
| `check_consistency()`                  | Add         | Placeholder for consistency checking            |
| `fix_inconsistencies()`                | Add         | Placeholder for inconsistency fixing            |
| `display_inconsistency_report()`       | Add         | New function for formatted output               |
| `display_fix_results()`                | Add         | New function for formatted output               |
| `delete_key()`                         | Modify      | Make --provider optional, add interactive mode  |
| `run_interactive_delete()`             | Add         | New function for interactive deletion           |
| `generate()` command                   | Modify      | Add --no-consistency-check and --auto-fix flags |
| `setup` command                        | Add         | New command for adding providers                |

### 6.2 New Imports Required

```python
# Add to existing imports
from typing import Any
import ollama  # For fetching Ollama models
```

### 6.3 New Flags for Generate Command

```python
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
```

---

## 7. Model Preference Storage

### 7.1 New Functionality Required

The system needs to store and retrieve model preferences per provider. This requires:

1. A new JSON file: `~/.specify/models.json`
2. Two new functions: `save_model_preference()` and `get_model_preference()`

### 7.2 Pseudocode

```python
# In specify/core/key_manager.py or a new config.py module

import json
from pathlib import Path

MODELS_FILE_NAME = "models.json"


def save_model_preference(provider: str, model: str) -> None:
    """Save the preferred model for a provider.

    Args:
        provider: Provider name (ollama, openai, anthropic).
        model: Model name to save.
    """
    config_dir = Path.home() / CONFIG_DIR_NAME
    config_dir.mkdir(parents=True, exist_ok=True)

    models_file = config_dir / MODELS_FILE_NAME

    # Load existing preferences
    preferences = {}
    if models_file.exists():
        try:
            preferences = json.loads(models_file.read_text())
        except json.JSONDecodeError:
            preferences = {}

    # Update and save
    preferences[provider] = model
    models_file.write_text(json.dumps(preferences, indent=2))


def get_model_preference(provider: str) -> str | None:
    """Get the preferred model for a provider.

    Args:
        provider: Provider name.

    Returns:
        Model name if set, None otherwise.
    """
    config_dir = Path.home() / CONFIG_DIR_NAME
    models_file = config_dir / MODELS_FILE_NAME

    if not models_file.exists():
        return None

    try:
        preferences = json.loads(models_file.read_text())
        return preferences.get(provider)
    except json.JSONDecodeError:
        return None
```

---

## 8. Test Scenarios

### 8.1 First-Run Detection Tests

| Test ID | Scenario                          | Expected Behavior                                |
| ------- | --------------------------------- | ------------------------------------------------ |
| FR-001  | Start CLI with no keys configured | Interactive onboarding wizard starts             |
| FR-002  | Start CLI with keys configured    | Main menu appears directly                       |
| FR-003  | Start CLI with only env var keys  | Main menu appears (env vars count as configured) |
| FR-004  | Start CLI with --help flag        | Help message shown, no onboarding                |
| FR-005  | Start CLI with --version flag     | Version shown, no onboarding                     |

### 8.2 Interactive Onboarding Tests

| Test ID | Scenario                              | Expected Behavior                    |
| ------- | ------------------------------------- | ------------------------------------ |
| IO-001  | Select Ollama provider                | Prompt for base URL with default     |
| IO-002  | Select OpenAI provider                | Prompt for API key (hidden input)    |
| IO-003  | Select Anthropic provider             | Prompt for API key (hidden input)    |
| IO-004  | Select model from fetched list        | Model is stored as preference        |
| IO-005  | Enter custom model name               | Custom model is stored as preference |
| IO-006  | Cancel during provider selection      | Graceful exit with message           |
| IO-007  | Cancel during model selection         | Graceful exit with message           |
| IO-008  | Cancel during key input               | Graceful exit with message           |
| IO-009  | Ollama not running during model fetch | Fallback to custom model prompt      |
| IO-010  | Invalid provider number               | Re-prompt with error message         |

### 8.3 Main Menu Tests

| Test ID | Scenario                           | Expected Behavior                   |
| ------- | ---------------------------------- | ----------------------------------- |
| MM-001  | Select "Generate documents"        | Prompt for document type and prompt |
| MM-002  | Select "Add another provider"      | Run onboarding wizard               |
| MM-003  | Select "List configured providers" | Display providers with masked keys  |
| MM-004  | Select "Delete a provider"         | Run interactive delete              |
| MM-005  | Select "Exit"                      | Exit CLI with goodbye message       |
| MM-006  | Press Ctrl+C                       | Exit CLI with goodbye message       |
| MM-007  | Enter invalid menu number          | Re-prompt with error message        |

### 8.4 Post-Generation Consistency Check Tests

| Test ID | Scenario                          | Expected Behavior                           |
| ------- | --------------------------------- | ------------------------------------------- |
| PG-001  | Generate with no inconsistencies  | Prompt to check, then show "all consistent" |
| PG-002  | Generate with inconsistencies     | Prompt to check, show report, prompt to fix |
| PG-003  | Accept fix after inconsistencies  | Apply fixes, loop back to check prompt      |
| PG-004  | Decline fix after inconsistencies | Exit loop, show summary                     |
| PG-005  | Decline check after generation    | Skip to summary                             |
| PG-006  | Use --no-consistency-check flag   | Skip entire consistency flow                |
| PG-007  | Use --auto-fix flag               | Auto-fix without prompting, one iteration   |
| PG-008  | Press Ctrl+C during check prompt  | Exit gracefully                             |
| PG-009  | Multiple fix iterations           | Loop continues until user declines          |

### 8.5 Interactive Delete Tests

| Test ID | Scenario                               | Expected Behavior               |
| ------- | -------------------------------------- | ------------------------------- |
| ID-001  | Run delete-key with --provider flag    | Non-interactive deletion        |
| ID-002  | Run delete-key without --provider      | Interactive provider list shown |
| ID-003  | Select provider from list              | Confirmation prompt shown       |
| ID-004  | Confirm deletion                       | Key deleted, success message    |
| ID-005  | Decline deletion                       | Cancelled message, no deletion  |
| ID-006  | Press 'q' to quit                      | Cancelled message, no deletion  |
| ID-007  | Run delete-key with no keys configured | "No keys configured" message    |
| ID-008  | Invalid selection number               | Re-prompt with error message    |
| ID-009  | Press Ctrl+C during selection          | Exit gracefully                 |

### 8.6 Integration Tests

| Test ID | Scenario                                 | Expected Behavior                |
| ------- | ---------------------------------------- | -------------------------------- |
| INT-001 | Full flow: onboarding → generate → check | Complete user journey works      |
| INT-002 | Add provider → list → delete → list      | Provider management flow works   |
| INT-003 | Generate all docs with consistency loop  | All 5 docs generated, loop works |
| INT-004 | Non-interactive mode with all flags      | CI/CD mode works without prompts |

---

## 9. Implementation Checklist

### Phase 1: Core Infrastructure

- [ ] Add first-run detection to `cli()` function
- [ ] Create `run_interactive_onboarding()` function
- [ ] Create `prompt_provider_selection()` function
- [ ] Create `prompt_model_selection()` function
- [ ] Create `prompt_key_or_url()` function
- [ ] Create `fetch_models_from_provider()` function
- [ ] Add model preference storage functions

### Phase 2: Main Menu

- [ ] Create `show_main_menu()` function
- [ ] Create `handle_generate_documents()` function
- [ ] Create `handle_list_providers()` function
- [ ] Create `handle_delete_provider_interactive()` function
- [ ] Add `setup` command for adding providers

### Phase 3: Consistency Check Loop

- [ ] Create `run_consistency_check_loop()` function
- [ ] Add `--no-consistency-check` flag to generate command
- [ ] Add `--auto-fix` flag to generate command
- [ ] Create `display_inconsistency_report()` function
- [ ] Create `display_fix_results()` function
- [ ] Integrate with generate command

### Phase 4: Interactive Delete

- [ ] Modify `delete_key()` to make --provider optional
- [ ] Create `run_interactive_delete()` function
- [ ] Add confirmation prompt

### Phase 5: Testing

- [ ] Write unit tests for all new functions
- [ ] Write integration tests for complete flows
- [ ] Test with actual Ollama instance
- [ ] Test error handling and edge cases

---

## 10. Dependencies

### 10.1 Existing Dependencies (No Changes Needed)

- `click` - CLI framework
- `cryptography` - Key encryption
- `ollama` - Ollama SDK (for model fetching)

### 10.2 New Dependencies

None required. All functionality can be implemented with existing dependencies.

---

## 11. Error Handling

### 11.1 Error Scenarios

| Scenario                         | Handling                          |
| -------------------------------- | --------------------------------- |
| Ollama not running               | Fallback to custom model prompt   |
| Network error during model fetch | Fallback to custom model prompt   |
| Invalid API key format           | Validation error, re-prompt       |
| Key storage failure              | Display error, offer retry        |
| User cancels (Ctrl+C)            | Graceful exit with message        |
| Empty input                      | Re-prompt with validation message |

### 11.2 Error Messages

```python
ERROR_MESSAGES = {
    "provider_fetch_failed": "Could not fetch models from {provider}. You can enter a custom model name.",
    "key_storage_failed": "Failed to save configuration: {error}",
    "invalid_provider": "Invalid provider selection. Please try again.",
    "empty_input": "{field} cannot be empty. Please try again.",
    "no_keys_configured": "No API keys configured.",
    "delete_failed": "Failed to delete key: {error}",
}
```

---

## 12. Future Considerations

### 12.1 Potential Enhancements

- Add support for custom provider URLs (e.g., self-hosted OpenAI-compatible APIs)
- Add model validation by attempting a test API call
- Add configuration import/export functionality
- Add profile support for multiple configurations

### 12.2 Known Limitations

- Model fetching for OpenAI/Anthropic requires API key first (chicken-and-egg problem)
- Consistency checking and fixing are placeholders until Sprint 3
- No support for custom providers beyond the three built-in options
