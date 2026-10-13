"""Shared visual tokens for a quiet, accessible drawing workspace."""

from pathlib import Path

from PySide6.QtGui import QColor, QPalette

ACCENT = "#3469dc"
INK = "#243047"
MUTED = "#65748b"
SURFACE = "#f5f7fb"
BORDER = "#e1e7f0"

STYLESHEET = """
QMainWindow, QDialog { background: #f5f7fb; color: #243047; }
QWidget { font-size: 13px; }
QLabel { color: #243047; background: transparent; }
QLabel[role="muted"] { color: #65748b; }
QLabel[role="eyebrow"] { color: #65748b; font-size: 11px; font-weight: 600; }
QLabel[role="title"] { font-size: 23px; font-weight: 600; }
QLabel[role="subtitle"] { font-size: 16px; font-weight: 600; }
QLabel#Brand { font-size: 18px; font-weight: 600; }
QFrame#AppHeader { background: #ffffff; border-bottom: 1px solid #e1e7f0; }
QFrame#SearchBox { background: #f5f7fb; border: 1px solid #e1e7f0; border-radius: 10px; }
QFrame#SearchBox[focused="true"] { border-color: #3469dc; background: #ffffff; }
QLineEdit#NameInput { background: transparent; border: none; padding: 8px; font-size: 14px; }
QComboBox#InputMode { background: transparent; border: none; }
QFrame#WorkspaceBar { background: #f5f7fb; border-bottom: 1px solid #e1e7f0; }
QFrame#ToolRail { background: #ffffff; border: 1px solid #e1e7f0; border-radius: 12px; }
QFrame#ContextBar, QFrame#WelcomeCard { background: #ffffff; border: 1px solid #e1e7f0;
    border-radius: 12px; }
QFrame#GuideFooter { background: #ffffff; border-top: 1px solid #e1e7f0; }
QScrollArea#RailScroll { background: transparent; }
QFrame#GuidePanel { background: #ffffff; border-left: 1px solid #e1e7f0; }
QFrame#FlowStage { background: #f5f7fb; border: 1px solid #e1e7f0; border-radius: 10px; }
QFrame#FlowStage[active="true"] { background: #edf3ff; border-color: #b4cbfa; }
QFrame#Feedback { background: #fff5eb; border: 1px solid #edc99f; border-radius: 8px; }
QPushButton, QToolButton { color: #243047; background: #ffffff; border: 1px solid #e1e7f0;
    border-radius: 7px; padding: 7px 12px; min-height: 20px; }
QPushButton:hover, QToolButton:hover { background: #edf3ff; border-color: #bdd0f5; }
QPushButton:pressed, QToolButton:pressed { background: #dce8ff; }
QPushButton:focus, QToolButton:focus { border: 2px solid #3469dc; }
QPushButton:disabled, QToolButton:disabled { color: #9da8b9; background: #f7f9fc;
    border-color: #edf0f5; }
QPushButton[role="primary"] { background: #3469dc; border-color: #3469dc; color: white;
    font-weight: 600; }
QPushButton[role="primary"]:hover { background: #2858c2; }
QPushButton[role="primary"]:disabled { background: #c2d2f2; border-color: #c2d2f2; color: #ffffff; }
QPushButton[role="quiet"], QToolButton[role="quiet"] { background: transparent;
    border-color: transparent; }
QPushButton[role="quiet"]:hover, QToolButton[role="quiet"]:hover { background: #eaf0fb; }
QPushButton[role="chip"] { padding: 5px 9px; min-width: 22px; }
QPushButton[role="chip"]:checked { background: #edf3ff; border-color: #3469dc; color: #2858c2; }
QPushButton[role="mode"] { background: transparent; border: none; padding: 7px 14px;
    color: #65748b; }
QPushButton[role="mode"]:checked { background: white; color: #2858c2; border: 1px solid #dce5f3; }
QToolButton[role="tool"] { border: none; background: transparent; padding: 5px;
    font-size: 10px; min-height: 40px; max-height: 40px; min-width: 44px; max-width: 44px; }
QToolButton[role="tool"]:checked { background: #eaf0ff; color: #2858c2; }
QToolButton[role="tool"]:hover { background: #f0f4fb; }
QLineEdit, QComboBox, QSpinBox, QPlainTextEdit { background: #ffffff; color: #243047;
    border: 1px solid #dce3ef; border-radius: 6px; padding: 6px; min-height: 20px;
    selection-background-color: #3469dc; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QPlainTextEdit:focus { border-color: #3469dc; }
QComboBox::drop-down { border: none; width: 20px; }
QComboBox::down-arrow { image: url("CHEVRON_PATH"); width: 16px; height: 16px; }
QScrollArea { background: #ffffff; border: none; }
QDockWidget { color: #243047; }
QDockWidget::title { background: #f5f7fb; padding: 12px; font-weight: 600; }
QStatusBar { background: #f5f7fb; border-top: 1px solid #e1e7f0; color: #65748b; }
QStatusBar::item { border: none; }
QMenuBar { background: #ffffff; color: #243047; }
QMenu { background: #ffffff; color: #243047; border: 1px solid #e1e7f0; padding: 5px; }
QMenu::item { padding: 7px 24px; }
QMenu::item:selected { background: #edf3ff; }
QToolTip { color: #243047; background: white; border: 1px solid #dce3ef; padding: 6px; }
QScrollBar:vertical { width: 10px; background: #f5f7fb; margin: 0; }
QScrollBar:horizontal { height: 10px; background: #f5f7fb; margin: 0; }
QScrollBar::handle { background: #d0d8e5; border-radius: 4px; min-height: 24px; min-width: 24px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
"""


def apply_theme(widget):
    palette = QPalette(widget.palette())
    for role, value in (
        (QPalette.ColorRole.Window, SURFACE),
        (QPalette.ColorRole.WindowText, INK),
        (QPalette.ColorRole.Base, "#ffffff"),
        (QPalette.ColorRole.Text, INK),
        (QPalette.ColorRole.Button, "#ffffff"),
        (QPalette.ColorRole.ButtonText, INK),
        (QPalette.ColorRole.Highlight, ACCENT),
        (QPalette.ColorRole.HighlightedText, "#ffffff"),
    ):
        palette.setColor(role, QColor(value))
    widget.setPalette(palette)
    chevron = (Path(__file__).parent / "assets" / "chevron.svg").as_posix()
    widget.setStyleSheet(STYLESHEET.replace("CHEVRON_PATH", chevron))
