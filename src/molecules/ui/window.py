"""A focused chemical drawing workspace."""

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from threading import Event

from PySide6.QtCore import QObject, QRectF, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtGui import QAction, QKeySequence, QUndoCommand, QUndoStack
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDockWidget,
    QFileDialog,
    QFormLayout,
    QGraphicsScene,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QWidget,
)

from molecules.chemistry.adapter import clean_layout
from molecules.chemistry.resolver import resolve
from molecules.domain.document import Document
from molecules.rendering.scene import populate
from molecules.storage.native import load_document, save_document
from molecules.ui.annotations import AnnotationsMixin
from molecules.ui.canvas import Canvas
from molecules.ui.pathways import PathwayMixin
from molecules.ui.workspace import WorkspaceMixin

FILE_FILTER = "Molecules documents (*.molecules.json)"


class DocumentCommand(QUndoCommand):
    def __init__(self, editor, title, before, after):
        super().__init__(title)
        self.editor, self.before, self.after = editor, deepcopy(before), deepcopy(after)
        self.selection = editor.selected.copy()

    def restore(self, document):
        self.editor.document = deepcopy(document)
        ids = {e.id for e in [*document.atoms, *document.bonds]}
        for name in ("arrows", "notes"):
            ids.update(e.id for e in getattr(document, name, []))
        self.editor.selected = self.selection & ids
        self.editor.revision += 1
        self.editor.refresh()

    def undo(self):
        self.restore(self.before)

    def redo(self):
        self.restore(self.after)


class LookupSignals(QObject):
    finished = Signal(int, object, str, str)


class LookupTask(QRunnable):
    def __init__(self, serial, query, mode):
        super().__init__()
        self.serial, self.query, self.mode = serial, query, mode
        self.cancelled = Event()
        self.signals = LookupSignals()

    def run(self):
        document, warning, error = None, "", ""
        try:
            if not self.cancelled.is_set():
                document, warning = resolve(self.query, self.mode)
        except Exception as exc:
            error = str(exc)
        if not self.cancelled.is_set():
            self.signals.finished.emit(self.serial, document, warning, error)


