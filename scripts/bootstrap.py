from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

# 检查 Python 3.13
# → 创建 .venv
# → 安装锁定依赖
# → 安装当前项目
# → 创建 .env
PROJECT_ROOT = Path(__file__).resolve().parents[1]
VENV_DIRECTORY = PROJECT_ROOT / ".venv"


def run(command: list[str]) -> None:
    """在项目根目录执行命令，失败时立即停止。"""
    print(f"\n执行：{' '.join(command)}", flush=True)
    subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        check=True,
    )


def get_venv_python() -> Path:
    """返回当前操作系统中虚拟环境的 Python 路径。"""
    if sys.platform == "win32":
        return VENV_DIRECTORY / "Scripts" / "python.exe"

    return VENV_DIRECTORY / "bin" / "python"


def create_environment_file() -> None:
    """首次初始化时根据示例创建本地环境变量文件。"""
    environment_file = PROJECT_ROOT / ".env"

    if environment_file.exists():
        print("\n.env 已存在，保留当前配置。")
        return

    example_file = PROJECT_ROOT / ".env.example"
    shutil.copyfile(example_file, environment_file)
    print("\n已根据 .env.example 创建 .env，请填写 API 密钥。")


def main() -> int:
    """创建虚拟环境并安装锁定的开发依赖。"""
    if sys.version_info[:2] != (3, 13):
        print(
            "需要使用 Python 3.13 执行初始化脚本，"
            f"当前版本为 {sys.version_info.major}.{sys.version_info.minor}。"
        )
        return 1

    try:
        if not VENV_DIRECTORY.exists():
            run(
                [
                    sys.executable,
                    "-m",
                    "venv",
                    str(VENV_DIRECTORY),
                ]
            )
        else:
            print("\n.venv 已存在，继续使用当前虚拟环境。")

        venv_python = get_venv_python()
        lock_file = (
            "requirements-dev.lock"
            if sys.platform == "win32"
            else "requirements-dev-linux.lock"
        )

        run(
            [
                str(venv_python),
                "-m",
                "pip",
                "install",
                "--require-hashes",
                "--requirement",
                lock_file,
            ]
        )

        run(
            [
                str(venv_python),
                "-m",
                "pip",
                "install",
                "--no-deps",
                "--no-build-isolation",
                "--editable",
                ".",
            ]
        )

        create_environment_file()
    except subprocess.CalledProcessError as exc:
        print(f"\n初始化失败，命令退出码：{exc.returncode}")
        return exc.returncode

    print("\n项目初始化完成。")
    print("请填写 .env，然后执行 start 命令启动服务。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
