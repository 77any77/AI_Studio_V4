import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from ai_studio.ui.main_window import MainWindow


def test_main_window_starts(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    assert window.windowTitle() == "AI Studio V4"
