# This function calculates the area of a rectangle
def rectangle_area(length: float, width: float) -> float:
    # The area of a rectangle is calculated by multiplying its length and width
    area = length * width
    
    # The area is returned as the output of the function with a more informative message
    print(f"The area of the rectangle with length {length:.2f} and width {width:.2f} is {area:.2f}.")
    
    # Return the area to enable further calculations if needed
    return area

# Example usage:
result = rectangle_area(4, 5)
print(f"The calculated area ({result:.2f}) can be used for further calculations.")
