from __future__ import annotations

import shutil
import traceback
from pathlib import Path

PATCH_ROOT = Path(__file__).resolve().parent
LOG_PATH = PATCH_ROOT / "安装更新中心日志.txt"


def is_project_root(path: Path) -> bool:
    return (
        (path / "src" / "ai_studio" / "ui" / "main_window.py").is_file()
        and (path / "src" / "ai_studio").is_dir()
    )


def find_project_root() -> Path | None:
    for candidate in [PATCH_ROOT, PATCH_ROOT.parent, Path.cwd(), Path.cwd().parent]:
        candidate = candidate.resolve()
        if is_project_root(candidate):
            return candidate
    return None


def ask_project_root() -> Path:
    print()
    print("没有自动找到 AI_Studio_V4 项目目录。")
    print("请复制项目文件夹完整路径，例如：D:\\AI_Studio_V4")
    while True:
        raw = input("请输入 AI_Studio_V4 项目路径：").strip().strip('"')
        path = Path(raw).expanduser()
        if is_project_root(path):
            return path.resolve()
        print("目录无效，应存在：src\\ai_studio\\ui\\main_window.py")


def copy_tree(source: Path, destination: Path) -> None:
    for item in source.rglob("*"):
        if not item.is_file():
            continue
        if "__pycache__" in item.parts or item.suffix == ".pyc":
            continue
        target = destination / item.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        if item.resolve() == target.resolve():
            continue
        shutil.copy2(item, target)


def replace_once(text: str, old: str, new: str, label: str, required: bool = True) -> str:
    if new in text:
        print(f"[跳过] {label} 已安装")
        return text
    if old not in text:
        if required:
            raise RuntimeError(
                f"无法安装‘{label}’：main_window.py 中没有找到预期代码。"
                "请确认已安装 v0.5 单页生产流水线。"
            )
        print(f"[跳过] 未找到可选位置：{label}")
        return text
    print(f"[安装] {label}")
    return text.replace(old, new, 1)


def patch_main_window(path: Path) -> None:
    backup = path.with_suffix(".py.v061_backup")
    if not backup.exists():
        shutil.copy2(path, backup)
        print(f"[备份] {backup.name}")

    text = path.read_text(encoding="utf-8")
    marker = "from ai_studio.ui.worker import Worker\n"
    import_line = "from ai_studio.ui.update_center import UpdateCenterWidget\n"
    if import_line not in text:
        if marker not in text:
            raise RuntimeError("main_window.py 中找不到 Worker 导入语句。")
        text = text.replace(marker, marker + import_line, 1)
        print("[安装] 更新中心导入")
    else:
        print("[跳过] 更新中心导入已存在")

    old_nav = 'self.nav.addItems([\n            "生产线",\n            "API 设置",\n        ])'
    new_nav = 'self.nav.addItems([\n            "生产线",\n            "API 设置",\n            "软件更新",\n        ])'
    text = replace_once(text, old_nav, new_nav, "左侧软件更新菜单")

    old_stack = 'self.stack.addWidget(self._production_page())\n        self.stack.addWidget(self._api_page())'
    new_stack = 'self.stack.addWidget(self._production_page())\n        self.stack.addWidget(self._api_page())\n        self.update_center = UpdateCenterWidget(\n            self.thread_pool,\n            self.settings_service.path.parent,\n            self,\n        )\n        self.stack.addWidget(self.update_center)'
    text = replace_once(text, old_stack, new_stack, "更新中心页面")

    old_ready = 'self.statusBar().showMessage("准备就绪")'
    new_ready = 'self.statusBar().showMessage("准备就绪")\n        if getattr(self, "update_center", None):\n            if self.update_center.should_auto_check():\n                from PySide6.QtCore import QTimer\n                QTimer.singleShot(\n                    1800,\n                    lambda: self.update_center.check_update(\n                        silent=True\n                    ),\n                )'
    text = replace_once(text, old_ready, new_ready, "启动自动检查更新", required=False)

    compile(text, str(path), "exec")
    path.write_text(text, encoding="utf-8")
    print("[检查] main_window.py 语法通过")


def install(target: Path) -> None:
    print(f"补丁目录：{PATCH_ROOT}")
    print(f"项目目录：{target}")
    copy_tree(PATCH_ROOT / "src", target / "src")
    copy_tree(PATCH_ROOT / "updater", target / "updater")
    copy_tree(PATCH_ROOT / ".github", target / ".github")
    copy_tree(PATCH_ROOT / "tests", target / "tests")
    patch_main_window(target / "src" / "ai_studio" / "ui" / "main_window.py")
    print("=" * 58)
    print("更新中心安装完成。")
    print("GitHub Desktop 提交说明：Fix built-in updater installation")
    print("=" * 58)


def main() -> int:
    try:
        project_root = find_project_root() or ask_project_root()
        install(project_root)
        LOG_PATH.write_text(f"安装成功\n项目目录：{project_root}\n", encoding="utf-8")
        return 0
    except Exception:
        details = traceback.format_exc()
        LOG_PATH.write_text(details, encoding="utf-8")
        print("=" * 58)
        print("安装失败：")
        print(details)
        print(f"错误日志：{LOG_PATH}")
        print("=" * 58)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
