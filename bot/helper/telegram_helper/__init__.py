# This function calculates the area of a rectangle
def rectangle_area(length: float, width: float) -> float:
    # Check if the length and width are positive numbers
    if length <= 0 or width <= 0:
        raise ValueError("Both length and width must be positive numbers.")

    # Calculate the area of the rectangle
    area = length * width

    # Print a more informative message with the area
    message = f"The area of the rectangle with length {length:.2f} and width {width:.2f} is {area:.2f}."
    print(message)

    # Return the calculated area
    return area

# Example usage:
result = rectangle_area(4, 5)
# The calculated area (20.00) can be used for further calculations.

