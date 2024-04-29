#!/usr/bin/env python3

"""
This module provides a set of functions for performing basic arithmetic operations.
"""

from typing import Any, Callable, Dict, Union

def is_number(value: Any) -> bool:
    """
    Returns True if the given value is a number (int or float), False otherwise.
    """
    return isinstance(value, (int, float))

def add_numbers(num1: Union[int, float], num2: Union[int, float]) -> Union[int, float]:
    """
    Adds two numbers (int or float) and returns the result as the same type.
    """
    return num1 + num2

