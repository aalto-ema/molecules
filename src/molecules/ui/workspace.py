"""Canvas-first workspace, contextual editing, and mechanism guidance."""

from dataclasses import replace

from PySide6.QtCore import QEvent, QSize, Qt
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from molecules.domain.document import ELEMENTS
from molecules.ui.icons import icon
from molecules.ui.theme import apply_theme


def label(text, role=None):
    widget = QLabel(text)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    if role:
        widget.setProperty("role", role)
    return widget


def button(text, callback, role=None, glyph=None):
    widget = QPushButton(text)
    if role:
        widget.setProperty("role", role)
    if glyph:
        widget.setIcon(icon(glyph, "#ffffff" if role == "primary" else "#415574"))
    widget.clicked.connect(callback)
    return widget


class WorkspaceMixin:
    def create_toolbar(self):
        self.workspace_mode = "structure"
        self.details_open = False
        self.tool_group = QActionGroup(self)
        self.tool_actions = {}
        self.tools = QToolBar(self)  # Action registry; the rail presents these actions.
        self.tools.hide()
        self.element = QComboBox()
        self.element.addItems(
            [
                "C",
                "N",
                "O",
                "S",
                "P",
                "F",
                "Cl",
                "Br",
                "I",
                "H",
                "B",
                "Si",
                "Na",
                "K",
                "Li",
                "Mg",
                "Fe",
            ]
        )
        self.element.setEditable(True)
        self.element.hide()
        self.order = QSpinBox()
        self.order.setRange(1, 3)
        self.order.hide()
        self.apply_bond_button = QPushButton()
        self.apply_bond_button.hide()
        for key, name, shortcut in (
            ("select", "Select", "V"),
            ("atom", "Atom", "A"),
            ("bond", "Bond", "B"),
        ):
            self.add_tool(key, name, shortcut)
        root = QWidget()
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        header = QFrame()
        header.setObjectName("AppHeader")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(24, 14, 24, 16)
        header_layout.setSpacing(14)
        title_row = QHBoxLayout()
        brand = label("Molecules")
        brand.setObjectName("Brand")
        title_row.addWidget(brand)
        self.document_badge = label("Untitled", "muted")
        self.document_badge.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred
        )
        title_row.addSpacing(20)
        title_row.addWidget(self.document_badge)
        title_row.addStretch()
        title_row.addWidget(button("Open", self.open_document, "quiet", "open"))
        title_row.addWidget(button("Save", self.save_document, "quiet", "save"))
        title_row.addWidget(button("Export", self.export_drawing, None, "export"))
        header_layout.addLayout(title_row)
        search_row = QHBoxLayout()
        search_row.setSpacing(10)
        search_box = self.search_box = QFrame()
        search_box.setObjectName("SearchBox")
        search_layout = QHBoxLayout(search_box)
        search_layout.setContentsMargins(6, 2, 6, 2)
        self.input_mode = QComboBox()
        self.input_mode.setObjectName("InputMode")
        self.input_mode.addItems(["Name", "SMILES"])
        self.input_mode.setFixedWidth(96)
        self.name_input = QLineEdit()
        self.name_input.setObjectName("NameInput")
        self.name_input.setPlaceholderText("Type a molecule name — e.g. aspirin")
        self.name_input.setClearButtonEnabled(True)
        self.name_input.installEventFilter(self)
        self.name_input.returnPressed.connect(self.start_lookup)
        self.name_input.textChanged.connect(self.cancel_lookup)
        self.input_mode.currentTextChanged.connect(self.cancel_lookup)
        self.input_mode.currentTextChanged.connect(
            lambda mode: self.name_input.setPlaceholderText(
                "Paste SMILES — e.g. CC(=O)O"
                if mode == "SMILES"
                else "Type a molecule name — e.g. aspirin"
            )
        )
        search_layout.addWidget(self.input_mode)
        search_layout.addWidget(self.name_input, 1)
        search_row.addWidget(search_box, 1)
        self.lookup_button = button("Generate", self.start_lookup, "primary")
        search_row.addWidget(self.lookup_button)
        self.cancel_button = button("Cancel", self.cancel_lookup)
        self.cancel_button.hide()
        search_row.addWidget(self.cancel_button)
        header_layout.addLayout(search_row)
        self.feedback = QFrame()
        self.feedback.setObjectName("Feedback")
        feedback_layout = QHBoxLayout(self.feedback)
        feedback_layout.setContentsMargins(12, 8, 8, 8)
        self.feedback_label = label("")
        self.feedback_label.setWordWrap(True)
        feedback_layout.addWidget(self.feedback_label, 1)
        feedback_layout.addWidget(button("Dismiss", self.feedback.hide, "quiet"))
        self.feedback.hide()
        header_layout.addWidget(self.feedback)
        outer.addWidget(header)
        bar = QFrame()
        bar.setObjectName("WorkspaceBar")
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(20, 8, 20, 8)
        modes = QButtonGroup(self)
        self.mode_buttons = {}
        for key, name in (
            ("structure", "Structure"),
            ("pathway", "Pathway"),
            ("mechanism", "Mechanism"),
        ):
            control = button(name, lambda checked=False, k=key: self.set_workspace_mode(k), "mode")
            control.setCheckable(True)
            control.setChecked(key == "structure")
            modes.addButton(control)
            self.mode_buttons[key] = control
            bar_layout.addWidget(control)
        bar_layout.addStretch()
        for action, glyph in ((self.undo_action, "undo"), (self.redo_action, "redo")):
            control = QToolButton()
            control.setDefaultAction(action)
            action.setIcon(icon(glyph))
            control.setProperty("role", "quiet")
            control.setFixedSize(36, 34)
            bar_layout.addWidget(control)
        bar_layout.addSpacing(8)
        bar_layout.addWidget(button("Fit", self.fit_drawing, "quiet", "fit"))
        self.zoom_label = label("100%", "muted")
        self.zoom_label.setMinimumWidth(44)
        bar_layout.addWidget(self.zoom_label)
        outer.addWidget(bar)
        work = QWidget()
        work_layout = QHBoxLayout(work)
        work_layout.setContentsMargins(14, 14, 14, 14)
        work_layout.setSpacing(12)
        self.rail = QFrame()
        self.rail.setObjectName("ToolRail")
        self.rail.setFixedWidth(68)
        self.rail_layout = QVBoxLayout(self.rail)
        self.rail_layout.setContentsMargins(6, 10, 6, 10)
        self.rail_layout.setSpacing(4)
        self.rail_scroll = QScrollArea()
        self.rail_scroll.setObjectName("RailScroll")
        self.rail_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.rail_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.rail_scroll.setWidgetResizable(True)
        self.rail_scroll.setFixedWidth(78)
        self.rail_scroll.setWidget(self.rail)
        work_layout.addWidget(self.rail_scroll)
        self.view.setFrameShape(QFrame.Shape.NoFrame)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        work_layout.addWidget(self.view, 1)
        self.guide = self.build_guide()
        work_layout.addWidget(self.guide)
        self.guide.hide()
        self.pathway_guide = self.build_pathway_guide()
        work_layout.addWidget(self.pathway_guide)
        self.pathway_guide.hide()
        outer.addWidget(work, 1)
        self.setCentralWidget(root)
        self.context_bar = QFrame(self.view.viewport())
        self.context_bar.setObjectName("ContextBar")
        self.context_layout = QHBoxLayout(self.context_bar)
        self.context_layout.setContentsMargins(12, 8, 12, 8)
        self.context_layout.setSpacing(6)
        self.context_bar.hide()
        self.welcome = self.build_welcome()
        self.canvas_hint = label("Select a structure to edit", "muted")
        self.canvas_hint.setParent(self.view.viewport())
        self.canvas_hint.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.lookup_note = label("Local drawing · explicit name lookup", "muted")
        self.lookup_note.setToolTip(
            "Built-in names work offline. Other names go to OPSIN only when you submit."
        )
        self.statusBar().addPermanentWidget(self.lookup_note)
        apply_theme(self)

    def eventFilter(self, watched, event):
        if watched is getattr(self, "name_input", None) and event.type() in (
            QEvent.Type.FocusIn,
            QEvent.Type.FocusOut,
        ):
            self.search_box.setProperty("focused", event.type() == QEvent.Type.FocusIn)
            self.search_box.style().unpolish(self.search_box)
            self.search_box.style().polish(self.search_box)
        return super().eventFilter(watched, event)

    def zoom(self, factor):
        if 0.2 <= self.view.transform().m11() * factor <= 5:
            self.view.scale(factor, factor)
            self.update_workspace()

    def finish_workspace(self):
        self.rail_buttons = {}
        for key in (
            "select",
            "bond",
            "atom",
            "ring",
            "pathway",
            "electron",
            "reaction",
            "text",
            "plus",
        ):
            if key == "ring":
                control = QToolButton()
                control.setText("Rings")
                control.setIcon(icon("ring"))
                control.clicked.connect(self.insert_ring)
            else:
                control = QToolButton()
                control.setDefaultAction(self.tool_actions[key])
                self.tool_actions[key].setIcon(icon(key))
            control.setProperty("role", "tool")
            control.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            control.setIconSize(QSize(24, 24))
            control.setFixedSize(54, 50)
            control.setAccessibleName(
                "Ring templates" if key == "ring" else self.tool_actions[key].text()
            )
            if key == "reaction":
                menu = QMenu(control)
                for arrow in ("reaction", "equilibrium", "retro"):
                    menu.addAction(self.tool_actions[arrow])
                control.setMenu(menu)
                control.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
            control.ensurePolished()
            self.rail_layout.addWidget(control)
            self.rail_buttons[key] = control
        self.rail_layout.addStretch()
        more = QToolButton()
        more.setIcon(icon("more"))
        more.setText("More")
        more.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        more.setProperty("role", "tool")
        more.setFixedSize(54, 50)
        menu = QMenu(more)
        self.action(menu, "Clean layout", self.cleanup)
        self.action(menu, "Align selected atoms…", self.align_selection)
        self.action(menu, "Check chemistry", self.check_chemistry)
        self.action(menu, "Mechanism example", self.load_mechanism_example)
        more.setMenu(menu)
        more.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.rail_layout.addWidget(more)
        self.inspector.setWindowTitle("Advanced properties")
        dock_title = QWidget()
        title_layout = QHBoxLayout(dock_title)
        title_layout.setContentsMargins(16, 10, 8, 10)
        title_layout.addWidget(label("Advanced properties", "subtitle"))
        title_layout.addStretch()
        close = QToolButton()
        close.setText("×")
        close.setAccessibleName("Close advanced properties")
        close.setProperty("role", "quiet")
        close.clicked.connect(self.toggle_details)
        title_layout.addWidget(close)
        self.inspector.setTitleBarWidget(dock_title)
        self.inspector.hide()
        self._context_state = None
        self._guide_steps = None
        self.set_workspace_mode("structure")

    def build_welcome(self):
        card = QFrame(self.view.viewport())
        card.setObjectName("WelcomeCard")
        card.setFixedWidth(418)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(16)
        layout.addWidget(label("YOUR DRAWING WORKSPACE", "eyebrow"))
        layout.addWidget(label("Start with a molecule.", "title"))
        note = label(
            "Type a name above, or choose an example.\nEvery structure stays editable.", "muted"
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        chips = QHBoxLayout()
        for name in ("Ethanol", "Aspirin", "Caffeine"):
            chips.addWidget(
                button(name, lambda checked=False, n=name: self.generate_example(n), "chip")
            )
        layout.addLayout(chips)
        layout.addWidget(
            button("Explore a reaction mechanism", self.load_mechanism_example, "quiet", "electron")
        )
        layout.addWidget(label("Draw from scratch with the Atom or Bond tool.", "muted"))
        card.adjustSize()
        return card

    def build_guide(self):
        guide = QFrame()
        guide.setObjectName("GuidePanel")
        layout = QVBoxLayout(guide)
        layout.setContentsMargins(18, 20, 18, 18)
        layout.setSpacing(14)
        layout.addWidget(label("REACTION MECHANISM", "eyebrow"))
        layout.addWidget(label("Follow the electrons", "subtitle"))
        self.step_choice = QComboBox()
        self.step_choice.currentIndexChanged.connect(lambda _: self.update_mechanism_guide())
        layout.addWidget(self.step_choice)
        self.flow_stages = []
        for heading, text in (
            ("1  Choose a source", "Click an atom, lone pair, or bond."),
            ("2  Choose a target", "Click where the electrons go."),
        ):
            frame = QFrame()
            frame.setObjectName("FlowStage")
            section = QVBoxLayout(frame)
            section.setContentsMargins(12, 12, 12, 12)
            section.addWidget(label(heading, "subtitle"))
            body = label(text, "muted")
            body.setWordWrap(True)
            section.addWidget(body)
            layout.addWidget(frame)
            self.flow_stages.append((frame, body))
        self.flow_begin = button(
            "Draw electron flow", lambda: self.set_tool("electron"), "primary", "electron"
        )
        layout.addWidget(self.flow_begin)
        self.flow_cancel = button("Cancel this arrow", self.cancel_flow, "quiet")
        layout.addWidget(self.flow_cancel)
        pair_row = QHBoxLayout()
        pair_row.addWidget(label("Electron count", "muted"))
        self.flow_count = QComboBox()
        self.flow_count.addItem("Pair (2)", 2)
        self.flow_count.addItem("Single (1)", 1)
        self.flow_count.currentIndexChanged.connect(self.change_flow_count)
        pair_row.addWidget(self.flow_count)
        layout.addLayout(pair_row)
        layout.addSpacing(8)
        self.review_heading = label("3  Review the next step", "subtitle")
        layout.addWidget(self.review_heading)
        self.flow_summary = label("Add electron arrows to describe a transformation.", "muted")
        self.flow_summary.setWordWrap(True)
        layout.addWidget(self.flow_summary)
        self.review_button = button("Review next step", self.review_current_step, "primary")
        layout.addWidget(self.review_button)
        self.flow_feedback = label("", "muted")
        self.flow_feedback.setWordWrap(True)
        layout.addWidget(self.flow_feedback)
        layout.addStretch()
        layout.addWidget(button("Try an example", self.load_mechanism_example, "quiet"))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(guide)
        panel = QFrame()
        panel.setObjectName("GuidePanel")
        panel.setFixedWidth(264)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(0)
        panel_layout.addWidget(scroll, 1)
        footer = QFrame()
        footer.setObjectName("GuideFooter")
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(18, 12, 18, 18)
        footer_layout.setSpacing(10)
        for control in (
            self.review_heading,
            self.flow_summary,
            self.review_button,
            self.flow_feedback,
        ):
            layout.removeWidget(control)
            footer_layout.addWidget(control)
        panel_layout.addWidget(footer)
        return panel

    def add_tool(self, key, text, shortcut=None):
        action = QAction(text, self)
        action.setCheckable(True)
        if shortcut:
            action.setShortcut(shortcut)
            action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            self.view.addAction(action)
        action.setToolTip(f"{text} ({shortcut})" if shortcut else text)
        action.triggered.connect(lambda checked=False, k=key: self.set_tool(k))
        self.tool_group.addAction(action)
        self.tools.addAction(action)
        self.tool_actions[key] = action
        detail = {
            "select": "Double-click atoms to edit; double-click bonds to cycle. "
            "Alt-drag moves a molecule.",
            "bond": "Drag from an atom. Click a bond to cycle order. Keys 1, 2, 3 choose order.",
            "atom": "Click to place an atom. Type C, N, O, S, P, F, or H to change an element.",
            "electron": "Click a source, hover to preview, then click a target.",
        }.get(key, "")
        if detail:
            action.setToolTip(action.toolTip() + "\n" + detail)
        if key == "select":
            action.setChecked(True)

    def set_workspace_mode(self, mode):
        if mode == self.workspace_mode and getattr(self, "_workspace_mode_ready", False):
            return
        self.workspace_mode = mode
        self.mode_buttons[mode].setChecked(True)
        if hasattr(self, "rail_buttons"):
            self.rail_buttons["electron"].setVisible(mode == "mechanism")
            self.rail_buttons["plus"].setVisible(mode in ("mechanism", "pathway"))
            self.rail_buttons["pathway"].setVisible(mode == "pathway")
        self.guide.setVisible(mode == "mechanism" and not self.details_open)
        self.pathway_guide.setVisible(mode == "pathway" and not self.details_open)
        self.rail_layout.activate()
        self.rail.setMinimumHeight(self.rail_layout.minimumSize().height())
        if mode == "pathway":
            from molecules.domain.geometry import molecule_group, selected_atoms

            picked = selected_atoms(self.document, self.selected)
            if picked:
                first = next(iter(picked))
                group = molecule_group(self.document, first)
                if picked <= group:
                    self.pathway_source = first
        self.set_tool(
            "electron" if mode == "mechanism" else "pathway" if mode == "pathway" else "select"
        )
        self._workspace_mode_ready = True
        self.update_workspace()

    def toggle_details(self):
        self.details_open = not self.details_open
        self.inspector.setVisible(self.details_open and bool(self.selected))
        self.guide.setVisible(self.workspace_mode == "mechanism" and not self.details_open)
        self.pathway_guide.setVisible(self.workspace_mode == "pathway" and not self.details_open)
        self.position_overlays()

    def generate_example(self, name):
        self.input_mode.setCurrentText("Name")
        self.name_input.setText(name)
        self.start_lookup()

    def load_mechanism_example(self):
        self.mechanism_example()
        self.set_workspace_mode("mechanism")
        self.set_tool("select")

    def show_feedback(self, text):
        self.feedback_label.setText(text)
        self.feedback.show()
        self.position_overlays()

    def cancel_flow(self):
        self.flow_source = None
        self.view.cancel_gesture()
        self.update_workspace()

    def change_flow_count(self, *_):
        if hasattr(self, "electron_count"):
            self.electron_count.setCurrentText(str(self.flow_count.currentData()))

    def step_arrows(self):
        step = self.step_choice.currentData()
        atoms = {a.id: a for a in self.document.atoms}
        bonds = {b.id: b for b in self.document.bonds}

        def belongs(arrow):
            anchor = arrow.start_anchor
            if anchor in atoms:
                return atoms[anchor].step == step
            if anchor in bonds:
                return atoms[bonds[anchor].start].step == step
            return True

        return [a for a in self.document.arrows if a.kind == "electron" and belongs(a)]

    def review_current_step(self):
        ids = {a.id for a in self.step_arrows()}
        if ids:
            self.create_next_step(arrow_ids=ids)

    def anchor_description(self, identity):
        atoms = {a.id: a for a in self.document.atoms}
        if identity in atoms:
            a = atoms[identity]
            return f"{a.label or a.element} atom" + (f" · charge {a.charge:+d}" if a.charge else "")
        bond = next((b for b in self.document.bonds if b.id == identity), None)
        if bond:
            symbol = {1: "–", 2: "=", 3: "≡"}[bond.order]
            return f"{atoms[bond.start].element}{symbol}{atoms[bond.end].element} bond"
        return "Manual point on the canvas"

    def update_mechanism_guide(self):
        if not hasattr(self, "flow_source"):
            return
        steps = tuple(sorted({a.step for a in self.document.atoms})) or (0,)
        if steps != getattr(self, "_guide_steps", None):
            self.step_choice.blockSignals(True)
            self.step_choice.clear()
            for step in steps:
                self.step_choice.addItem(f"Step {step + 1}", step)
            self.step_choice.setCurrentIndex(len(steps) - 1)
            self.step_choice.blockSignals(False)
            self._guide_steps = steps
        has_source = self.flow_source is not None
        for index, (frame, text) in enumerate(self.flow_stages):
            frame.setProperty("active", self.view.tool == "electron" and index == int(has_source))
            frame.style().unpolish(frame)
            frame.style().polish(frame)
            if index == 0:
                text.setText(
                    self.anchor_description(self.flow_source[0])
                    if has_source
                    else "Click an atom, lone pair, or bond."
                )
            else:
                text.setText(
                    "Hover to preview. Click to place the arrow."
                    if has_source
                    else "Then click where the electrons go."
                )
        self.flow_cancel.setVisible(has_source)
        self.flow_begin.setVisible(self.view.tool != "electron")
        arrows = self.step_arrows()
        self.flow_summary.setText(
            f"{len(arrows)} electron arrow{'s' if len(arrows) != 1 else ''} on this step."
            if arrows
            else "No electron arrows yet."
        )
        self.review_button.setToolTip(
            "Preview bond and charge changes. The current drawing is preserved."
        )
        self.review_button.setEnabled(bool(arrows) and not has_source)

    def update_workspace(self):
        if not hasattr(self, "welcome"):
            return
        empty = not (self.document.atoms or self.document.arrows or self.document.notes)
        self.welcome.setVisible(empty and self.view.tool == "select")
        state = (
            frozenset(self.selected),
            self.revision,
            self.view.tool,
            self.flow_source is not None,
        )
        if state != getattr(self, "_context_state", None):
            self.build_context_bar()
            self._context_state = state
        hints = {
            "select": "Double-click to edit atoms or cycle bonds · "
            "Space-drag to pan · Alt-drag a molecule",
            "atom": f"Click to place {self.element.currentText()} · Click an atom to replace it",
            "bond": "Drag to grow a bond · Click a bond to cycle its order · Alt bypasses snapping",
            "electron": "Choose an electron source"
            if self.flow_source is None
            else "Choose a target · Escape cancels this arrow",
            "pathway": "Click a reactant, then a product to connect · "
            "Add products in any direction from the panel",
            "reaction": "Drag to place a reaction arrow",
            "equilibrium": "Drag to place an equilibrium arrow",
            "retro": "Drag to place a retrosynthesis arrow",
            "text": "Click to add text or reaction conditions",
            "plus": "Click to place a plus sign",
        }
        self._hint_text = hints.get(self.view.tool, "")
        self.canvas_hint.setText(self._hint_text)
        self.canvas_hint.adjustSize()
        self.zoom_label.setText(f"{self.view.transform().m11() * 100:.0f}%")
        self.update_mechanism_guide()
        self.update_pathway_guide()
        self.position_overlays()

    def position_overlays(self):
        if not hasattr(self, "context_bar"):
            return
        width, height = self.view.viewport().width(), self.view.viewport().height()
        self.document_badge.setVisible(self.centralWidget().width() >= 760)
        badge_text = getattr(self, "_document_badge_text", self.document_badge.text())
        available = min(420, max(30, self.centralWidget().width() - 550))
        self.document_badge.setMaximumWidth(available)
        self.document_badge.setText(
            self.document_badge.fontMetrics().elidedText(
                badge_text, Qt.TextElideMode.ElideRight, available
            )
        )
        self.document_badge.setToolTip(badge_text)
        compact = width < 560
        if compact != getattr(self, "_context_compact", None):
            self.build_context_bar()
        hint = getattr(self, "_hint_text", "")
        self.canvas_hint.setText(
            self.canvas_hint.fontMetrics().elidedText(
                hint, Qt.TextElideMode.ElideRight, max(40, width - 36)
            )
        )
        self.canvas_hint.setToolTip(hint)
        self.canvas_hint.adjustSize()
        self.context_bar.adjustSize()
        self.context_bar.move(max(8, (width - self.context_bar.width()) // 2), 14)
        self.welcome.adjustSize()
        self.welcome.move(
            max(8, (width - self.welcome.width()) // 2),
            max(80, (height - self.welcome.height()) // 2 - 20),
        )
        self.canvas_hint.move(18, max(18, height - 30))
        self.context_bar.raise_()

    def build_context_bar(self):
        compact = self._context_compact = self.view.viewport().width() < 560
        while self.context_layout.count():
            item = self.context_layout.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()
        atoms = [a for a in self.document.atoms if a.id in self.selected]
        bonds = [b for b in self.document.bonds if b.id in self.selected]
        arrows = [a for a in self.document.arrows if a.id in self.selected]
        notes = [n for n in self.document.notes if n.id in self.selected]
        self.context_bar.setVisible(bool(self.selected) or self.view.tool in ("atom", "bond"))
        if self.view.tool == "electron" and self.flow_source is not None:
            self.context_bar.hide()
            return
        from molecules.domain.geometry import rotation_atoms, selected_atoms

        picked = selected_atoms(self.document, self.selected)
        whole = (
            picked and picked == rotation_atoms(self.document, self.selected) and len(picked) > 1
        )
        if whole and self.view.tool not in ("atom", "bond"):
            self.context_layout.addWidget(label(f"{len(picked)} ATOMS", "eyebrow"))
            self.context_layout.addWidget(self.rotation_button())
            self.context_layout.addWidget(button("Copy", self.copy_selection, "quiet"))
        elif atoms and self.view.tool != "bond" or self.view.tool == "atom":
            self.context_layout.addWidget(
                label(
                    atoms[0].element
                    if len(atoms) == 1
                    else f"{len(atoms)} atoms"
                    if atoms
                    else "New atom",
                    "eyebrow",
                )
            )
            for element in ("C", "N", "O") if compact else ("C", "N", "O", "S", "H"):
                control = button(
                    element, lambda checked=False, e=element: self.quick_element(e), "chip"
                )
                control.setToolTip(f"Change element to {element} ({element})")
                self.context_layout.addWidget(control)
            if atoms:
                self.context_layout.addWidget(button("−", lambda: self.adjust_charge(-1), "chip"))
                charge = atoms[0].charge if len({a.charge for a in atoms}) == 1 else "mixed"
                self.context_layout.addWidget(
                    label(f"{charge:+d}" if isinstance(charge, int) else charge)
                )
                self.context_layout.addWidget(button("+", lambda: self.adjust_charge(1), "chip"))
        elif bonds or self.view.tool == "bond":
            self.context_layout.addWidget(label("BOND" if bonds else "NEW BOND", "eyebrow"))
            for order, name in ((1, "Single"), (2, "Double"), (3, "Triple")):
                self.context_layout.addWidget(
                    button(name, lambda checked=False, o=order: self.quick_order(o), "chip")
                )
            if bonds and not compact:
                style = QToolButton()
                style.setText("Style")
                menu = QMenu(style)
                for value in ("plain", "wedge", "hash", "wavy"):
                    menu.addAction(
                        value.title(), lambda checked=False, v=value: self.quick_bond_style(v)
                    )
                style.setMenu(menu)
                style.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
                self.context_layout.addWidget(style)
        elif arrows:
            self.context_layout.addWidget(
                label(
                    "FLOW"
                    if compact
                    else "ELECTRON FLOW"
                    if arrows[0].kind == "electron"
                    else "ARROW",
                    "eyebrow",
                )
            )
            if all(a.kind != "electron" for a in arrows):
                self.context_layout.addWidget(button("Caption…", self.edit_arrow_caption, "chip"))
                self.context_layout.addWidget(
                    button("Reverse", self.reverse_reaction_arrows, "chip")
                )
            if all(a.kind == "electron" for a in arrows):
                self.context_layout.addWidget(
                    button("Pair", lambda: self.quick_arrow_electrons(2), "chip")
                )
                self.context_layout.addWidget(
                    button("Single", lambda: self.quick_arrow_electrons(1), "chip")
                )
                if not compact:
                    self.context_layout.addWidget(button("Flip curve", self.flip_curve, "chip"))
        elif notes:
            self.context_layout.addWidget(label("TEXT", "eyebrow"))
            self.context_layout.addWidget(button("Edit text", self.edit_note, "chip"))
        if atoms and not whole and not compact:
            self.context_layout.addWidget(button("Molecule", self.select_molecule, "quiet"))
        if atoms and not whole and not compact:
            self.context_layout.addWidget(self.rotation_button(compact=True))
        if self.selected:
            self.context_layout.addWidget(button("Details", self.toggle_details, "quiet"))
            remove = QToolButton()
            remove.setIcon(icon("delete"))
            remove.setToolTip("Delete selection")
            remove.setAccessibleName("Delete selection")
            remove.clicked.connect(self.delete_selection)
            self.context_layout.addWidget(remove)
        for index in range(self.context_layout.count()):
            self.context_layout.itemAt(index).widget().show()
        self.context_layout.activate()
        self.context_bar.adjustSize()

    def quick_element(self, element):
        self.element.setCurrentText(element)
        if any(a.id in self.selected for a in self.document.atoms):
            self.edit(
                "Change element",
                lambda d: setattr(
                    d,
                    "atoms",
                    [
                        replace(
                            a, element=element, label="", aromatic=False, chiral=0, hydrogens=-1
                        )
                        if a.id in self.selected
                        else a
                        for a in d.atoms
                    ],
                ),
            )
        else:
            self.set_tool("atom")
        self.view.setFocus()

    def adjust_charge(self, delta):
        self.edit(
            "Change charge",
            lambda d: setattr(
                d,
                "atoms",
                [
                    replace(a, charge=a.charge + delta) if a.id in self.selected else a
                    for a in d.atoms
                ],
            ),
        )

        self.view.setFocus()

    def quick_order(self, order):
        self.order.setValue(order)
        if any(b.id in self.selected for b in self.document.bonds):
            self.set_bond_order()
        else:
            self.set_tool("bond")
        self.view.setFocus()

    def quick_bond_style(self, value):
        self.bond_style.setCurrentText(value)
        self.apply_bond_style()
        self.view.setFocus()

    def cycle_bond(self, identity):
        self.selected = {identity}
        bond = next(b for b in self.document.bonds if b.id == identity)
        self.quick_order(bond.order % 3 + 1)

    def quick_arrow_electrons(self, count):
        self.electron_count.setCurrentText(str(count))
        self.edit(
            "Change electron count",
            lambda d: setattr(
                d,
                "arrows",
                [
                    replace(a, electrons=count)
                    if a.id in self.selected and a.kind == "electron"
                    else a
                    for a in d.arrows
                ],
            ),
        )
        self.view.setFocus()

    def flip_curve(self):
        self.edit(
            "Flip electron curve",
            lambda d: setattr(
                d,
                "arrows",
                [
                    replace(a, curvature=-a.curvature)
                    if a.id in self.selected and a.kind == "electron"
                    else a
                    for a in d.arrows
                ],
            ),
        )

    def select_molecule(self, identity=None):
        from molecules.domain.geometry import molecule_group, selected_atoms

        seeds = {identity} if identity else selected_atoms(self.document, self.selected)
        ids = set()
        for seed in seeds:
            ids.update(molecule_group(self.document, seed))
        self.selected = ids | {b.id for b in self.document.bonds if b.start in ids and b.end in ids}
        self.refresh()

    def finish_atom_text(self, identity, text):
        text = text.strip()
        if not text or len(text) > 40:
            return
        self.edit(
            "Edit atom label",
            lambda d: setattr(
                d,
                "atoms",
                [
                    replace(
                        a,
                        element=text if text in ELEMENTS else a.element,
                        label="" if text in ELEMENTS else text,
                        aromatic=False if text in ELEMENTS else a.aromatic,
                        hydrogens=-1 if text in ELEMENTS else a.hydrogens,
                    )
                    if a.id == identity
                    else a
                    for a in d.atoms
                ],
            ),
        )
