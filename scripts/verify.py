from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def verification_commands(
    python: str = sys.executable,
    npm: str | None = None,
) -> list[list[str]]:
    npm_executable = npm or ("npm.cmd" if sys.platform == "win32" else "npm")
    return [
        [python, "-m", "pytest", "-q"],
        [python, "-m", "ruff", "check", "backend", "tests", "scripts"],
        [npm_executable, "--prefix", "frontend", "run", "lint"],
        [npm_executable, "--prefix", "frontend", "test"],
        [npm_executable, "--prefix", "frontend", "run", "typecheck"],
        [npm_executable, "--prefix", "frontend", "run", "build"],
    ]


def main() -> int:
    for command in verification_commands():
        print(f"\n==> {' '.join(command)}", flush=True)
        result = subprocess.run(command, cwd=PROJECT_ROOT, check=False)
        if result.returncode:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
