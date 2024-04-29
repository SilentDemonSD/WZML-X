from dataclasses import dataclass
from typing import Final

@dataclass
class Version:
    major: Final[int]
    minor: Final[int] = 0
    patch: Final[int] = 0

    def __post_init__(self):
        # Validate the attributes
        assert isinstance(self.major, int), "major must be an integer"
        assert isinstance(self.minor, int), "minor must be an integer"
        assert isinstance(self.patch, int), "patch must be an integer"

    def __repr__(self):
        return f"Version(major={self.major}, minor={self.minor}, patch={self.patch})"
