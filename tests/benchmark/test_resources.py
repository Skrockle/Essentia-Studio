from pathlib import Path

from essentia_studio.benchmark.resources import (
    ResourceLimits,
    detect_resource_limits,
    recommend_workers,
)


def _write(root: Path, relative_path: str, value: str) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def test_reads_cgroup_v2_memory_and_cpu_quota(tmp_path: Path) -> None:
    _write(tmp_path, "sys/fs/cgroup/memory.max", "4294967296")
    _write(tmp_path, "sys/fs/cgroup/cpu.max", "200000 100000")

    assert detect_resource_limits(tmp_path) == ResourceLimits(4_294_967_296, 2)


def test_treats_v2_max_memory_as_unlimited(tmp_path: Path) -> None:
    _write(tmp_path, "sys/fs/cgroup/memory.max", "max")
    _write(tmp_path, "sys/fs/cgroup/cpu.max", "max 100000")

    limits = detect_resource_limits(tmp_path)

    assert limits.memory_bytes is None
    assert limits.cpu_count >= 1


def test_falls_back_to_cgroup_v1(tmp_path: Path) -> None:
    _write(tmp_path, "sys/fs/cgroup/memory/memory.limit_in_bytes", "2147483648")
    _write(tmp_path, "sys/fs/cgroup/cpu/cpu.cfs_quota_us", "150000")
    _write(tmp_path, "sys/fs/cgroup/cpu/cpu.cfs_period_us", "100000")

    assert detect_resource_limits(tmp_path) == ResourceLimits(2_147_483_648, 2)


def test_recommendation_reserves_memory_and_caps_cpu() -> None:
    assert recommend_workers(
        memory_limit=4_000,
        baseline_peak=400,
        worker_peak=900,
        cpu_count=8,
        safety_margin=0.30,
    ) == 2


def test_no_worker_when_one_does_not_fit() -> None:
    assert recommend_workers(1_000, 400, 900, 8, 0.30) == 0


def test_unlimited_memory_remains_capped_by_cpu_and_maximum() -> None:
    assert recommend_workers(None, 400, 900, 12, 0.30, maximum=6) == 6
