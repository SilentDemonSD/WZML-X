# This function calculates the area of a rectangle
def rectangle_area(length: float, width: float) -> float:
    # The area of a rectangle is calculated by multiplying its length and width
    area = length * width
    
    # The area is returned as the output of the function with a more informative message
    print("The area of the rectangle with length {:.2f} and width {:.2f} is {:.2f}.".format(length, width, area))
    return area

# Example usage:
rectangle_area(4, 5)
