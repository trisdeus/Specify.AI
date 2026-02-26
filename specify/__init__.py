"""
Specify.AI - Local-first CLI tool that transforms a single prompt into
five production-ready documents using AI.

This package provides:
- CLI interface for document generation
- LLM provider abstraction (Ollama, OpenAI, Anthropic)
- Document generators (App Flow, BDD, Design Doc, PRD, Tech Arch)
- Consistency checking and recommendations

Example usage:
    >>> import specify
    >>> specify.__version__
    '0.1.0'
"""

from __future__ import annotations

__version__ = "0.1.0"
__author__ = "Specify.AI Team"
__license__ = "MIT"

__all__ = [
    "__author__",
    "__license__",
    "__version__",
]
