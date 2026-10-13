"""Reaction drawing, clipboard, and contextual annotation properties."""

import json
from copy import deepcopy
from dataclasses import asdict, replace

from PySide6.QtCore import QPointF
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QInputDialog,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QToolBar,
)

from molecules.chemistry.adapter import from_smiles
from molecules.domain.document import Arrow, Note, new_id
from molecules.rendering.scene import arrow_geometry
from molecules.storage.native import SCHEMA_VERSION, decode_document


class AnnotationsMixin:
    def create_annotation_tools(self):
        self.flow_source = None
        self.clipboard_document = None
        self.tools = QToolBar("Reactions and templates", self)
        self.tools.setMovable(False)
        self.tools.hide()
        for key, label in (
            ("reaction", "Arrow"),
            ("equilibrium", "Equilibrium"),
            ("retro", "Retrosynthesis"),
            ("electron", "Flow"),
            ("text", "Text"),
            ("plus", "+"),
        ):
            self.add_tool(key, label, "E" if key == "electron" else "T" if key == "text" else None)
        ring = QPushButton("Ring template…")
        ring.clicked.connect(self.insert_ring)
        self.tools.addWidget(ring)
        next_step = QPushButton("Create next step…")
        next_step.clicked.connect(self.create_next_step)
        self.tools.addWidget(next_step)
        example = QPushButton("Mechanism example")
        example.clicked.connect(self.mechanism_example)
        self.tools.addWidget(example)
        self.action(self.edit_menu, "Copy", self.copy_selection, QKeySequence.StandardKey.Copy)
        self.action(self.edit_menu, "Cut", self.cut_selection, QKeySequence.StandardKey.Cut)
        self.action(self.edit_menu, "Paste", self.paste_selection, QKeySequence.StandardKey.Paste)
        self.action(self.edit_menu, "Align selection…", self.align_selection)
        self.action(self.edit_menu, "Check chemistry", self.check_chemistry)
        self.action(
            self.edit_menu, "Create step from selected arrows…", lambda: self.create_next_step(True)
        )
        form = self.inspector.widget().layout()
        self.lone_pairs = QSpinBox()
        self.lone_pairs.setRange(0, 4)
        self.radicals = QSpinBox()
        self.radicals.setRange(0, 4)
        form.addRow("Lone pairs", self.lone_pairs)
        form.addRow("Radical electrons", self.radicals)
        electrons = self.electron_marks_apply = QPushButton("Apply electron marks")
        electrons.clicked.connect(self.apply_electron_marks)
        form.addRow(electrons)
        self.curvature = QSpinBox()
        self.curvature.setRange(-1000, 1000)
        self.electron_count = QComboBox()
        self.electron_count.addItems(["2", "1"])
        form.addRow("Arrow curvature", self.curvature)
        form.addRow("Electrons in arrow", self.electron_count)
        arrow_apply = self.arrow_apply = QPushButton("Apply arrow properties")
        arrow_apply.clicked.connect(self.apply_arrow_properties)
        form.addRow(arrow_apply)
        self.note_text = QPlainTextEdit()
        self.note_text.setMaximumHeight(110)
        self.note_size = QSpinBox()
        self.note_size.setRange(8, 96)
        self.note_size.setValue(18)
        self.note_apply = QPushButton("Apply text properties")
        self.note_apply.clicked.connect(self.apply_note_properties)
        form.addRow("Text", self.note_text)
        form.addRow("Text size", self.note_size)
        form.addRow(self.note_apply)
        self.action(self.edit_menu, "Edit selected text…", self.edit_note)

    def annotation_press(self, tool, kind, identity, point):
        if tool == "pathway":
            self.pathway_click(kind, identity)
            return True
        if tool == "electron":
            if self.flow_source is None:
                self.flow_source = (identity if kind in ("atom", "bond") else "", point)
                self.selected = {identity} if identity else set()
                self.refresh()
                self.statusBar().showMessage("Select the electron target · Escape cancels")
                self.update_workspace()
            else:
                anchor, start = self.flow_source
                end_anchor = identity if kind in ("atom", "bond") else ""
                if anchor and anchor == end_anchor:
                    return True
                arrow = Arrow(
                    new_id(),
                    "electron",
                    start.x(),
                    start.y(),
                    point.x(),
                    point.y(),
                    start_anchor=anchor,
                    end_anchor=end_anchor,
                    electrons=self.flow_count.currentData(),
                    curvature=self.view.suggest_curvature(start, point),
                )
                self.selected = {arrow.id}
                self.edit("Draw electron arrow", lambda d: d.arrows.append(arrow))
                self.flow_source = None
                self.view.flow_preview = None
                self.update_workspace()
            return True
        if tool in ("text", "plus"):
            text = "+"
            if tool == "text":
                text, ok = QInputDialog.getMultiLineText(
                    self, "Add annotation", "Text or reaction conditions"
                )
                if not ok or not text.strip():
                    return True
            self.edit(
                "Add annotation",
                lambda d: d.notes.append(
                    Note(new_id(), text, point.x(), point.y(), 24 if tool == "plus" else 18)
                ),
            )
            return True
        return False

    def annotation_release(self, tool, start, end):
        if tool in ("reaction", "equilibrium", "retro") and (end - start).manhattanLength() > 10:
            self.edit(
                "Draw reaction arrow",
                lambda d: d.arrows.append(
                    Arrow(new_id(), tool, start.x(), start.y(), end.x(), end.y(), 0)
                ),
            )

    def move_annotations(self, document, delta, selection):
        document.notes = [
            replace(n, x=n.x + delta.x(), y=n.y + delta.y()) if n.id in selection else n
            for n in document.notes
        ]
        arrows = []
        for a in document.arrows:
            if a.id not in selection:
                arrows.append(a)
                continue
            if a.start_group:
                if not set(a.start_group + a.end_group) & selection:
                    start, end, _ = arrow_geometry(document, a)
                    side = a.label_side
                    if side == "auto":
                        side = (
                            "above"
                            if abs(end.x() - start.x()) >= abs(end.y() - start.y())
                            else "right"
                        )
                    changes = {
                        "above": -delta.y(),
                        "below": delta.y(),
                        "left": -delta.x(),
                        "right": delta.x(),
                    }
                    offset = a.label_offset + changes[side]
                    if offset < 0:
                        side = {
                            "above": "below",
                            "below": "above",
                            "left": "right",
                            "right": "left",
                        }[side]
                    a = replace(a, label_side=side, label_offset=max(8, min(200, abs(offset))))
            else:
                a = replace(
                    a,
                    x1=a.x1 + (delta.x() if not a.start_anchor else 0),
                    y1=a.y1 + (delta.y() if not a.start_anchor else 0),
                    x2=a.x2 + (delta.x() if not a.end_anchor else 0),
                    y2=a.y2 + (delta.y() if not a.end_anchor else 0),
                )
            arrows.append(a)
        document.arrows = arrows

    def remove_annotations(self, document):
        ids = {a.id for a in document.atoms} | {b.id for b in document.bonds}
        document.notes = [n for n in document.notes if n.id not in self.selected]
        arrows = []
        for a in document.arrows:
            if (
                a.id in self.selected
                or a.start_anchor
                and a.start_anchor not in ids
                or a.end_anchor
                and a.end_anchor not in ids
            ):
                continue
            if a.start_group:
                start, end = (
                    [i for i in a.start_group if i in ids],
                    [i for i in a.end_group if i in ids],
                )
                if not start or not end:
                    continue
                a = replace(a, start_group=start, end_group=end)
            arrows.append(a)
        document.arrows = arrows

    def filter_annotations(self, document, atom_ids):
        anchors = atom_ids | {b.id for b in document.bonds}
        document.notes = [n for n in document.notes if n.id in self.selected]
        arrows = []
        for a in document.arrows:
            if a.id in self.selected:
                start, end, _ = arrow_geometry(self.document, a)
                arrows.append(
                    replace(
                        a,
                        x1=start.x(),
                        y1=start.y(),
                        x2=end.x(),
                        y2=end.y(),
                        start_anchor=a.start_anchor if a.start_anchor in anchors else "",
                        end_anchor=a.end_anchor if a.end_anchor in anchors else "",
                        start_group=a.start_group
                        if set(a.start_group + a.end_group) <= atom_ids
                        else [],
                        end_group=a.end_group
                        if set(a.start_group + a.end_group) <= atom_ids
                        else [],
                    )
                )
        document.arrows = arrows

    def update_annotation_inspector(self):
        atoms = [a for a in self.document.atoms if a.id in self.selected]
        if len(atoms) == 1:
            self.lone_pairs.setValue(atoms[0].lone_pairs)
            self.radicals.setValue(atoms[0].radicals)
        arrows = [a for a in self.document.arrows if a.id in self.selected]
        if len(arrows) == 1:
            self.curvature.setValue(round(arrows[0].curvature))
            self.electron_count.setCurrentText(str(arrows[0].electrons))

        notes = [n for n in self.document.notes if n.id in self.selected]
        if len(notes) == 1:
            self.note_text.setPlainText(notes[0].text)
            self.note_size.setValue(notes[0].size)

    def apply_note_properties(self):
        self.edit(
            "Change text properties",
            lambda d: setattr(
                d,
                "notes",
                [
                    replace(n, text=self.note_text.toPlainText(), size=self.note_size.value())
                    if n.id in self.selected
                    else n
                    for n in d.notes
                ],
            ),
        )

    def apply_electron_marks(self):
        self.edit(
            "Change electron marks",
            lambda d: setattr(
                d,
                "atoms",
                [
                    replace(a, lone_pairs=self.lone_pairs.value(), radicals=self.radicals.value())
                    if a.id in self.selected
                    else a
                    for a in d.atoms
                ],
            ),
        )

    def apply_arrow_properties(self):
        self.edit(
            "Change arrow properties",
            lambda d: setattr(
                d,
                "arrows",
                [
                    replace(
                        a,
                        curvature=self.curvature.value(),
                        electrons=int(self.electron_count.currentText()),
                    )
                    if a.id in self.selected
                    else a
                    for a in d.arrows
                ],
            ),
        )

    def edit_note(self):
        notes = [n for n in self.document.notes if n.id in self.selected]
        if len(notes) != 1:
            self.statusBar().showMessage("Select one text annotation to edit.")
            return
        text, ok = QInputDialog.getMultiLineText(self, "Edit annotation", "Text", notes[0].text)
        if ok:
            self.edit(
                "Edit annotation",
                lambda d: setattr(
                    d,
                    "notes",
                    [replace(n, text=text) if n.id == notes[0].id else n for n in d.notes],
                ),
            )

    def insert_ring(self):
        templates = {
            "Benzene": "c1ccccc1",
            "Cyclohexane": "C1CCCCC1",
            "Cyclopentane": "C1CCCC1",
            "Cyclopropane": "C1CC1",
            "Pyridine": "c1ccncc1",
        }
        name, ok = QInputDialog.getItem(
            self, "Ring template", "Template", list(templates), 0, False
        )
        if ok:
            self.insert_document(from_smiles(templates[name], name))

    def copy_selection(self):
        document = self.selection_document()
        if not document.atoms and not document.arrows and not document.notes:
            return
        content = json.dumps({"schema_version": SCHEMA_VERSION, **asdict(document)})
        QApplication.clipboard().setText("Molecules drawing\n" + content)
        self.statusBar().showMessage("Selection copied", 3000)

    def cut_selection(self):
        self.copy_selection()
        self.delete_selection()

    def paste_selection(self):
        content = QApplication.clipboard().text()
        if not content.startswith("Molecules drawing\n"):
            self.statusBar().showMessage("Copy a drawing selection first.")
            return
        try:
            source = decode_document(content.partition("\n")[2].encode("utf-8"))
            ids = {
                e.id: new_id()
                for e in [*source.atoms, *source.bonds, *source.notes, *source.arrows]
            }
            atoms = [
                replace(a, id=ids[a.id], identity=new_id(), x=a.x + 36, y=a.y + 36)
                for a in source.atoms
            ]
            bonds = [
                replace(
                    b,
                    id=ids[b.id],
                    start=ids[b.start],
                    end=ids[b.end],
                    stereo_atoms=[ids[a] for a in b.stereo_atoms],
                )
                for b in source.bonds
            ]
            arrows = [
                replace(
                    a,
                    id=ids[a.id],
                    x1=a.x1 + 36,
                    y1=a.y1 + 36,
                    x2=a.x2 + 36,
                    y2=a.y2 + 36,
                    start_anchor=ids.get(a.start_anchor, ""),
                    end_anchor=ids.get(a.end_anchor, ""),
                    start_group=[ids[i] for i in a.start_group],
                    end_group=[ids[i] for i in a.end_group],
                )
                for a in source.arrows
            ]
            notes = [replace(n, id=ids[n.id], x=n.x + 36, y=n.y + 36) for n in source.notes]
            result = deepcopy(self.document)
            result.atoms += atoms
            result.bonds += bonds
            result.arrows += arrows
            result.notes += notes
            result.sources += [
                replace(s, atom_ids=[ids[a] for a in s.atom_ids]) for s in source.sources
            ]
            self.selected = set(ids.values())
            self.commit("Paste selection", result)
        except (ValueError, KeyError) as exc:
            QMessageBox.warning(self, "Could not paste drawing", str(exc))

    def align_selection(self):
        atoms = [a for a in self.document.atoms if a.id in self.selected]
        if len(atoms) < 2:
            self.statusBar().showMessage("Select at least two atoms to align.")
            return
        direction, ok = QInputDialog.getItem(
            self, "Align atoms", "Alignment", ["Horizontal", "Vertical"], 0, False
        )
        if ok:
            key = "y" if direction == "Horizontal" else "x"
            value = sum(getattr(a, key) for a in atoms) / len(atoms)
            self.edit(
                "Align atoms",
                lambda d: setattr(
                    d,
                    "atoms",
                    [replace(a, **{key: value}) if a.id in self.selected else a for a in d.atoms],
                ),
            )

    def check_chemistry(self):
        from molecules.chemistry.adapter import chemistry_warning

        warning = chemistry_warning(self.document)
        QMessageBox.information(
            self,
            "Chemistry check",
            warning or "RDKit found no valence errors. This does not verify a reaction mechanism.",
        )

    def create_next_step(self, use_selection=False, arrow_ids=None):
        from PySide6.QtWidgets import QDialog

        from molecules.mechanisms.steps import propose_next_step
        from molecules.ui.mechanism_dialog import MechanismDialog

        try:
            selected_arrows = {
                a.id for a in self.document.arrows if a.id in self.selected and a.kind == "electron"
            }
            if use_selection and not selected_arrows:
                raise ValueError("Select one or more electron arrows first.")
            proposal = propose_next_step(
                self.document,
                arrow_ids if arrow_ids is not None else selected_arrows if use_selection else None,
            )
        except ValueError as exc:
            self.flow_feedback.setText(str(exc))
            if self.workspace_mode != "mechanism":
                self.set_workspace_mode("mechanism")
            return
        self.flow_feedback.setText("")
        dialog = MechanismDialog(proposal, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.selected = proposal.atom_ids
            self.commit("Create mechanism step", proposal.document)
            self.fit_drawing()

    def mechanism_example(self):
        # Pair-electron attack on a carbonyl, followed by pi-bond cleavage.
        d = from_smiles("[OH-].CC=O", "Nucleophilic addition")
        donor, _, carbon, oxygen = d.atoms
        carbonyl = next(b for b in d.bonds if b.order == 2)
        d.atoms[0] = replace(donor, lone_pairs=3)
        d.arrows = [
            Arrow(
                new_id(), "electron", donor.x, donor.y, carbon.x, carbon.y, 60, donor.id, carbon.id
            ),
            Arrow(new_id(), "electron", 0, 0, oxygen.x, oxygen.y, -45, carbonyl.id, oxygen.id),
        ]
        d.notes = [Note(new_id(), "Nucleophilic addition", 0, -120)]
        result = deepcopy(self.document)
        if not result.atoms and not result.notes and not result.arrows:
            result.title = d.title
        if result.atoms or result.notes or result.arrows:
            right = max((a.x for a in result.atoms), default=0)
            offset = QPointF(right + 250, 0)
            d.atoms = [replace(a, x=a.x + offset.x()) for a in d.atoms]
            self.move_annotations(d, offset, {e.id for e in [*d.arrows, *d.notes]})
        result.atoms += d.atoms
        result.bonds += d.bonds
        result.arrows += d.arrows
        result.notes += d.notes
        self.selected = {a.id for a in d.arrows}
        self.commit("Insert mechanism example", result)
        self.fit_drawing()

    def update_inspector_visibility(self):
        form = self.inspector_content.layout()
        atoms = any(a.id in self.selected for a in self.document.atoms)
        bonds = any(b.id in self.selected for b in self.document.bonds)
        arrows = any(a.id in self.selected for a in self.document.arrows)
        for control in (
            self.atom_element,
            self.atom_charge,
            self.atom_isotope,
            self.atom_hydrogens,
            self.atom_label,
            self.atom_apply,
            self.lone_pairs,
            self.radicals,
            self.electron_marks_apply,
        ):
            form.setRowVisible(control, atoms)
        for control in (self.bond_style, self.bond_apply):
            form.setRowVisible(control, bonds)
        notes = any(n.id in self.selected for n in self.document.notes)
        for control in (self.note_text, self.note_size, self.note_apply):
            form.setRowVisible(control, notes)
        for control in (self.curvature, self.electron_count, self.arrow_apply):
            form.setRowVisible(control, arrows)
