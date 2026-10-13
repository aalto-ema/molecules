"""Small vector-like tool glyphs painted at high DPI; no external icon runtime."""

import math

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPen, QPixmap, QPolygonF


def icon(name, color="#415574"):
    pixmap = QPixmap(48, 48)
    pixmap.setDevicePixelRatio(2)
    pixmap.fill(Qt.GlobalColor.transparent)
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(color), 1.7)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    if name == "select":
        p.drawPolygon(
            QPolygonF(
                [QPointF(6, 3), QPointF(18, 13), QPointF(12, 14), QPointF(9, 20), QPointF(6, 3)]
            )
        )
    elif name in ("bond", "molecule"):
        p.drawPolyline(QPolygonF([QPointF(3, 17), QPointF(11, 7), QPointF(21, 15)]))
        if name == "molecule":
            for x, y in ((3, 17), (11, 7), (21, 15)):
                p.setBrush(QColor(color))
                p.drawEllipse(QPointF(x, y), 2, 2)
    elif name == "ring":
        p.drawPolygon(
            QPolygonF(
                [
                    QPointF(12 + 9 * math.cos(i * math.pi / 3), 12 + 9 * math.sin(i * math.pi / 3))
                    for i in range(6)
                ]
            )
        )
    elif name in ("reaction", "retro", "equilibrium", "pathway"):
        for y in [9, 15] if name not in ("reaction", "pathway") else [12]:
            p.drawLine(3, y, 21, y)
        p.drawPolyline(QPolygonF([QPointF(16, 7), QPointF(21, 12), QPointF(16, 17)]))
        if name == "equilibrium":
            p.drawPolyline(QPolygonF([QPointF(8, 10), QPointF(3, 15), QPointF(8, 20)]))
    elif name == "electron":
        path = QPainterPath(QPointF(4, 18))
        path.cubicTo(0, 1, 24, 1, 19, 17)
        p.drawPath(path)
        p.drawPolyline(QPolygonF([QPointF(14, 13), QPointF(19, 17), QPointF(22, 11)]))
    elif name == "rotate":
        path = QPainterPath(QPointF(19, 17))
        path.cubicTo(9, 27, -3, 11, 8, 5)
        path.cubicTo(16, 1, 23, 9, 20, 13)
        p.drawPath(path)
        p.drawPolyline(QPolygonF([QPointF(16, 9), QPointF(20, 14), QPointF(23, 8)]))
    elif name in ("undo", "redo"):
        if name == "redo":
            p.translate(24, 0)
            p.scale(-1, 1)
        path = QPainterPath(QPointF(5, 8))
        path.cubicTo(23, 4, 24, 22, 9, 19)
        p.drawPath(path)
        p.drawPolyline(QPolygonF([QPointF(9, 3), QPointF(4, 8), QPointF(10, 12)]))
    elif name == "fit":
        for x, y, dx, dy in ((4, 4, 1, 1), (20, 4, -1, 1), (4, 20, 1, -1), (20, 20, -1, -1)):
            p.drawLine(x, y, x + dx * 5, y)
            p.drawLine(x, y, x, y + dy * 5)
    elif name == "save":
        p.drawRoundedRect(4, 3, 16, 18, 2, 2)
        p.drawRect(8, 3, 8, 6)
        p.drawRect(8, 14, 8, 7)
    elif name == "open":
        path = QPainterPath(QPointF(3, 19))
        for point in (
            QPointF(3, 5),
            QPointF(10, 5),
            QPointF(12, 8),
            QPointF(20, 8),
            QPointF(20, 19),
            QPointF(3, 19),
        ):
            path.lineTo(point)
        p.drawPath(path)
        p.drawLine(3, 11, 20, 11)
    elif name == "export":
        p.drawPolyline(
            QPolygonF([QPointF(5, 13), QPointF(5, 20), QPointF(19, 20), QPointF(19, 13)])
        )
        p.drawLine(12, 3, 12, 15)
        p.drawPolyline(QPolygonF([QPointF(7, 8), QPointF(12, 3), QPointF(17, 8)]))
    else:
        font = QFont()
        font.setPixelSize(18)
        font.setWeight(QFont.Weight.Medium)
        p.setFont(font)
        p.drawText(
            0,
            0,
            24,
            24,
            Qt.AlignmentFlag.AlignCenter,
            {"atom": "N", "text": "T", "plus": "+", "delete": "×", "more": "···"}.get(name, "·"),
        )
    p.end()
    return QIcon(pixmap)
