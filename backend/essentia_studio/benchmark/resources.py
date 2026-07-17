from __future__ import annotations

import math
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ResourceLimits:
    memory_bytes: int | None
    cpu_count: int


def detect_resource_limits(root: Path = Path("/")) -> ResourceLimits:
    memory_found, memory_bytes = _memory_limit(root)
    if not memory_found:
        memory_bytes = _host_memory_bytes()

    available_cpus = _available_cpu_count()
    quota_cpus = _cpu_quota(root)
    cpu_count = min(available_cpus, quota_cpus) if quota_cpus is not None else available_cpus
    return ResourceLimits(memory_bytes=memory_bytes, cpu_count=max(1, cpu_count))


def recommend_workers(
    memory_limit: int | None,
    baseline_peak: int,
    worker_peak: int,
    cpu_count: int,
    safety_margin: float = 0.30,
    maximum: int = 64,
) -> int:
    cpu_cap = max(0, min(cpu_count, maximum))
    if cpu_cap == 0 or worker_peak <= 0:
        return 0
    if memory_limit is None:
        return cpu_cap

    usable = math.floor(memory_limit * (1 - safety_margin)) - baseline_peak
    memory_workers = max(0, math.floor(usable / worker_peak))
    return min(memory_workers, cpu_cap)


def _memory_limit(root: Path) -> tuple[bool, int | None]:
    v2_path = root / "sys/fs/cgroup/memory.max"
    if v2_path.is_file():
        value = _read(v2_path)
        return True, None if value == "max" else _positive_int(value)

    v1_path = root / "sys/fs/cgroup/memory/memory.limit_in_bytes"
    if v1_path.is_file():
        value = _positive_int(_read(v1_path))
        if value is None or value >= 1 << 60:
            return True, None
        return True, value
    return False, None


def _cpu_quota(root: Path) -> int | None:
    v2_path = root / "sys/fs/cgroup/cpu.max"
    if v2_path.is_file():
        quota, period = _read(v2_path).split(maxsplit=1)
        if quota == "max":
            return None
        return _quota_to_cpus(_positive_int(quota), _positive_int(period))

    quota_path = root / "sys/fs/cgroup/cpu/cpu.cfs_quota_us"
    period_path = root / "sys/fs/cgroup/cpu/cpu.cfs_period_us"
    if quota_path.is_file() and period_path.is_file():
        quota = _positive_int(_read(quota_path))
        period = _positive_int(_read(period_path))
        return _quota_to_cpus(quota, period)
    return None


def _quota_to_cpus(quota: int | None, period: int | None) -> int | None:
    if quota is None or period is None:
        return None
    return max(1, math.ceil(quota / period))


def _available_cpu_count() -> int:
    try:
        return max(1, len(os.sched_getaffinity(0)))
    except AttributeError:
        return max(1, os.cpu_count() or 1)


def _host_memory_bytes() -> int | None:
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        return pages * page_size if pages > 0 and page_size > 0 else None
    except (AttributeError, OSError, ValueError):
        return None


def _positive_int(value: str) -> int | None:
    try:
        parsed = int(value)
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()
