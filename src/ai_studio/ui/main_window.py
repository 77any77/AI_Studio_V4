from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QThreadPool, Qt
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
    QProgressBar,
    QSpinBox,
    QStackedWidget,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ai_studio.core.paths import logs_dir
from ai_studio.models.config import (
    APIProfile,
    PROVIDER_PRESETS,
    TASK_LABELS,
)
from ai_studio.services.api_client import OpenAICompatibleClient
from ai_studio.services.director_engine import (
    DirectorEngine,
    PromptCompileResult,
    StoryboardResult,
)
from ai_studio.services.novel_pipeline import NovelPipeline, PipelineResult
from ai_studio.services.router_service import APIRouterService
from ai_studio.services.settings_service import SettingsService
from ai_studio.ui.worker import Worker


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("AI Studio V4")
        self.resize(1460, 920)

        self.thread_pool = QThreadPool.globalInstance()
        self.settings_service = SettingsService()
        self.app_settings = self.settings_service.load()
        self.current_profile_id: str | None = None
        self._loading_profile = False

        self.pipeline_result: PipelineResult | None = None
        self.storyboard_result: StoryboardResult | None = None
        self.prompt_result: PromptCompileResult | None = None

        self._build_ui()
        self._refresh_profile_list(select_first=True)
        self._refresh_route_combos()
        self._apply_style()
        self.statusBar().showMessage("准备就绪")

    def _build_ui(self) -> None:
        container = QWidget()
        self.setCentralWidget(container)
        root = QHBoxLayout(container)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.nav = QListWidget()
        self.nav.setFixedWidth(205)
        self.stack = QStackedWidget()

        pages = [
            ("项目首页", self._home_page()),
            ("小说工作台", self._novel_page()),
            ("资产分析", self._result_page()),
            ("导演分镜", self._storyboard_page()),
            ("视频 Prompt", self._prompt_page()),
            ("API 中心", self._api_page()),
        ]

        for title, page in pages:
            self.nav.addItem(title)
            self.stack.addWidget(page)

        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.nav.setCurrentRow(0)

        root.addWidget(self.nav)
        root.addWidget(self.stack, 1)

        status = QStatusBar()
        self.setStatusBar(status)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setFixedWidth(190)
        self.progress.hide()
        status.addPermanentWidget(self.progress)

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
            "当前生产链路：\n\n"
            "小说导入 → 故事分析 → 人物/场景/道具资产 → "
            "导演分镜 → Seedance视频Prompt\n\n"
            "各模块可以使用不同API。"
        )
        info.setWordWrap(True)
        info.setObjectName("infoCard")
        layout.addWidget(info)
        layout.addStretch()
        return page

    def _novel_page(self) -> QWidget:
        page, layout = self._page("小说工作台")

        toolbar = QHBoxLayout()
        import_button = QPushButton("导入 TXT")
        import_button.clicked.connect(self._import_txt)
        clear_button = QPushButton("清空")
        clear_button.clicked.connect(self._clear_novel)
        analyze_button = QPushButton("开始完整分析")
        analyze_button.clicked.connect(self._run_full_pipeline)

        toolbar.addWidget(import_button)
        toolbar.addWidget(clear_button)
        toolbar.addWidget(analyze_button)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.novel_stats = QLabel("字符：0")
        layout.addWidget(self.novel_stats)

        self.novel_edit = QPlainTextEdit()
        self.novel_edit.setPlaceholderText(
            "导入或粘贴小说正文，然后点击“开始完整分析”。"
        )
        self.novel_edit.textChanged.connect(self._update_novel_stats)
        layout.addWidget(self.novel_edit, 1)
        return page

    def _result_page(self) -> QWidget:
        page, layout = self._page("故事与资产分析")

        self.result_tabs = QTabWidget()
        self.analysis_view = self._readonly_editor()
        self.characters_view = self._readonly_editor()
        self.scenes_view = self._readonly_editor()
        self.props_view = self._readonly_editor()
        self.raw_view = self._readonly_editor()

        self.result_tabs.addTab(self.analysis_view, "故事分析")
        self.result_tabs.addTab(self.characters_view, "人物资产")
        self.result_tabs.addTab(self.scenes_view, "场景资产")
        self.result_tabs.addTab(self.props_view, "道具资产")
        self.result_tabs.addTab(self.raw_view, "原始结果")
        layout.addWidget(self.result_tabs, 1)
        return page

    def _storyboard_page(self) -> QWidget:
        page, layout = self._page("Director Engine · 自动导演分镜")

        toolbar = QHBoxLayout()
        generate_button = QPushButton("生成导演分镜")
        generate_button.clicked.connect(self._run_storyboard)
        export_button = QPushButton("导出分镜 JSON")
        export_button.clicked.connect(self._export_storyboard)
        toolbar.addWidget(generate_button)
        toolbar.addWidget(export_button)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.storyboard_summary = QLabel(
            "尚未生成分镜。请先完成小说资产分析。"
        )
        self.storyboard_summary.setObjectName("infoCard")
        layout.addWidget(self.storyboard_summary)

        self.storyboard_view = self._readonly_editor()
        layout.addWidget(self.storyboard_view, 1)
        return page

    def _prompt_page(self) -> QWidget:
        page, layout = self._page("视频 Prompt 编译器")

        toolbar = QHBoxLayout()
        compile_button = QPushButton("编译 Seedance Prompt")
        compile_button.clicked.connect(self._run_prompt_compile)
        export_json = QPushButton("导出 Prompt JSON")
        export_json.clicked.connect(self._export_prompts_json)
        export_text = QPushButton("导出 Prompt TXT")
        export_text.clicked.connect(self._export_prompts_text)
        toolbar.addWidget(compile_button)
        toolbar.addWidget(export_json)
        toolbar.addWidget(export_text)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.prompt_summary = QLabel(
            "尚未编译视频Prompt。请先生成导演分镜。"
        )
        self.prompt_summary.setObjectName("infoCard")
        layout.addWidget(self.prompt_summary)

        self.prompt_view = self._readonly_editor()
        layout.addWidget(self.prompt_view, 1)
        return page

    def _readonly_editor(self) -> QPlainTextEdit:
        editor = QPlainTextEdit()
        editor.setReadOnly(True)
        return editor

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
            "导演分镜和视频Prompt可以指定不同模型。"
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

    def _run_full_pipeline(self) -> None:
        novel = self.novel_edit.toPlainText().strip()
        if not novel:
            QMessageBox.warning(
                self, "缺少小说", "请先导入或粘贴小说正文。"
            )
            return

        self.app_settings = self.settings_service.load()
        pipeline = NovelPipeline(APIRouterService(self.app_settings))
        self._start_worker(
            lambda: pipeline.run_all(novel),
            self._pipeline_finished,
            "正在进行故事分析与资产提取……",
        )

    def _pipeline_finished(self, result: PipelineResult) -> None:
        self.pipeline_result = result
        self.storyboard_result = None
        self.prompt_result = None

        self.analysis_view.setPlainText(
            json.dumps(result.analysis, ensure_ascii=False, indent=2)
        )
        self.characters_view.setPlainText(
            json.dumps(result.characters, ensure_ascii=False, indent=2)
        )
        self.scenes_view.setPlainText(
            json.dumps(result.scenes, ensure_ascii=False, indent=2)
        )
        self.props_view.setPlainText(
            json.dumps(result.props, ensure_ascii=False, indent=2)
        )
        self.raw_view.setPlainText(
            json.dumps(result.raw_results, ensure_ascii=False, indent=2)
        )
        self.storyboard_view.clear()
        self.prompt_view.clear()
        self.storyboard_summary.setText(
            "资产分析已完成，可以生成导演分镜。"
        )
        self.prompt_summary.setText(
            "请先生成导演分镜。"
        )
        self.nav.setCurrentRow(2)

        QMessageBox.information(
            self,
            "分析完成",
            f"人物 {len(result.characters)} 个\n"
            f"场景 {len(result.scenes)} 个\n"
            f"道具 {len(result.props)} 个",
        )

    def _run_storyboard(self) -> None:
        if self.pipeline_result is None:
            QMessageBox.warning(
                self,
                "缺少资产",
                "请先完成小说的故事与资产分析。",
            )
            return

        novel = self.novel_edit.toPlainText().strip()
        router = APIRouterService(self.settings_service.load())
        engine = DirectorEngine(router)
        result = self.pipeline_result

        self._start_worker(
            lambda: engine.create_storyboard(
                novel=novel,
                analysis=result.analysis,
                characters=result.characters,
                scenes=result.scenes,
                props=result.props,
            ),
            self._storyboard_finished,
            "Director Engine 正在生成分镜……",
        )

    def _storyboard_finished(
        self,
        result: StoryboardResult,
    ) -> None:
        self.storyboard_result = result
        self.prompt_result = None

        display = {
            "episode_title": result.episode_title,
            "total_duration": result.total_duration,
            "shots": result.shots,
        }
        self.storyboard_view.setPlainText(
            json.dumps(display, ensure_ascii=False, indent=2)
        )
        self.storyboard_summary.setText(
            f"标题：{result.episode_title}　"
            f"镜头：{len(result.shots)} 个　"
            f"总时长：{result.total_duration} 秒"
        )
        self.prompt_summary.setText(
            "导演分镜已生成，可以编译视频Prompt。"
        )
        self.nav.setCurrentRow(3)

        QMessageBox.information(
            self,
            "分镜完成",
            f"共生成 {len(result.shots)} 个镜头，"
            f"总时长 {result.total_duration} 秒。",
        )

    def _run_prompt_compile(self) -> None:
        if self.storyboard_result is None:
            QMessageBox.warning(
                self,
                "缺少分镜",
                "请先生成导演分镜。",
            )
            return
        if self.pipeline_result is None:
            QMessageBox.warning(
                self,
                "缺少资产",
                "人物、场景和道具资产不存在。",
            )
            return

        router = APIRouterService(self.settings_service.load())
        engine = DirectorEngine(router)
        assets = self.pipeline_result
        storyboard = self.storyboard_result

        self._start_worker(
            lambda: engine.compile_video_prompts(
                storyboard=storyboard,
                characters=assets.characters,
                scenes=assets.scenes,
                props=assets.props,
            ),
            self._prompt_finished,
            "正在编译 Seedance 视频 Prompt……",
        )

    def _prompt_finished(
        self,
        result: PromptCompileResult,
    ) -> None:
        self.prompt_result = result
        self.prompt_view.setPlainText(
            json.dumps(
                {"prompts": result.prompts},
                ensure_ascii=False,
                indent=2,
            )
        )
        self.prompt_summary.setText(
            f"已编译 {len(result.prompts)} 条视频Prompt。"
        )
        self.nav.setCurrentRow(4)

        QMessageBox.information(
            self,
            "编译完成",
            f"已生成 {len(result.prompts)} 条视频Prompt。",
        )

    def _start_worker(
        self,
        function,
        on_result,
        message: str,
    ) -> None:
        worker = Worker(function)
        worker.signals.result.connect(on_result)
        worker.signals.error.connect(self._operation_failed)
        worker.signals.finished.connect(self._operation_stopped)

        self._set_busy(True, message)
        self.thread_pool.start(worker)

    def _operation_failed(self, details: str) -> None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = logs_dir() / f"operation_{timestamp}.log"
        path.write_text(details, encoding="utf-8")

        last_line = (
            details.strip().splitlines()[-1]
            if details.strip()
            else "未知错误"
        )
        QMessageBox.critical(
            self,
            "操作失败",
            f"{last_line}\n\n详细日志：\n{path}",
        )

    def _operation_stopped(self) -> None:
        self._set_busy(False, "操作完成")

    def _set_busy(self, busy: bool, message: str) -> None:
        self.progress.setVisible(busy)
        self.nav.setEnabled(not busy)
        self.statusBar().showMessage(message)

    def _export_storyboard(self) -> None:
        if self.storyboard_result is None:
            QMessageBox.warning(
                self, "没有内容", "当前没有可导出的分镜。"
            )
            return

        default_name = (
            f"{self.storyboard_result.episode_title}_导演分镜.json"
        )
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "导出导演分镜",
            default_name,
            "JSON文件 (*.json)",
        )
        if not filename:
            return

        data = {
            "episode_title": self.storyboard_result.episode_title,
            "total_duration": self.storyboard_result.total_duration,
            "shots": self.storyboard_result.shots,
        }
        Path(filename).write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        QMessageBox.information(
            self, "导出完成", f"已保存到：\n{filename}"
        )

    def _export_prompts_json(self) -> None:
        if self.prompt_result is None:
            QMessageBox.warning(
                self, "没有内容", "当前没有可导出的Prompt。"
            )
            return

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "导出视频Prompt",
            "Seedance_Prompts.json",
            "JSON文件 (*.json)",
        )
        if not filename:
            return

        Path(filename).write_text(
            json.dumps(
                {"prompts": self.prompt_result.prompts},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        QMessageBox.information(
            self, "导出完成", f"已保存到：\n{filename}"
        )

    def _export_prompts_text(self) -> None:
        if self.prompt_result is None:
            QMessageBox.warning(
                self, "没有内容", "当前没有可导出的Prompt。"
            )
            return

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "导出视频Prompt",
            "Seedance_Prompts.txt",
            "文本文件 (*.txt)",
        )
        if not filename:
            return

        blocks = []
        for item in self.prompt_result.prompts:
            blocks.append(
                f"【{item.get('shot_id', '')}】"
                f" 时长：{item.get('duration', '')}秒\n"
                f"{item.get('prompt', '')}\n"
                f"负面约束：{item.get('negative_prompt', '')}\n"
                f"连续性：{item.get('continuity_reference', '')}\n"
            )

        Path(filename).write_text(
            "\n".join(blocks),
            encoding="utf-8",
        )
        QMessageBox.information(
            self, "导出完成", f"已保存到：\n{filename}"
        )

    def _update_novel_stats(self) -> None:
        text = self.novel_edit.toPlainText()
        non_space = len("".join(text.split()))
        self.novel_stats.setText(
            f"字符：{len(text):,}　非空字符：{non_space:,}"
        )

    def _clear_novel(self) -> None:
        self.novel_edit.clear()

    def _import_txt(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "导入小说",
            "",
            "文本文件 (*.txt);;所有文件 (*.*)",
        )
        if not filename:
            return

        raw = Path(filename).read_bytes()
        for encoding in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
            try:
                self.novel_edit.setPlainText(raw.decode(encoding))
                self.statusBar().showMessage(
                    f"已导入：{filename}", 5000
                )
                return
            except UnicodeDecodeError:
                continue

        QMessageBox.warning(
            self, "导入失败", "无法识别文本编码。"
        )

    def _refresh_profile_list(
        self,
        select_first: bool = False,
    ) -> None:
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
            for index, profile in enumerate(
                self.app_settings.profiles
            ):
                if profile.profile_id == selected_id:
                    target_row = index
                    break

        if self.app_settings.profiles:
            self.profile_list.setCurrentRow(target_row)

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
        if preset:
            self.base_url_edit.setText(preset["base_url"])
            self.model_edit.setText(preset["model"])

    def _toggle_key_visibility(self, checked: bool) -> None:
        self.api_key_edit.setEchoMode(
            QLineEdit.Normal if checked else QLineEdit.Password
        )

    def _add_profile(self) -> None:
        profile = APIProfile(
            name=f"接口 {len(self.app_settings.profiles) + 1}"
        )
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
                self, "无法删除", "至少需要保留一个接口。"
            )
            return

        profile = self.app_settings.profiles[row]
        if QMessageBox.question(
            self,
            "删除接口",
            f"确定删除“{profile.name}”吗？",
        ) != QMessageBox.Yes:
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
        for index, existing in enumerate(
            self.app_settings.profiles
        ):
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
            result = OpenAICompatibleClient(
                profile
            ).test_connection()
            QMessageBox.information(
                self,
                "连接成功",
                f"接口：{result.profile_name}\n"
                f"模型：{result.model}\n"
                f"耗时：{result.elapsed_seconds:.2f} 秒\n"
                f"返回：{result.text}",
            )
        except Exception as exc:
            QMessageBox.critical(
                self, "连接失败", str(exc)
            )

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
            current_id = self.app_settings.task_routes.get(
                task_key, ""
            )
            combo.blockSignals(True)
            combo.clear()

            for name, profile_id in profile_items:
                combo.addItem(name, profile_id)

            index = combo.findData(current_id)
            combo.setCurrentIndex(index if index >= 0 else 0)
            combo.blockSignals(False)

    def _save_routes(self) -> None:
        for task_key, combo in self.route_combos.items():
            profile_id = combo.currentData()
            if profile_id:
                self.app_settings.task_routes[task_key] = str(
                    profile_id
                )

        self.settings_service.save(self.app_settings)
        QMessageBox.information(
            self, "保存成功", "任务API路由已保存。"
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
