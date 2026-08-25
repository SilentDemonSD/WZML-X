def get_version() -> str:
    MAJOR = "3"
    MINOR = "1"
    PATCH = "10"
    STATE = "x"
    return f"v{MAJOR}.{MINOR}.{PATCH}-{STATE}"


if __name__ == "__main__":
    print(get_version())
