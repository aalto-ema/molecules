"""Export options with an accurate raster preview of the shared drawing."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from molecules.exports.visual import image


class ExportDialog(QDialog):
    def __init__(self, document, selection=None, parent=None):
        super().__init__(parent)
        self.document, self.selection = document, selection
        self.color = "#ffffff"
        self.setWindowTitle("Export drawing")
        self.resize(800, 560)
        layout = QHBoxLayout(self)
        form = QFormLayout()
        self.format = QComboBox()
        self.format.addItems(["PNG", "SVG", "PDF"])
        self.scope = QComboBox()
        self.scope.addItem("Entire drawing")
        if selection and (
            selection.atoms or getattr(selection, "notes", []) or getattr(selection, "arrows", [])
        ):
            self.scope.addItem("Selection")
        self.width, self.height, self.dpi, self.padding = [QSpinBox() for _ in range(4)]
        self.width.setRange(64, 16000)
        self.height.setRange(64, 16000)
        self.width.setValue(1600)
        self.height.setValue(1000)
        self.dpi.setRange(36, 1200)
        self.dpi.setValue(300)
        self.padding.setRange(0, 200)
        self.padding.setValue(24)
        self.background = QComboBox()
        self.background.addItems(["Transparent", "White", "Custom"])
        self.color_button = QPushButton("Choose color…")
        self.color_button.clicked.connect(self.choose_color)
        for title, control in (
            ("Format", self.format),
            ("Content", self.scope),
            ("Width (px)", self.width),
            ("Height (px)", self.height),
            ("DPI / physical size", self.dpi),
            ("Padding (drawing units)", self.padding),
            ("Background", self.background),
            ("", self.color_button),
        ):
            form.addRow(title, control)
        self.size_note = QLabel()
        self.size_note.setWordWrap(True)
        form.addRow(self.size_note)
        form.addRow(
            QLabel(
                "SVG and PDF keep vector strokes and text.\n"
                "PDF viewers usually display a white page."
            )
        )
        left = QVBoxLayout()
        left.addLayout(form)
        left.addStretch()
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Export…")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        left.addWidget(buttons)
        layout.addLayout(left)
        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumSize(400, 400)
        self.preview.setStyleSheet("background:#e4e8ed; border:1px solid #ccd3dc;")
        layout.addWidget(self.preview, 1)
        for control in (self.width, self.height, self.dpi, self.padding):
            control.valueChanged.connect(self.update_preview)
        for control in (self.format, self.scope, self.background):
            control.currentTextChanged.connect(self.update_preview)
        self.update_preview()

    def choose_color(self):
        color = QColorDialog.getColor(parent=self)
        if color.isValid():
            self.color = color.name()
            self.background.setCurrentText("Custom")
            self.update_preview()

    def chosen_document(self):
        return self.selection if self.scope.currentText() == "Selection" else self.document

    def options(self):
        background = {"Transparent": None, "White": "#ffffff", "Custom": self.color}[
            self.background.currentText()
        ]
        return dict(
            format=self.format.currentText(),
            width=self.width.value(),
            height=self.height.value(),
            dpi=self.dpi.value(),
            padding=self.padding.value(),
            background=background,
        )

    def update_preview(self, *_):
        options = self.options()
        scale = min(480 / options["width"], 420 / options["height"])
        width = max(1, round(options["width"] * scale))
        height = max(1, round(options["height"] * scale))
        rendered = image(
            self.chosen_document(),
            width,
            height,
            background=options["background"],
            padding=options["padding"],
        )
        if options["background"] is None:
            checker = QImage(rendered.size(), QImage.Format.Format_ARGB32)
            painter = QPainter(checker)
            for y in range(0, rendered.height(), 12):
                for x in range(0, rendered.width(), 12):
                    painter.fillRect(
                        x,
                        y,
                        12,
                        12,
                        QColor("#eef0f3") if (x // 12 + y // 12) % 2 else QColor("#ffffff"),
                    )
            painter.drawImage(0, 0, rendered)
            painter.end()
            rendered = checker
        self.preview.setPixmap(QPixmap.fromImage(rendered))
        self.color_button.setEnabled(self.background.currentText() == "Custom")
        self.size_note.setText(
            f"{options['width'] / options['dpi'] * 25.4:.1f} × "
            f"{options['height'] / options['dpi'] * 25.4:.1f} mm at {options['dpi']} DPI"
        )
