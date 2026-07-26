from __future__ import annotations

import logging
import sys
import traceback

from PySide6.QtWidgets import QApplication, QMessageBox

from ai_studio.core.paths import logs_dir
from ai_studio.ui.main_window import MainWindow


def configure_logging() -> None:
    log_file = logs_dir() / "ai_studio.log"
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        encoding="utf-8",
    )


def main() -> int:
    configure_logging()
    app = QApplication(sys.argv)
    app.setApplicationName("AI Studio V4")
    try:
        window = MainWindow()
        window.show()
        return app.exec()
    except Exception:
        detail = traceback.format_exc()
        logging.exception("Application startup failed")
        QMessageBox.critical(
            None,
            "AI Studio V4 启动失败",
            detail[-1800:],
        )
        return 1
