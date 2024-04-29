def is_prime(n: int) -> bool:
    """Returns True if n is a prime number, and False otherwise. Checks only odd numbers up to the square root of n."""
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    i = 3
    while i * i <= n:
        if n % i == 0:
            return False
        i += 2
    return True

def largest_prime(numbers: list[int]) -> int | None:
    """Returns the largest prime number in the input list, or None if no prime numbers are found.
    If the input list is empty, returns None.
    """
    if not numbers:
        return None
    prime = None
    for num in numbers:
        if is_prime(num):
            if prime is None or num > prime:
                prime = num
    return prime
