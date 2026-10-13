from copy import deepcopy

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtWidgets import QDialog, QPushButton

from molecules.chemistry.adapter import from_smiles
from molecules.ui.window import MainWindow


def editor(qtbot, smiles="CCO"):
    window = MainWindow()
    qtbot.addWidget(window)
    window.confirm_discard = lambda: True
    window.insert_document(from_smiles(smiles))
    window.show()
    window.fit_drawing()
    return window


def clean(window):
    window.saved_document = deepcopy(window.document)


def test_contextual_element_and_charge_edits_need_no_apply(qtbot):
    window = editor(qtbot)
    atom = window.document.atoms[-1]
    window.selected = {atom.id}
    window.refresh()
    assert not window.inspector.isVisible()
    change = next(
        b for b in window.context_bar.findChildren(QPushButton) if b.text() == "N" and b.isVisible()
    )
    qtbot.mouseClick(change, Qt.MouseButton.LeftButton)
    assert window.document.atoms[-1].element == "N"
    add_charge = next(
        b for b in window.context_bar.findChildren(QPushButton) if b.text() == "+" and b.isVisible()
    )
    qtbot.mouseClick(add_charge, Qt.MouseButton.LeftButton)
    assert window.document.atoms[-1].charge == 1
    window.undo_stack.undo()
    assert window.document.atoms[-1].charge == 0
    clean(window)


def test_double_click_atom_edits_inline_and_escape_discards(qtbot):
    window = editor(qtbot)
    atom = window.document.atoms[-1]
    point = window.view.mapFromScene(QPointF(atom.x, atom.y))
    qtbot.mouseDClick(window.view.viewport(), Qt.MouseButton.LeftButton, pos=point)
    field = window.view.inline_atom
    assert field.isVisible()
    field.setText("Cl")
    qtbot.keyClick(field, Qt.Key.Key_Return)
    assert window.document.atoms[-1].element == "Cl"
    window.view.show_atom_input(atom.id, QPointF(atom.x, atom.y))
    field = window.view.inline_atom
    field.setText("N")
    qtbot.keyClick(field, Qt.Key.Key_Escape)
    assert window.document.atoms[-1].element == "Cl"
    clean(window)


def test_double_click_bond_cycles_and_is_undoable(qtbot):
    window = editor(qtbot)
    window.selected.clear()
    window.refresh()
    a, b = window.document.atoms[:2]
    point = window.view.mapFromScene(QPointF((a.x + b.x) / 2, (a.y + b.y) / 2))
    qtbot.mouseDClick(window.view.viewport(), Qt.MouseButton.LeftButton, pos=point)
    assert window.document.bonds[0].order == 2
    window.undo_stack.undo()
    assert window.document.bonds[0].order == 1
    clean(window)


def test_alt_drag_moves_entire_molecule_in_one_command(qtbot):
    window = editor(qtbot)
    original = deepcopy(window.document)
    atom = original.atoms[0]
    start = window.view.mapFromScene(QPointF(atom.x, atom.y))
    end = start + QPoint(25, 30)
    qtbot.mousePress(
        window.view.viewport(),
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.AltModifier,
        pos=start,
    )
    qtbot.mouseMove(window.view.viewport(), pos=end)
    qtbot.mouseRelease(
        window.view.viewport(),
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.AltModifier,
        pos=end,
    )
    changes = [
        (new.x - old.x, new.y - old.y)
        for new, old in zip(window.document.atoms, original.atoms, strict=True)
    ]
    assert changes[0] != (0, 0)
    assert all(
        abs(dx - changes[0][0]) < 0.001 and abs(dy - changes[0][1]) < 0.001 for dx, dy in changes
    )
    window.undo_stack.undo()
    assert window.document == original
    clean(window)


def test_source_target_hover_is_a_preview_until_clicked(qtbot):
    window = editor(qtbot, "[OH-].C=O")
    window.set_workspace_mode("mechanism")
    window.fit_drawing()
    source, target = window.document.atoms[:2]
    start = window.view.mapFromScene(QPointF(source.x, source.y))
    end = window.view.mapFromScene(QPointF(target.x, target.y))
    qtbot.mouseClick(window.view.viewport(), Qt.MouseButton.LeftButton, pos=start)
    assert window.flow_source[0] == source.id
    qtbot.mouseMove(window.view.viewport(), pos=end)
    assert window.view.flow_preview
    assert not window.document.arrows
    assert window.flow_stages[1][0].property("active")
    qtbot.mouseClick(window.view.viewport(), Qt.MouseButton.LeftButton, pos=end)
    assert len(window.document.arrows) == 1
    assert window.document.arrows[0].start_anchor == source.id
    assert window.document.arrows[0].end_anchor == target.id
    assert window.flow_source is None
    window.undo_stack.undo()
    assert not window.document.arrows
    clean(window)


