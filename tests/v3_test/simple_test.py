"""
Simple test file to verify the atom system is working.
"""


def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


def subtract(a: int, b: int) -> int:
    """Subtract b from a."""
    return a - b


def multiply(a: int, b: int) -> int:
    """Multiply two numbers."""
    return a * b


def divide(a: float, b: float) -> float:
    """Divide a by b."""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b


if __name__ == "__main__":
    # Basic test demonstrations
    print("Testing add:", add(2, 3), "== 5:", add(2, 3) == 5)
    print("Testing subtract:", subtract(5, 3), "== 2:", subtract(5, 3) == 2)
    print("Testing multiply:", multiply(4, 3), "== 12:", multiply(4, 3) == 12)
    print("Testing divide:", divide(10, 2), "== 5.0:", divide(10, 2) == 5.0)
    print("\nAll basic tests passed!")
