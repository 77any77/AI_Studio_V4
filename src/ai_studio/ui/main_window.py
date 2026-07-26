from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ai_studio.models.config import APISettings
from ai_studio.services.api_client import OpenAICompatibleClient
from ai_studio.services.settings_service import SettingsService


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("AI Studio V4")
        self.resize(1280, 800)
        self.settings_service = SettingsService()
        self._build_ui()
        self._load_settings()

    def _build_ui(self) -> None:
        container = QWidget()
        self.setCentralWidget(container)
        root = QHBoxLayout(container)
        root.setContentsMargins(0, 0, 0, 0)

        self.nav = QListWidget()
        self.nav.setFixedWidth(190)
        self.stack = QStackedWidget()

        pages = [
            ("项目首页", self._home_page()),
            ("小说导入", self._novel_page()),
            ("API 设置", self._settings_page()),
        ]
        for title, page in pages:
            self.nav.addItem(title)
            self.stack.addWidget(page)

        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.nav.setCurrentRow(0)
        root.addWidget(self.nav)
        root.addWidget(self.stack, 1)

        self.setStyleSheet(
            '''
            QWidget { background:#111722; color:#edf2fa; font-size:14px; }
            QListWidget { background:#171f2d; border:0; padding:14px; }
            QListWidget::item { height:44px; padding-left:10px; border-radius:7px; }
            QListWidget::item:selected { background:#2d3d58; }
            QLineEdit, QPlainTextEdit {
                background:#182130; border:1px solid #35445e;
                border-radius:7px; padding:8px;
            }
            QPushButton {
                background:#3567d4; border:0; border-radius:7px;
                padding:9px 16px; font-weight:600;
            }
            QPushButton:hover { background:#4276e5; }
            '''
        )

    def _page(self, title: str) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        heading = QLabel(title)
        heading.setStyleSheet("font-size:24px;font-weight:700")
        layout.addWidget(heading)
        return page, layout

    def _home_page(self) -> QWidget:
        page, layout = self._page("项目首页")
        info = QLabel(
            "AI Studio V4 正式工程版。当前里程碑："
            "稳定启动、配置持久化、小说导入和 API 连接。"
        )
        info.setWordWrap(True)
        layout.addWidget(info)
        layout.addStretch()
        return page

    def _novel_page(self) -> QWidget:
        page, layout = self._page("小说导入")
        row = QHBoxLayout()
        button = QPushButton("导入 TXT")
        button.clicked.connect(self._import_txt)
        row.addWidget(button)
        row.addStretch()
        layout.addLayout(row)
        self.novel_edit = QPlainTextEdit()
        self.novel_edit.setPlaceholderText("粘贴小说正文或导入 TXT 文件")
        layout.addWidget(self.novel_edit, 1)
        return page

    def _settings_page(self) -> QWidget:
        page, layout = self._page("API 设置")
        form = QFormLayout()

        self.provider_edit = QLineEdit()
        self.base_url_edit = QLineEdit()
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.model_edit = QLineEdit()

        form.addRow("服务商", self.provider_edit)
        form.addRow("Base URL", self.base_url_edit)
        form.addRow("API Key", self.api_key_edit)
        form.addRow("模型", self.model_edit)
        layout.addLayout(form)

        row = QHBoxLayout()
        save_button = QPushButton("保存设置")
        save_button.clicked.connect(self._save_settings)
        test_button = QPushButton("测试连接")
        test_button.clicked.connect(self._test_connection)
        row.addWidget(save_button)
        row.addWidget(test_button)
        row.addStretch()
        layout.addLayout(row)
        layout.addStretch()
        return page

    def _load_settings(self) -> None:
        value = self.settings_service.load()
        self.provider_edit.setText(value.provider)
        self.base_url_edit.setText(value.base_url)
        self.api_key_edit.setText(value.api_key)
        self.model_edit.setText(value.model)

    def _current_settings(self) -> APISettings:
        return APISettings(
            provider=self.provider_edit.text().strip(),
            base_url=self.base_url_edit.text().strip(),
            api_key=self.api_key_edit.text(),
            model=self.model_edit.text().strip(),
        )

    def _save_settings(self) -> None:
        self.settings_service.save(self._current_settings())
        QMessageBox.information(self, "保存成功", "API 设置已保存在本机。")

    def _test_connection(self) -> None:
        try:
            settings = self._current_settings()
            self.settings_service.save(settings)
            result = OpenAICompatibleClient(settings).test_connection()
            QMessageBox.information(self, "连接成功", result)
        except Exception as exc:
            QMessageBox.critical(self, "连接失败", str(exc))

    def _import_txt(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self, "导入小说", "", "文本文件 (*.txt)"
        )
        if not filename:
            return
        raw = Path(filename).read_bytes()
        for encoding in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
            try:
                self.novel_edit.setPlainText(raw.decode(encoding))
                return
            except UnicodeDecodeError:
                continue
        QMessageBox.warning(self, "导入失败", "无法识别文本编码。")
