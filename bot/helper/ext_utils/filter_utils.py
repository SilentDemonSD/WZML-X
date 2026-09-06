from re import IGNORECASE, compile as re_compile, error as re_error

DOC_ATTRS = ("document",)
MEDIA_ATTRS = ("video", "audio", "photo", "animation", "voice", "video_note")
ALL_ATTRS = DOC_ATTRS + MEDIA_ATTRS
CONTENT_TYPES = ("doc", "med", "all")
MAX_PATTERN = 500


def norm_extensions(value):
    if not value:
        return ()
    parts = value.split() if isinstance(value, str) else value
    return tuple(x.lstrip(".").strip().lower() for x in parts if str(x).strip())


def matches_extension(name, exts):
    if not name or not exts:
        return False
    return name.strip().lower().endswith(tuple(exts))


def compile_pattern(value, label):
    if not value:
        return None
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1].strip()
    if not value:
        return None
    if len(value) > MAX_PATTERN:
        raise ValueError(f"{label} pattern is too long, max {MAX_PATTERN} characters")
    try:
        return re_compile(value, IGNORECASE)
    except re_error as err:
        raise ValueError(f"Bad {label} pattern: {err}") from None


def media_of(message):
    for attr in ALL_ATTRS:
        found = getattr(message, attr, None)
        if found:
            return found
    return None


def file_name_of(message):
    found = media_of(message)
    return getattr(found, "file_name", "") or ""


def caption_of(message):
    return getattr(message, "caption", None) or getattr(message, "text", None) or ""


def size_of(message):
    found = media_of(message)
    return int(getattr(found, "file_size", 0) or 0)


def has_any(message, attrs):
    return any(getattr(message, attr, None) for attr in attrs)


class MessageFilter:
    __slots__ = ("content_type", "exts", "name_in", "name_ex", "cap_in", "cap_ex")

    def __init__(self, content_type="all", exts=(), patterns=None):
        if content_type not in CONTENT_TYPES:
            raise ValueError(f"Content type must be one of {', '.join(CONTENT_TYPES)}")
        self.content_type = content_type
        self.exts = norm_extensions(exts)
        patterns = patterns or {}
        self.name_in = compile_pattern(patterns.get("mn"), "-mn")
        self.name_ex = compile_pattern(patterns.get("xn"), "-xn")
        self.cap_in = compile_pattern(patterns.get("mc"), "-mc")
        self.cap_ex = compile_pattern(patterns.get("xc"), "-xc")

    @property
    def active(self):
        return bool(
            self.content_type != "all"
            or self.exts
            or self.name_in
            or self.name_ex
            or self.cap_in
            or self.cap_ex
        )

    def verdict(self, message):
        if message is None or getattr(message, "empty", False):
            return "empty"
        if getattr(message, "service", None):
            return "service"
        if self.content_type == "doc":
            if not has_any(message, DOC_ATTRS):
                return "type"
        elif self.content_type == "med":
            if not has_any(message, MEDIA_ATTRS):
                return "type"
        elif not has_any(message, ALL_ATTRS) and not caption_of(message):
            return "type"
        name = file_name_of(message)
        if self.exts and matches_extension(name, self.exts):
            return "ext"
        if self.name_in and not self.name_in.search(name):
            return "name"
        if self.name_ex and self.name_ex.search(name):
            return "name"
        caption = caption_of(message)
        if self.cap_in and not self.cap_in.search(caption):
            return "caption"
        if self.cap_ex and self.cap_ex.search(caption):
            return "caption"
        return None

    def keep(self, message):
        return self.verdict(message) is None
