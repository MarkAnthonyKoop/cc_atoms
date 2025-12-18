# Calculator Module

## Overview
A simple Python calculator module with basic arithmetic operations and string expression evaluation.

## Status
COMPLETE

## Progress
- [x] Created calculator.py with add, subtract, multiply, divide functions
- [x] Added evaluate() function for string expressions like "2 + 3"
- [x] Implemented proper error handling for division by zero
- [x] Created comprehensive test suite (32 tests)
- [x] All tests passing

## Current State

### calculator.py
- `add(a, b)` - Add two numbers
- `subtract(a, b)` - Subtract b from a
- `multiply(a, b)` - Multiply two numbers
- `divide(a, b)` - Divide a by b (raises ZeroDivisionError if b is 0)
- `evaluate(expression)` - Evaluate a string like "2 + 3"

### tests/test_calculator.py
- TestAdd: 5 tests
- TestSubtract: 5 tests
- TestMultiply: 5 tests
- TestDivide: 6 tests (including division by zero)
- TestEvaluate: 11 tests (including error cases)

## Usage

```python
from calculator import add, subtract, multiply, divide, evaluate

# Direct function calls
add(2, 3)        # 5
subtract(5, 3)   # 2
multiply(4, 3)   # 12
divide(10, 2)    # 5.0

# String expression evaluation
evaluate("2 + 3")   # 5.0
evaluate("10 / 2")  # 5.0
```

## Running Tests

```bash
python3 -m pytest tests/test_calculator.py -v
```
