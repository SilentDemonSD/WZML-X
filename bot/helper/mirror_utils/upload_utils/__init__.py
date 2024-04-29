def calculate_rectangle_area(length: float, width: float) -> float:
    """
    This function calculates the area of a rectangle.

    :param length: The length of the rectangle. It must be a positive number.
    :param width: The width of the rectangle. It must be a positive number.
    :return: The area of the rectangle.
    :raises ValueError: If the length or width is less than or equal to zero.
    """
    if not all([isinstance(num, (int, float)) for num in (length, width)]):
        raise TypeError("Both length and width must be numbers.")
    
    if length <= 0 or width <= 0:
        raise ValueError("Both length and width must be positive numbers.")
    
    area = length * width
    return area
