"""Export drawing geometry without canvas selection or hit targets."""

import os
import tempfile
from pathlib import Path

from PySide6.QtCore import QFile, QIODevice, QMarginsF, QRectF, QSize, QSizeF, Qt
from PySide6.QtGui import QColor, QImage, QPageLayout, QPageSize, QPainter, QPdfWriter
from PySide6.QtSvg import QSvgGenerator

from molecules.rendering.scene import content_scene


def paint(scene, device, width, height, background=None):
    painter = QPainter(device)
    if not painter.isActive():
        raise ValueError("Could not initialize the export device.")
    try:
        painter.setRenderHints(
            QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing
        )
        target = QRectF(0, 0, width, height)
        if background:
            painter.fillRect(target, QColor(background))
        scene.render(painter, target, scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
    finally:
        painter.end()


def image(document, width=1600, height=1000, dpi=300, background=None, padding=24):
    if width < 1 or height < 1 or width * height > 80_000_000:
        raise ValueError("Choose positive dimensions with at most 80 million pixels.")
    scene = content_scene(document)
    scene.setSceneRect(scene.itemsBoundingRect().adjusted(-padding, -padding, padding, padding))
    result = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
    if result.isNull():
        raise ValueError("Not enough memory for this export size.")
    result.fill(Qt.GlobalColor.transparent)
    result.setDotsPerMeterX(round(dpi / 0.0254))
    result.setDotsPerMeterY(round(dpi / 0.0254))
    paint(scene, result, width, height, background)
    return result


def export(
    document,
    path: Path,
    format="PNG",
    width=1600,
    height=1000,
    dpi=300,
    background=None,
    padding=24,
):
    document.validate()
    if (
        not document.atoms
        and not getattr(document, "notes", [])
        and not getattr(document, "arrows", [])
    ):
        raise ValueError("Add a structure or annotation before exporting.")
    if not 1 <= width <= 16000 or not 1 <= height <= 16000 or not 36 <= dpi <= 1200:
        raise ValueError("Unsupported dimensions or DPI.")
    if background is not None and not QColor(background).isValid():
        raise ValueError("Choose a valid background color.")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent, suffix="." + format.lower(), delete=False
        ) as stream:
            temporary = Path(stream.name)
        if format == "PNG":
            if not image(document, width, height, dpi, background, padding).save(
                str(temporary), "PNG"
            ):
                raise ValueError("PNG export failed.")
        else:
            scene = content_scene(document)
            scene.setSceneRect(
                scene.itemsBoundingRect().adjusted(-padding, -padding, padding, padding)
            )
            output = QFile(str(temporary))
            if not output.open(QIODevice.OpenModeFlag.WriteOnly):
                raise OSError(output.errorString())
            device = None
            try:
                if format == "SVG":
                    device = QSvgGenerator()
                    device.setOutputDevice(output)
                    device.setSize(QSize(width, height))
                    device.setViewBox(QRectF(0, 0, width, height))
                    device.setResolution(dpi)
                    device.setTitle(document.title)
                    paint(scene, device, width, height, background)
                elif format == "PDF":
                    device = QPdfWriter(output)
                    device.setResolution(dpi)
                    device.setTitle(document.title)
                    device.setPageSize(
                        QPageSize(
                            QSizeF(width / dpi * 25.4, height / dpi * 25.4),
                            QPageSize.Unit.Millimeter,
                        )
                    )
                    device.setPageMargins(QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Millimeter)
                    paint(scene, device, device.width(), device.height(), background)
                else:
                    raise ValueError("Export format must be PNG, SVG, or PDF.")
            finally:
                # Finalize vector writers and release the OS handle before atomic
                # replacement or cleanup, including when rendering raises.
                del device
                output.close()
        if temporary.stat().st_size == 0:
            raise ValueError("Export produced an empty file.")
        os.replace(temporary, path)
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)
