from os import cpu_count


def allowed_cpus():
    try:
        from os import sched_getaffinity

        cpus = sorted(sched_getaffinity(0))
        if cpus:
            return cpus
    except (ImportError, OSError):
        pass
    return list(range(cpu_count() or 1))


def cpu_layout():
    cpus = allowed_cpus()
    threads = max(1, len(cpus) // 2)
    cores = ",".join(str(i) for i in cpus[:threads])
    service = "" if len(cpus) <= 2 else ",".join(str(i) for i in cpus[threads:])
    return len(cpus), threads, cores, service
