from __future__ import annotations

import argparse
import subprocess
import sys
import time
from collections.abc import Sequence


def commands_for(
    target: str,
    python: str = sys.executable,
    npm: str | None = None,
) -> list[list[str]]:
    npm_executable = npm or ("npm.cmd" if sys.platform == "win32" else "npm")
    backend = [
        python,
        "-m",
        "uvicorn",
        "essentia_studio.main:create_app",
        "--factory",
        "--reload",
        "--port",
        "8000",
    ]
    frontend = [npm_executable, "--prefix", "frontend", "run", "dev"]
    return {"backend": [backend], "frontend": [frontend], "all": [backend, frontend]}[target]


def stop_processes(processes: Sequence[subprocess.Popen[bytes]]) -> None:
    for process in processes:
        if process.poll() is None:
            process.terminate()

    for process in processes:
        if process.poll() is not None:
            continue
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def run(target: str) -> int:
    processes: list[subprocess.Popen[bytes]] = []
    try:
        for command in commands_for(target):
            processes.append(subprocess.Popen(command))
        while all(process.poll() is None for process in processes):
            time.sleep(0.2)
        return next(process.returncode or 0 for process in processes if process.poll() is not None)
    except KeyboardInterrupt:
        return 130
    finally:
        stop_processes(processes)


def main() -> int:
    parser = argparse.ArgumentParser(description="Start Essentia Studio development services.")
    parser.add_argument("target", choices=["backend", "frontend", "all"], nargs="?", default="all")
    arguments = parser.parse_args()
    return run(arguments.target)


if __name__ == "__main__":
    raise SystemExit(main())
