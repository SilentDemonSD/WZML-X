def is_prime(n: int) -> bool:
    """Returns True if n is a prime number, and False otherwise."""
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True

def largest_prime(numbers: list[int]) -> int | None:
    """Returns the largest prime number in the input list."""
    largest_prime = None
    for num in numbers:
        if is_prime(num) and (largest_prime is None or num > largest_prime):
            largest_prime = num
    return largest_prime
