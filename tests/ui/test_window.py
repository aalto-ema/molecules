from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox

from molecules.storage.native import load_document
from molecules.ui.window import MainWindow


def test_open_save_and_new(qtbot, monkeypatch, tmp_path):
    window = MainWindow()
    qtbot.addWidget(window)
    example = Path(__file__).resolve().parents[2] / "examples" / "ethanol.molecules.json"
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args: (str(example), ""))
    window.open_document()
    assert window.document.title == "Ethanol"
    assert window.scene.items()

    destination = tmp_path / "copy.molecules.json"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (str(destination), ""))
    window.save_as()
    assert load_document(destination) == window.document
    assert window.path == destination

    window.new_document()
    assert window.path is None
    assert not window.document.atoms
    assert not any(item.data(1) for item in window.scene.items())


def test_failed_open_preserves_current_document(qtbot, monkeypatch, tmp_path):
    window = MainWindow()
    qtbot.addWidget(window)
    original = window.document
    bad_file = tmp_path / "bad.molecules.json"
    bad_file.write_text('{"schema_version": 99, "title": "Bad", "atoms": [], "bonds": []}')
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args: (str(bad_file), ""))
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: warnings.append(args[2]))
    window.open_document()
    assert warnings
    assert window.document is original
    assert window.path is None
