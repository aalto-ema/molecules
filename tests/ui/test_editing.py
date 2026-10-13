from copy import deepcopy

from molecules.chemistry.adapter import from_smiles
from molecules.ui.window import MainWindow


def test_atom_and_bond_edits_undo_and_redo(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.insert_document(from_smiles("CCO"))
    inserted = deepcopy(window.document)
    window.selected = {inserted.atoms[-1].id}
    window.refresh()
    window.atom_charge.setValue(-1)
    window.apply_atom_properties()
    assert window.document.atoms[-1].charge == -1
    window.undo_stack.undo()
    assert window.document == inserted
    window.undo_stack.redo()
    assert window.document.atoms[-1].charge == -1
    window.saved_document = deepcopy(window.document)


def test_stale_lookup_does_not_open_preview(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.lookup_revision = window.revision
    serial = window.lookup_serial
    window.cancel_lookup()
    window.lookup_finished(serial, from_smiles("CCO"), "", "")
    assert not window.document.atoms


def test_bond_drag_is_one_undoable_gesture(qtbot):
    from PySide6.QtCore import QPointF, Qt

    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    window.set_tool("bond")
    start = window.view.mapFromScene(QPointF(0, 0))
    end = window.view.mapFromScene(QPointF(65, 20))
    qtbot.mousePress(window.view.viewport(), Qt.MouseButton.LeftButton, pos=start)
    qtbot.mouseMove(window.view.viewport(), pos=end)
    qtbot.mouseRelease(window.view.viewport(), Qt.MouseButton.LeftButton, pos=end)
    assert len(window.document.atoms) == 2
    assert len(window.document.bonds) == 1
    assert window.undo_stack.count() == 1
    window.undo_stack.undo()
    assert not window.document.atoms


def test_drag_atom_moves_connected_bond_without_extra_history(qtbot):
    from PySide6.QtCore import QPoint, QPointF, Qt

    window = MainWindow()
    qtbot.addWidget(window)
    window.document = from_smiles("CCO")
    window.saved_document = deepcopy(window.document)
    window.refresh()
    window.show()
    original = deepcopy(window.document)
    atom = original.atoms[-1]
    start = window.view.mapFromScene(QPointF(atom.x, atom.y))
    end = start + QPoint(30, 25)
    qtbot.mousePress(window.view.viewport(), Qt.MouseButton.LeftButton, pos=start)
    qtbot.mouseMove(window.view.viewport(), pos=end)
    qtbot.mouseRelease(window.view.viewport(), Qt.MouseButton.LeftButton, pos=end)
    assert window.document.atoms[-1].x != atom.x
    assert window.document.bonds == original.bonds
    assert window.undo_stack.count() == 1
    window.undo_stack.undo()
    assert window.document == original


def test_worker_lookup_preview_and_insertion(qtbot, monkeypatch):
    from PySide6.QtWidgets import QDialog

    window = MainWindow()
    qtbot.addWidget(window)
    monkeypatch.setattr(QDialog, "exec", lambda self: QDialog.DialogCode.Accepted)
    window.name_input.setText("ethanol")
    window.start_lookup()
    qtbot.waitUntil(lambda: len(window.document.atoms) == 3)
    assert window.undo_stack.count() == 1
    assert not window.cancel_button.isVisible()
    window.saved_document = deepcopy(window.document)


def test_input_change_cancels_worker_result(qtbot):
    from PySide6.QtCore import QThreadPool

    window = MainWindow()
    qtbot.addWidget(window)
    window.name_input.setText("ethanol")
    window.start_lookup()
    window.name_input.setText("aspirin")
    QThreadPool.globalInstance().waitForDone(2000)
    qtbot.wait(20)
    assert not window.document.atoms
    assert window.lookup_button.isEnabled()
