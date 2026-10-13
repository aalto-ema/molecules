"""Canvas gestures produce one undoable document change each."""

import math
from copy import deepcopy
from dataclasses import replace

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsView, QLineEdit, QMenu

from molecules.domain.document import Arrow, Atom, Bond, new_id
from molecules.domain.geometry import rotate_molecules, rotation_atoms, selected_atoms
from molecules.rendering.scene import electron_geometry, molecule_rect


class AtomInput(QLineEdit):
    confirmed = Signal(str)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.confirmed.emit(self.text())
            self.hide()
            self.parentWidget().setFocus()
        elif event.key() == Qt.Key.Key_Escape:
            self.hide()
            self.parentWidget().setFocus()
        else:
            super().keyPressEvent(event)

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.hide()


class Canvas(QGraphicsView):
    def __init__(self, scene, editor):
        super().__init__(scene)
        self.editor = editor
        self.tool = "select"
        self.press_point = None
        self.start_id = None
        self.before = None
        self.moving = set()
        self.curve_id = None
        self.rotating = False
        self.rotation_angle = 0
        self.rotation_pivot = None
        self.rotation_radius = 0
        self.hover_kind = None
        self.hover_id = None
        self.flow_preview = None
        self.inline_atom = None
        self.panning = False
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing)
        self.setBackgroundBrush(QColor("white"))
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

    def rotation_geometry(self):
        if self.tool != "select" or self.before is not None and not self.rotating:
            return None
        picked = selected_atoms(self.editor.document, self.editor.selected)
        if len(picked) < 2 or picked != rotation_atoms(self.editor.document, self.editor.selected):
            return None
        bounds = molecule_rect(self.editor.document, picked)
        if self.rotating:
            pivot = self.rotation_pivot
            radius = self.rotation_radius
            theta = math.radians(self.rotation_angle - 90)
            handle = pivot + QPointF(math.cos(theta) * radius, math.sin(theta) * radius)
        else:
            pivot = bounds.center()
            radius = bounds.height() / 2 + 28 / max(0.2, self.transform().m11())
            handle = pivot + QPointF(0, -radius)
        return pivot, handle, bounds, radius

    def hit(self, point):
        geometry = self.rotation_geometry()
        if geometry is not None:
            _, handle, _, _ = geometry
            if math.hypot(point.x() - handle.x(), point.y() - handle.y()) <= 12 / max(
                0.2, self.transform().m11()
            ):
                return "rotation", "rotation"
        radius = 8 / max(0.2, self.transform().m11())
        items = self.scene().items(
            QRectF(point.x() - radius, point.y() - radius, 2 * radius, 2 * radius)
        )
        for kind in ("handle", "atom", "bond", "arrow", "note"):
            for item in items:
                if item.data(0) == kind:
                    return kind, item.data(1)
        return None, None

    def mousePressEvent(self, event):
        if self.panning or event.button() == Qt.MouseButton.MiddleButton:
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            super().mousePressEvent(event)
            return
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        point = self.mapToScene(event.position().toPoint())
        kind, identity = self.hit(point)
        self.press_point = point
        self.start_id = identity if kind == "atom" else None
        if self.tool == "bond" and self.start_id:
            atom = next(a for a in self.editor.document.atoms if a.id == self.start_id)
            self.press_point = QPointF(atom.x, atom.y)
        if self.tool == "select":
            if kind == "rotation":
                pivot, _, _, radius = self.rotation_geometry()
                self.rotation_pivot, self.rotation_radius = pivot, radius
                self.rotation_start = math.atan2(point.y() - pivot.y(), point.x() - pivot.x())
                self.rotation_angle = 0
                self.rotating = True
                self.before = deepcopy(self.editor.document)
                return
            if identity:
                if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    self.editor.selected.symmetric_difference_update({identity})
                elif identity not in self.editor.selected:
                    self.editor.selected = {identity}
                if kind == "atom" and event.modifiers() & Qt.KeyboardModifier.AltModifier:
                    self.editor.select_molecule(identity)
                self.curve_id = identity if kind == "handle" else None
                self.before = deepcopy(self.editor.document)
                self.moving = {a.id for a in self.before.atoms if a.id in self.editor.selected}
                for b in self.before.bonds:
                    if b.id in self.editor.selected:
                        self.moving.update((b.start, b.end))
            elif not event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self.editor.selected.clear()
            self.editor.refresh()
        elif self.tool == "atom":
            element = self.editor.element.currentText()
            if kind == "atom":
                self.editor.edit(
                    "Change element",
                    lambda d: setattr(
                        d,
                        "atoms",
                        [
                            replace(a, element=element, aromatic=False, chiral=0, hydrogens=-1)
                            if a.id == identity
                            else a
                            for a in d.atoms
                        ],
                    ),
                )
            else:
                self.editor.edit(
                    "Add atom",
                    lambda d: d.atoms.append(
                        Atom(
                            new_id(),
                            element,
                            point.x(),
                            point.y(),
                            step=max((a.step for a in d.atoms), default=0),
                        )
                    ),
                )
            self.press_point = None
        elif self.tool == "bond" and kind == "bond":
            self.editor.selected = {identity}
            self.editor.cycle_bond(identity)
            self.press_point = None
        elif hasattr(self.editor, "annotation_press"):
            if self.editor.annotation_press(self.tool, kind, identity, point):
                self.press_point = None

    def mouseMoveEvent(self, event):
        if self.panning or self.dragMode() == QGraphicsView.DragMode.ScrollHandDrag:
            super().mouseMoveEvent(event)
            return
        point = self.mapToScene(event.position().toPoint())
        self.hover_kind, self.hover_id = self.hit(point)
        if self.tool == "electron" and self.editor.flow_source is not None:
            anchor = self.hover_id if self.hover_kind in ("atom", "bond") else ""
            source, start = self.editor.flow_source
            self.flow_preview = None if anchor and anchor == source else (point, anchor)
            target_label = self.editor.flow_stages[1][1]
            target_label.setText(
                "Choose a different target."
                if anchor and anchor == source
                else self.editor.anchor_description(anchor) + " · click to confirm"
            )
        self.viewport().update()
        if self.press_point is not None:
            if self.before is not None:
                if self.rotating:
                    theta = math.atan2(
                        point.y() - self.rotation_pivot.y(), point.x() - self.rotation_pivot.x()
                    )
                    angle = math.degrees(theta - self.rotation_start)
                    angle = (angle + 180) % 360 - 180
                    if not event.modifiers() & Qt.KeyboardModifier.AltModifier:
                        angle = round(angle / 15) * 15
                    self.rotation_angle = angle
                    result = rotate_molecules(
                        self.before,
                        self.editor.selected,
                        angle,
                        (self.rotation_pivot.x(), self.rotation_pivot.y()),
                    )
                    self.editor.canvas_hint.setText(
                        f"Rotate {angle:.1f}° · Alt for free rotation · Escape cancels"
                    )
                else:
                    delta = point - self.press_point
                    result = deepcopy(self.before)
                    result.atoms = [
                        replace(a, x=a.x + delta.x(), y=a.y + delta.y())
                        if a.id in self.moving
                        else a
                        for a in result.atoms
                    ]
                    if self.curve_id:
                        from molecules.rendering.scene import arrow_geometry

                        arrow = next(a for a in result.arrows if a.id == self.curve_id)
                        start, end, _ = arrow_geometry(result, arrow)
                        delta_arrow = end - start
                        length = max(0.01, math.hypot(delta_arrow.x(), delta_arrow.y()))
                        displacement = point - (start + end) * 0.5
                        curve = (
                            -delta_arrow.y() * displacement.x() + delta_arrow.x() * displacement.y()
                        ) / length
                        result.arrows = [
                            replace(a, curvature=curve) if a.id == arrow.id else a
                            for a in result.arrows
                        ]
                    elif hasattr(self.editor, "move_annotations"):
                        self.editor.move_annotations(result, delta, self.editor.selected)
                self.editor.document = result
                self.editor.refresh()
            elif self.tool == "select":
                self.editor.refresh()
                self.scene().addRect(
                    QRectF(self.press_point, point).normalized(), QPen(QColor("#397cdb"), 1)
                )
            else:
                if self.tool == "bond":
                    kind, end_id = self.hit(point)
                    point = self.bond_endpoint(
                        self.press_point,
                        point,
                        event.modifiers(),
                        end_id if kind == "atom" else None,
                    )
                self.editor.refresh()
                self.scene().addLine(
                    self.press_point.x(),
                    self.press_point.y(),
                    point.x(),
                    point.y(),
                    QPen(QColor("#397cdb"), 1.5, Qt.PenStyle.DashLine),
                )
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.dragMode() == QGraphicsView.DragMode.ScrollHandDrag:
            super().mouseReleaseEvent(event)
            if not self.panning:
                self.setDragMode(QGraphicsView.DragMode.NoDrag)
            return
        if event.button() != Qt.MouseButton.LeftButton or self.press_point is None:
            return
        point = self.mapToScene(event.position().toPoint())
        if self.before is not None:
            result = self.editor.document
            self.editor.document = self.before
            self.editor.commit("Rotate molecule" if self.rotating else "Move selection", result)
        elif self.tool == "select":
            rect = QRectF(self.press_point, point).normalized()
            for item in self.scene().items(rect):
                if item.data(1):
                    self.editor.selected.add(item.data(1))
        elif self.tool == "bond":
            start_point = self.press_point
            start_id = self.start_id
            kind, end_id = self.hit(point)
            end_id = end_id if kind == "atom" else None
            if end_id == start_id and start_id:
                self.cancel_gesture()
                return
            point = self.bond_endpoint(start_point, point, event.modifiers(), end_id)

            def add_bond(d):
                first, last = start_id or new_id(), end_id or new_id()
                step = next(
                    (a.step for a in d.atoms if a.id == start_id),
                    max((a.step for a in d.atoms), default=0),
                )
                if end_id and any(a.id == end_id and a.step != step for a in d.atoms):
                    raise ValueError("Connect atoms within the same mechanism step.")
                if not start_id:
                    d.atoms.append(Atom(first, "C", start_point.x(), start_point.y(), step=step))
                if not end_id:
                    d.atoms.append(
                        Atom(
                            last, self.editor.element.currentText(), point.x(), point.y(), step=step
                        )
                    )
                if not any({b.start, b.end} == {first, last} for b in d.bonds):
                    d.bonds.append(Bond(new_id(), first, last, self.editor.order.value()))

            self.editor.edit("Draw bond", add_bond)
        elif hasattr(self.editor, "annotation_release"):
            self.editor.annotation_release(self.tool, self.press_point, point)
        self.before = None
        self.rotating = False
        self.rotation_angle = 0
        self.press_point = None
        self.curve_id = None
        self.moving.clear()
        self.flow_preview = None
        self.editor.refresh()

    def bond_endpoint(self, start, point, modifiers, end_id=None):
        if end_id:
            atom = next(a for a in self.editor.document.atoms if a.id == end_id)
            return QPointF(atom.x, atom.y)
        dx, dy = point.x() - start.x(), point.y() - start.y()
        angle = math.atan2(dy, dx) if math.hypot(dx, dy) > 5 else -math.pi / 6
        if not modifiers & Qt.KeyboardModifier.AltModifier:
            angle = round(angle / (math.pi / 6)) * (math.pi / 6)
        return start + QPointF(60 * math.cos(angle), 60 * math.sin(angle))

    def cancel_gesture(self):
        if self.before is not None:
            self.editor.document = self.before
        self.before = None
        self.rotating = False
        self.rotation_angle = 0
        self.press_point = None
        self.start_id = None
        self.curve_id = None
        self.moving.clear()
        self.flow_preview = None
        self.editor.refresh()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.cancel_gesture()
            self.editor.selected.clear()
            self.editor.flow_source = None
            self.editor.refresh()
        elif event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self.panning = True
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        elif event.modifiers() in (
            Qt.KeyboardModifier.NoModifier,
            Qt.KeyboardModifier.ShiftModifier,
        ):
            key = event.text().upper()
            if key in ("C", "N", "O", "S", "P", "F", "H"):
                self.editor.quick_element(key)
            elif key in ("+", "=", "-") and self.editor.selected:
                self.editor.adjust_charge(-1 if key == "-" else 1)
            elif key in ("1", "2", "3"):
                self.editor.quick_order(int(key))
            else:
                super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self.panning = False
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
        super().keyReleaseEvent(event)

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        scale = self.transform().m11() * factor
        if 0.2 <= scale <= 5:
            self.scale(factor, factor)
        self.editor.update_workspace()
        event.accept()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.editor.position_overlays()

    def leaveEvent(self, event):
        self.hover_id = None
        self.flow_preview = None
        self.viewport().update()
        super().leaveEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton or self.tool != "select":
            super().mouseDoubleClickEvent(event)
            return
        point = self.mapToScene(event.position().toPoint())
        kind, identity = self.hit(point)
        self.cancel_gesture()
        if kind == "bond":
            self.editor.cycle_bond(identity)
        elif kind == "atom":
            self.editor.selected = {identity}
            self.editor.refresh()
            self.show_atom_input(identity, point)
        elif kind == "arrow":
            self.editor.selected = {identity}
            self.editor.refresh()
            self.editor.edit_arrow_caption()
        elif kind == "note":
            self.editor.selected = {identity}
            self.editor.refresh()
            self.editor.edit_note()

    def show_atom_input(self, identity, point):
        if self.inline_atom is not None:
            self.inline_atom.deleteLater()
        self.inline_atom = AtomInput(self.viewport())
        atom = next(a for a in self.editor.document.atoms if a.id == identity)
        self.inline_atom.setText(atom.label or atom.element)
        self.inline_atom.setToolTip("Element or abbreviation · Enter applies · Escape cancels")
        self.inline_atom.setAccessibleName("Edit atom element or label")
        self.inline_atom.setFixedSize(140, 38)
        position = self.mapFromScene(point)
        self.inline_atom.move(
            max(4, min(position.x() - 70, self.viewport().width() - 144)),
            max(4, min(position.y() + 20, self.viewport().height() - 42)),
        )
        self.inline_atom.confirmed.connect(
            lambda text: self.editor.finish_atom_text(identity, text)
        )
        self.inline_atom.show()
        self.inline_atom.setFocus()
        self.inline_atom.selectAll()

    def contextMenuEvent(self, event):
        point = self.mapToScene(event.pos())
        kind, identity = self.hit(point)
        if identity:
            self.editor.selected = {identity}
            self.editor.refresh()
        menu = QMenu(self)
        if kind == "atom":
            elements = menu.addMenu("Element")
            for element in ("C", "N", "O", "S", "P", "H", "F", "Cl", "Br"):
                elements.addAction(
                    element, lambda checked=False, e=element: self.editor.quick_element(e)
                )
            menu.addAction("Charge +1", lambda: self.editor.adjust_charge(1))
            menu.addAction("Charge −1", lambda: self.editor.adjust_charge(-1))
            menu.addAction("Select molecule", lambda: self.editor.select_molecule(identity))
            menu.addMenu(self.editor.rotation_menu())
        elif kind == "bond":
            for order, text in ((1, "Single bond"), (2, "Double bond"), (3, "Triple bond")):
                menu.addAction(text, lambda checked=False, o=order: self.editor.quick_order(o))
        elif kind == "arrow":
            arrow = next(a for a in self.editor.document.arrows if a.id == identity)
            if arrow.kind == "electron":
                menu.addAction("Flip curve", self.editor.flip_curve)
            else:
                menu.addAction("Edit caption…", self.editor.edit_arrow_caption)
                menu.addAction("Reverse arrow", self.editor.reverse_reaction_arrows)
        if identity:
            menu.addSeparator()
            menu.addAction("Advanced properties", self.editor.toggle_details)
            menu.addAction("Delete", self.editor.delete_selection)
        else:
            menu.addAction("Fit drawing", self.editor.fit_drawing)
            menu.addAction("Paste", self.editor.paste_selection)
        menu.exec(event.globalPos())

    def suggest_curvature(self, start, end):
        delta = end - start
        length = max(1, math.hypot(delta.x(), delta.y()))
        normal = QPointF(-delta.y() / length, delta.x() / length)
        magnitude = max(30, min(85, length * 0.45))
        middle = (start + end) * 0.5
        obstacles = [
            QPointF(a.x, a.y)
            for a in self.editor.document.atoms
            if (QPointF(a.x, a.y) - start).manhattanLength() > 10
            and (QPointF(a.x, a.y) - end).manhattanLength() > 10
        ]

        def clearance(sign):
            point = middle + normal * (magnitude * sign)
            return min(((point - a).manhattanLength() for a in obstacles), default=100)

        return magnitude if clearance(1) >= clearance(-1) else -magnitude

    def drawForeground(self, painter, rect):
        super().drawForeground(painter, rect)
        scale = max(0.2, self.transform().m11())
        geometry = self.rotation_geometry()
        if geometry is not None:
            pivot, handle, bounds, _ = geometry
            painter.setPen(QPen(QColor(52, 105, 220, 100), 1 / scale, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(bounds.adjusted(-8 / scale, -8 / scale, 8 / scale, 8 / scale))
            painter.drawLine(pivot, handle)
            painter.setPen(QPen(QColor("#3469dc"), 1.3 / scale))
            painter.setBrush(QColor("white"))
            painter.drawEllipse(handle, 11 / scale, 11 / scale)
            font = QFont("Arial")
            font.setPixelSize(max(1, round(15 / scale)))
            painter.setFont(font)
            painter.drawText(
                QRectF(handle.x() - 10 / scale, handle.y() - 10 / scale, 20 / scale, 20 / scale),
                Qt.AlignmentFlag.AlignCenter,
                "↻",
            )
        painter.setPen(QPen(QColor("#3469dc"), 1.3 / scale))
        painter.setBrush(QColor(52, 105, 220, 18))
        if self.hover_kind == "atom" and self.hover_id:
            atom = next((a for a in self.editor.document.atoms if a.id == self.hover_id), None)
            if atom:
                painter.drawEllipse(QPointF(atom.x, atom.y), 10 / scale, 10 / scale)
        elif self.hover_kind == "bond" and self.hover_id:
            bond = next((b for b in self.editor.document.bonds if b.id == self.hover_id), None)
            if bond:
                atoms = {a.id: a for a in self.editor.document.atoms}
                a, b = atoms[bond.start], atoms[bond.end]
                painter.setPen(QPen(QColor(52, 105, 220, 50), 8 / scale))
                painter.drawLine(QPointF(a.x, a.y), QPointF(b.x, b.y))
        if self.flow_preview and self.editor.flow_source:
            end, anchor = self.flow_preview
            source, start = self.editor.flow_source
            arrow = Arrow(
                "preview",
                "electron",
                start.x(),
                start.y(),
                end.x(),
                end.y(),
                self.suggest_curvature(start, end),
                source,
                anchor,
                self.editor.flow_count.currentData(),
            )
            start, end, control = electron_geometry(self.editor.document, arrow)
            path = QPainterPath(start)
            path.quadTo(control, end)
            painter.setPen(QPen(QColor("#3469dc"), 1.7, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)
            tangent = end - control
            length = max(0.01, math.hypot(tangent.x(), tangent.y()))
            direction = tangent / length
            normal = QPointF(-direction.y(), direction.x())
            for sign in [1] if arrow.electrons == 1 else [-1, 1]:
                painter.drawLine(end, end - direction * 10 + normal * sign * 5)
