from math import ceil
from os import cpu_count

AUTO_SHARE = 0.6


def allowed_cpus():
    try:
        from os import sched_getaffinity

        cpus = sorted(sched_getaffinity(0))
        if cpus:
            return cpus
    except (ImportError, OSError):
        pass
    return list(range(cpu_count() or 1))


def _parse_ids(spec, cpus):
    ids = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            try:
                lo, hi = (int(x) for x in part.split("-", 1))
            except ValueError:
                return []
            ids.extend(range(lo, hi + 1))
        else:
            try:
                ids.append(int(part))
            except ValueError:
                return []
    allowed = set(cpus)
    return sorted({i for i in ids if i in allowed})


def _take(cpus, count):
    return cpus[: max(1, min(count, len(cpus)))]


def _pick_cpus(cpus, spec):
    spec = str(spec or "").strip().lower()
    if not spec or spec == "auto":
        return _take(cpus, ceil(len(cpus) * AUTO_SHARE))
    if spec in ("all", "0", "max"):
        return list(cpus)
    if spec.endswith("%"):
        try:
            pct = float(spec[:-1])
        except ValueError:
            return _take(cpus, ceil(len(cpus) * AUTO_SHARE))
        return _take(cpus, ceil(len(cpus) * pct / 100))
    if spec.isdigit():
        return _take(cpus, int(spec))
    picked = _parse_ids(spec, cpus)
    return picked or _take(cpus, ceil(len(cpus) * AUTO_SHARE))


def ffmpeg_cpus():
    from .config_manager import Config

    return _pick_cpus(allowed_cpus(), Config.FFMPEG_CORES)


def ffmpeg_layout():
    """(taskset core list, -threads value) for FFmpeg, per Config.FFMPEG_CORES."""
    picked = ffmpeg_cpus()
    return ",".join(str(i) for i in picked), len(picked)


def service_cores():
    """Core list for background services: whatever FFmpeg was not given.

    Empty means "do not pin" — either FFmpeg holds every CPU or the box has
    too few cores for a split to be worth it.
    """
    cpus = allowed_cpus()
    if len(cpus) <= 2:
        return ""
    taken = set(ffmpeg_cpus())
    return ",".join(str(i) for i in cpus if i not in taken)
