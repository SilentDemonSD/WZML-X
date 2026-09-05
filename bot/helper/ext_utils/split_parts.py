from re import IGNORECASE, compile as re_compile

SPLIT_OVERLAP = 3

PART_RE = re_compile(r"^(.*)\.part(\d{1,4})(\.[A-Za-z0-9]+)$", IGNORECASE)


def part_key(name):
    found = PART_RE.match(name or "")
    if not found:
        return None
    return found.group(1), int(found.group(2)), found.group(3).lower()


def part_series(names):
    keys = [part_key(n) for n in names]
    if len(keys) < 2 or any(k is None for k in keys):
        return None
    if len({(k[0], k[2]) for k in keys}) != 1:
        return None
    nums = [k[1] for k in keys]
    if len(set(nums)) != len(nums):
        return None
    return keys


def split_trims(names):
    keys = part_series(names)
    if keys is None:
        return None
    nums = [k[1] for k in keys]
    if nums != sorted(nums):
        return None
    return [0] + [
        SPLIT_OVERLAP if nums[at] - nums[at - 1] == 1 else 0
        for at in range(1, len(nums))
    ]
