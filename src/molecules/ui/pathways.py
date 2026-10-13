"""Simple labeled pathways and molecule rotation, separate from electron flow."""

from copy import deepcopy
from dataclasses import replace

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontMetricsF
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLineEdit,
    QMenu,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
)

from molecules.domain.document import Source
from molecules.domain.geometry import (
    molecule_group,
    rotate_molecules,
    rotation_atoms,
    selected_atoms,
)
from molecules.domain.pathways import add_product, connect_molecules
from molecules.rendering.scene import molecule_rect
from molecules.ui.icons import icon
from molecules.ui.workspace import button, label


class PathwayMixin:
    def build_pathway_guide(self):
        self.pathway_source = None
        self.add_tool("pathway", "Link", "L")
        panel = QFrame()
        panel.setObjectName("GuidePanel")
        panel.setFixedWidth(280)
        outer = QVBoxLayout(panel)
        outer.setContentsMargins(0, 0, 0, 0)
        body = QFrame()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(18, 20, 18, 18)
        layout.setSpacing(14)
        layout.addWidget(label("SIMPLE REACTION PATHWAY", "eyebrow"))
        layout.addWidget(label("Connect your molecules", "subtitle"))
        layout.addWidget(label("1  Choose a reactant", "subtitle"))
        self.pathway_source_label = label("Click a molecule on the canvas.", "muted")
        self.pathway_source_label.setWordWrap(True)
        layout.addWidget(self.pathway_source_label)
        layout.addWidget(label("2  Product", "subtitle"))
        self.product_mode = QComboBox()
        self.product_mode.addItems(["Name", "SMILES"])
        self.product_input = QLineEdit()
        self.product_input.setPlaceholderText("Product name or SMILES")
        self.product_input.returnPressed.connect(self.start_pathway_lookup)
        self.product_input.textEdited.connect(self.cancel_lookup)
        self.product_input.textChanged.connect(lambda _: self.update_pathway_guide())
        self.product_mode.currentTextChanged.connect(self.cancel_lookup)
        layout.addWidget(self.product_mode)
        layout.addWidget(self.product_input)
        layout.addWidget(label("3  Arrow text", "subtitle"))
        self.pathway_caption = QLineEdit()
        self.pathway_caption.setPlaceholderText("e.g. 2H⁺ + 2e⁻, catalyst, conditions")
        self.pathway_caption.setMaxLength(300)
        self.pathway_caption.textEdited.connect(self.cancel_lookup)
        layout.addWidget(self.pathway_caption)
        presets = QHBoxLayout()
        presets.addWidget(
            button("2H⁺ + 2e⁻", lambda: self.set_pathway_caption("2H⁺ + 2e⁻"), "chip")
        )
        presets.addWidget(button("Custom", lambda: self.pathway_caption.setFocus(), "quiet"))
        layout.addLayout(presets)
        self.pathway_direction = QComboBox()
        for title, key in (
            ("→  Right", "right"),
            ("↓  Down", "down"),
            ("←  Left", "left"),
            ("↑  Up", "up"),
        ):
            self.pathway_direction.addItem(title, key)
        self.pathway_direction.currentIndexChanged.connect(self.cancel_lookup)
        layout.addWidget(label("Direction", "muted"))
        layout.addWidget(self.pathway_direction)
        tip = label(
            "Already drawn the product? Use Link and click the reactant, then the product. "
            "Place molecules anywhere.",
            "muted",
        )
        tip.setWordWrap(True)
        layout.addWidget(tip)
        layout.addWidget(
            button("Link existing molecules", lambda: self.set_tool("pathway"), "quiet", "reaction")
        )
        layout.addStretch()
        layout.addWidget(button("Try a redox pathway", self.pathway_example, "quiet"))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)
        footer = QFrame()
        footer.setObjectName("GuideFooter")
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(18, 12, 18, 18)
        self.pathway_feedback = label("", "muted")
        self.pathway_feedback.setWordWrap(True)
        footer_layout.addWidget(self.pathway_feedback)
        self.add_product_button = button(
            "Add product + arrow", self.start_pathway_lookup, "primary"
        )
        footer_layout.addWidget(self.add_product_button)
        outer.addWidget(footer)
        return panel

    def set_pathway_caption(self, text):
        self.cancel_lookup()
        self.pathway_caption.setText(text)

    def current_pathway_source(self):
        if self.pathway_source and any(a.id == self.pathway_source for a in self.document.atoms):
            return molecule_group(self.document, self.pathway_source)
        return set()

    def update_pathway_guide(self):
        if not hasattr(self, "add_product_button"):
            return
        picked = selected_atoms(self.document, self.selected)
        if self.workspace_mode == "pathway" and self.view.tool != "pathway" and picked:
            groups = [molecule_group(self.document, identity) for identity in picked]
            if all(group == groups[0] for group in groups):
                self.pathway_source = next(a.id for a in self.document.atoms if a.id in groups[0])
        source = self.current_pathway_source()
        if source:
            provenance = next(
                (s.query for s in self.document.sources if source <= set(s.atom_ids)), "Molecule"
            )
            self.pathway_source_label.setText(
                f"{provenance}\n{len(source)} atoms selected as reactant"
            )
        else:
            self.pathway_source_label.setText("Click a reactant molecule, then add its product.")
        busy = self.lookup_task is not None
        self.add_product_button.setEnabled(
            bool(source and self.product_input.text().strip()) and not busy
        )
        self.add_product_button.setText("Generating product…" if busy else "Add product + arrow")

    def start_pathway_lookup(self):
        source = self.current_pathway_source()
        if not source:
            self.pathway_feedback.setText("Select a reactant molecule first.")
            return
        query = self.product_input.text().strip()
        if not query:
            self.product_input.setFocus()
            return
        intent = dict(
            source=source,
            direction=self.pathway_direction.currentData(),
            label=self.pathway_caption.text(),
        )
        self.pathway_feedback.setText("")
        self.launch_lookup(query, self.product_mode.currentText(), intent)
        self.update_pathway_guide()

    def insert_pathway_product(self, product, intent):
        source = intent["source"]
        first = molecule_rect(self.document, source)
        second = molecule_rect(product, {a.id for a in product.atoms})
        font = QFont("Arial")
        font.setPixelSize(16)
        width = max(
            (QFontMetricsF(font).horizontalAdvance(line) for line in intent["label"].splitlines()),
            default=0,
        )
        gap = max(180, width + 60) if intent["direction"] in ("left", "right") else 180
        result = add_product(
            self.document,
            source,
            product,
            intent["direction"],
            intent["label"],
            (first.left(), first.top(), first.right(), first.bottom()),
            (second.left(), second.top(), second.right(), second.bottom()),
            gap,
        )
        self.selected = {a.id for a in product.atoms}
        self.pathway_source = product.atoms[0].id
        self.commit("Add pathway product", result)
        self.product_input.clear()
        self.set_tool("select")
        self.fit_drawing()

    def pathway_click(self, kind, identity):
        if kind not in ("atom", "bond"):
            self.pathway_feedback.setText("Click a molecule to choose or connect it.")
            return
        if kind == "bond":
            identity = next(b.start for b in self.document.bonds if b.id == identity)
        target = molecule_group(self.document, identity)
        source = self.current_pathway_source()
        if not source or source == target:
            self.pathway_source = identity
            self.selected = target | {
                b.id for b in self.document.bonds if b.start in target and b.end in target
            }
            self.pathway_feedback.setText(
                "Choose a product on the canvas, or enter one in the panel."
            )
            self.refresh()
            return
        try:
            result = connect_molecules(self.document, source, target, self.pathway_caption.text())
            self.pathway_source = identity
            self.selected = {result.arrows[-1].id}
            self.commit("Connect pathway molecules", result)
            self.pathway_feedback.setText(
                "Connected. This product is the reactant for the next arrow."
            )
        except ValueError as exc:
            self.pathway_feedback.setText(str(exc))

    def edit_arrow_caption(self):
        arrows = [a for a in self.document.arrows if a.id in self.selected and a.kind != "electron"]
        if not arrows:
            return
        text, ok = QInputDialog.getMultiLineText(
            self, "Arrow caption", "Reaction conditions or stoichiometry", arrows[0].label
        )
        if ok:
            self.edit(
                "Edit reaction caption",
                lambda d: setattr(
                    d,
                    "arrows",
                    [
                        replace(a, label=text)
                        if a.id in self.selected and a.kind != "electron"
                        else a
                        for a in d.arrows
                    ],
                ),
            )

    def reverse_reaction_arrows(self):
        self.edit(
            "Reverse reaction arrow",
            lambda d: setattr(
                d,
                "arrows",
                [
                    replace(
                        a,
                        x1=a.x2,
                        y1=a.y2,
                        x2=a.x1,
                        y2=a.y1,
                        start_anchor=a.end_anchor,
                        end_anchor=a.start_anchor,
                        start_group=a.end_group,
                        end_group=a.start_group,
                    )
                    if a.id in self.selected and a.kind != "electron"
                    else a
                    for a in d.arrows
                ],
            ),
        )

    def rotation_menu(self, parent=None):
        menu = QMenu("Rotate molecule", parent or self)
        for title, angle in (("↶  90°", -90), ("↶  15°", -15), ("↷  15°", 15), ("↷  90°", 90)):
            menu.addAction(title, lambda checked=False, value=angle: self.rotate_selected(value))
        menu.addSeparator()
        menu.addAction("Exact angle…", self.choose_rotation)
        return menu

    def rotation_button(self, compact=False):
        control = QPushButton("" if compact else "Rotate")
        control.setIcon(icon("rotate"))
        control.setToolTip(
            "Rotate whole molecules · drag the circular handle · Alt for a free angle"
        )
        control.setAccessibleName("Rotate molecule")
        control.setMenu(self.rotation_menu(control))
        return control

    def choose_rotation(self):
        value, ok = QInputDialog.getDouble(
            self, "Rotate molecule", "Clockwise angle (degrees)", 0, -360, 360, 1
        )
        if ok:
            self.rotate_selected(value)

    def rotate_selected(self, degrees):
        identities = rotation_atoms(self.document, self.selected)
        if not identities:
            return
        bounds = molecule_rect(self.document, identities)
        result = rotate_molecules(
            self.document, self.selected, degrees, (bounds.center().x(), bounds.center().y())
        )
        self.selected = identities | {
            b.id for b in self.document.bonds if b.start in identities and b.end in identities
        }
        self.commit("Rotate molecule", result)
        self.set_tool("select")
        self.view.setFocus()

    def pathway_example(self):
        from molecules.chemistry.adapter import from_smiles

        quinone, hydroquinone = "O=C1C=CC(=O)C=C1", "Oc1ccc(O)cc1"

        def molecule(smiles, name):
            d = from_smiles(smiles, name)
            d.sources = [
                Source(name, "Built-in redox drawing example", smiles, [a.id for a in d.atoms])
            ]
            return d

        first = molecule(quinone, "1,4-Benzoquinone")
        result = deepcopy(self.document)
        if not result.atoms:
            result.title = "Simple redox pathway"
        offset = max((a.x for a in result.atoms), default=-200) + 200 if result.atoms else 0
        result.atoms += [replace(a, x=a.x + offset) for a in first.atoms]
        result.bonds += first.bonds
        result.sources += first.sources
        source = {a.id for a in first.atoms}
        for direction, smiles, name, caption in (
            ("right", hydroquinone, "Hydroquinone", "2H⁺ + 2e⁻"),
            ("down", quinone, "1,4-Benzoquinone", "Oxidation\n−2H⁺ −2e⁻"),
            ("left", hydroquinone, "Hydroquinone", "Reduction\n2H⁺ + 2e⁻"),
        ):
            product = molecule(smiles, name)
            first_bounds, next_bounds = (
                molecule_rect(result, source),
                molecule_rect(product, {a.id for a in product.atoms}),
            )
            result = add_product(
                result,
                source,
                product,
                direction,
                caption,
                (
                    first_bounds.left(),
                    first_bounds.top(),
                    first_bounds.right(),
                    first_bounds.bottom(),
                ),
                (next_bounds.left(), next_bounds.top(), next_bounds.right(), next_bounds.bottom()),
                180,
            )
            source = {a.id for a in product.atoms}
        self.pathway_source = next(iter(source))
        self.selected = source
        self.commit("Insert simple redox pathway", result)
        self.set_workspace_mode("pathway")
        self.set_tool("select")
        self.fit_drawing()
