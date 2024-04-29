from dataclasses import dataclass
from typing import Final

@dataclass
class Version:
    """A dataclass representing a software version with major, minor, and patch numbers."""
    major: Final[int]  # Major version number (e.g., 1 for version 1.0.0)
    minor: int = 0  # Minor version number (e.g., 0 for version 1.0.0)
    patch: int = 0  # Patch version number (e.g., 0 for version 1.0.0)

    def __post_init__(self):
        """Validate the attributes after initialization."""
        # Raise a TypeError if major is not an integer
        if not isinstance(self.major, int):
            raise TypeError("major must be an integer")
        
        # Raise a TypeError if minor is not an integer
        if not isinstance(self.minor, int):
            raise TypeError("minor must be an integer")
        
        # Raise a TypeError if patch is not an integer
        if not isinstance(self.patch, int):
            raise TypeError("patch must be an integer")

    def __repr__(self):
        """Return a string representation of the object that is unambiguous and useful for debugging."""
        return f"Version(major={self.major}, minor={self.minor}, patch={self.patch})"

    def to_tuple(self):
        """Return the version as a tuple of integers."""
        return (self.major, self.minor, self.patch)

    def to_string(self):
        """Return the version as a string in the format 'major.minor.patch'."""
        return f"{self.major}.{self.minor}.{self.patch}"
