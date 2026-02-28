"""
Pytest configuration and fixtures for Specify.AI tests.

This module provides shared fixtures for testing:
- temp_config_dir: Temporary config directory for testing
- sample_prompt: Sample product prompt for testing
- mock_ollama_response: Mock response from Ollama API
- mock_openai_response: Mock response from OpenAI API
- mock_anthropic_response: Mock response from Anthropic API
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

# ─────────────────────────────────────────────────────────────────────────────
# Directory Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def temp_config_dir(tmp_path: Path) -> Path:
    """
    Create a temporary config directory for testing.

    This fixture creates a .specify directory in a temporary location
    for testing configuration and key storage without affecting the
    user's actual configuration.

    Args:
        tmp_path: Pytest's built-in temporary path fixture.

    Returns:
        Path to the temporary config directory.

    Example:
        >>> def test_config(temp_config_dir):
        ...     assert temp_config_dir.exists()
        ...     assert temp_config_dir.name == ".specify"
    """
    config_dir = tmp_path / ".specify"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    """
    Create a temporary output directory for testing.

    This fixture creates an output directory for testing document
    generation without affecting the user's actual output directory.

    Args:
        tmp_path: Pytest's built-in temporary path fixture.

    Returns:
        Path to the temporary output directory.
    """
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir


# ─────────────────────────────────────────────────────────────────────────────
# Sample Data Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def sample_prompt() -> str:
    """
    Sample product prompt for testing.

    Returns:
        A sample product description prompt.

    Example:
        >>> def test_generation(sample_prompt):
        ...     assert "task management" in sample_prompt.lower()
    """
    return "Build a simple task management app with user authentication"


@pytest.fixture
def sample_long_prompt() -> str:
    """
    Long sample product prompt for testing.

    Returns:
        A longer sample product description prompt.
    """
    return """
    Build a comprehensive task management application with the following features:
    
    1. User authentication with email/password and OAuth (Google, GitHub)
    2. Task creation, editing, and deletion
    3. Task categories and tags
    4. Due dates and reminders
    5. Task priorities (low, medium, high, urgent)
    6. Task assignments to team members
    7. Comments and attachments on tasks
    8. Search and filter functionality
    9. Dashboard with task statistics
    10. Mobile-responsive design
    
    The app should support multiple teams and projects, with role-based
    access control (admin, manager, member). It should integrate with
    calendar apps and support email notifications.
    """


# ─────────────────────────────────────────────────────────────────────────────
# Mock API Response Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_ollama_response() -> dict[str, object]:
    """
    Mock response from Ollama API.

    Returns:
        A dictionary representing a mock Ollama API response.

    Example:
        >>> def test_ollama_client(mock_ollama_response):
        ...     assert mock_ollama_response["done"] is True
        ...     assert "App Flow Document" in mock_ollama_response["response"]
    """
    return {
        "model": "llama3",
        "created_at": "2024-01-01T00:00:00Z",
        "response": """# App Flow Document

## Overview
This document outlines the user flow for a task management application.

## User Flows

### 1. User Registration
1. User opens the app
2. User clicks "Sign Up"
3. User enters email and password
4. User verifies email
5. User is redirected to dashboard

### 2. Task Creation
1. User clicks "New Task"
2. User enters task details
3. User sets due date and priority
4. User saves task
5. Task appears in task list
""",
        "done": True,
        "total_duration": 5000000000,
        "load_duration": 500000000,
        "prompt_eval_count": 50,
        "prompt_eval_duration": 1000000000,
        "eval_count": 200,
        "eval_duration": 3500000000,
    }


@pytest.fixture
def mock_openai_response() -> dict[str, object]:
    """
    Mock response from OpenAI API.

    Returns:
        A dictionary representing a mock OpenAI API response.

    Example:
        >>> def test_openai_client(mock_openai_response):
        ...     choices = mock_openai_response["choices"]
        ...     assert len(choices) == 1
        ...     assert "content" in choices[0]["message"]
    """
    return {
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "created": 1704067200,
        "model": "gpt-4",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": """# Product Requirements Document

## 1. Introduction
This PRD defines the requirements for a task management application.

## 2. Problem Statement
Users need a simple way to manage tasks and stay organized.

## 3. Goals
- Enable users to create and manage tasks
- Provide task categorization and prioritization
- Support team collaboration

## 4. User Stories
- As a user, I want to create tasks so I can track my work
- As a user, I want to set due dates so I don't miss deadlines
- As a user, I want to assign tasks to team members
""",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 200,
            "total_tokens": 300,
        },
    }


@pytest.fixture
def mock_anthropic_response() -> dict[str, object]:
    """
    Mock response from Anthropic API.

    Returns:
        A dictionary representing a mock Anthropic API response.

    Example:
        >>> def test_anthropic_client(mock_anthropic_response):
        ...     content = mock_anthropic_response["content"]
        ...     assert len(content) == 1
        ...     assert content[0]["type"] == "text"
    """
    return {
        "id": "msg_123",
        "type": "message",
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": """# Technical Architecture Document

## 1. System Overview
A task management application with a client-server architecture.

## 2. Technology Stack
- Frontend: React with TypeScript
- Backend: Python with FastAPI
- Database: PostgreSQL
- Cache: Redis

## 3. Architecture Diagram
```
[Client] -> [API Gateway] -> [Backend Services] -> [Database]
```

## 4. Key Components
- Authentication Service
- Task Service
- Notification Service
- File Storage Service
""",
            }
        ],
        "model": "claude-3-opus-20240229",
        "stop_reason": "end_turn",
        "usage": {
            "input_tokens": 100,
            "output_tokens": 200,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# CLI Test Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def cli_runner() -> pytest.CliRunner:
    """
    Create a Click CLI test runner.

    Returns:
        A Click CliRunner instance for testing CLI commands.

    Example:
        >>> def test_cli_version(cli_runner):
        ...     from specify.cli import cli
        ...     result = cli_runner.invoke(cli, ["--version"])
        ...     assert result.exit_code == 0
        ...     assert "specify-ai" in result.output
    """
    return CliRunner()


# ─────────────────────────────────────────────────────────────────────────────
# Configuration Markers
# ─────────────────────────────────────────────────────────────────────────────


def pytest_configure(config: pytest.Config) -> None:
    """
    Configure custom pytest markers.

    This function registers custom markers used in the test suite.

    Args:
        config: The pytest configuration object.
    """
    config.addinivalue_line(
        "markers",
        "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    )
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests",
    )
    config.addinivalue_line(
        "markers",
        "unit: marks tests as unit tests",
    )
