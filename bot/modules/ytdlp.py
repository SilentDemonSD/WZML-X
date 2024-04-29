#!/usr/bin/env python3

"""
This module provides a set of functions for performing basic arithmetic operations.
"""

from typing import Any, Callable, Dict, Union

def is_number(value: Any) -> bool:
    """
    Returns True if the given value is a number, False otherwise.
    """
    return isinstance(value, (int, float))

def add_numbers(num1: float, num2: float) -> float:
    """
    Adds two numbers and returns the result.
    """
    return num1 + num2

def subtract_numbers(num1: float, num2: float) -> float:
    """
    Subtracts the second number from the first and returns the result.
    """
    return num1 - num2

def multiply_numbers(num1: float, num2: float) -> float:
    """
    Multiplies two numbers and returns the result.
    """
    return num1 * num2

def divide_numbers(num1: float, num2: float) -> float:
    """
    Divides the first number by the second and returns the result.
    """
    if not is_number(num2) or num2 == 0:
        raise ValueError("Divisor cannot be zero.")
    return num1 / num2

def square(num: float) -> float:
    """
    Returns the square of a number.
    """
    if not is_number(num) or num < 0:
        raise ValueError("Input must be a non-negative number.")
    return num * num

ARITHMETIC_OPERATIONS: Dict[str, Callable[[Union[int, float]], Union[int, float]]] = {
    "add": add_numbers,
    "subtract": subtract_numbers,
    "multiply": multiply_numbers,
    "divide": divide_numbers,
    "square": square,
}

if __name__ == "__main__":
    # Example usage
    num = 5
    print(f"{num} squared is {ARITHMETIC_OPERATIONS['square'](num)}")
