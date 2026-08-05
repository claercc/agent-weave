from __future__ import annotations

import subprocess
import sys

# 所有检查统一使用当前虚拟环境中的 Python。
COMMANDS: tuple[tuple[str, ...], ...] = (
    (
        sys.executable,
        "-m",
        "black",
        "--check",
        "app",
        "tests",
        "scripts",
        "main.py",
    ),
    (
        sys.executable,
        "-m",
        "flake8",
        "app",
        "tests",
        "scripts",
        "main.py",
    ),
    (
        sys.executable,
        "-m",
        "mypy",
        "app",
        "scripts",
        "main.py",
    ),
    (
        sys.executable,
        "-m",
        "pytest",
        "-q",
    ),
)


def main() -> int:
    """依次执行全部质量检查，任一失败时立即退出。"""
    for command in COMMANDS:
        print(f"\n执行检查：{' '.join(command)}", flush=True)

        result = subprocess.run(
            command,
            check=False,
        )

        if result.returncode != 0:
            print(f"\n检查失败，退出码：{result.returncode}")
            return result.returncode

    print("\n全部质量检查通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
