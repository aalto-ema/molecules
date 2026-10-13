"""A single geometry projection shared by the editor and all visual exports."""

import math
from html import escape

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QFont, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QGraphicsScene

from molecules.domain.document import Document
from molecules.domain.geometry import connected_atoms

INK = QColor("#25313d")
ACCENT = QColor("#3469dc")


def tag(item, kind, identity):
    item.setData(0, kind)
    item.setData(1, identity)
    return item


def add_label(scene, text, x, y, kind, identity, size=18, html=False):
    font = QFont("Arial")
    font.setPixelSize(size)
    item = scene.addText("" if html else text, font)
    if html:
        item.setHtml(text)
    item.setDefaultTextColor(INK)
    rect = item.boundingRect()
    item.setPos(x - rect.width() / 2, y - rect.height() / 2)
    item.setZValue(3)
    tag(item, kind, identity)
    return item


def populate(scene: QGraphicsScene, document, selected=frozenset(), editing=False):
    scene.clear()
    atoms = {a.id: a for a in document.atoms}
    degree = {a.id: 0 for a in document.atoms}
    for bond in document.bonds:
        degree[bond.start] += 1
        degree[bond.end] += 1
    labels = {}
    for atom in document.atoms:
        visible = (
            atom.element != "C"
            or degree[atom.id] == 0
            or atom.charge
            or atom.isotope
            or atom.label
            or atom.hydrogens >= 0
            or atom.radicals
            or atom.lone_pairs
        )
        if visible:
            text = escape(atom.label or atom.element)
            if atom.isotope:
                text = f"<sup>{atom.isotope}</sup>" + text
            valence = {
                "C": 4,
                "N": 3,
                "O": 2,
                "F": 1,
                "Cl": 1,
                "Br": 1,
                "I": 1,
                "S": 2,
                "P": 3,
            }.get(atom.element, 0)
            if atom.element == "N":
                valence += atom.charge
            elif atom.element == "O":
                valence += atom.charge
            elif atom.element == "C" and atom.charge:
                valence = 3
            bonded = sum(b.order for b in document.bonds if atom.id in (b.start, b.end))
            hydrogen_count = (
                atom.hydrogens if atom.hydrogens >= 0 else max(0, valence - bonded - atom.radicals)
            )
            if atom.aromatic and atom.element == "N" and atom.hydrogens < 0:
                hydrogen_count = 0
            if hydrogen_count and not atom.label:
                text += "H" + (f"<sub>{hydrogen_count}</sub>" if hydrogen_count > 1 else "")
            if atom.charge:
                charge = str(abs(atom.charge)) if abs(atom.charge) != 1 else ""
                charge += "+" if atom.charge > 0 else "−"
                text += f"<sup>{charge}</sup>"
            item = add_label(scene, text, atom.x, atom.y, "atom", atom.id, html=True)
            labels[atom.id] = item
            if atom.label and len(atom.label) > 3 and degree[atom.id] == 1:
                connection = next(b for b in document.bonds if atom.id in (b.start, b.end))
                neighbor = atoms[
                    connection.end if connection.start == atom.id else connection.start
                ]
                dx, dy = atom.x - neighbor.x, atom.y - neighbor.y
                rect = item.boundingRect()
                if abs(dx) >= abs(dy):
                    item.setX(atom.x + 4 if dx >= 0 else atom.x - rect.width() - 4)
                else:
                    item.setY(atom.y + 4 if dy >= 0 else atom.y - rect.height() - 4)
        if editing:
            halo = scene.addEllipse(
                atom.x - 11,
                atom.y - 11,
                22,
                22,
                QPen(ACCENT, 1.5) if atom.id in selected else QPen(Qt.PenStyle.NoPen),
                QColor(57, 124, 219, 35) if atom.id in selected else QColor(0, 0, 0, 0),
            )
            halo.setZValue(4)
            tag(halo, "atom", atom.id)
    for bond in document.bonds:
        a, b = atoms[bond.start], atoms[bond.end]
        dx, dy = b.x - a.x, b.y - a.y
        length = math.hypot(dx, dy)
        if length < 0.01:
            continue
        ux, uy = dx / length, dy / length
        nx, ny = -uy, ux

        def trim(atom, direction):
            item = labels.get(atom.id)
            if item is None:
                return 0
            rect = item.sceneBoundingRect().adjusted(-3, -3, 3, 3)
            origin = QPointF(atom.x, atom.y)
            if not rect.contains(origin):
                return 0
            distances = []
            if abs(direction.x()) > 0.001:
                edge = rect.right() if direction.x() > 0 else rect.left()
                distances.append((edge - origin.x()) / direction.x())
            if abs(direction.y()) > 0.001:
                edge = rect.bottom() if direction.y() > 0 else rect.top()
                distances.append((edge - origin.y()) / direction.y())
            return min(distances, default=0)

        first_trim, last_trim = trim(a, QPointF(ux, uy)), trim(b, QPointF(-ux, -uy))
        start = QPointF(a.x + ux * first_trim, a.y + uy * first_trim)
        end = QPointF(b.x - ux * last_trim, b.y - uy * last_trim)
        if first_trim + last_trim < length - 1:
            pen = QPen(ACCENT if bond.id in selected else INK, 2)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            if bond.style == "wedge":
                item = scene.addPolygon(
                    QPolygonF(
                        [start, end + QPointF(nx * 6, ny * 6), end - QPointF(nx * 6, ny * 6)]
                    ),
                    QPen(Qt.PenStyle.NoPen),
                    pen.color(),
                )
                tag(item, "bond", bond.id)
            elif bond.style == "hash":
                for i in range(1, 9):
                    t = i / 9
                    p = start * (1 - t) + end * t
                    tag(
                        scene.addLine(
                            p.x() - nx * t * 6,
                            p.y() - ny * t * 6,
                            p.x() + nx * t * 6,
                            p.y() + ny * t * 6,
                            pen,
                        ),
                        "bond",
                        bond.id,
                    )
            elif bond.style == "wavy":
                path = QPainterPath(start)
                for i in range(1, 33):
                    t = i / 32
                    p = (
                        start * (1 - t)
                        + end * t
                        + QPointF(nx, ny) * (3 * math.sin(t * 8 * math.pi))
                    )
                    path.lineTo(p)
                tag(scene.addPath(path, pen), "bond", bond.id)
            else:
                for i in range(bond.order):
                    offset = (i - (bond.order - 1) / 2) * 5
                    tag(
                        scene.addLine(
                            start.x() + nx * offset,
                            start.y() + ny * offset,
                            end.x() + nx * offset,
                            end.y() + ny * offset,
                            pen,
                        ),
                        "bond",
                        bond.id,
                    )
        if editing:
            path = QPainterPath(QPointF(a.x, a.y))
            path.lineTo(b.x, b.y)
            hit = scene.addPath(path, QPen(QColor(0, 0, 0, 0), 14))
            hit.setZValue(1)
            tag(hit, "bond", bond.id)
    annotations(scene, document, selected, editing)
    return scene.itemsBoundingRect()


