"""
Pytest configuration and shared fixtures
"""

import pytest
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="session")
def test_data_dir():
    """Return path to test data directory."""
    return Path(__file__).parent.parent / "data" / "test"


@pytest.fixture(scope="session")
def temp_data_dir():
    """Return path to temporary data directory."""
    return Path(__file__).parent.parent / "data" / "temp"


@pytest.fixture
def sample_csv_data():
    """Sample CSV data for testing."""
    return """id,name,description,price
1,Product A,Description A,10.99
2,Product B,Description B,20.99
3,Product C,Description C,30.99
"""


# Add more shared fixtures here
