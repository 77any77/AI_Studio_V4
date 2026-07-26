from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import time
import zipfile
from datetime import datetime
from pathlib import Path

PROTECTED_NAMES = {"config", "projects", "assets", "logs", "exports", "user_data"}


def wait_for_process(pid: int, timeout: int = 60) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            os.kill(pid, 0)
        except OSError:
            return
        time.sleep(0.5)


def copy_update(source: Path, install_dir: Path) -> None:
    for item in source.iterdir():
        if item.name in PROTECTED_NAMES:
            continue
        destination = install_dir / item.name
        if item.is_dir():
            if destination.exists():
                shutil.rmtree(destination)
            shutil.copytree(item, destination)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, destination)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", required=True)
    parser.add_argument("--install-dir", required=True)
    parser.add_argument("--main-exe", required=True)
    parser.add_argument("--wait-pid", type=int, required=True)
    args = parser.parse_args()

    package = Path(args.package).resolve()
    install_dir = Path(args.install_dir).resolve()
    main_exe = install_dir / args.main_exe
    wait_for_process(args.wait_pid)

    work_dir = install_dir / "_update_work"
    extract_dir = work_dir / "extract"
    backup_dir = work_dir / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    try:
        if work_dir.exists():
            shutil.rmtree(work_dir)
        extract_dir.mkdir(parents=True, exist_ok=True)
        backup_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(package) as archive:
            archive.extractall(extract_dir)
        entries = list(extract_dir.iterdir())
        update_root = entries[0] if len(entries) == 1 and entries[0].is_dir() else extract_dir

        for item in install_dir.iterdir():
            if item.name in PROTECTED_NAMES or item.name == "_update_work":
                continue
            destination = backup_dir / item.name
            if item.is_dir():
                shutil.copytree(item, destination)
            else:
                shutil.copy2(item, destination)

        copy_update(update_root, install_dir)
        package.unlink(missing_ok=True)
        if main_exe.exists():
            subprocess.Popen([str(main_exe)], cwd=str(install_dir))
        return 0
    except Exception as exc:
        try:
            for item in install_dir.iterdir():
                if item.name in PROTECTED_NAMES or item.name == "_update_work":
                    continue
                shutil.rmtree(item) if item.is_dir() else item.unlink(missing_ok=True)
            for item in backup_dir.iterdir():
                destination = install_dir / item.name
                shutil.copytree(item, destination) if item.is_dir() else shutil.copy2(item, destination)
        except Exception:
            pass
        (install_dir / "update_error.log").write_text(f"更新失败：{exc}", encoding="utf-8")
        if main_exe.exists():
            subprocess.Popen([str(main_exe)], cwd=str(install_dir))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
