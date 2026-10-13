from copy import deepcopy
from dataclasses import replace

from PySide6.QtCore import QPointF, Qt
from PySide6.QtWidgets import QDialog, QGraphicsTextItem
from rdkit import Chem

from molecules.chemistry.adapter import from_smiles, to_mol
from molecules.domain.geometry import rotate_molecules
from molecules.domain.pathways import add_product
from molecules.exports.visual import export
from molecules.rendering.scene import arrow_geometry, content_scene
from molecules.storage.native import load_document, save_document
from molecules.ui.window import MainWindow


def window(qtbot):
    w = MainWindow()
    qtbot.addWidget(w)
    w.confirm_discard = lambda: True
    return w


def test_pathway_product_lookup_is_one_undoable_step(qtbot, monkeypatch):
    w = window(qtbot)
    w.insert_document(from_smiles("CC=O"))
    original = deepcopy(w.document)
    w.set_workspace_mode("pathway")
    w.product_mode.setCurrentText("SMILES")
    w.product_input.setText("CCO")
    w.pathway_direction.setCurrentIndex(1)
    w.pathway_caption.setText("2H⁺ + 2e⁻")
    monkeypatch.setattr(QDialog, "exec", lambda self: QDialog.DialogCode.Accepted)
    w.start_pathway_lookup()
    qtbot.waitUntil(lambda: len(w.document.arrows) == 1)
    assert w.document.arrows[0].label == "2H⁺ + 2e⁻"
    assert all(a.y > 100 for a in w.document.atoms if a.step == 1)
    w.undo_stack.undo()
    assert w.document == original
    w.undo_stack.redo()
    assert len(w.document.arrows) == 1


def test_link_tool_connects_two_existing_molecules(qtbot):
    w = window(qtbot)
    first, second = from_smiles("CC=O"), from_smiles("CCO")
    w.insert_document(first)
    w.insert_document(second)
    w.selected.clear()
    w.set_workspace_mode("pathway")
    w.pathway_source = None
    w.pathway_caption.setText("Catalyst / arbitrary conditions")
    w.show()
    w.fit_drawing()
    for molecule in (first, second):
        atom = next(a for a in w.document.atoms if a.id == molecule.atoms[0].id)
        pos = w.view.mapFromScene(QPointF(atom.x, atom.y))
        qtbot.mouseClick(w.view.viewport(), Qt.MouseButton.LeftButton, pos=pos)
    assert len(w.document.arrows) == 1
    assert w.document.arrows[0].label == "Catalyst / arbitrary conditions"
    assert w.pathway_source == second.atoms[0].id


def test_pathway_caption_and_link_follow_move_rotate_and_roundtrip(qapp, tmp_path):
    d = from_smiles("CC=O")
    source = {a.id for a in d.atoms}
    p = from_smiles("CCO")
    d = add_product(d, source, p, "left", "E = −0.5 V\nCustom conditions")
    arrow = d.arrows[0]
    before = arrow_geometry(d, arrow)[0]
    d.atoms = [replace(a, y=a.y + 100) if a.id in source else a for a in d.atoms]
    d = rotate_molecules(d, source, 45)
    after = arrow_geometry(d, arrow)[0]
    assert before != after
    path = tmp_path / "pathway.json"
    save_document(d, path)
    assert load_document(path) == d
    for format in ("PNG", "SVG", "PDF"):
        output = tmp_path / ("pathway." + format.lower())
        export(d, output, format=format)
        assert output.stat().st_size > 100
    scene = content_scene(d)
    label = next(
        i for i in scene.items() if isinstance(i, QGraphicsTextItem) and i.data(1) == arrow.id
    )
    assert label.toPlainText() == arrow.label
    assert label.rotation() == 0


def test_drag_rotation_is_one_undoable_gesture(qtbot):
    w = window(qtbot)
    w.insert_document(from_smiles("CCO"))
    w.select_molecule()
    w.show()
    w.fit_drawing()
    before = deepcopy(w.document)
    pivot, handle, _, radius = w.view.rotation_geometry()
    start = w.view.mapFromScene(handle)
    end = w.view.mapFromScene(pivot + QPointF(radius, 0))
    count = w.undo_stack.count()
    qtbot.mousePress(w.view.viewport(), Qt.MouseButton.LeftButton, pos=start)
    qtbot.mouseMove(w.view.viewport(), pos=end)
    qtbot.mouseRelease(w.view.viewport(), Qt.MouseButton.LeftButton, pos=end)
    assert w.document != before
    assert w.document.bonds == before.bonds
    assert w.undo_stack.count() == count + 1
    w.undo_stack.undo()
    assert w.document == before


def test_escape_cancels_rotation(qtbot):
    w = window(qtbot)
    w.insert_document(from_smiles("CCO"))
    w.select_molecule()
    w.show()
    w.fit_drawing()
    before = deepcopy(w.document)
    pivot, handle, _, radius = w.view.rotation_geometry()
    qtbot.mousePress(w.view.viewport(), Qt.MouseButton.LeftButton, pos=w.view.mapFromScene(handle))
    qtbot.mouseMove(w.view.viewport(), pos=w.view.mapFromScene(pivot + QPointF(radius, 0)))
    qtbot.keyClick(w.view, Qt.Key.Key_Escape)
    assert w.document == before
    assert not w.view.rotating


def test_rotation_preserves_stereochemistry(qapp):
    d = from_smiles("N[C@@H](C)C(=O)O")
    original = Chem.MolToSmiles(to_mol(d))
    for angle in (15, 90, 180, -45):
        rotated = rotate_molecules(d, {d.atoms[0].id}, angle)
        assert Chem.MolToSmiles(to_mol(rotated)) == original


def test_copy_paste_and_delete_preserve_pathway_references(qtbot):
    w = window(qtbot)
    w.pathway_example()
    before = deepcopy(w.document)
    w.select_all()
    w.copy_selection()
    w.paste_selection()
    w.document.validate()
    assert len(w.document.arrows) == 6
    assert not set(w.document.arrows[0].start_group) & set(w.document.arrows[3].start_group)
    w.undo_stack.undo()
    assert w.document == before
    w.selected = {before.arrows[0].start_group[0]}
    w.delete_selection()
    assert len(w.document.arrows) == 3
    w.document.validate()
    w.undo_stack.undo()
    assert w.document == before


def test_rotation_popup_stays_hidden_and_keeps_label(qtbot):
    w = window(qtbot)
    control = w.rotation_button()
    qtbot.addWidget(control)
    control.show()
    qtbot.wait(20)
    assert control.text() == "Rotate"
    assert not control.menu().isVisible()
    assert control.menu().isWindow()


def test_arrow_only_copy_freezes_group_geometry(qtbot, tmp_path):
    w = window(qtbot)
    w.pathway_example()
    arrow = w.document.arrows[0]
    start, end, _ = arrow_geometry(w.document, arrow)
    w.selected = {arrow.id}
    fragment = w.selection_document()
    fragment.validate()
    copied = fragment.arrows[0]
    assert not fragment.atoms
    assert not copied.start_group and not copied.end_group
    assert (copied.x1, copied.y1, copied.x2, copied.y2) == (start.x(), start.y(), end.x(), end.y())
    assert copied.label == arrow.label
    export(fragment, tmp_path / "arrow.svg", format="SVG")
