def calculate_rectangle_area(length: float, width: float) -> float:
    """
    This function calculates the area of a rectangle.

    :param length: The length of the rectangle (must be non-negative).
    :param width: The width of the rectangle (must be non-negative).
    :return: The area of the rectangle.
    :raises ValueError: If either the length or width is negative.
    """
    if length < 0 or width < 0:
        raise ValueError("Both length and width must be non-negative.")
    area = length * width
    return area
