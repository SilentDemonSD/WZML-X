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
        self._validate_integer("major", self.major)
        self._validate_integer("minor", self.minor)
        self._validate_integer("patch", self.patch)

    def _validate_integer(self, name: str, value: object):
        """Raise a TypeError if the value is not an integer."""
        if not isinstance(value, int):
            raise TypeError(f"{name} must be an integer")

    def __repr__(self):
        """Return a string representation of the object that is unambiguous and useful for debugging."""
        return f"Version(major={self.major}, minor={self.minor}, patch={self.patch})"

    def to_tuple(self):
        """Return the version as a tuple of integers."""
        # Return a tuple of (major, minor, patch)
        return (self.major, self.minor, self.patch)

    def to_string(self):
        """Return the version as a string in the format 'major.minor.patch'."""
        # Return the version as a string with each number separated by a dot
        return f"{self.major}.{self.minor}.{self.patch}"
