"""Greeter module with simple greeting functions.

This module provides functions for greeting and bidding farewell to users.
"""


def greet(name: str) -> str:
    """Return a greeting message for the given name.

    Args:
        name: The name to greet.

    Returns:
        A greeting in the format "Hello, {name}!"

    Raises:
        TypeError: If name is not a string.
    """
    if not isinstance(name, str):
        raise TypeError("name must be a string")
    return f"Hello, {name}!"


def farewell(name: str) -> str:
    """Return a farewell message for the given name.

    Args:
        name: The name to bid farewell to.

    Returns:
        A farewell in the format "Goodbye, {name}!"

    Raises:
        TypeError: If name is not a string.
    """
    if not isinstance(name, str):
        raise TypeError("name must be a string")
    return f"Goodbye, {name}!"