def content_scene(document):
    scene = QGraphicsScene()
    populate(scene, document)
    scene.setSceneRect(scene.itemsBoundingRect().adjusted(-24, -24, 24, 24))
    return scene


def anchor_point(document, identity, fallback):
    for atom in document.atoms:
        if atom.id == identity:
            return QPointF(atom.x, atom.y)
    atoms = {a.id: a for a in document.atoms}
    for bond in document.bonds:
        if bond.id == identity:
            a, b = atoms[bond.start], atoms[bond.end]
            return QPointF((a.x + b.x) / 2, (a.y + b.y) / 2)
    return fallback


def molecule_rect(document, identities):
    """Actual chemical bounds, including labels, without editor decorations."""
    identities = connected_atoms(document, set(identities))
    fragment = Document(
        atoms=[a for a in document.atoms if a.id in identities],
        bonds=[b for b in document.bonds if b.start in identities and b.end in identities],
    )
    return content_scene(fragment).itemsBoundingRect()


def box_edge(rect, direction):
    distances = []
    if abs(direction.x()) > 0.001:
        distances.append(rect.width() / 2 / abs(direction.x()))
    if abs(direction.y()) > 0.001:
        distances.append(rect.height() / 2 / abs(direction.y()))
    return rect.center() + direction * (min(distances, default=0) + 18)


def arrow_geometry(document, arrow, bounds_cache=None):
    if arrow.start_group:
        cache = bounds_cache if bounds_cache is not None else {}
        boxes = []
        for group in (arrow.start_group, arrow.end_group):
            key = tuple(sorted(group))
            if key not in cache:
                cache[key] = molecule_rect(document, group)
            boxes.append(cache[key])
        first, second = boxes
        delta = second.center() - first.center()
        length = max(0.01, math.hypot(delta.x(), delta.y()))
        direction = delta / length
        start, end = box_edge(first, direction), box_edge(second, -direction)
        if (end - start).x() * direction.x() + (end - start).y() * direction.y() < 12:
            start = first.center() + delta * 0.35
            end = second.center() - delta * 0.35
    else:
        start = anchor_point(document, arrow.start_anchor, QPointF(arrow.x1, arrow.y1))
        end = anchor_point(document, arrow.end_anchor, QPointF(arrow.x2, arrow.y2))
    delta = end - start
    length = max(0.01, math.hypot(delta.x(), delta.y()))
    normal = QPointF(-delta.y() / length, delta.x() / length)
    control = (start + end) * 0.5 + normal * arrow.curvature
    return start, end, control


