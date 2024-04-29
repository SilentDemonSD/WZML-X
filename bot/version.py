from dataclasses import dataclass
from typing import Final

@dataclass
class Version:
    major: Final[int]
    minor: int = 0
    patch: int = 0

    def __post_init__(self):
        # Validate the attributes
        if not isinstance(self.major, int):
            raise TypeError("major must be an integer")
        if not isinstance(self.minor, int):
            raise TypeError("minor must be an integer")
        if not isinstance(self.patch, int):
            raise TypeError("patch must be an integer")

    def __repr__(self):
        return f"Version(major={self.major}, minor={self.minor}, patch={self.patch})"

    def to_tuple(self):
        """Return the version as a tuple of integers."""
        return (self.major, self.minor, self.patch)

    def to_string(self):
        """Return the version as a string in the format 'major.minor.patch'."""
        return f"{self.major}.{self.minor}.{self.patch}"
