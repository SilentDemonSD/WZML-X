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
    return num1 + num