def arrow_caption(scene, arrow, start, end):
    if not arrow.label:
        return
    item = add_label(scene, arrow.label, 0, 0, "arrow", arrow.id, 16)
    rect = item.boundingRect()
    middle = (start + end) * 0.5
    dx, dy = end.x() - start.x(), end.y() - start.y()
    side = arrow.label_side
    if side == "auto":
        side = "above" if abs(dx) >= abs(dy) else "right"
    if side in ("above", "below"):
        offset = rect.height() / 2 + arrow.label_offset
        middle += QPointF(0, -offset if side == "above" else offset)
    else:
        offset = rect.width() / 2 + arrow.label_offset
        middle += QPointF(-offset if side == "left" else offset, 0)
    item.setPos(middle.x() - rect.width() / 2, middle.y() - rect.height() / 2)


def electron_geometry(document, arrow):
    """Use identical anchored endpoints for the live preview and final drawing."""
    start, end, control = arrow_geometry(document, arrow)

    def clearance(identity):
        atom = next((a for a in document.atoms if a.id == identity), None)
        if atom:
            visible = (
                atom.element != "C"
                or atom.charge
                or atom.isotope
                or atom.label
                or atom.hydrogens >= 0
            )
            return 17 if visible else 4
        return 5 if identity else 0

    def shorten(point, towards, distance):
        delta = towards - point
        length = max(0.01, math.hypot(delta.x(), delta.y()))
        return point + delta / length * min(distance, length * 0.3)

    if arrow.start_anchor:
        start = shorten(start, control, clearance(arrow.start_anchor))
    if arrow.end_anchor:
        end = shorten(end, control, clearance(arrow.end_anchor))
    return start, end, control


def arrow_head(scene, point, tangent, pen, kind, identity, fishhook=False):
    length = max(0.01, math.hypot(tangent.x(), tangent.y()))
    direction = tangent / length
    normal = QPointF(-direction.y(), direction.x())
    for sign in [1] if fishhook else [-1, 1]:
        tip = point - direction * 11 + normal * (sign * 5)
        tag(scene.addLine(point.x(), point.y(), tip.x(), tip.y(), pen), kind, identity)


def annotations(scene, document, selected, editing):
    for atom in document.atoms:
        for i in range(atom.lone_pairs):
            x = atom.x + (i - (atom.lone_pairs - 1) / 2) * 12
            for dx in (-2, 2):
                tag(
                    scene.addEllipse(x + dx - 1.5, atom.y - 23, 3, 3, QPen(Qt.PenStyle.NoPen), INK),
                    "atom",
                    atom.id,
                )
        for i in range(atom.radicals):
            tag(
                scene.addEllipse(
                    atom.x + 13 + i * 5, atom.y - 17, 3, 3, QPen(Qt.PenStyle.NoPen), INK
                ),
                "atom",
                atom.id,
            )
    for note in document.notes:
        add_label(scene, note.text, note.x, note.y, "note", note.id, note.size)
        if editing and note.id in selected:
            # Screen-only outline; exports use a separate unselected scene.
            item = next(i for i in scene.items() if i.data(1) == note.id)
            rect = item.sceneBoundingRect()
            tag(scene.addRect(rect, QPen(ACCENT, 1, Qt.PenStyle.DashLine)), "note", note.id)
    bounds_cache = {}
    for arrow in document.arrows:
        start, end, control = arrow_geometry(document, arrow, bounds_cache)
        delta = end - start
        length = max(0.01, math.hypot(delta.x(), delta.y()))
        normal = QPointF(-delta.y() / length, delta.x() / length)
        pen = QPen(ACCENT if arrow.id in selected else INK, 1.8)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        if arrow.kind == "electron":
            start, end, control = electron_geometry(document, arrow)
            path = QPainterPath(start)
            path.quadTo(control, end)
            tag(scene.addPath(path, pen), "arrow", arrow.id)
            arrow_head(scene, end, end - control, pen, "arrow", arrow.id, arrow.electrons == 1)
            if editing and arrow.id in selected:
                tag(
                    scene.addEllipse(
                        control.x() - 5, control.y() - 5, 10, 10, QPen(ACCENT, 1), QColor("white")
                    ),
                    "handle",
                    arrow.id,
                )
        elif arrow.kind == "reaction":
            tag(scene.addLine(start.x(), start.y(), end.x(), end.y(), pen), "arrow", arrow.id)
            arrow_head(scene, end, delta, pen, "arrow", arrow.id)
        elif arrow.kind == "equilibrium":
            for sign in (-1, 1):
                a, b = (start, end) if sign == 1 else (end, start)
                a, b = a + normal * sign * 4, b + normal * sign * 4
                tag(scene.addLine(a.x(), a.y(), b.x(), b.y(), pen), "arrow", arrow.id)
                arrow_head(scene, b, b - a, pen, "arrow", arrow.id, True)
        elif arrow.kind == "retro":
            for sign in (-1, 1):
                a, b = start + normal * sign * 3, end - delta / length * 8 + normal * sign * 3
                tag(scene.addLine(a.x(), a.y(), b.x(), b.y(), pen), "arrow", arrow.id)
            arrow_head(scene, end, delta, pen, "arrow", arrow.id)

        if arrow.kind != "electron":
            arrow_caption(scene, arrow, start, end)
