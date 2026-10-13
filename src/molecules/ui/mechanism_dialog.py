"""Side-by-side review keeps electron-flow changes concrete and reversible."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
)

from molecules.chemistry.adapter import chemistry_warning
from molecules.domain.document import Document
from molecules.rendering.scene import content_scene
from molecules.ui.workspace import label


class MechanismDialog(QDialog):
    def __init__(self, proposal, parent):
        super().__init__(parent)
        self.setWindowTitle("Review next mechanism step")
        self.resize(900, 650)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(16)
        layout.addWidget(label("Review the electron flow", "title"))
        layout.addWidget(
            label("Confirm the bond and charge changes before adding the next step.", "muted")
        )
        ids = proposal.atom_ids
        after = Document(
            atoms=[a for a in proposal.document.atoms if a.id in ids],
            bonds=[b for b in proposal.document.bonds if b.start in ids and b.end in ids],
        )
        identities = {a.identity for a in after.atoms}
        old_atoms = [
            a
            for a in parent.document.atoms
            if (a.identity or a.id) in identities and a.step == proposal.source_step
        ]
        old_ids = {a.id for a in old_atoms}
        before = Document(
            atoms=old_atoms,
            bonds=[b for b in parent.document.bonds if b.start in old_ids and b.end in old_ids],
        )
        previews = QHBoxLayout()
        self.previews = []
        for title, document in (("Current step", before), ("Proposed next step", after)):
            card = QFrame()
            card.setObjectName("ContextBar")
            box = QVBoxLayout(card)
            box.setContentsMargins(14, 14, 14, 14)
            box.addWidget(label(title, "subtitle"))
            scene = content_scene(document)
            view = QGraphicsView(scene)
            view.setFrameShape(QFrame.Shape.NoFrame)
            view.setRenderHints(parent.view.renderHints())
            view.setBackgroundBrush(Qt.GlobalColor.white)
            box.addWidget(view, 1)
            previews.addWidget(card, 1)
            self.previews.append((view, scene))
        layout.addLayout(previews, 1)
        changes = QLabel("\n".join("• " + change for change in proposal.changes))
        changes.setWordWrap(True)
        changes.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(changes)
        warning = chemistry_warning(after)
        note = label(
            warning
            or "The drawing follows your arrows. Review the chemistry before using the mechanism.",
            "muted",
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Add next step")
        buttons.button(QDialogButtonBox.StandardButton.Ok).setProperty("role", "primary")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.scene = self.previews[-1][1]
        self.preview = self.previews[-1][0]

    def showEvent(self, event):
        super().showEvent(event)
        for view, scene in self.previews:
            view.fitInView(scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
