def is_prime(n: int) -> bool:
    """
    Returns True if the input integer `n` is a prime number, and False otherwise.
    The function checks only odd numbers up to the square root of `n` to improve performance.
    """
    if n < 2:  # If n is less than 2, it cannot be a prime number.
        return False
    if n == 2:  # 2 is a prime number.
        return True
    if n % 2 == 0:  # Even numbers greater than 2 are not prime numbers.
        return False

    # Check odd numbers up to the square root of n.
    i = 3
    while i * i <= n:
        if n % i == 0:  # If n is divisible by an odd number i, it's not a prime number.
            return False
        i += 2  # Increment i by 2 to check only odd numbers.

    return True  # If no odd numbers up to the square root of n divide n, it's a prime number.

def largest_prime(numbers: list[int]) -> int | None:
    """
    Returns the largest prime number in the input list `numbers`, or `None` if no prime numbers are found.
    If the input list is empty, returns `None`.
    """
    if not numbers:  # If the input list is empty, return `None`.
        return None

    prime = None  # Initialize the variable to store the largest prime number.

    for num in numbers:  # Iterate through the input list.
        if is_prime(num):  # If the current number is prime, check if it's larger than the current largest prime.
            if prime is None or num > prime:
                prime = num  # Update the largest prime number.

    return prime  # Return the largest prime number found in the input list.
