"""Test utilities.py."""
from app import my_function


def test__my_function() -> None:
    """Test my_function."""
    assert my_function(1, 2) == 3