def test_escape_cancels_flow_without_changing_drawing(qtbot):
    window = editor(qtbot)
    before = deepcopy(window.document)
    window.set_workspace_mode("mechanism")
    atom = window.document.atoms[0]
    point = window.view.mapFromScene(QPointF(atom.x, atom.y))
    qtbot.mouseClick(window.view.viewport(), Qt.MouseButton.LeftButton, pos=point)
    qtbot.keyClick(window.view, Qt.Key.Key_Escape)
    assert window.flow_source is None
    assert window.view.flow_preview is None
    assert window.document == before
    clean(window)


def test_guide_can_review_an_earlier_step(qtbot, monkeypatch):
    window = MainWindow()
    qtbot.addWidget(window)
    window.confirm_discard = lambda: True
    window.load_mechanism_example()
    monkeypatch.setattr(QDialog, "exec", lambda self: QDialog.DialogCode.Accepted)
    window.review_current_step()
    assert max(a.step for a in window.document.atoms) == 1
    window.step_choice.setCurrentIndex(0)
    window.review_current_step()
    assert max(a.step for a in window.document.atoms) == 2
    clean(window)


def test_small_workspace_keeps_selection_controls_in_view(qtbot):
    window = editor(qtbot)
    window.set_workspace_mode("mechanism")
    window.resize(840, 620)
    window.selected = {window.document.atoms[-1].id}
    window.set_tool("select")
    window.refresh()
    qtbot.wait(10)
    bar = window.context_bar
    assert bar.x() >= 0
    assert bar.x() + bar.width() <= window.view.viewport().width()
    clean(window)


def test_changing_electron_count_preserves_each_curve(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.confirm_discard = lambda: True
    window.load_mechanism_example()
    curvatures = [a.curvature for a in window.document.arrows]
    window.quick_arrow_electrons(1)
    assert [a.electrons for a in window.document.arrows] == [1, 1]
    assert [a.curvature for a in window.document.arrows] == curvatures
    clean(window)


def test_keyboard_element_and_charge_shortcuts(qtbot):
    window = editor(qtbot)
    window.selected = {window.document.atoms[-1].id}
    window.refresh()
    qtbot.keyClick(window.view, Qt.Key.Key_N)
    qtbot.keyClick(window.view, Qt.Key.Key_Plus)
    assert window.document.atoms[-1].element == "N"
    assert window.document.atoms[-1].charge == 1
    clean(window)


def test_name_lookup_errors_are_inline_and_keep_input(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.confirm_discard = lambda: True
    window.show()
    window.name_input.setText("unresolved name")
    window.lookup_revision = window.revision
    window.lookup_finished(window.lookup_serial, None, "", "Name lookup is unavailable.")
    assert window.feedback.isVisible()
    assert window.feedback_label.text() == "Name lookup is unavailable."
    assert window.name_input.text() == "unresolved name"
    assert not window.document.atoms


def test_welcome_and_hover_decorations_do_not_enter_exports(qtbot):
    from molecules.rendering.scene import content_scene

    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    assert window.welcome.isVisible()
    assert not window.scene.items()
    window.insert_document(from_smiles("CCO"))
    assert not window.welcome.isVisible()
    exported = content_scene(window.document)
    assert not any(i.data(0) == "handle" for i in exported.items())
    clean(window)


def test_advanced_changes_only_the_field_that_was_edited(qtbot):
    from dataclasses import replace

    window = editor(qtbot)
    atom = window.document.atoms[-1]
    window.document.atoms[-1] = replace(atom, isotope=18, hydrogens=1, label="OH")
    window.selected = {atom.id}
    window.revision += 1
    window.refresh()
    window.atom_charge.setValue(-1)
    window.apply_atom_properties()
    changed = window.document.atoms[-1]
    assert (changed.charge, changed.isotope, changed.hydrogens, changed.label) == (-1, 18, 1, "OH")
    clean(window)
