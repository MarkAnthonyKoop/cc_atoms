"""
Unit tests for calculator module.
"""
import pytest
import sys
from pathlib import Path

# Add parent directory to path to import calculator
sys.path.insert(0, str(Path(__file__).parent.parent))

from calculator import add, subtract, multiply, divide, evaluate


class TestAdd:
    """Tests for the add function."""

    def test_add_positive_numbers(self):
        assert add(2, 3) == 5

    def test_add_negative_numbers(self):
        assert add(-2, -3) == -5

    def test_add_mixed_numbers(self):
        assert add(-2, 3) == 1

    def test_add_floats(self):
        assert add(2.5, 3.5) == 6.0

    def test_add_zero(self):
        assert add(0, 5) == 5
        assert add(5, 0) == 5


class TestSubtract:
    """Tests for the subtract function."""

    def test_subtract_positive_numbers(self):
        assert subtract(5, 3) == 2

    def test_subtract_negative_numbers(self):
        assert subtract(-5, -3) == -2

    def test_subtract_mixed_numbers(self):
        assert subtract(5, -3) == 8

    def test_subtract_floats(self):
        assert subtract(5.5, 3.5) == 2.0

    def test_subtract_zero(self):
        assert subtract(5, 0) == 5
        assert subtract(0, 5) == -5


class TestMultiply:
    """Tests for the multiply function."""

    def test_multiply_positive_numbers(self):
        assert multiply(2, 3) == 6

    def test_multiply_negative_numbers(self):
        assert multiply(-2, -3) == 6

    def test_multiply_mixed_numbers(self):
        assert multiply(-2, 3) == -6

    def test_multiply_floats(self):
        assert multiply(2.5, 4) == 10.0

    def test_multiply_by_zero(self):
        assert multiply(5, 0) == 0
        assert multiply(0, 5) == 0


class TestDivide:
    """Tests for the divide function."""

    def test_divide_positive_numbers(self):
        assert divide(6, 3) == 2

    def test_divide_negative_numbers(self):
        assert divide(-6, -3) == 2

    def test_divide_mixed_numbers(self):
        assert divide(-6, 3) == -2

    def test_divide_floats(self):
        assert divide(7.5, 2.5) == 3.0

    def test_divide_zero_numerator(self):
        assert divide(0, 5) == 0

    def test_divide_by_zero_raises_error(self):
        with pytest.raises(ZeroDivisionError) as excinfo:
            divide(5, 0)
        assert "Cannot divide by zero" in str(excinfo.value)


class TestEvaluate:
    """Tests for the evaluate function."""

    def test_evaluate_addition(self):
        assert evaluate("2 + 3") == 5

    def test_evaluate_subtraction(self):
        assert evaluate("5 - 3") == 2

    def test_evaluate_multiplication(self):
        assert evaluate("4 * 3") == 12

    def test_evaluate_division(self):
        assert evaluate("10 / 2") == 5

    def test_evaluate_floats(self):
        assert evaluate("2.5 + 3.5") == 6.0

    def test_evaluate_negative_numbers(self):
        assert evaluate("-2 + 5") == 3

    def test_evaluate_division_by_zero(self):
        with pytest.raises(ZeroDivisionError):
            evaluate("5 / 0")

    def test_evaluate_invalid_operator(self):
        with pytest.raises(ValueError) as excinfo:
            evaluate("5 % 3")
        assert "Unknown operator" in str(excinfo.value)

    def test_evaluate_invalid_format_too_few_parts(self):
        with pytest.raises(ValueError) as excinfo:
            evaluate("5 +")
        assert "Invalid expression format" in str(excinfo.value)

    def test_evaluate_invalid_format_too_many_parts(self):
        with pytest.raises(ValueError) as excinfo:
            evaluate("5 + 3 + 2")
        assert "Invalid expression format" in str(excinfo.value)

    def test_evaluate_invalid_number(self):
        with pytest.raises(ValueError) as excinfo:
            evaluate("abc + 3")
        assert "Invalid numbers" in str(excinfo.value)
