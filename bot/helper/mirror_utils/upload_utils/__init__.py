def calculate_rectangle_area(length: float, width: float) -> float:
    """
    This function calculates the area of a rectangle.

    :param length: The length of the rectangle. It must be a positive number.
    :param width: The width of the rectangle. It must be a positive number.
    :return: The area of the rectangle.
    :raises TypeError: If the length or width is not a number.
    :raises ValueError: If the length or width is less than or equal to zero.
    """
    # Check if the input types are numbers
    if not isinstance(length, (int, float)) or not isinstance(width, (int, float)):
        raise TypeError("Both length and width must be numbers.")

    # Check if the input values are positive
    if length <= 0 or width <= 0:
        raise ValueError("Both length and width must be positive numbers.")

    # Calculate the area
    area = length * width

    # Return the area
    return area
