"""Defines test fixtures for pytest unit-tests."""
import pytest


@pytest.fixture
def fake_dataset() -> dict:
    """Returns a fake dataset for testing."""
    return {
        "name": "test-dataset",
        "data": [1, 2, 3, 4, 5],
    }

