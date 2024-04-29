#!/usr/bin/env python3

def add_numbers(num1: float, num2: float) -> float:
    """
    Adds two numbers and returns the result.

    :param num1: The first number to add.
    :param num2: The second number to add.
    :return: The sum of the two numbers.
    """
    return num1 + num2

def subtract_numbers(num1: float, num2: float) -> float:
    """
    Subtracts the second number from the first and returns the result.

    :param num1: The first number to subtract from.
    :param num2: The second number to subtract.
    :return: The result of subtracting num2 from num1.
    """
    return num1 - num2

def multiply_numbers(num1: float, num2: float) -> float:
    """
    Multiplies two numbers and returns the result.

    :param num1: The first number to multiply.
    :param num2: The second number to multiply.
    :return: The product of the two numbers.
    """
    return num1 * num2

def divide_numbers(num1: float, num2: float) -> float:
    """
    Divides the first number by the second and returns the result.

    :param num1: The number to divide.
    :param num2: The divisor.
    :return: The result of dividing num1 by num2.
    """
    if num2 == 0:
        raise ValueError("Divisor cannot be zero.")
    return num1 / num2
