from copy import deepcopy
from dataclasses import replace

from PySide6.QtCore import QPointF

from molecules.chemistry.adapter import from_smiles
from molecules.domain.document import Arrow, Note, new_id
from molecules.exports.visual import export
from molecules.rendering.scene import arrow_geometry
from molecules.storage.native import load_document, save_document
from molecules.ui.window import MainWindow


def test_annotations_round_trip_and_export(qapp, tmp_path):
    d = from_smiles("CCO")
    d.notes = [Note(new_id(), "NaOH, room temperature", 0, 100)]
    d.arrows = [
        Arrow(
            new_id(),
            "electron",
            0,
            0,
            50,
            50,
            start_anchor=d.atoms[-1].id,
            end_anchor=d.bonds[0].id,
        ),
        Arrow(new_id(), "equilibrium", 0, 150, 200, 150),
    ]
    d.atoms[-1] = replace(d.atoms[-1], lone_pairs=2)
    path = tmp_path / "reaction.json"
    save_document(d, path)
    assert load_document(path) == d
    for format in ("PNG", "SVG", "PDF"):
        output = tmp_path / ("reaction." + format.lower())
        export(d, output, format=format)
        assert output.stat().st_size > 100
    before = arrow_geometry(d, d.arrows[0])[0]
    d.atoms[-1] = replace(d.atoms[-1], x=d.atoms[-1].x + 25)
    after = arrow_geometry(d, d.arrows[0])[0]
    assert after - before == QPointF(25, 0)


def test_delete_anchored_atom_and_undo(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.document = from_smiles("CCO")
    atom = window.document.atoms[-1]
    window.document.arrows = [Arrow(new_id(), "electron", 0, 0, 40, 40, start_anchor=atom.id)]
    original = deepcopy(window.document)
    window.selected = {atom.id}
    window.delete_selection()
    assert not window.document.arrows
    window.undo_stack.undo()
    assert window.document == original
    window.saved_document = deepcopy(window.document)


def test_copy_paste_remaps_atom_and_arrow_anchors(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.document = from_smiles("CCO")
    window.document.arrows = [
        Arrow(
            new_id(),
            "electron",
            0,
            0,
            40,
            40,
            start_anchor=window.document.atoms[0].id,
            end_anchor=window.document.atoms[-1].id,
        )
    ]
    window.select_all()
    window.copy_selection()
    window.paste_selection()
    window.document.validate()
    assert len(window.document.atoms) == 6
    assert window.document.arrows[0].start_anchor != window.document.arrows[1].start_anchor
    window.saved_document = deepcopy(window.document)


def test_guided_step_uses_all_current_arrows_and_is_undoable(qtbot, monkeypatch):
    from PySide6.QtWidgets import QDialog

    window = MainWindow()
    qtbot.addWidget(window)
    window.mechanism_example()
    original = deepcopy(window.document)
    window.selected = {window.document.arrows[-1].id}
    monkeypatch.setattr(QDialog, "exec", lambda self: QDialog.DialogCode.Accepted)
    window.create_next_step()
    new_atoms = [a for a in window.document.atoms if a.step == 1]
    assert [a.charge for a in new_atoms] == [0, 0, 0, -1]
    assert new_atoms[0].lone_pairs == 2
    window.undo_stack.undo()
    assert window.document == original
    window.saved_document = deepcopy(window.document)
