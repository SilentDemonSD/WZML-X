def is_prime(n: int) -> bool:
    """Returns True if n is a prime number, and False otherwise."""
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True

def largest_prime_number(numbers: List[int]) -> Union[int, str]:
    """Returns the largest prime number in the input list. If there are no prime numbers in the list, returns a message indicating so."""
    primes = [num for num in numbers if is_prime(num)]
    if primes:
        return max(primes)
    else:
        return "There are no prime numbers in the input list."
