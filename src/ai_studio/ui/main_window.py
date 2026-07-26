from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
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
    QSpinBox,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ai_studio.models.config import (
    APIProfile,
    AppSettings,
    PROVIDER_PRESETS,
    TASK_LABELS,
)
from ai_studio.services.api_client import OpenAICompatibleClient
from ai_studio.services.settings_service import SettingsService


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("AI Studio V4")
        self.resize(1360, 860)

        self.settings_service = SettingsService()
        self.app_settings = self.settings_service.load()
        self.current_profile_id: str | None = None
        self._loading_profile = False

        self._build_ui()
        self._refresh_profile_list(select_first=True)
        self._refresh_route_combos()
        self._apply_style()

    def _build_ui(self) -> None:
        container = QWidget()
        self.setCentralWidget(container)
        root = QHBoxLayout(container)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.nav = QListWidget()
        self.nav.setFixedWidth(190)
        self.stack = QStackedWidget()

        pages = [
            ("项目首页", self._home_page()),
            ("小说导入", self._novel_page()),
            ("API 中心", self._api_page()),
        ]

        for title, page in pages:
            self.nav.addItem(title)
            self.stack.addWidget(page)

        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.nav.setCurrentRow(0)

        root.addWidget(self.nav)
        root.addWidget(self.stack, 1)

    def _page(self, title: str) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        heading = QLabel(title)
        heading.setObjectName("pageTitle")
        layout.addWidget(heading)
        return page, layout

    def _home_page(self) -> QWidget:
        page, layout = self._page("项目首页")
        info = QLabel(
            "AI Studio V4 多 API 路由版\n\n"
            "每个推理任务都可以使用不同 API。"
        )
        info.setWordWrap(True)
        info.setObjectName("infoCard")
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

    def _api_page(self) -> QWidget:
        page, layout = self._page("多 API 管理与任务路由")

        tabs = QTabWidget()
        tabs.addTab(self._profiles_tab(), "接口配置")
        tabs.addTab(self._routes_tab(), "任务分流")
        layout.addWidget(tabs, 1)
        return page

    def _profiles_tab(self) -> QWidget:
        tab = QWidget()
        root = QHBoxLayout(tab)
        root.setContentsMargins(12, 12, 12, 12)

        left = QVBoxLayout()
        self.profile_list = QListWidget()
        self.profile_list.currentRowChanged.connect(
            self._profile_selection_changed
        )
        left.addWidget(self.profile_list, 1)

        profile_buttons = QHBoxLayout()
        add_button = QPushButton("新增接口")
        add_button.clicked.connect(self._add_profile)
        delete_button = QPushButton("删除接口")
        delete_button.clicked.connect(self._delete_profile)
        profile_buttons.addWidget(add_button)
        profile_buttons.addWidget(delete_button)
        left.addLayout(profile_buttons)

        left_box = QWidget()
        left_box.setLayout(left)
        left_box.setMinimumWidth(260)
        left_box.setMaximumWidth(320)

        right = QVBoxLayout()
        form = QFormLayout()

        self.profile_name_edit = QLineEdit()
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(PROVIDER_PRESETS.keys())
        self.provider_combo.currentTextChanged.connect(
            self._provider_changed
        )

        self.base_url_edit = QLineEdit()
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)

        key_row = QHBoxLayout()
        key_row.addWidget(self.api_key_edit, 1)
        self.show_key_check = QCheckBox("显示")
        self.show_key_check.toggled.connect(self._toggle_key_visibility)
        key_row.addWidget(self.show_key_check)
        key_widget = QWidget()
        key_widget.setLayout(key_row)

        self.model_edit = QLineEdit()
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(10, 600)
        self.timeout_spin.setSuffix(" 秒")
        self.enabled_check = QCheckBox("启用此接口")

        form.addRow("配置名称", self.profile_name_edit)
        form.addRow("服务商", self.provider_combo)
        form.addRow("Base URL", self.base_url_edit)
        form.addRow("API Key", key_widget)
        form.addRow("模型", self.model_edit)
        form.addRow("超时", self.timeout_spin)
        form.addRow("", self.enabled_check)
        right.addLayout(form)

        action_row = QHBoxLayout()
        save_button = QPushButton("保存当前接口")
        save_button.clicked.connect(self._save_current_profile)
        test_button = QPushButton("测试当前接口")
        test_button.clicked.connect(self._test_current_profile)
        action_row.addWidget(save_button)
        action_row.addWidget(test_button)
        action_row.addStretch()
        right.addLayout(action_row)

        note = QLabel(
            "说明：可以建立多个接口配置。"
            "例如 DeepSeek 用于故事分析，OpenAI 用于导演分镜，"
            "Ollama 用于本地批量任务。"
        )
        note.setWordWrap(True)
        note.setObjectName("infoCard")
        right.addWidget(note)
        right.addStretch()

        right_box = QWidget()
        right_box.setLayout(right)

        root.addWidget(left_box)
        root.addWidget(right_box, 1)
        return tab

    def _routes_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(18, 18, 18, 18)

        intro = QLabel(
            "为每个推理任务指定 API。后续各引擎会自动按这里的规则调用。"
        )
        intro.setWordWrap(True)
        intro.setObjectName("infoCard")
        layout.addWidget(intro)

        self.route_combos: dict[str, QComboBox] = {}
        form = QFormLayout()
        for task_key, label in TASK_LABELS.items():
            combo = QComboBox()
            self.route_combos[task_key] = combo
            form.addRow(label, combo)
        layout.addLayout(form)

        save_button = QPushButton("保存任务路由")
        save_button.clicked.connect(self._save_routes)
        layout.addWidget(save_button, alignment=Qt.AlignLeft)
        layout.addStretch()
        return tab

    def _refresh_profile_list(self, select_first: bool = False) -> None:
        selected_id = self.current_profile_id
        self.profile_list.blockSignals(True)
        self.profile_list.clear()

        for profile in self.app_settings.profiles:
            status = "" if profile.enabled else "（停用）"
            self.profile_list.addItem(
                f"{profile.name} · {profile.provider}{status}"
            )

        self.profile_list.blockSignals(False)

        target_row = 0
        if selected_id:
            for index, profile in enumerate(self.app_settings.profiles):
                if profile.profile_id == selected_id:
                    target_row = index
                    break

        if self.app_settings.profiles and (select_first or selected_id):
            self.profile_list.setCurrentRow(target_row)
        elif self.app_settings.profiles:
            self.profile_list.setCurrentRow(0)

    def _profile_selection_changed(self, row: int) -> None:
        if row < 0 or row >= len(self.app_settings.profiles):
            return
        profile = self.app_settings.profiles[row]
        self.current_profile_id = profile.profile_id
        self._load_profile(profile)

    def _load_profile(self, profile: APIProfile) -> None:
        self._loading_profile = True
        try:
            self.profile_name_edit.setText(profile.name)
            self.provider_combo.setCurrentText(profile.provider)
            self.base_url_edit.setText(profile.base_url)
            self.api_key_edit.setText(profile.api_key)
            self.model_edit.setText(profile.model)
            self.timeout_spin.setValue(profile.timeout_seconds)
            self.enabled_check.setChecked(profile.enabled)
        finally:
            self._loading_profile = False

    def _provider_changed(self, provider: str) -> None:
        if self._loading_profile:
            return
        preset = PROVIDER_PRESETS.get(provider)
        if not preset:
            return
        self.base_url_edit.setText(preset["base_url"])
        self.model_edit.setText(preset["model"])

    def _toggle_key_visibility(self, checked: bool) -> None:
        self.api_key_edit.setEchoMode(
            QLineEdit.Normal if checked else QLineEdit.Password
        )

    def _add_profile(self) -> None:
        number = len(self.app_settings.profiles) + 1
        profile = APIProfile(name=f"接口 {number}")
        self.app_settings.profiles.append(profile)
        self.current_profile_id = profile.profile_id
        self._refresh_profile_list()
        self._refresh_route_combos()

    def _delete_profile(self) -> None:
        row = self.profile_list.currentRow()
        if row < 0 or row >= len(self.app_settings.profiles):
            return
        if len(self.app_settings.profiles) <= 1:
            QMessageBox.warning(
                self,
                "无法删除",
                "至少需要保留一个 API 接口配置。",
            )
            return

        profile = self.app_settings.profiles[row]
        answer = QMessageBox.question(
            self,
            "删除接口",
            f"确定删除“{profile.name}”吗？",
        )
        if answer != QMessageBox.Yes:
            return

        self.app_settings.profiles.pop(row)
        fallback_id = self.app_settings.profiles[0].profile_id
        for task_key, profile_id in list(
            self.app_settings.task_routes.items()
        ):
            if profile_id == profile.profile_id:
                self.app_settings.task_routes[task_key] = fallback_id

        self.current_profile_id = fallback_id
        self.settings_service.save(self.app_settings)
        self._refresh_profile_list()
        self._refresh_route_combos()

    def _current_profile_from_form(self) -> APIProfile:
        profile_id = self.current_profile_id or APIProfile().profile_id
        return APIProfile(
            profile_id=profile_id,
            name=self.profile_name_edit.text().strip() or "未命名接口",
            provider=self.provider_combo.currentText(),
            base_url=self.base_url_edit.text().strip(),
            api_key=self.api_key_edit.text(),
            model=self.model_edit.text().strip(),
            timeout_seconds=self.timeout_spin.value(),
            enabled=self.enabled_check.isChecked(),
        )

    def _save_current_profile(self) -> None:
        profile = self._current_profile_from_form()
        for index, existing in enumerate(self.app_settings.profiles):
            if existing.profile_id == profile.profile_id:
                self.app_settings.profiles[index] = profile
                break
        else:
            self.app_settings.profiles.append(profile)

        self.current_profile_id = profile.profile_id
        self.settings_service.save(self.app_settings)
        self._refresh_profile_list()
        self._refresh_route_combos()
        QMessageBox.information(
            self,
            "保存成功",
            f"接口“{profile.name}”已保存。",
        )

    def _test_current_profile(self) -> None:
        profile = self._current_profile_from_form()
        try:
            result = OpenAICompatibleClient(profile).test_connection()
            QMessageBox.information(
                self,
                "连接成功",
                f"接口：{result.profile_name}\n"
                f"模型：{result.model}\n"
                f"耗时：{result.elapsed_seconds:.2f} 秒\n"
                f"返回：{result.text}",
            )
        except Exception as exc:
            QMessageBox.critical(self, "连接失败", str(exc))

    def _refresh_route_combos(self) -> None:
        profile_items = [
            (profile.name, profile.profile_id)
            for profile in self.app_settings.profiles
            if profile.enabled
        ]
        if not profile_items:
            profile_items = [
                (profile.name, profile.profile_id)
                for profile in self.app_settings.profiles
            ]

        for task_key, combo in getattr(
            self, "route_combos", {}
        ).items():
            current_id = self.app_settings.task_routes.get(task_key, "")
            combo.blockSignals(True)
            combo.clear()
            for name, profile_id in profile_items:
                combo.addItem(name, profile_id)

            selected_index = combo.findData(current_id)
            combo.setCurrentIndex(
                selected_index if selected_index >= 0 else 0
            )
            combo.blockSignals(False)

    def _save_routes(self) -> None:
        for task_key, combo in self.route_combos.items():
            profile_id = combo.currentData()
            if profile_id:
                self.app_settings.task_routes[task_key] = str(profile_id)

        self.settings_service.save(self.app_settings)
        QMessageBox.information(
            self,
            "保存成功",
            "所有任务的 API 路由已保存。",
        )

    def _import_txt(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "导入小说",
            "",
            "文本文件 (*.txt)",
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

        QMessageBox.warning(
            self,
            "导入失败",
            "无法识别文本编码。",
        )

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QWidget {
                background:#111722;
                color:#edf2fa;
                font-size:14px;
            }
            QListWidget {
                background:#171f2d;
                border:0;
                padding:14px;
            }
            QListWidget::item {
                min-height:42px;
                padding-left:10px;
                border-radius:7px;
            }
            QListWidget::item:selected {
                background:#2d3d58;
            }
            QLineEdit, QPlainTextEdit, QComboBox, QSpinBox {
                background:#182130;
                border:1px solid #35445e;
                border-radius:7px;
                padding:8px;
            }
            QPushButton {
                background:#3567d4;
                border:0;
                border-radius:7px;
                padding:9px 16px;
                font-weight:600;
            }
            QPushButton:hover {
                background:#4276e5;
            }
            QLabel#pageTitle {
                font-size:24px;
                font-weight:700;
            }
            QLabel#infoCard {
                background:#182130;
                border:1px solid #35445e;
                border-radius:8px;
                padding:14px;
            }
            QTabWidget::pane {
                border:1px solid #35445e;
            }
            QTabBar::tab {
                background:#182130;
                padding:9px 16px;
            }
            QTabBar::tab:selected {
                background:#2d3d58;
            }
            """
        )
