"""
Simple calculator module with basic arithmetic operations.
"""


def add(a: float, b: float) -> float:
    """Add two numbers."""
    return a + b


def subtract(a: float, b: float) -> float:
    """Subtract b from a."""
    return a - b


def multiply(a: float, b: float) -> float:
    """Multiply two numbers."""
    return a * b


def divide(a: float, b: float) -> float:
    """
    Divide a by b.

    Raises:
        ZeroDivisionError: If b is zero.
    """
    if b == 0:
        raise ZeroDivisionError("Cannot divide by zero")
    return a / b


def evaluate(expression: str) -> float:
    """
    Evaluate a simple arithmetic expression string.

    Supports: +, -, *, /

    Args:
        expression: A string like "2 + 3" or "10 / 2"

    Returns:
        The result of the arithmetic operation.

    Raises:
        ValueError: If the expression format is invalid.
        ZeroDivisionError: If dividing by zero.
    """
    parts = expression.split()

    if len(parts) != 3:
        raise ValueError(f"Invalid expression format: '{expression}'. Expected format: 'a op b'")

    try:
        a = float(parts[0])
        op = parts[1]
        b = float(parts[2])
    except ValueError:
        raise ValueError(f"Invalid numbers in expression: '{expression}'")

    operations = {
        '+': add,
        '-': subtract,
        '*': multiply,
        '/': divide,
    }

    if op not in operations:
        raise ValueError(f"Unknown operator: '{op}'. Supported operators: +, -, *, /")

    return operations[op](a, b)
