def is_prime(n: int) -> bool:
    """
    Returns True if the input integer `n` is a prime number, and False otherwise.

    A prime number is a natural number greater than 1 that has no positive divisors other than 1 and itself.
    This function checks if a number is prime by iterating from 2 to the square root of the number and
    checking if any of these numbers divide `n` without a remainder. If such a divisor is found, the function
    immediately returns False, as the number is not prime. If no divisors are found, the function returns True,
    indicating that the number is prime.

    :param n: The integer number to check for primality.
    :return: A boolean value indicating whether `n` is prime or not.
    """
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True

def largest_prime_number(numbers: List[int]) -> Union[int, str]:
    """
    Returns the largest prime number in the input list of integers. If there are no prime numbers in the list,
    returns a message indicating so.

    This function first filters the input list to keep only the prime numbers using the `is_prime` function.
    If there are any prime numbers in the list, it returns the maximum prime number found. Otherwise, it returns
    a string message indicating that there are no prime numbers in the input list.

    :param numbers: The list of integers to search for the largest prime number.
    :return: The largest prime number in the input list or a message indicating that there are no prime numbers.
    """
    primes = [num for num in numbers if is_prime(num)]
    if primes:
        return max(primes)
    else:
        return "There are no prime numbers in the input list."