class MainWindow(WorkspaceMixin, PathwayMixin, AnnotationsMixin, QMainWindow):
    def __init__(self):
        super().__init__()
        self.document = Document()
        self.path = None
        self.selected = set()
        self.revision = 0
        self.lookup_serial = 0
        self.lookup_task = None
        self.saved_document = deepcopy(self.document)
        self.undo_stack = QUndoStack(self)
        self.undo_stack.indexChanged.connect(self.update_title)
        self.resize(1240, 820)
        self.setMinimumSize(820, 560)
        self.scene = QGraphicsScene(self)
        self.view = Canvas(self.scene, self)
        self.create_menus()
        self.create_toolbar()
        self.create_inspector()
        self.create_annotation_tools()
        self.inspector_content = self.inspector.widget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(self.inspector_content)
        self.inspector.setWidget(scroll)
        self.finish_workspace()
        self.refresh()

    def action(self, menu, text, callback, shortcut=None):
        action = QAction(text, self)
        if shortcut:
            action.setShortcut(shortcut)
        action.triggered.connect(callback)
        menu.addAction(action)
        return action

    def create_menus(self):
        file_menu = self.menuBar().addMenu("&File")
        for text, shortcut, callback in (
            ("&New", QKeySequence.StandardKey.New, self.new_document),
            ("&Open…", QKeySequence.StandardKey.Open, self.open_document),
            ("&Save", QKeySequence.StandardKey.Save, self.save_document),
            ("Save &As…", QKeySequence.StandardKey.SaveAs, self.save_as),
        ):
            self.action(file_menu, text, callback, shortcut)
        self.action(file_menu, "Export drawing…", self.export_drawing, "Ctrl+Shift+E")
        self.file_menu = file_menu
        edit = self.menuBar().addMenu("&Edit")
        undo = self.undo_action = self.undo_stack.createUndoAction(self, "Undo")
        undo.setShortcut(QKeySequence.StandardKey.Undo)
        edit.addAction(undo)
        redo = self.redo_action = self.undo_stack.createRedoAction(self, "Redo")
        redo.setShortcut(QKeySequence.StandardKey.Redo)
        edit.addAction(redo)
        self.action(
            edit, "Delete selection", self.delete_selection, QKeySequence.StandardKey.Delete
        )
        self.action(edit, "Select all", self.select_all, QKeySequence.StandardKey.SelectAll)
        self.action(edit, "Clean layout", self.cleanup, "Ctrl+Shift+L")
        self.action(edit, "Rotate molecule…", self.choose_rotation)
        self.action(edit, "Edit reaction caption…", self.edit_arrow_caption)
        self.edit_menu = edit
        view = self.menuBar().addMenu("&View")
        self.action(view, "Fit drawing", self.fit_drawing, "Ctrl+0")
        self.action(view, "Zoom in", lambda: self.zoom(1.2), QKeySequence.StandardKey.ZoomIn)
        self.action(
            view,
            "Zoom out",
            lambda: self.zoom(1 / 1.2),
            QKeySequence.StandardKey.ZoomOut,
        )
        self.view_menu = view

    def set_tool(self, key):
        self.view.cancel_gesture()
        self.flow_source = None
        self.view.tool = key
        self.tool_actions[key].setChecked(True)
        self.view.setFocus()
        help_text = {
            "select": "Drag to move · Shift adds to selection · Space-drag pans",
            "atom": "Click to place an atom or replace an existing element",
            "bond": "Drag from an atom to draw a bond · Alt disables angle snapping",
        }
        self.statusBar().showMessage(help_text.get(key, "Click or drag on the canvas"))
        if key == "electron" and self.workspace_mode != "mechanism":
            self.workspace_mode = "mechanism"
            self.mode_buttons["mechanism"].setChecked(True)
            self.guide.show()
            if hasattr(self, "rail_buttons"):
                self.rail_buttons["electron"].show()
                self.rail_buttons["plus"].show()
        self.view.setCursor(
            Qt.CursorShape.ArrowCursor if key == "select" else Qt.CursorShape.CrossCursor
        )
        self.update_workspace()

    def create_inspector(self):
        self._atom_fields_dirty = set()
        self._syncing_inspector = False
        self.inspector = QDockWidget("Selection", self)
        self.inspector.setMinimumWidth(280)
        self.inspector.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea)
        self.inspector.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.selection_label = QLabel()
        self.selection_label.setWordWrap(True)
        layout.addRow(self.selection_label)
        self.atom_element = QLineEdit()
        self.atom_charge = QSpinBox()
        self.atom_charge.setRange(-20, 20)
        self.atom_isotope = QSpinBox()
        self.atom_isotope.setRange(0, 400)
        self.atom_hydrogens = QSpinBox()
        self.atom_hydrogens.setRange(-1, 12)
        self.atom_hydrogens.setSpecialValueText("Automatic")
        self.atom_hydrogens.setValue(-1)
        self.atom_label = QLineEdit()
        self.atom_label.setPlaceholderText("Optional abbreviation")
        for label, control in (
            ("Element", self.atom_element),
            ("Charge", self.atom_charge),
            ("Isotope (0 = natural)", self.atom_isotope),
            ("Hydrogens", self.atom_hydrogens),
            ("Label", self.atom_label),
        ):
            layout.addRow(label, control)
        self.atom_apply = QPushButton("Apply atom properties")
        self.atom_apply.clicked.connect(self.apply_atom_properties)
        layout.addRow(self.atom_apply)
        for field, control in (
            ("element", self.atom_element),
            ("charge", self.atom_charge),
            ("isotope", self.atom_isotope),
            ("hydrogens", self.atom_hydrogens),
            ("label", self.atom_label),
        ):
            signal = control.textChanged if isinstance(control, QLineEdit) else control.valueChanged
            signal.connect(lambda value, name=field: self.mark_atom_field(name))
        self.bond_style = QComboBox()
        self.bond_style.addItems(["plain", "wedge", "hash", "wavy"])
        layout.addRow("Bond style", self.bond_style)
        apply_style = self.bond_apply = QPushButton("Apply bond style")
        apply_style.clicked.connect(self.apply_bond_style)
        layout.addRow(apply_style)
        self.inspector.setWidget(widget)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.inspector)

    def mark_atom_field(self, name):
        if not self._syncing_inspector:
            self._atom_fields_dirty.add(name)
            self.atom_apply.setEnabled(any(a.id in self.selected for a in self.document.atoms))

    def update_inspector(self):
        self._syncing_inspector = True
        atoms = [a for a in self.document.atoms if a.id in self.selected]
        bonds = [b for b in self.document.bonds if b.id in self.selected]
        self.inspector.setVisible(self.details_open and bool(self.selected))
        self.selection_label.setText(f"{len(atoms)} atoms · {len(bonds)} bonds selected")
        self.atom_apply.setEnabled(False)
        self.apply_bond_button.setEnabled(bool(bonds))
        if len(atoms) == 1:
            a = atoms[0]
            self.atom_element.setText(a.element)
            self.atom_charge.setValue(a.charge)
            self.atom_isotope.setValue(a.isotope)
            self.atom_hydrogens.setValue(a.hydrogens)
            self.atom_label.setText(a.label)
            self.atom_element.setPlaceholderText("Element symbol")
            self.atom_label.setPlaceholderText("Optional abbreviation")
        elif len(atoms) > 1:
            self.atom_element.clear()
            self.atom_label.clear()
            self.atom_element.setPlaceholderText("Keep existing elements")
            self.atom_label.setPlaceholderText("Keep existing labels")
        if len(bonds) == 1:
            self.bond_style.setCurrentText(bonds[0].style)
            self.order.setValue(bonds[0].order)
        self._atom_fields_dirty.clear()
        self._syncing_inspector = False

    def edit(self, title, mutation):
        result = deepcopy(self.document)
        try:
            mutation(result)
            self.commit(title, result)
        except (ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, "Could not apply change", str(exc))

    def commit(self, title, document):
        document.validate()
        if document != self.document:
            self.undo_stack.push(DocumentCommand(self, title, self.document, document))

    def apply_atom_properties(self):
        properties = dict(
            element=self.atom_element.text().strip(),
            charge=self.atom_charge.value(),
            isotope=self.atom_isotope.value(),
            hydrogens=self.atom_hydrogens.value(),
            label=self.atom_label.text().strip(),
        )
        properties = {
            key: value
            for key, value in properties.items()
            if key in self._atom_fields_dirty and (key != "element" or value)
        }
        self.edit(
            "Change atom properties",
            lambda d: setattr(
                d,
                "atoms",
                [
                    replace(a, **{k: v for k, v in properties.items() if k != "element" or v})
                    if a.id in self.selected
                    else a
                    for a in d.atoms
                ],
            ),
        )

    def set_bond_order(self):
        self.edit(
            "Change bond order",
            lambda d: setattr(
                d,
                "bonds",
                [
                    replace(b, order=self.order.value(), aromatic=False, stereo=0, stereo_atoms=[])
                    if b.id in self.selected
                    else b
                    for b in d.bonds
                ],
            ),
        )

    def apply_bond_style(self):
        self.edit(
            "Change bond style",
            lambda d: setattr(
                d,
                "bonds",
                [
                    replace(b, style=self.bond_style.currentText(), order=1, aromatic=False)
                    if b.id in self.selected
                    else b
                    for b in d.bonds
                ],
            ),
        )

    def select_all(self):
        self.selected = {
            e.id
            for e in [
                *self.document.atoms,
                *self.document.bonds,
                *self.document.arrows,
                *self.document.notes,
            ]
        }
        self.refresh()

    def delete_selection(self):
        def remove(d):
            d.atoms = [a for a in d.atoms if a.id not in self.selected]
            ids = {a.id for a in d.atoms}
            d.bonds = [
                replace(b, stereo_atoms=[], stereo=0)
                if any(a not in ids for a in b.stereo_atoms)
                else b
                for b in d.bonds
                if b.id not in self.selected and b.start in ids and b.end in ids
            ]
            d.sources = [
                replace(s, atom_ids=[a for a in s.atom_ids if a in ids])
                for s in d.sources
                if any(a in ids for a in s.atom_ids)
            ]
            if hasattr(self, "remove_annotations"):
                self.remove_annotations(d)

        self.edit("Delete selection", remove)
        self.selected.clear()
        self.refresh()

    def cleanup(self):
        if not self.document.atoms:
            return
        try:
            self.commit("Clean layout", clean_layout(self.document))
        except (ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, "Could not clean layout", str(exc))

    def start_lookup(self):
        query = self.name_input.text().strip()
        if not query:
            self.name_input.setFocus()
            return
        self.launch_lookup(query, self.input_mode.currentText())

    def launch_lookup(self, query, mode, intent=None):
        self.cancel_lookup()
        self.lookup_intent = intent
        self.feedback.hide()
        serial = self.lookup_serial
        self.lookup_revision = self.revision
        task = LookupTask(serial, query, mode)
        self.lookup_task = task
        task.signals.finished.connect(self.lookup_finished)
        self.lookup_button.setEnabled(False)
        self.lookup_button.setText("Generating…")
        self.cancel_button.show()
        self.statusBar().showMessage("Generating structure…")
        QThreadPool.globalInstance().start(task)

    def cancel_lookup(self, *_):
        self.lookup_serial += 1
        self.lookup_intent = None
        if self.lookup_task:
            self.lookup_task.cancelled.set()
            self.lookup_task = None
            self.statusBar().showMessage("Structure generation cancelled", 3000)
        if hasattr(self, "lookup_button"):
            self.lookup_button.setEnabled(True)
            self.lookup_button.setText("Generate")
            self.cancel_button.hide()
        self.update_pathway_guide()

    def lookup_finished(self, serial, document, warning, error):
        if serial != self.lookup_serial or self.lookup_revision != self.revision:
            if serial == self.lookup_serial:
                self.cancel_lookup()
                self.statusBar().showMessage(
                    "Drawing changed. Generate again to insert a structure."
                )
            return
        self.lookup_task = None
        self.lookup_button.setEnabled(True)
        self.lookup_button.setText("Generate")
        self.cancel_button.hide()
        self.update_pathway_guide()
        if error:
            self.show_feedback(error)
            self.statusBar().showMessage("Try another name, SMILES, or manual drawing.")
            return
        from molecules.ui.structure_dialog import StructureDialog

        intent = getattr(self, "lookup_intent", None)
        self.update_pathway_guide()
        dialog = StructureDialog(document, warning, self)
        if (
            dialog.exec() == QDialog.DialogCode.Accepted
            and serial == self.lookup_serial
            and self.lookup_revision == self.revision
        ):
            if intent:
                self.insert_pathway_product(document, intent)
            else:
                self.insert_document(document)

    def insert_document(self, document):
        result = deepcopy(self.document)
        if not result.atoms and not result.notes and not result.arrows:
            result.title = document.title
        right = max((a.x for a in result.atoms), default=-180)
        left = min((a.x for a in document.atoms), default=0)
        offset = right + 140 - left if result.atoms else 0
        result.atoms += [
            replace(
                a,
                x=a.x + offset,
                step=max((existing.step for existing in self.document.atoms), default=0),
            )
            for a in document.atoms
        ]
        result.bonds += deepcopy(document.bonds)
        result.sources += deepcopy(document.sources)
        self.selected = {a.id for a in document.atoms}
        self.commit("Insert molecule", result)
        self.fit_drawing()
        self.set_tool("select")

    def selection_document(self):
        d = deepcopy(self.document)
        ids = {a.id for a in d.atoms if a.id in self.selected}
        for b in d.bonds:
            if b.id in self.selected:
                ids.update((b.start, b.end))
        d.atoms = [a for a in d.atoms if a.id in ids]
        d.bonds = [
            replace(b, stereo_atoms=[], stereo=0)
            if any(a not in ids for a in b.stereo_atoms)
            else b
            for b in d.bonds
            if b.start in ids and b.end in ids
        ]
        d.sources = [
            replace(s, atom_ids=[a for a in s.atom_ids if a in ids])
            for s in d.sources
            if any(a in ids for a in s.atom_ids)
        ]
        if hasattr(self, "filter_annotations"):
            self.filter_annotations(d, ids)
        return d

    def export_drawing(self):
        from molecules.exports.visual import export
        from molecules.ui.export_dialog import ExportDialog

        if (
            not self.document.atoms
            and not getattr(self.document, "notes", [])
            and not getattr(self.document, "arrows", [])
        ):
            self.statusBar().showMessage("Add a structure or annotation before exporting.")
            return
        dialog = ExportDialog(self.document, self.selection_document(), self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        options = dialog.options()
        extension = options["format"].lower()
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export drawing", f"Drawing.{extension}", f"{options['format']} (*.{extension})"
        )
        if not filename:
            return
        path = Path(filename)
        if path.suffix.lower() != "." + extension:
            path = Path(str(path) + "." + extension)
            if (
                path.exists()
                and QMessageBox.question(
                    self,
                    "Replace export?",
                    f"Replace {path.name}?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                != QMessageBox.StandardButton.Yes
            ):
                return
        try:
            export(dialog.chosen_document(), path, **options)
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, "Could not export drawing", str(exc))
            return
        self.statusBar().showMessage(f"Exported {path.name}", 5000)

    def is_dirty(self):
        return self.document != self.saved_document

    def confirm_discard(self):
        if not self.is_dirty():
            return True
        response = QMessageBox.question(
            self,
            "Save changes?",
            "Save this drawing before continuing?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if response == QMessageBox.StandardButton.Save:
            return self.save_document()
        return response == QMessageBox.StandardButton.Discard

    def new_document(self):
        if not self.confirm_discard():
            return
        self.cancel_lookup()
        self.view.cancel_gesture()
        self.document = Document()
        self.path = None
        self.reset_history()

    def reset_history(self):
        self.flow_source = None
        self.details_open = False
        self.inspector.hide()
        self.guide.setVisible(self.workspace_mode == "mechanism")
        self.pathway_guide.setVisible(self.workspace_mode == "pathway")
        self.pathway_source = None
        self.selected.clear()
        self.saved_document = deepcopy(self.document)
        self.undo_stack.clear()
        self.revision += 1
        self.refresh()
        self.fit_drawing()

    def open_document(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Open structure", "", FILE_FILTER)
        if not filename:
            return
        try:
            document = load_document(Path(filename))
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Could not open document", str(exc))
            return
        if not self.confirm_discard():
            return
        self.cancel_lookup()
        self.view.cancel_gesture()
        self.document = document
        self.path = Path(filename)
        self.reset_history()

    def save_document(self):
        return self.save_as() if self.path is None else self._save_to(self.path)

    def save_as(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save drawing", str(self.path or "Untitled.molecules.json"), FILE_FILTER
        )
        if not filename:
            return False
        if not filename.endswith(".molecules.json"):
            filename += ".molecules.json"
            if Path(filename).exists():
                if (
                    QMessageBox.question(
                        self,
                        "Replace document?",
                        f"Replace {Path(filename).name}?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No,
                    )
                    != QMessageBox.StandardButton.Yes
                ):
                    return False
        return self._save_to(Path(filename))

    def _save_to(self, path):
        try:
            save_document(self.document, path)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Could not save document", str(exc))
            return False
        self.path = path
        self.saved_document = deepcopy(self.document)
        self.undo_stack.setClean()
        self.update_title()
        self.statusBar().showMessage("Drawing saved", 4000)
        return True

    def update_title(self, *_):
        title = self.path.name if self.path else self.document.title
        self.setWindowTitle(f"{title}{' *' if self.is_dirty() else ''} — Molecules")
        if hasattr(self, "document_badge"):
            state = (
                "Unsaved changes" if self.is_dirty() else "Saved" if self.path else "New drawing"
            )
            self._document_badge_text = f"{title} · {state}"
            self.document_badge.setText(self._document_badge_text)

    def refresh(self):
        populate(self.scene, self.document, self.selected, editing=True)
        self.scene.setSceneRect(
            self.scene.itemsBoundingRect()
            .united(QRectF(-500, -350, 1000, 700))
            .adjusted(-200, -200, 200, 200)
        )
        self.update_title()
        inspector_state = (frozenset(self.selected), self.revision)
        if getattr(self, "_inspector_state", None) != inspector_state:
            self.update_inspector()
            self.update_annotation_inspector()
            self.update_inspector_visibility()
            self._inspector_state = inspector_state
        self.statusBar().showMessage(
            f"{len(self.document.atoms)} atoms · {len(self.document.bonds)} bonds"
        )
        self.update_workspace()

    def fit_drawing(self):
        bounds = self.scene.itemsBoundingRect()
        if not self.document.atoms and not self.document.arrows and not self.document.notes:
            self.view.resetTransform()
            self.view.centerOn(0, 0)
        else:
            self.view.fitInView(
                bounds.adjusted(-100, -100, 100, 100), Qt.AspectRatioMode.KeepAspectRatio
            )
            if self.view.transform().m11() > 1.5:
                self.view.resetTransform()
                self.view.scale(1.5, 1.5)
                self.view.centerOn(bounds.center())
        self.update_workspace()

    def showEvent(self, event):
        super().showEvent(event)
        if not getattr(self, "_has_shown", False):
            if not self.document.atoms:
                self.name_input.setFocus()
            self._has_shown = True

    def closeEvent(self, event):
        self.view.cancel_gesture()
        if self.confirm_discard():
            self.cancel_lookup()
            event.accept()
        else:
            event.ignore()
