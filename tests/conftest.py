# tests/conftest.py
"""Shared pytest fixtures for all tests."""

import pytest
import os
import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


@pytest.fixture(autouse=True)
def clean_env():
    """Ensure clean environment for each test."""
    # Store original env
    original_env = os.environ.copy()
    yield
    # Restore original env
    os.environ.clear()
    os.environ.update(original_env)
