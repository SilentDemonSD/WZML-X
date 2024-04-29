from dataclasses import dataclass

@dataclass
class Version:
    major: int
    minor: int = 0
    patch: int = 0
    # You can add more attributes if needed

    def __post_init__(self):
        # Validate the attributes
        if not isinstance(self.major, int):
            raise TypeError("major must be an integer")
        if not isinstance(self.minor, int):
            raise TypeError("minor must be an integer")
        if not isinstance(self.patch, int):
            raise TypeError("patch must be an integer")

