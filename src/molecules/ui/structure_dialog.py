"""A clear structure/provenance preview before inserting a resolved molecule."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFrame, QGraphicsView, QVBoxLayout

from molecules.rendering.scene import content_scene
from molecules.ui.workspace import label


class StructureDialog(QDialog):
    def __init__(self, document, warning, parent):
        super().__init__(parent)
        self.setWindowTitle("Add molecule")
        self.resize(640, 520)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(14)
        title = label(document.title, "title")
        title.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(label(document.sources[0].provider, "muted"))
        self.scene = content_scene(document)
        self.preview = QGraphicsView(self.scene)
        self.preview.setFrameShape(QFrame.Shape.NoFrame)
        self.preview.setBackgroundBrush(Qt.GlobalColor.white)
        self.preview.setRenderHints(parent.view.renderHints())
        layout.addWidget(self.preview, 1)
        if warning:
            note = label(warning, "muted")
            note.setWordWrap(True)
            layout.addWidget(note)
        layout.addWidget(label("After insertion, click an atom or bond to edit it.", "muted"))
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        add = buttons.button(QDialogButtonBox.StandardButton.Ok)
        add.setText("Add to drawing")
        add.setProperty("role", "primary")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def showEvent(self, event):
        super().showEvent(event)
        self.preview.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
