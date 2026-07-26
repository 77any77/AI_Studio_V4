from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Signal, Slot
from PySide6.QtWidgets import (
    QCheckBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPlainTextEdit, QProgressBar, QPushButton,
    QVBoxLayout, QWidget,
)

from ai_studio.services.update_service import (
    UpdateInfo, UpdateService, default_install_dir, find_updater_executable,
)
from ai_studio.version import APP_VERSION


class UpdateSignals(QObject):
    result = Signal(object)
    error = Signal(str)
    progress = Signal(int, int)
    finished = Signal()


class UpdateWorker(QRunnable):
    def __init__(self, function):
        super().__init__()
        self.function = function
        self.signals = UpdateSignals()

    @Slot()
    def run(self) -> None:
        try:
            self.signals.result.emit(self.function(self.signals))
        except Exception as exc:
            self.signals.error.emit(str(exc))
        finally:
            self.signals.finished.emit()


class UpdateCenterWidget(QWidget):
    def __init__(self, thread_pool, config_dir: Path, parent=None) -> None:
        super().__init__(parent)
        self.thread_pool = thread_pool
        self.config_dir = config_dir
        self.config_path = config_dir / "update_settings.json"
        self.update_info: UpdateInfo | None = None
        self.downloaded_file: Path | None = None
        self._build_ui()
        self._load_settings()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)
        title = QLabel("软件更新")
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        self.version_label = QLabel(f"当前版本：v{APP_VERSION}")
        self.version_label.setObjectName("infoCard")
        layout.addWidget(self.version_label)

        form = QFormLayout()
        self.release_api_edit = QLineEdit()
        self.release_api_edit.setPlaceholderText(
            "https://api.github.com/repos/用户名/AI_Studio_V4/releases/latest"
        )
        self.asset_pattern_edit = QLineEdit(r"AI-Studio-V4-Update.*\.zip$")
        form.addRow("Release API", self.release_api_edit)
        form.addRow("更新包匹配", self.asset_pattern_edit)
        layout.addLayout(form)

        option_row = QHBoxLayout()
        self.auto_check_box = QCheckBox("启动时自动检查更新")
        self.auto_download_box = QCheckBox("发现更新后自动下载")
        option_row.addWidget(self.auto_check_box)
        option_row.addWidget(self.auto_download_box)
        option_row.addStretch()
        layout.addLayout(option_row)

        buttons = QHBoxLayout()
        self.save_button = QPushButton("保存更新设置")
        self.check_button = QPushButton("检查更新")
        self.download_button = QPushButton("下载更新")
        self.install_button = QPushButton("立即安装并重启")
        self.download_button.setEnabled(False)
        self.install_button.setEnabled(False)
        self.save_button.clicked.connect(self._save_settings)
        self.check_button.clicked.connect(self.check_update)
        self.download_button.clicked.connect(self.download_update)
        self.install_button.clicked.connect(self.install_update)
        for button in (self.save_button, self.check_button, self.download_button, self.install_button):
            buttons.addWidget(button)
        buttons.addStretch()
        layout.addLayout(buttons)

        self.progress = QProgressBar()
        self.progress.hide()
        layout.addWidget(self.progress)
        self.status_label = QLabel("尚未检查更新。")
        self.status_label.setObjectName("stepSummary")
        layout.addWidget(self.status_label)
        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setReadOnly(True)
        self.notes_edit.setPlaceholderText("更新说明会显示在这里。")
        layout.addWidget(self.notes_edit, 1)

    def _load_settings(self) -> None:
        data = {}
        if self.config_path.exists():
            try:
                data = json.loads(self.config_path.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        self.release_api_edit.setText(str(data.get("release_api_url") or ""))
        self.asset_pattern_edit.setText(str(data.get("asset_pattern") or r"AI-Studio-V4-Update.*\.zip$"))
        self.auto_check_box.setChecked(bool(data.get("auto_check", True)))
        self.auto_download_box.setChecked(bool(data.get("auto_download", False)))

    def _save_settings(self) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "release_api_url": self.release_api_edit.text().strip(),
            "asset_pattern": self.asset_pattern_edit.text().strip(),
            "auto_check": self.auto_check_box.isChecked(),
            "auto_download": self.auto_download_box.isChecked(),
        }
        self.config_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        self.status_label.setText("更新设置已保存。")

    def should_auto_check(self) -> bool:
        return self.auto_check_box.isChecked()

    def _service(self) -> UpdateService:
        return UpdateService(
            APP_VERSION,
            self.release_api_edit.text().strip(),
            self.asset_pattern_edit.text().strip() or r"AI-Studio-V4-Update.*\.zip$",
        )

    def check_update(self, silent: bool = False) -> None:
        self._save_settings()
        worker = UpdateWorker(lambda signals: self._service().check_update())
        worker.signals.result.connect(lambda result: self._check_finished(result, silent))
        worker.signals.error.connect(lambda msg: self._failed(msg, silent))
        worker.signals.finished.connect(lambda: self._set_busy(False))
        self._set_busy(True, "正在检查更新……")
        self.thread_pool.start(worker)

    def _check_finished(self, update: UpdateInfo, silent: bool) -> None:
        self.update_info = update
        self.notes_edit.setPlainText(update.notes)
        if update.has_update:
            self.status_label.setText(f"发现新版本：v{update.latest_version}｜当前：v{update.current_version}")
            self.download_button.setEnabled(True)
            if self.auto_download_box.isChecked():
                self.download_update()
            elif not silent:
                QMessageBox.information(self, "发现新版本", f"发现 AI Studio v{update.latest_version}。")
        else:
            self.status_label.setText(f"当前已经是最新版本 v{update.current_version}。")
            if not silent:
                QMessageBox.information(self, "无需更新", "当前已经是最新版本。")

    def download_update(self) -> None:
        if self.update_info is None:
            self.check_update()
            return
        update = self.update_info
        service = self._service()

        def task(signals):
            return service.download_update(update, lambda done, total: signals.progress.emit(done, total))

        worker = UpdateWorker(task)
        worker.signals.progress.connect(self._download_progress)
        worker.signals.result.connect(self._download_finished)
        worker.signals.error.connect(lambda msg: self._failed(msg, False))
        worker.signals.finished.connect(lambda: self._set_busy(False))
        self.progress.show()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self._set_busy(True, "正在下载更新包……")
        self.thread_pool.start(worker)

    def _download_progress(self, done: int, total: int) -> None:
        if total <= 0:
            self.progress.setRange(0, 0)
            return
        percent = int(done * 100 / total)
        self.progress.setRange(0, 100)
        self.progress.setValue(percent)
        self.status_label.setText(f"正在下载更新包：{percent}%")

    def _download_finished(self, path: Path) -> None:
        self.downloaded_file = path
        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        self.install_button.setEnabled(True)
        self.status_label.setText(f"更新包已下载：{path.name}")

    def install_update(self) -> None:
        if self.downloaded_file is None:
            QMessageBox.warning(self, "没有更新包", "请先下载更新包。")
            return
        try:
            install_dir = default_install_dir()
            updater = find_updater_executable(install_dir)
        except Exception as exc:
            QMessageBox.critical(self, "无法启动更新器", str(exc))
            return
        if QMessageBox.question(self, "安装更新", "软件将关闭、安装更新并自动重新启动。\n是否继续？") != QMessageBox.Yes:
            return
        args = [
            str(updater), "--package", str(self.downloaded_file),
            "--install-dir", str(install_dir),
            "--main-exe", Path(os.sys.executable).name,
            "--wait-pid", str(os.getpid()),
        ]
        subprocess.Popen(
            args,
            cwd=str(install_dir),
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
            close_fds=True,
        )
        self.window().close()

    def _set_busy(self, busy: bool, message: str = "") -> None:
        self.save_button.setEnabled(not busy)
        self.check_button.setEnabled(not busy)
        self.download_button.setEnabled(not busy and self.update_info is not None and self.update_info.has_update)
        self.install_button.setEnabled(not busy and self.downloaded_file is not None)
        if message:
            self.status_label.setText(message)

    def _failed(self, message: str, silent: bool) -> None:
        self.status_label.setText(f"更新失败：{message}")
        if not silent:
            QMessageBox.critical(self, "更新失败", message)
