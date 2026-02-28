"""Unit tests for package metadata and configuration."""

import importlib.metadata

import pytest


def test_package_version():
    """Test that the package version is correctly defined."""
    # This test verifies that the version can be retrieved.
    # In an installed environment, it checks the distribution.
    # In a development environment, it might rely on the package attribute if defined.
    try:
        version = importlib.metadata.version("specify-ai")
        assert version == "0.1.0"
    except importlib.metadata.PackageNotFoundError:
        # If the package is not installed (e.g., running from source without install),
        # we verify the static configuration is correct by checking the pyproject.toml
        # or simply passing if we can't verify dynamically.
        # For this test, we assume the environment is set up correctly or we check the constant.
        pytest.skip("Package not installed, cannot verify dynamic version metadata")


def test_entry_point_exists():
    """Test that the CLI entry point is registered."""
    entry_points = importlib.metadata.entry_points()

    # Handle different return types for entry_points() across Python versions
    if isinstance(entry_points, dict):
        console_scripts = entry_points.get("console_scripts", [])
    else:
        # Python 3.10+ returns an EntryPoints object
        console_scripts = entry_points.select(group="console_scripts")

    specify_entry = None
    for entry in console_scripts:
        if entry.name == "specify":
            specify_entry = entry
            break

    assert specify_entry is not None, "CLI entry point 'specify' not found"
    assert specify_entry.value == "specify.cli:main"


def test_import_main_package():
    """Test that the main specify package can be imported."""
    import specify

    assert specify is not None


def test_dependencies_available():
    """Test that core dependencies are available."""
    # These imports should not raise ImportError if dependencies are installed
    import click
    import pydantic
    import structlog

    assert click is not None
    assert pydantic is not None
    assert structlog is not None
