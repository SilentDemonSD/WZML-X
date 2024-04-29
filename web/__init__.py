from typing import List, Optional

def is_prime(n: int) -> bool:
    """Returns True if n is a prime number, and False otherwise."""
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True

def largest_prime(numbers: List[int]) -> Optional[int]:
    """Returns the largest prime number in the input list, or None if no prime numbers are found."""
    prime = max(num for num in numbers if is_prime(num), default=None)
    return prime
