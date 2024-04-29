from typing import List, Optional

def is_prime(n: int) -> bool:
    """
    Returns True if the input integer n is a prime number, and False otherwise.

    A prime number is a natural number greater than 1 that has no positive
    divisors other than 1 and itself. This function checks if a number is prime
    by iterating from 2 to the square root of n and checking if n is divisible
    by any of these numbers. If n is divisible by any number in this range, it
    is not a prime number. Otherwise, it is a prime number.

    :param n: The input integer to check for primality.
    :return: A boolean value indicating whether n is a prime number.
    """
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True

def largest_prime(numbers: List[int]) -> Optional[int]:
    """
    Returns the largest prime number in the input list of integers, or None if
    no prime numbers are found.

    This function iterates through the input list of integers and checks if each
    number is a prime number using the is_prime function. If a number is prime,
    it is compared to the current maximum prime number found so far. If the number
    is larger than the current maximum prime number, it becomes the new maximum
    prime number. If no prime numbers are found in the input list, the function
    returns None.

    :param numbers: The input list of integers to find the largest prime number.
    :return: The largest prime number in the input list, or None if no prime
             numbers are found.
    """
    prime = max(num for num in numbers if is_prime(num), default=None)
    return prime
