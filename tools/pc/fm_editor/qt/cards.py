"""The Cards page."""
from __future__ import annotations

from .common import *      # noqa: F401,F403
from .common import (_qimage, _line_count, _pairs_text, _parse_pairs, _whole,
                     _card_image, _pack_texture)      # noqa: F401


class CardsMixin:
    def preview_card_model(self):
        self.model_preview_button.setChecked(True)
        self.preview_image.hide()
        self.model_preview.show()
        self.model_preview.show_card(self.project, self.files, self.current)

    def _open_card_model_window(self):
        from .monster_view import MonsterDialog
        dialog = getattr(self, "model_preview_dialog", None)
        if dialog is None:
            dialog = MonsterDialog(self)
            self.model_preview_dialog = dialog
        dialog.show_card(self.project, self.files, self.current)
        dialog.canvas.yaw = self.model_preview.yaw
        dialog.canvas.pitch = self.model_preview.pitch
        dialog.canvas.zoom = self.model_preview.zoom
        dialog.canvas.render()
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def preview_card_text(self):
        existing = getattr(self, "text_preview_dialog", None)
        if existing is not None:
            existing.show()
            existing.raise_()
            return
        dialog = QDialog(self)
        self.text_preview_dialog = dialog
        dialog.setWindowTitle("Card text preview")
        layout = QVBoxLayout(dialog)
        controls = QHBoxLayout()
        mode = QComboBox()
        mode.addItems(["Retail font", "HD text: port font", "HD text: font file"])
        scale = QSpinBox()
        scale.setRange(1, 4)
        scale.setValue(2)
        choose = QPushButton("Font file…")
        for control in (mode, scale, choose):
            controls.addWidget(control)
        layout.addLayout(controls)
        picture, details = QLabel(), QLabel()
        details.setWordWrap(True)
        layout.addWidget(picture)
        layout.addWidget(details)
        cache = {}
        font_path = None

        def refresh(*_):
            if self._loading:
                return
            try:
                path = card_text.port_face_path() if mode.currentIndex() == 1 else font_path
                face = None
                if mode.currentIndex() and path:
                    if path not in cache:
                        cache[path] = ttf.Font(path)
                    face = cache[path]
                key = (id(self.files.wa), id(face))
                if key not in cache:
                    cache[key] = card_text.Renderer(card_text.RetailFont(self.files.wa), face)
                rendered, lay = cache[key].render(self.description.toPlainText(), scale.value())
                picture.setPixmap(QPixmap.fromImage(_qimage(rendered.width, rendered.height, rendered.rgba)))
                notes = [f"{lay.rows} rows; {lay.hidden} hidden. Row {card_text.SHOWN_ROWS} overlaps the frame."]
                if lay.cut_rows:
                    notes.append("Long words cut on rows: " + ", ".join(str(row + 1) for row in lay.cut_rows))
                if mode.currentIndex() and not face:
                    notes.append("No font selected or found; using retail font.")
                if face:
                    notes.append(f"{face.name} ({path})")
                    if scale.value() == 1:
                        notes.append("HD text starts at 2x; 1x uses the retail font.")
                details.setText("\n".join(notes))
            except (OSError, ValueError, IndexError, KeyError, struct.error, ttf.FontError) as problem:
                picture.clear()
                details.setText(str(problem))

        def choose_font():
            nonlocal font_path
            path, _ = QFileDialog.getOpenFileName(self, "Choose a font", "", "Fonts (*.ttf *.ttc *.otf)")
            if path:
                font_path = path
                mode.setCurrentIndex(2)
                refresh()

        def closed(*_):
            self.description.textChanged.disconnect(refresh)
            self.text_preview_dialog = None
            self.refresh_text_preview = None
            dialog.deleteLater()

        self.refresh_text_preview = refresh
        self.description.textChanged.connect(refresh)
        mode.currentIndexChanged.connect(refresh)
        scale.valueChanged.connect(refresh)
        choose.clicked.connect(choose_font)
        dialog.finished.connect(closed)
        refresh()
        dialog.show()
    def toggle_password_visibility(self, visible):
        self.fields["password"].setEchoMode(
            QLineEdit.EchoMode.Normal if visible else QLineEdit.EchoMode.Password)
    def _build_cards(self, parent):
        ui_path = UI_DIR / "cards_page.ui"
        ui_file = QFile(str(ui_path))
        if not ui_file.open(QIODevice.OpenModeFlag.ReadOnly):
            raise RuntimeError(f"Could not open Cards Designer form {ui_path}: {ui_file.errorString()}")
        loader = QUiLoader()
        page = loader.load(ui_file, parent)
        ui_file.close()
        if page is None:
            raise RuntimeError(f"Could not load Cards Designer form {ui_path}: {loader.errorString()}")
        page_layout = QVBoxLayout(parent)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(page)
        self.cards_form = page

        def widget(widget_type, name):
            found = page.findChild(widget_type, name)
            if found is None:
                raise RuntimeError(f"Cards Designer form is missing widget {name!r}")
            return found

        self.search = widget(QLineEdit, "cardSearchEdit")
        self.filter = widget(QComboBox, "cardFilterCombo")
        self.advanced_filter_button = widget(QPushButton, "advancedCardFilterButton")
        self.filter.setMaximumWidth(190)
        self.advanced_card_filters = {"types": set(), "attributes": set(), "bounds": {}}
        self.listing = widget(QTableWidget, "cardTable")
        self.card_count = widget(QLabel, "cardCountLabel")
        self.add_button = widget(QPushButton, "addCopyButton")
        designer_card_id = widget(QSpinBox, "cardIdSpinBox")
        self.card_id = CardIdSpinBox(designer_card_id.parentWidget())
        self.card_id.setObjectName(designer_card_id.objectName())
        self.card_id.setRange(designer_card_id.minimum(), designer_card_id.maximum())
        self.card_id.setReadOnly(True)
        self.card_id.setMaximumWidth(90)
        designer_card_id.parentWidget().layout().replaceWidget(designer_card_id, self.card_id)
        designer_card_id.deleteLater()
        self.description = widget(QTextEdit, "descriptionEdit")
        # The game wraps the text at 20 letters a line (validate.text_lines).
        # A fixed-pitch face is what makes those columns countable while typing,
        # as the Tk form's 21-column Text box does.
        card_face = QFont(self.description.font())
        card_face.setStyleHint(QFont.StyleHint.Monospace)
        card_face.setFamilies(["Consolas", "DejaVu Sans Mono", "Liberation Mono", "Menlo",
                               "Courier New", "monospace"])
        card_face.setFixedPitch(True)
        self.description.setFont(card_face)
        self.description.ensurePolished()
        self.description.setFixedHeight(
            8 * self.description.fontMetrics().lineSpacing()
            + int(2 * self.description.document().documentMargin()) + 18)
        self.description_status = widget(QLabel, "descriptionStatusLabel")
        self.added_panel = widget(QFrame, "addedCardPanel")
        self.key_edit = widget(QLineEdit, "stableKeyEdit")
        self.drops = widget(QCheckBox, "dropsCheckBox")
        self.opponents = widget(QCheckBox, "opponentsCheckBox")
        self.base_card_info = widget(QLabel, "baseCardInfoLabel")
        self.apply_button = widget(QPushButton, "applyButton")
        self.remove_button = widget(QPushButton, "removeCopyButton")
        self.validation = widget(QLabel, "validationLabel")
        self.preview_image = widget(QLabel, "previewImageLabel")
        self.disc_preview_button = widget(QPushButton, "discPreviewButton")
        self.hd_preview_button = widget(QPushButton, "hdPreviewButton")
        self.model_preview_button = widget(QPushButton, "modelPreviewButton")
        self.model_preview_button.clicked.connect(self.preview_card_model)
        self.model_preview_button.installEventFilter(self)
        from .monster_view import ModelCanvas
        self.model_preview = ModelCanvas(self.preview_image.parentWidget())
        self.model_preview.setObjectName("modelPreviewCanvas")
        preview_layout = self.preview_image.parentWidget().layout()
        preview_layout.insertWidget(preview_layout.indexOf(self.preview_image) + 1, self.model_preview, 1)
        self.model_preview.hide()
        self.model_preview.doubleClicked.connect(self._open_card_model_window)
        self.fields = {
            "name": widget(QLineEdit, "nameEdit"),
            "type": widget(QComboBox, "typeCombo"),
            "attribute": widget(QComboBox, "attributeCombo"),
            "level": widget(QSpinBox, "levelSpinBox"),
            "star1": widget(QComboBox, "guardian1Combo"),
            "star2": widget(QComboBox, "guardian2Combo"),
            "attack": widget(QSpinBox, "attackSpinBox"),
            "defense": widget(QSpinBox, "defenseSpinBox"),
            "frame": widget(QComboBox, "frameCombo"),
            "password": widget(QLineEdit, "passwordEdit"),
            "starchips": widget(QSpinBox, "starchipsSpin"),
            # A magic, trap, ritual or equip card has an effect where a
            # monster has its stats, and an attack trap a threshold with it.
            "effect": widget(QComboBox, "effectCombo"),
            "trap_threshold": widget(QSpinBox, "trapThresholdSpin"),
            # What an equip adds to the monster it is on, where another kind
            # of card chooses an effect ("equips" bonus_attack/bonus_defense).
            "equip_attack": widget(QSpinBox, "equipAttackSpin"),
            "equip_defense": widget(QSpinBox, "equipDefenseSpin"),
        }
        self.effect_caption = widget(QLabel, "effectLabel")
        self.trap_caption = widget(QLabel, "trapThresholdLabel")
        self.bonus_captions = {"equip_attack": widget(QLabel, "equipAttackLabel"),
                               "equip_defense": widget(QLabel, "equipDefenseLabel")}
        self._shown_effect, self._shown_threshold = "", -1
        # Password and Starchips share Card Data's two columns, so the right
        # one starts where Attribute, Frame, DEF and Guardian Star 2 do. Their
        # grid is its own, and without this the password field takes the width
        # it likes and pushes Starchips out of line.
        # The password is up to eight digits and nothing else, so the box
        # takes nothing else either, as the Starchips spin box does.
        password = self.fields["password"]
        password.setMaxLength(8)
        password.setValidator(QRegularExpressionValidator(QRegularExpression(r"[0-9]{0,8}"), password))
        password.setToolTip("Up to 8 digits, or blank for none")
        password_grid = page.findChild(QGridLayout, "passwordGrid")
        for column in (0, 1):
            password_grid.setColumnStretch(column, 1)
        # Game Text: the box, what the game makes of it, and the colour
        # codes it reads ({f8 0A NN}, card_text.Renderer).
        self.card_data_tabs = widget(QTabWidget, "cardDataTabs")
        self._build_card_effects(widget)
        self.card_text_preview = widget(QLabel, "cardTextPreview")
        self.card_text_preview.setStyleSheet("background:#0b1422;border:1px solid #26374c;border-radius:6px")
        self.description.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.description.customContextMenuRequested.connect(self._card_text_menu)
        self.preview_panel = self.preview_image.parentWidget()
        self.preview_panel.installEventFilter(self)
        self._build_card_reference(parent)
        self.extra_info = QLabel()
        self.extra_info.setWordWrap(True)
        form_layout = self.validation.parentWidget().layout()
        form_layout.insertWidget(form_layout.indexOf(self.validation), self.extra_info)
        self.revert_button = widget(QPushButton, "revertButton")
        for field in self.fields.values():
            if isinstance(field, QLineEdit):
                field.returnPressed.connect(self.apply_card)
            elif isinstance(field, QSpinBox):
                field.lineEdit().returnPressed.connect(self.apply_card)
        self.type_box = self.fields["type"]
        self.attribute_box = self.fields["attribute"]
        self.level_box = self.fields["level"]
        self.attack_box = self.fields["attack"]
        self.defense_box = self.fields["defense"]
        self.star1_box = self.fields["star1"]
        self.star2_box = self.fields["star2"]
        self.frame_box = self.fields["frame"]

        self.filter.addItems(self.FILTERS)
        self.type_box.addItems(TYPE_NAMES)
        self.attribute_box.addItems(ATTRIBUTE_NAMES + ["6 (magic)", "7 (trap)"])
        self.star1_box.addItems(STAR_NAMES)
        self.star2_box.addItems(STAR_NAMES)
        self.frame_box.addItems(["By card type"] + FRAME_NAMES)
        self.listing.setColumnCount(6)
        self.listing.setHorizontalHeaderLabels(["ID", "Name", "Type", "ATK", "DEF", "State"])
        self.listing.setAlternatingRowColors(True)
        self.listing.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.listing.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.listing.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.listing.verticalHeader().setVisible(False)
        header = self.listing.horizontalHeader()
        header.setStretchLastSection(False)
        # Only the name grows. Everything else is as wide as its content needs,
        # so all six columns fit a narrow list instead of scrolling sideways.
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setMinimumSectionSize(40)
        for column, width in ((0, 44), (2, 92), (3, 52), (4, 52), (5, 64)):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
            header.resizeSection(column, width)
        self.listing.setWordWrap(False)         # a long name elides, it does not double the row
        self.listing.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.attack_box.setRange(0, 5110)
        self.attack_box.setSingleStep(10)
        self.defense_box.setRange(0, 5110)
        self.defense_box.setSingleStep(10)
        # 0 is no card: the spin box shows "—" with nothing selected.
        self.card_id.setRange(0, 32766)
        self.card_id.setSpecialValueText("—")
        self.card_id.setReadOnly(True)
        self.apply_button.setObjectName("primary")
        self.description_status.setStyleSheet("color:#9aacc4")
        self.card_count.setStyleSheet("color:#9aacc4")
        self.base_card_info.setStyleSheet("color:#9aacc4")
        self.validation.setStyleSheet("color:#ff7777")
        self.preview_image.setStyleSheet("background:#101a2a;border:1px solid #26374c;border-radius:7px")
        self.preview_mode_group = QButtonGroup(page)
        self.preview_mode_group.setExclusive(True)
        self.preview_mode_group.addButton(self.disc_preview_button)
        self.preview_mode_group.addButton(self.hd_preview_button)
        self.preview_mode_group.addButton(self.model_preview_button)
        self.model_preview_button.setCheckable(True)
        self.disc_preview_button.setCheckable(True)
        self.hd_preview_button.setCheckable(True)
        self.disc_preview_button.setChecked(True)
        for name in ("listTitle", "dataTitle", "previewTitle"):
            widget(QLabel, name).setStyleSheet("font-size:16px;font-weight:650;color:#f3f7fc")
        # The card form is a column of paired fields, not a page: hold it to the
        # width it needs so the list beside it keeps its six columns.
        data_scroll = widget(QScrollArea, "cardDataScroll")
        data_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        short_popup(self.fields["effect"])      # a type's effects outrun the screen
        for box in (self.type_box, self.attribute_box, self.star1_box, self.star2_box, self.frame_box,
                    self.fields["effect"]):
            box.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
            box.setMinimumContentsLength(8)
            box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        for field in (self.level_box, self.attack_box, self.defense_box):
            field.setMaximumWidth(150)
        widget(QFrame, "cardListPanel").setMinimumWidth(400)
        widget(QFrame, "cardDataPanel").setMinimumWidth(420)
        widget(QFrame, "cardPreviewPanel").setMinimumWidth(240)
        splitter = widget(QSplitter, "cardsSplitter")
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 4)
        splitter.setStretchFactor(2, 3)
        splitter.setSizes([520, 610, 490])

        # A card in the list: where the mod uses it, and its picture
        # (card_links.install does this for the Tk lists).
        self.listing.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.listing.customContextMenuRequested.connect(self._card_list_menu)
        self.search.textChanged.connect(self.refresh_cards)
        self.disc_preview_button.clicked.connect(lambda: self._set_preview_scale(1))
        self.hd_preview_button.clicked.connect(lambda: self._set_preview_scale(4))
        self.filter.currentTextChanged.connect(self.refresh_cards)
        self.advanced_filter_button.clicked.connect(self._open_advanced_card_filter)
        self.listing.itemSelectionChanged.connect(self.select_card)
        self.add_button.clicked.connect(self.add_card)
        self.description.textChanged.connect(self.update_text_count)
        self.apply_button.clicked.connect(self.apply_card)
        widget(QPushButton, "revertButton").clicked.connect(self.revert_card)
        self.remove_button.clicked.connect(self.remove_card)
        for field in (self.fields["name"], self.fields["password"], self.key_edit):
            field.textChanged.connect(self._render_preview)
        self.type_box.currentIndexChanged.connect(self._type_changed)
        self.fields["effect"].currentIndexChanged.connect(self._effect_changed)
        for field in (self.attribute_box, self.star1_box, self.star2_box, self.frame_box):
            field.currentIndexChanged.connect(self._render_preview)
        for field in (self.star1_box, self.star2_box):
            field.currentIndexChanged.connect(self._render_card_text)
        for field in (self.level_box, self.attack_box, self.defense_box):
            field.valueChanged.connect(self._render_preview)
        # The marks follow what is typed, not only what is applied.
        for field in (self.fields["name"], self.fields["password"]):
            field.textChanged.connect(self._marks_follow)
        for field in (self.type_box, self.attribute_box, self.star1_box, self.star2_box, self.frame_box,
                      self.fields["effect"]):
            field.currentIndexChanged.connect(self._marks_follow)
        for field in (self.level_box, self.attack_box, self.defense_box, self.fields["starchips"],
                      self.fields["equip_attack"], self.fields["equip_defense"]):
            field.valueChanged.connect(self._marks_follow)
        self.description.textChanged.connect(self._marks_follow)
    def _card_list_menu(self, point):
        item = self.listing.itemAt(point)
        if item is None:
            return
        row = self.listing.item(item.row(), 0)
        cid = row.data(Qt.ItemDataRole.UserRole) if row is not None else None
        if not cid:
            return
        menu = QMenu(self)
        menu.addAction(f"Where {self.project.card_label(cid)} is used…").triggered.connect(
            lambda: self.show_card_uses(cid))
        menu.addAction("Show its picture in Art").triggered.connect(lambda: self.goto_art(cid))
        menu.exec(self.listing.viewport().mapToGlobal(point))

    def show_card_uses(self, cid):
        """Everything in the mod that names this card, each line a way to the
        page it is on (card_uses.where_used; the Tk window's is card_links.UsesWindow)."""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Where {self.project.card_label(cid)} is used")
        dialog.resize(640, 440)
        layout = QVBoxLayout(dialog)
        summary = QLabel(dialog)
        layout.addWidget(summary)
        table = QTableWidget(0, 2, dialog)
        table.setHorizontalHeaderLabels(["Where", "What"])
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        table.setToolTip("Double-click a line to go to it.")
        layout.addWidget(table, 1)
        close = QPushButton("Close", dialog)
        close.clicked.connect(dialog.accept)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(close)
        layout.addLayout(row)
        lines = []

        def fill():
            """Listed again each time it comes back, so it follows the edits."""
            lines[:] = card_uses.where_used(self.project, cid) if cid in self.project.cards else []
            table.setRowCount(len(lines))
            for index, (where, what, target) in enumerate(lines):
                for column, text in enumerate((where, what)):
                    cell = QTableWidgetItem(str(text))
                    cell.setData(Qt.ItemDataRole.UserRole, index)
                    if target is None:
                        cell.setForeground(QColor("#9aacc4"))      # nowhere to go from here
                    table.setItem(index, column, cell)
            table.resizeColumnToContents(0)
            summary.setText(f"{len(lines)} use(s)" if lines else
                            "Nothing in the mod uses this card: no fusion, equip, ritual, deck, drop, "
                            "pack or starter pool.")
            if lines:
                table.selectRow(0)

        def go(index):
            if 0 <= index < len(lines) and lines[index][2] is not None:
                self._go_to_use(lines[index][2])
                fill()

        table.cellDoubleClicked.connect(lambda r, _c=0: go(r))
        fill()
        self.card_uses_dialog = dialog
        dialog.finished.connect(lambda *_: setattr(self, "card_uses_dialog", None))
        dialog.show()
        return dialog

    def _go_to_use(self, target):
        """Where a line of "Where it's used" points, in this window's pages.
        The areas and targets the Problems page already goes to
        (card_links.open_target does this for the Tk window)."""
        kind = target[0]
        area, where = {"card": ("Cards", lambda: target[1]),
                       "fusions": ("Fusions", lambda: (target[1],)),
                       "equips": ("Equips", lambda: target[1]),
                       "rituals": ("Rituals", lambda: target[1]),
                       "pool": ("Duelists", lambda: (target[1], target[2])),
                       "starter": ("Starter decks", lambda: target[1]),
                       "pack": ("Packs", lambda: target[1])}.get(kind, (None, None))
        if area is None:
            return
        self.go_to(SimpleNamespace(area=area, where="", message="", target=where()))

    def _open_advanced_card_filter(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Advanced card filters")
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        lists = QHBoxLayout()
        type_list = self._checkable_list(TYPE_NAMES, dialog, height=8)
        attribute_list = self._checkable_list(ATTRIBUTE_NAMES, dialog, height=8)
        type_list.setMaximumHeight(164)
        attribute_list.setMaximumHeight(164)
        for title, listing in (("Card type", type_list), ("Attribute", attribute_list)):
            panel = QVBoxLayout()
            panel.addWidget(QLabel(title, dialog))
            panel.addWidget(listing)
            lists.addLayout(panel, 1)
        layout.addLayout(lists)
        ranges = QGridLayout()
        range_edits = {}
        for column, (label, low, high) in enumerate((("ATK", "atk_min", "atk_max"),
                                                     ("DEF", "def_min", "def_max"),
                                                     ("Level", "level_min", "level_max"))):
            ranges.addWidget(QLabel(label, dialog), 0, column * 3)
            ranges.addWidget(QLabel("Min", dialog), 1, column * 3)
            low_edit = QLineEdit(dialog)
            low_edit.setPlaceholderText("Any")
            value = self.advanced_card_filters["bounds"].get(low)
            low_edit.setText("" if value is None else str(value))
            ranges.addWidget(low_edit, 1, column * 3 + 1)
            ranges.addWidget(QLabel("Max", dialog), 2, column * 3)
            high_edit = QLineEdit(dialog)
            high_edit.setPlaceholderText("Any")
            value = self.advanced_card_filters["bounds"].get(high)
            high_edit.setText("" if value is None else str(value))
            ranges.addWidget(high_edit, 2, column * 3 + 1)
            range_edits[low], range_edits[high] = low_edit, high_edit
        layout.addLayout(ranges)
        for listing, values in ((type_list, self.advanced_card_filters["types"]),
                                (attribute_list, self.advanced_card_filters["attributes"])):
            for i in range(listing.count()):
                if i in values:
                    listing.item(i).setCheckState(Qt.CheckState.Checked)
        actions = QHBoxLayout()
        clear = QPushButton("Clear filters", dialog)
        cancel = QPushButton("Cancel", dialog)
        apply = QPushButton("Apply filters", dialog)
        apply.setObjectName("primary")
        actions.addWidget(clear)
        actions.addStretch(1)
        actions.addWidget(cancel)
        actions.addWidget(apply)
        layout.addLayout(actions)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        dialog.setMinimumWidth(550)
        clear.clicked.connect(lambda: (self._clear_checkable_list(type_list),
                                       self._clear_checkable_list(attribute_list),
                                       [edit.clear() for edit in range_edits.values()]))
        cancel.clicked.connect(dialog.reject)
        apply.clicked.connect(dialog.accept)
        if not dialog.exec():
            return
        new_bounds = {}
        try:
            for key, edit in range_edits.items():
                value = edit.text().strip()
                new_bounds[key] = int(value) if value else None
            for label, low, high in (("ATK", "atk_min", "atk_max"), ("DEF", "def_min", "def_max"),
                                     ("Level", "level_min", "level_max")):
                if new_bounds[low] is not None and new_bounds[high] is not None and new_bounds[low] > new_bounds[high]:
                    raise ValueError(f"{label} minimum exceeds maximum")
        except ValueError as problem:
            QMessageBox.warning(self, "Advanced filters", str(problem))
            return
        self.advanced_card_filters = {
            "types": {i for i in range(type_list.count())
                      if type_list.item(i).checkState() == Qt.CheckState.Checked},
            "attributes": {i for i in range(attribute_list.count())
                           if attribute_list.item(i).checkState() == Qt.CheckState.Checked},
            "bounds": new_bounds,
        }
        self.refresh_cards(select_id=self.current)
    def refresh_cards(self, *_args, select_id=None):
        if not hasattr(self, "listing") or self.project is None:
            return
        selected = select_id or self.current
        self._loading = True
        held = sort_paused(self.listing)
        self.listing.setRowCount(0)
        for cid in sorted(self.project.cards):
            if not self._wanted(cid): continue
            card = self.project.cards[cid]
            row = self.listing.rowCount(); self.listing.insertRow(row)
            state = ("added" if cid in self.project.added else "changed" if self.project.card_changed(cid)
                     else "notes" if cid in self.project.notes else "")
            for col, value in enumerate((cid, card.name, TYPE_NAMES[card.type], card.attack, card.defense, state)):
                item = TableItem()
                item.setData(Qt.ItemDataRole.DisplayRole, value)
                if col == 0: item.setData(Qt.ItemDataRole.UserRole, cid)
                self._tint_state(item, state)
                self.listing.setItem(row, col, item)
        sort_resumed(self.listing, held)
        for row in range(self.listing.rowCount()):
            if self.listing.item(row, 0).data(Qt.ItemDataRole.UserRole) == selected:
                self.listing.selectRow(row)
                break
        if self.listing.currentRow() < 0 and self.listing.rowCount():
            self.listing.selectRow(0)
        self.card_count.setText(f"{self.listing.rowCount()} cards")
        self._loading = False
        if self.listing.currentRow() >= 0:
            self.select_card()
        else:
            # A filter with no results must not discard a pending edit.
            if self.current and not self.apply_card(quiet=True):
                return
            self.show_card(None)
    def select_card(self):
        if self._loading:
            return
        row = self.listing.currentRow()
        if row < 0: return
        item = self.listing.item(row, 0)
        cid = item.data(Qt.ItemDataRole.UserRole) if item else None
        if cid == self.current: return
        if self.current and not self.apply_card(quiet=True):
            self.refresh_cards(select_id=self.current)
            return
        self.show_card(cid)
    def goto_card(self, cid):
        """Show a card whatever the list is filtered to (CardsTab.goto)."""
        self.advanced_card_filters = {"types": set(), "attributes": set(), "bounds": {}}
        self.filter.setCurrentText(self.FILTERS[0])
        self.search.clear()
        self.refresh_cards(select_id=cid)
    def show_card(self, cid):
        self._loading = True
        self.current = cid
        if not cid or cid not in self.project.cards:
            self._clear_card_form()
            self._shown_effect, self._shown_threshold = "", -1
            self.effects_table.setRowCount(0)
            self._card_effect_buttons()
            for part in (self.effect_caption, self.fields["effect"],
                         self.trap_caption, self.fields["trap_threshold"],
                         *self.bonus_captions.values(),
                         self.fields["equip_attack"], self.fields["equip_defense"]):
                part.setVisible(False)
            self._loading = False
            return
        for widget in self._card_form_widgets():
            widget.setEnabled(True)
        card = self.project.cards[cid]
        self.card_id.setValue(cid)
        self.fields["name"].setText(card.name)
        self.fields["type"].setCurrentIndex(card.type)
        self._last_type_index = card.type
        self.fields["attribute"].setCurrentIndex(card.attribute)
        self.fields["level"].setValue(card.level)
        self.fields["attack"].setValue(card.attack)
        self.fields["defense"].setValue(card.defense)
        choices = guardian_stars.choices(self.project.other.get("guardian_stars"))
        # Keep even undefined imported IDs intact so validation can report them.
        while len(choices) <= max(card.star1, card.star2):
            choices.append(str(len(choices)))
        for key in ("star1", "star2"):
            self.fields[key].clear()
            self.fields[key].addItems(choices)
            self.fields[key].setCurrentIndex(getattr(card, key))
        threshold = self.project.trap_threshold_override(cid)
        # Anything else written there is the modder's: shown as the default,
        # and left alone unless the box is changed.
        self._shown_threshold = threshold if type(threshold) is int and 0 <= threshold <= 65535 else -1
        self.fields["trap_threshold"].setValue(self._shown_threshold)
        self._load_equip_bonus(cid)
        self._refresh_card_effects()
        self._show_card_kind(select=self._effect_label(self._effect_shown(cid)))
        # What the list ended up showing, which is what an untouched form has.
        self._shown_effect = self.fields["effect"].currentText()
        self.fields["frame"].setCurrentIndex(card.frame + 1)
        self.fields["password"].setText(self.project.password(cid))
        # The Password screen sells the disc's cards and knows nothing of an
        # added one, so there is no price to put on it.
        sold = cid in self.project.retail.cards
        self.fields["starchips"].setValue((self.project.starchip_cost(cid) or 0) if sold else 0)
        self.fields["starchips"].setEnabled(sold)
        self.fields["starchips"].setSpecialValueText("free" if sold else "not sold there")
        self.description.setPlainText(card.description)
        added = self.project.added.get(cid)
        self.added_panel.setVisible(added is not None)
        self.remove_button.setVisible(added is not None)
        self.key_edit.setText(added.key if added else "")
        self.drops.setChecked(added.drops if added else True)
        self.opponents.setChecked(added.opponents if added else False)
        self.base_card_info.setText(
            f"Copy of {self.project.card_label(added.base)}; identity {self.project.identity(cid)}\n"
            "Its password is for the card view; the Password screen sells disc cards."
            if added else "")
        self._show_card_reference(cid, added)
        extra = added.extra if added else self.project.card_extra.get(cid, {})
        kept = sorted(set(extra) - {"effect", "trap_threshold", "effects"})      # the form edits those
        self.extra_info.setText("Kept as written in mod.json: " + ", ".join(kept) if kept else "")
        self.revert_button.setText("Revert to Base" if added else "Revert to Retail")
        self._render_preview()
        self.update_text_count()
        self.validation.setText("")
        self._loading = False
        self._render_preview()
        if self.model_preview_button.isChecked():
            self.model_preview.show_card(self.project, self.files, cid)
        dialog = getattr(self, "model_preview_dialog", None)
        if dialog is not None and dialog.isVisible():
            dialog.show_card(self.project, self.files, cid)
        if getattr(self, "refresh_text_preview", None):
            self.refresh_text_preview()
    def _set_monster_fields_enabled(self, enabled):
        for name in ("attribute", "level", "attack", "defense", "star1", "star2"):
            self.fields[name].setEnabled(enabled)
    def _type_changed(self, index):
        self._last_type_index = index
        if not self._loading:
            self._show_card_kind()
            self._render_preview()
            self._render_card_text()

    def _effect_changed(self, _index=0):
        if not self._loading:
            self._show_trap_threshold()

    # A magic, trap, ritual or equip card's effect (tabs.py, cards.c
    # Cards_EffectId): the disc card of its own type whose effect it has, so
    # the game and the CPU play it as that card.
    EFFECT_NONE = "(none)"

    def _effect_kind(self, eid) -> int:
        """The type of the disc card `eid`, if it is no monster; else -1."""
        card = self.project.retail.cards.get(eid) if self.project else None
        return card.type if card and not card.is_monster() else -1

    def _effect_label(self, eid) -> str:
        if self._effect_kind(eid) < 0:
            return self.EFFECT_NONE
        card = self.project.retail.cards[eid]
        # Names describe fixed retail behaviours, not the mod's current
        # cards. Only duplicate names need a number to tell the choices apart.
        duplicate = any(other.id != eid and other.type == card.type and other.name == card.name
                        for other in self.project.retail.cards.values())
        return f"{card.name} ({eid})" if duplicate or card.name == self.EFFECT_NONE else card.name

    def _effect_default(self, cid) -> int:
        """The effect the card has with no "effect" key: a disc card its own,
        a copy its base's."""
        return self.project.effect_of(self.project.base_of(cid)) if cid in self.project.added else cid

    def _effect_shown(self, cid) -> int:
        eid = self.project.effect_of(cid)
        return eid if self._effect_kind(eid) == self.project.cards[cid].type else 0

    def _chosen_effect(self) -> int:
        kind = self.fields["type"].currentIndex()
        chosen = self.fields["effect"].currentText()
        return next((eid for eid in self.project.retail.cards
                     if self._effect_kind(eid) == kind and self._effect_label(eid) == chosen), 0)

    def _show_card_kind(self, select=None):
        """The monster's fields for a monster, the effect for the rest
        (tabs.CardsTab.show_kind)."""
        kind = self.fields["type"].currentIndex()
        monster = kind < gamedata.TYPE_MAGIC
        combo = self.fields["effect"]
        self._set_monster_fields_enabled(monster)
        # An equip needs none: a monster copied into one is played as an
        # equip whatever its effect says (tabs.show_kind, cards.c).
        chooses = not monster and kind != gamedata.TYPE_EQUIP
        self.effect_caption.setVisible(chooses)
        combo.setVisible(chooses)
        if chooses and self.project is not None:
            cid = self.current
            # The disc's cards of the same type: one of another would be
            # played as its own type, and the CPU would not know what to do
            # with it. "(none)" only for a card with no effect of its own to
            # fall back on.
            own = cid is not None and self._effect_kind(self._effect_default(cid)) == kind
            choices = [] if own else [self.EFFECT_NONE]
            choices += [self._effect_label(eid) for eid in sorted(self.project.retail.cards)
                        if self._effect_kind(eid) == kind]
            wanted = select if select is not None else combo.currentText()
            # An "effect" written for another type (shown as none) fits this
            # one: shown, so that the change of type keeps it.
            if select is None and cid and wanted == self._shown_effect:
                stored = self.project.effect_of(cid)
                if self._effect_kind(stored) == kind and self._effect_label(stored) in choices:
                    wanted = self._effect_label(stored)
            if wanted not in choices:
                wanted = choices[0] if not own else self._effect_label(self._effect_default(cid))
            blocked = combo.blockSignals(True)
            combo.clear()
            combo.addItems(choices)
            combo.setCurrentText(wanted)
            combo.blockSignals(blocked)
        if not chooses:
            # Nothing to choose from: a monster plays no effect of its own,
            # and an equip is played as one whatever it names.
            blocked = combo.blockSignals(True)
            combo.clear()
            combo.addItem(self.EFFECT_NONE)
            combo.setCurrentIndex(0)
            combo.blockSignals(blocked)
        self._show_trap_threshold()
        self._show_equip_bonus()
        if monster:
            self._refill_monster()

    def _show_trap_threshold(self):
        """Only an attack trap triggers at a threshold, and only the one its
        effect brings (model.trap_threshold_default)."""
        default = None
        if self.project is not None and self.fields["type"].currentIndex() == gamedata.TYPE_TRAP:
            default = self.project.trap_threshold_default(self._chosen_effect())
        box = self.fields["trap_threshold"]
        self.trap_caption.setVisible(default is not None)
        box.setVisible(default is not None)
        # -1 is the field left alone: the effect's own threshold stands.
        box.setSpecialValueText(f"Effect default ({default})" if default is not None else "")

    BONUS_NONE = -32768      # outside the game's range: the box left at its default

    def _show_equip_bonus(self):
        """An equip's ATK and DEF boosts, where another kind of card has its
        effect list (tabs.CardsTab.show_bonus). The box left at its lowest
        reads as the default, since the boost itself may be negative."""
        equip = self.fields["type"].currentIndex() == gamedata.TYPE_EQUIP and self.project is not None
        default = self.project.equip_bonus_default(self.current) if equip and self.current else (0, 0)
        for key, points in zip(("equip_attack", "equip_defense"), default):
            box, caption = self.fields[key], self.bonus_captions[key]
            caption.setVisible(equip)
            box.setVisible(equip)
            box.setSpecialValueText(f"Default ({points:+d})" if equip else "")

    def _load_equip_bonus(self, cid):
        """What the card holds: its own boosts, or the box at its default."""
        own = self.project.equip_bonus.get(cid)
        for key, points in zip(("equip_attack", "equip_defense"), own or (None, None)):
            self.fields[key].setValue(self.BONUS_NONE if points is None else points)

    def _store_equip_bonus(self, cid, card) -> bool:
        """The two boxes into the card's boost; whether that changed it. A
        card that is no longer an equip keeps none."""
        had = self.project.equip_bonus.get(cid)
        if card.type != gamedata.TYPE_EQUIP:
            self.project.set_equip_bonus(cid, None)
        else:
            default = self.project.equip_bonus_default(cid)
            points = [self.fields[key].value() for key in ("equip_attack", "equip_defense")]
            self.project.set_equip_bonus(cid, *(d if p == self.BONUS_NONE else p
                                                for p, d in zip(points, default)))
        return self.project.equip_bonus.get(cid) != had

    def _refill_monster(self):
        """A card applied as a non-monster lost its ATK, DEF, level and stars;
        made a monster again, it gets the disc card's (a copy's base's) back."""
        cid = self.current
        if self.project is None or cid not in self.project.cards or self.project.cards[cid].is_monster():
            return
        source = self.project.retail.cards.get(self.project.base_of(cid))
        if source is None or not source.is_monster():
            return
        self.fields["attack"].setValue(source.attack)
        self.fields["defense"].setValue(source.defense)
        self.fields["level"].setValue(source.level)
        self.fields["attribute"].setCurrentIndex(source.attribute)
        for key in ("star1", "star2"):
            self.fields[key].setCurrentIndex(getattr(source, key))

    def _store_effect(self, cid, card) -> bool:
        """The effect list into the card's "effect"; whether that changed it.
        Left out when it is what the card has anyway, or for a monster, which
        never plays one. An "effect" the form has not been touched for stays
        as written, whatever it names."""
        extra = (self.project.added[cid].extra if cid in self.project.added
                 else self.project.card_extra.get(cid, {}))
        if card.type == gamedata.TYPE_EQUIP:
            # An equip has no list: one the mod names stays (a copy of
            # Megamorph is still one), another type's goes.
            named = self.project.resolve(extra["effect"]) if "effect" in extra else None
            if not named or self._effect_kind(named) == gamedata.TYPE_EQUIP:
                return False
            del extra["effect"]
            if cid not in self.project.added and not extra:
                self.project.card_extra.pop(cid, None)
            return True
        if self.fields["effect"].currentText() == self._shown_effect and card.type == self.project.cards[cid].type:
            return False
        if card.is_monster() and self.project.cards[cid].is_monster():
            return False
        chosen = 0 if card.is_monster() else self._chosen_effect()
        default = self._effect_default(cid)
        wanted = chosen if chosen and chosen != default else None
        had = extra.get("effect")
        if wanted is None:
            if "effect" not in extra:
                return False
            del extra["effect"]
        else:
            if had is not None and self.project.resolve(had) == wanted:
                return False
            extra["effect"] = wanted
            if cid not in self.project.added:
                self.project.card_extra[cid] = extra
        if cid not in self.project.added and not extra:
            self.project.card_extra.pop(cid, None)
        return True

    # What the card was before the mod: the same fields as Card Data, in the
    # same order and two columns, set smaller and read-only under the picture.
    REFERENCE_ROWS = (("Name",), ("Type", "Attribute"), ("Level", "Frame"),
                      ("ATK", "DEF"), ("Guardian Star 1", "Guardian Star 2"),
                      ("Password", "Starchips"), ("Retail effect",), ("ATK boost", "DEF boost"),
                      ("Card text",))
    # Which field of the form each row is the disc's value for, so a row that
    # differs says so and puts its value back when it is clicked
    # (tabs.CardsTab.MARKED, retail_values, restore).
    REFERENCE_FIELDS = {"Name": "name", "Type": "type", "Attribute": "attribute", "Level": "level",
                        "Frame": "frame", "ATK": "attack", "DEF": "defense",
                        "Guardian Star 1": "star1", "Guardian Star 2": "star2",
                        "Password": "password", "Starchips": "starchips",
                        "Retail effect": "effect", "ATK boost": "equip_attack",
                        "DEF boost": "equip_defense", "Card text": "text"}
    REFERENCE_QSS = """
QLabel#referenceCaption { color: #8aa0bd; font-size: 10px; }
QLabel#referenceValue { background: #162337; border: 1px solid #2a3d55; border-radius: 5px;
  padding: 2px 6px; color: #dce6f4; font-size: 11px; }
QLabel#referenceTitle { color: #c9d8ed; font-weight: 600; }
QLabel#referenceCaption[changed="true"] { color: #8ab4f8; }
QLabel#referenceValue[changed="true"] { color: #8ab4f8; border-color: #3f6ea8; }
"""

    def _build_card_reference(self, parent):
        """The retail card under the preview: Card Data's fields, read-only."""
        panel = QWidget()
        panel.setObjectName("cardReferencePanel")
        panel.setStyleSheet(self.REFERENCE_QSS)
        column = QVBoxLayout(panel)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(5)
        self.reference_title = QLabel("Retail card")
        self.reference_title.setObjectName("referenceTitle")
        column.addWidget(self.reference_title)
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(4)
        self.reference_values = {}
        self.reference_captions = {}
        for row, names in enumerate(self.REFERENCE_ROWS):
            for col, name in enumerate(names):
                caption = QLabel(name)
                caption.setObjectName("referenceCaption")
                value = ClickableLabel("—")
                value.setObjectName("referenceValue")
                value.clicked.connect(lambda key=name: self._restore_retail_field(key))
                span = 2 if len(names) == 1 else 1
                grid.addWidget(caption, row * 2, col, 1, span)
                grid.addWidget(value, row * 2 + 1, col, 1, span)
                self.reference_values[name] = value
                self.reference_captions[name] = caption
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        column.addLayout(grid)
        # As tall as its rows and no taller: the picture above is the one
        # thing in the column that grows, up to a card of its own width, and
        # a stretch here would halve what it gets.
        panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.reference_panel = panel
        self.preview_image.parentWidget().layout().addWidget(panel)

    def _show_card_reference(self, cid, added):
        """Fill it from the disc's card, or from the base of an added one."""
        reference = self.project.retail.cards.get(cid) or self.project.cards[self.project.base_of(cid)]
        self.reference_title.setText("Base card" if added else "Retail card")
        attributes = ATTRIBUTE_NAMES + ["6 (magic)", "7 (trap)"]
        stars = guardian_stars.choices(self.project.other.get("guardian_stars"))
        star = lambda n: stars[n] if 0 <= n < len(stars) else str(n)
        shown = {
            "Name": reference.name or "—",
            "Type": TYPE_NAMES[reference.type] if 0 <= reference.type < len(TYPE_NAMES) else str(reference.type),
            "Attribute": attributes[reference.attribute] if 0 <= reference.attribute < len(attributes) else str(reference.attribute),
            "Level": str(reference.level),
            "Frame": FRAME_NAMES[reference.frame] if reference.frame >= 0 else "By card type",
            "ATK": f"{reference.attack:,}",
            "DEF": f"{reference.defense:,}",
            "Guardian Star 1": star(reference.star1),
            "Guardian Star 2": star(reference.star2),
            # The Password screen sells the disc's cards and knows no other.
            "Password": "card view only" if added else (self.project.retail.passwords.get(cid) or "none"),
            "Starchips": "not sold there" if added else f"{self.project.retail.starchips.get(cid, 0):,}",
            # What the disc's card plays as, for a card that chooses one: an
            # equip is played as an equip whatever it names.
            "Retail effect": (self._effect_label(reference.id)
                              if 0 <= self._effect_kind(reference.id) != gamedata.TYPE_EQUIP
                              and self.project.cards[cid].type != gamedata.TYPE_EQUIP else "—"),
            "Card text": " ".join(reference.description.split()) or "—",
        }
        # What an equip adds with no boost of its own (model.equip_bonus_default):
        # the disc's +500, or what a rule of the mod gives it.
        if self.project.cards[cid].type == gamedata.TYPE_EQUIP:
            for name, points in zip(("ATK boost", "DEF boost"), self.project.equip_bonus_default(cid)):
                shown[name] = f"{points:+d}"
        else:
            shown["ATK boost"] = shown["DEF boost"] = "—"
        self.reference_shown = shown
        for name, value in shown.items():
            label = self.reference_values[name]
            label.setText(QFontMetrics(label.font()).elidedText(value, Qt.TextElideMode.ElideRight,
                                                                max(60, label.width())))
            label.setToolTip(reference.description if name == "Card text" else value)
        self._mark_card_fields()

    def _marks_follow(self, *_):
        if not self._loading:
            self._mark_card_fields()

    def _form_value(self, key):
        """What the form holds for a marked field, as the panel words it."""
        if key == "text":
            return " ".join(self.description.toPlainText().split()) or "—"
        if key == "effect":
            kind = self.fields["type"].currentIndex()
            return self.fields["effect"].currentText() \
                if gamedata.TYPE_MAGIC <= kind != gamedata.TYPE_EQUIP else "—"
        if key == "password":
            if self.current in self.project.added:
                return self.reference_shown.get("Password")      # a card view only: nothing to compare
            return self.fields["password"].text().strip() or "none"
        if key == "starchips":
            if self.current not in self.project.retail.cards:
                return self.reference_shown.get("Starchips")
            return f"{self.fields['starchips'].value():,}"
        if key in ("equip_attack", "equip_defense"):
            if self.fields["type"].currentIndex() != gamedata.TYPE_EQUIP:
                return "—"
            points = self.fields[key].value()
            return self.reference_shown.get("ATK boost" if key == "equip_attack" else "DEF boost") \
                if points == self.BONUS_NONE else f"{points:+d}"
        if key in ("level", "attack", "defense"):
            value = self.fields[key].value()
            return f"{value:,}" if key != "level" else str(value)
        if key == "frame":
            index = self.fields["frame"].currentIndex() - 1
            return FRAME_NAMES[index] if index >= 0 else "By card type"
        if key in ("type", "attribute", "star1", "star2"):
            return self.fields[key].currentText()
        return self.fields["name"].text() or "—"

    def _mark_card_fields(self):
        """A row that differs from the disc says so, and is a hand to click
        (tabs.CardsTab.mark): clicking it puts that value back in the form."""
        shown = getattr(self, "reference_shown", None)
        for name, key in self.REFERENCE_FIELDS.items():
            label, caption = self.reference_values[name], self.reference_captions[name]
            differs = bool(shown) and self.current is not None and shown.get(name) != self._form_value(key)
            for part in (label, caption):
                if part.property("changed") != differs:
                    part.setProperty("changed", differs)
                    part.style().unpolish(part)
                    part.style().polish(part)
            label.setCursor(Qt.CursorShape.PointingHandCursor if differs else Qt.CursorShape.ArrowCursor)
            if differs:
                label.setToolTip(f"{shown.get(name)}\n\nClick to put the retail value back in the form.")

    def _restore_retail_field(self, name):
        """The disc's value back into the form; Apply stores it, as it stores
        anything else typed there (tabs.CardsTab.restore)."""
        key = self.REFERENCE_FIELDS.get(name)
        shown = getattr(self, "reference_shown", None)
        if key is None or not shown or self.current is None or self._loading:
            return
        if shown.get(name) == self._form_value(key):
            return
        reference = self.project.retail.cards.get(self.current) or \
            self.project.cards[self.project.base_of(self.current)]
        if key == "text":
            self.description.setPlainText(reference.description)
        elif key == "name":
            self.fields["name"].setText(reference.name)
        elif key == "effect":
            if self.fields["effect"].findText(shown[name]) >= 0:
                self.fields["effect"].setCurrentText(shown[name])
        elif key == "password":
            if self.current not in self.project.added:
                self.fields["password"].setText(self.project.retail.passwords.get(self.current) or "")
        elif key == "starchips":
            if self.current in self.project.retail.cards:
                self.fields["starchips"].setValue(self.project.retail.starchips.get(self.current, 0))
        elif key in ("equip_attack", "equip_defense"):
            self.fields[key].setValue(self.BONUS_NONE)      # the default again
        elif key == "frame":
            self.fields["frame"].setCurrentIndex(reference.frame + 1)
        elif key in ("level", "attack", "defense"):
            self.fields[key].setValue(getattr(reference, "attack" if key == "attack" else
                                              "defense" if key == "defense" else "level"))
        else:
            self.fields[key].setCurrentIndex(getattr(reference, key))
        self._mark_card_fields()
        self._render_preview()

    def _render_preview(self):
        if not self.current or self._loading: return
        if self.model_preview_button.isChecked():
            self.model_preview.show_card(self.project, self.files, self.current)
            return
        try:
            card = self.project.cards[self.current].copy()
            card.name = self.fields["name"].text()
            card.type = self.fields["type"].currentIndex()
            monster = card.type < gamedata.TYPE_MAGIC
            card.attribute = self.fields["attribute"].currentIndex()
            card.level = self.fields["level"].value()
            card.attack = self.fields["attack"].value()
            card.defense = self.fields["defense"].value()
            card.star1 = self.fields["star1"].currentIndex()
            card.star2 = self.fields["star2"].currentIndex()
            card.frame = self.fields["frame"].currentIndex() - 1
            card.description = self.description.toPlainText()
            preview_project = Project.__new__(Project)
            preview_project.__dict__ = self.project.__dict__.copy()
            preview_project.cards = self.project.cards.copy()
            preview_project.cards[self.current] = card
            scale = self.preview_scale
            pixmap = _card_image(preview_project, self.files.wa, self.current, self.frame_cache, scale)
            interpolation = (Qt.TransformationMode.SmoothTransformation if scale == 4
                             else Qt.TransformationMode.FastTransformation)
            # A card of this width is this tall, and the label is no taller:
            # it used to take the whole column, leaving a strip of nothing
            # under the card. The width comes from the panel rather than from
            # the label, so the picture cannot drive the size that drives the
            # picture; resizeEvent asks again once the panel has a width.
            panel = self.preview_image.parentWidget()
            edges = panel.layout().contentsMargins()
            room = panel.width() - edges.left() - edges.right()
            if room > 0:
                self.preview_image.setMaximumHeight(round(room * pixmap.height() / max(1, pixmap.width())))
            self.preview_image.setPixmap(pixmap.scaled(
                self.preview_image.contentsRect().size(), Qt.AspectRatioMode.KeepAspectRatio, interpolation))
            card = preview_project.cards[self.current]
            kind = TYPE_NAMES[card.type] if 0 <= card.type < len(TYPE_NAMES) else "Unknown"
            attribute = ATTRIBUTE_NAMES[card.attribute] if 0 <= card.attribute < len(ATTRIBUTE_NAMES) else ""
        except (IndexError, ValueError, OSError, art.pngio.PngError) as problem:
            self.preview_image.clear()
    def _set_preview_scale(self, scale):
        self.model_preview.hide()
        self.preview_image.show()
        (self.hd_preview_button if scale == 4 else self.disc_preview_button).setChecked(True)
        self.preview_scale = scale
        self._render_preview()
    # --- Effects: what the card does when it is played ----------------------
    #
    # The port has no key for these yet (src/pc/mods/mods.c), so they are
    # kept on the card as the editor keeps anything else it is given: a
    # mod.json entry's "effects", written back as it was read
    # (manifest.build_cards, card_extra). Nothing in the game reads them.
    EFFECT_WHEN = (("summon", "On summon",
                    "Put on the field, face up or face down (the CPU puts its monsters down face down): "
                    "played, fused, or a ritual's monster."),)
    EFFECT_DOES = (("boost", "Boost ATK/DEF"),
                   ("life", "Change life points"),
                   ("card", "A disc card's effect"))
    EFFECT_WHOSE = (("self", "This card"),
                    ("owner", "Its owner's monsters"),
                    ("opponent", "The opponent's monsters"),
                    ("opponent_lp", "The opponent"))

    def _build_card_effects(self, widget):
        controls = {name: widget(QPushButton, name + "Button")
                    for name in ("addEffect", "editEffect", "removeEffect", "effectUp", "effectDown")}
        self.effect_buttons = controls
        table = self.effects_table = widget(QTableWidget, "effectsTable")
        self.effects_note = widget(QLabel, "effectsNote")
        self.effects_note.setStyleSheet("color:#9aacc4")
        widget(QLabel, "effectsTitle").setStyleSheet("font-size:14px;font-weight:600;color:#f3f7fc")
        widget(QLabel, "effectsHint").setStyleSheet("color:#9aacc4")
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["#", "When", "Does"])
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        for column, width in ((0, 34), (1, 110)):
            table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
            table.horizontalHeader().resizeSection(column, width)
        table.itemSelectionChanged.connect(self._card_effect_buttons)
        table.cellDoubleClicked.connect(lambda *_: self._edit_card_effect())
        controls["addEffect"].clicked.connect(self._add_card_effect)
        controls["editEffect"].clicked.connect(self._edit_card_effect)
        controls["removeEffect"].clicked.connect(self._remove_card_effect)
        controls["effectUp"].clicked.connect(lambda: self._move_card_effect(-1))
        controls["effectDown"].clicked.connect(lambda: self._move_card_effect(1))

    def _card_effects(self, cid=None):
        """The card's list, as the mod wrote it."""
        cid = self.current if cid is None else cid
        if not cid or cid not in self.project.cards:
            return []
        extra = (self.project.added[cid].extra if cid in self.project.added
                 else self.project.card_extra.get(cid, {}))
        found = extra.get("effects")
        return found if isinstance(found, list) else []

    def _set_card_effects(self, effects):
        """Store the list on the card, or take the key away with the last one."""
        cid = self.current
        extra = (self.project.added[cid].extra if cid in self.project.added
                 else self.project.card_extra.setdefault(cid, {}))
        if effects:
            extra["effects"] = effects
        else:
            extra.pop("effects", None)
            if cid not in self.project.added and not extra:
                self.project.card_extra.pop(cid, None)
        self._mark_dirty()
        self._refresh_card_effects()

    def _effect_words(self, effect):
        """A line of the list: when it happens, and what it does."""
        if not isinstance(effect, dict):
            return "?", str(effect)
        when = dict((key, name) for key, name, _ in self.EFFECT_WHEN).get(effect.get("when"),
                                                                                 str(effect.get("when")))
        does = dict(self.EFFECT_DOES).get(effect.get("does"), str(effect.get("does")))
        whose = dict(self.EFFECT_WHOSE).get(effect.get("whose"), "")
        parts = [does]
        if whose:
            parts.append(whose.lower())
        only = [str(effect[key]) for key in ("only_type", "only_attribute") if effect.get(key)]
        if only:
            parts.append("(" + ", ".join(only) + " only)")
        if effect.get("does") == "boost":
            points = [f"{effect.get(key, 0):+d} {key.upper()}" for key in ("atk", "def") if effect.get(key)]
            parts.append(", ".join(points) if points else "no points")
        elif effect.get("does") == "life":
            parts.append(f"{effect.get('life', 0):+d} LP")
        elif effect.get("does") == "card":
            parts.append(self.project.card_label(effect["card"]) if isinstance(effect.get("card"), int)
                         and effect["card"] in self.project.cards else str(effect.get("card", "")))
        return when, " · ".join(part for part in parts if part)

    def _refresh_card_effects(self):
        table = self.effects_table
        effects = self._card_effects()
        table.setRowCount(len(effects))
        for row, effect in enumerate(effects):
            when, does = self._effect_words(effect)
            for column, text in enumerate((str(row + 1), when, does)):
                table.setItem(row, column, QTableWidgetItem(text))
        card = self.project.cards.get(self.current) if self.current else None
        self.effects_note.setText(
            "" if card is None or card.is_monster() else
            "Only a monster plays these; this card is no monster."
            if effects else "")
        self._card_effect_buttons()

    def _card_effect_buttons(self):
        row = self.effects_table.currentRow()
        count = self.effects_table.rowCount()
        chosen = 0 <= row < count
        for name, on in (("addEffect", bool(self.current)), ("editEffect", chosen), ("removeEffect", chosen),
                         ("effectUp", chosen and row > 0), ("effectDown", chosen and row + 1 < count)):
            self.effect_buttons[name].setEnabled(bool(on))

    def _add_card_effect(self):
        made = self._ask_card_effect({"when": "summon", "does": "boost", "whose": "self", "atk": 500, "def": 0})
        if made is not None:
            self._set_card_effects(self._card_effects() + [made])
            self.effects_table.selectRow(self.effects_table.rowCount() - 1)

    def _edit_card_effect(self):
        row = self.effects_table.currentRow()
        effects = self._card_effects()
        if not 0 <= row < len(effects) or not isinstance(effects[row], dict):
            return
        changed = self._ask_card_effect(effects[row])
        if changed is not None:
            effects = list(effects)
            effects[row] = changed
            self._set_card_effects(effects)
            self.effects_table.selectRow(row)

    def _remove_card_effect(self):
        row = self.effects_table.currentRow()
        effects = list(self._card_effects())
        if 0 <= row < len(effects):
            del effects[row]
            self._set_card_effects(effects)

    def _move_card_effect(self, delta):
        row = self.effects_table.currentRow()
        effects = list(self._card_effects())
        if 0 <= row < len(effects) and 0 <= row + delta < len(effects):
            effects[row], effects[row + delta] = effects[row + delta], effects[row]
            self._set_card_effects(effects)
            self.effects_table.selectRow(row + delta)

    def _ask_card_effect(self, effect):
        """The Edit effect form: what happens, to what, and by how much.
        Returns the effect as it was left, or None where it was cancelled."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Monster effect")
        layout = QVBoxLayout(dialog)
        form = QGridLayout()
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(7)
        layout.addLayout(form)

        def row(index, label, widget):
            form.addWidget(QLabel(label, dialog), index, 0)
            form.addWidget(widget, index, 1)
            return widget

        when = row(0, "When", short_popup(QComboBox(dialog)))
        for key, name, _ in self.EFFECT_WHEN:
            when.addItem(name, key)
        when.setCurrentIndex(max(0, when.findData(effect.get("when"))))
        said = QLabel(self.EFFECT_WHEN[0][2], dialog)
        said.setWordWrap(True)
        said.setStyleSheet("color:#9aacc4")
        form.addWidget(said, 1, 0, 1, 2)

        does = row(2, "Does", short_popup(QComboBox(dialog)))
        for key, name in self.EFFECT_DOES:
            does.addItem(name, key)
        does.setCurrentIndex(max(0, does.findData(effect.get("does"))))
        whose = row(3, "Whose", short_popup(QComboBox(dialog)))
        for key, name in self.EFFECT_WHOSE:
            whose.addItem(name, key)
        whose.setCurrentIndex(max(0, whose.findData(effect.get("whose"))))
        only_type = row(4, "Only type", short_popup(QComboBox(dialog)))
        only_type.addItem("Any", "")
        for name in TYPE_NAMES[:gamedata.TYPE_MAGIC]:
            only_type.addItem(name, name)
        only_type.setCurrentIndex(max(0, only_type.findData(effect.get("only_type", ""))))
        only_attribute = row(5, "Only attribute", short_popup(QComboBox(dialog)))
        only_attribute.addItem("Any", "")
        for name in ATTRIBUTE_NAMES:
            only_attribute.addItem(name, name)
        only_attribute.setCurrentIndex(max(0, only_attribute.findData(effect.get("only_attribute", ""))))
        points = {}
        for index, key in enumerate(("atk", "def")):
            box = row(6 + index, key.upper(), QSpinBox(dialog))
            box.setRange(-9999, 9999)
            box.setSingleStep(100)
            box.setValue(effect.get(key, 0) if isinstance(effect.get(key), int) else 0)
            points[key] = box
        life = row(8, "Life points", QSpinBox(dialog))
        life.setRange(-9999, 9999)
        life.setSingleStep(100)
        life.setValue(effect.get("life", -500) if isinstance(effect.get("life"), int) else -500)
        card = row(9, "Its effect", self._card_combo(dialog, effect.get("card") if effect.get("card") in
                                                     self.project.cards else None))

        def follows():
            """Only the fields the chosen kind of effect uses."""
            kind = does.currentData()
            for index, widget in ((6, points["atk"]), (7, points["def"])):
                widget.setVisible(kind == "boost")
                form.itemAtPosition(index, 0).widget().setVisible(kind == "boost")
            life.setVisible(kind == "life")
            form.itemAtPosition(8, 0).widget().setVisible(kind == "life")
            card.setVisible(kind == "card")
            form.itemAtPosition(9, 0).widget().setVisible(kind == "card")
            for widget in (only_type, only_attribute):
                widget.setEnabled(whose.currentData() != "opponent_lp")

        does.currentIndexChanged.connect(lambda *_: follows())
        whose.currentIndexChanged.connect(lambda *_: follows())
        follows()
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
                                   parent=dialog)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        made = {"when": when.currentData(), "does": does.currentData(), "whose": whose.currentData()}
        for key, box in (("only_type", only_type), ("only_attribute", only_attribute)):
            if box.isEnabled() and box.currentData():
                made[key] = box.currentData()
        if made["does"] == "boost":
            made["atk"], made["def"] = points["atk"].value(), points["def"].value()
        elif made["does"] == "life":
            made["life"] = life.value()
        elif made["does"] == "card" and card.currentData():
            made["card"] = card.currentData()
        # Anything the mod wrote that this form has no field for stays.
        kept = {k: v for k, v in effect.items()
                if k not in ("when", "does", "whose", "only_type", "only_attribute", "atk", "def", "life", "card")}
        made.update(kept)
        return made

    # The game's seven colour ramps, as the card view draws them
    # (card_text.RetailFont.colours_for, notes/modding.md).
    TEXT_COLOURS = ("White", "Yellow", "Blue", "Green", "Grey", "Orange", "Red")

    def _retail_font(self):
        """The disc's font, kept between draws: reading it is milliseconds,
        and the preview follows every letter typed."""
        held = getattr(self, "_text_font", None)
        if held is None or held[0] is not self.files.wa:
            held = (self.files.wa, card_text.RetailFont(self.files.wa))
            self._text_font = held
        return held[1]

    def _description_star(self, model, star):
        """The name and 16-pixel symbol the card viewer would use for a star."""
        if not star:
            return None
        entry = model.stars.get(star)
        image = None
        if entry and entry.icon:
            try:
                if entry.icon in self.project.files:
                    image = pngio.decode(self.project.files[entry.icon])
                elif self.project.source_dir:
                    image = pngio.read(Path(self.project.source_dir) / entry.icon)
            except (OSError, ValueError, pngio.PngError):
                image = None
        if image is None:
            try:
                found = guardian_stars.disc_icon(self.files.wa, star)
                if found is None:
                    found = guardian_stars.imported_icon(self.files.wa, star)
                if found is not None:
                    image = pngio.Image(*found)
            except (IndexError, ValueError, struct.error):
                image = None
        if image is not None and image.size != (16, 16):
            image = pngio.resample(image, 16, 16)
        return model.name(star), image

    def _render_card_text(self):
        """The complete description half of the in-game card viewer."""
        label = getattr(self, "card_text_preview", None)
        if label is None or self.files is None or not self.current:
            return
        try:
            font = self._retail_font()
            kind = self.type_box.currentIndex()
            type_name = TYPE_NAMES[kind] if 0 <= kind < len(TYPE_NAMES) else "Unknown"
            # The four non-monster symbols follow the twenty monster-type
            # symbols in the same text-icon page.
            type_icon = kind if kind < gamedata.TYPE_MAGIC else 0x14 + kind - gamedata.TYPE_MAGIC
            stars = ()
            if kind < gamedata.TYPE_MAGIC:
                model = guardian_stars.read(self.project.other.get("guardian_stars"))
                selected = (self.star1_box.currentIndex(), self.star2_box.currentIndex())
                stars = tuple(star for star in (self._description_star(model, item) for item in selected) if star)
            # Imported modified discs carry their active archive separately
            # from the retail files.  The description panel's UI tiles must
            # therefore come from preview_wa, just like its modified card
            # artwork, rather than from the editor's original game archive.
            # The description side is a Build Deck UI sprite.  Look up its
            # two CLUT readings independently so an HD/mod texture pack can
            # replace the stone and navy material just as the game does.
            stone = _pack_texture(self.project, self.frame_cache,
                                  0x10E4800, 64, 128, 4, 0x10E9600, 16)
            navy = _pack_texture(self.project, self.frame_cache,
                                 0x10E4800, 64, 128, 4, 0x10E9620, 16)
            image = card_text.render_description(
                font, self.description.toPlainText(), type_name, type_icon, stars, 2,
                wa=getattr(self, "preview_wa", self.files.wa),
                stone_sheet=stone, navy_sheet=navy)
            label.setText("")
            label.setPixmap(QPixmap.fromImage(_qimage(image.width, image.height, image.rgba)))
        except (OSError, ValueError, IndexError, KeyError, struct.error, pngio.PngError) as problem:
            label.setPixmap(QPixmap())
            label.setText(str(problem))

    def _colour_swatch(self, code):
        """The brightest step of a ramp, for the menu's entry."""
        picture = QPixmap(12, 12)
        try:
            picture.fill(QColor(*self._retail_font().colours_for(code)[-1]))
        except (OSError, ValueError, IndexError, struct.error):
            return QIcon()
        return QIcon(picture)

    # The icons the disc draws in a card's text ({f8 0B NN}): its page is an
    # eight-column grid (column = code & 7, row = (code & 0x38) >> 3), and the
    # rows are the twenty monster types, the four card kinds, then the ten
    # guardian stars. 0x22 up is the rest of the boot sheet's UI sprites,
    # which are documented as far as 0x28.
    TEXT_ICONS = (("Monster types", 0x00, gamedata.TYPE_MAGIC),
                  ("Card kinds", 0x14, 4),
                  ("Guardian stars", 0x18, 10),
                  ("Buttons", 0x22, 7))

    def _icon_name(self, title, code):
        """What the icon is: the type or kind it marks, the star it is, or its
        code where the sheet holds a sprite with no name of its own."""
        if title == "Monster types" and code < len(TYPE_NAMES):
            return TYPE_NAMES[code]
        if title == "Card kinds" and gamedata.TYPE_MAGIC + code - 0x14 < len(TYPE_NAMES):
            return TYPE_NAMES[gamedata.TYPE_MAGIC + code - 0x14]
        if title == "Guardian stars":
            stars = guardian_stars.choices(self.project.other.get("guardian_stars")) if self.project else []
            star = code - 0x18 + 1              # 0x18 is Mars, the first
            if star < len(stars):
                return stars[star]
        return f"{code:02X}"

    def _text_icon(self, code):
        """A text icon as it is drawn, for the menu's entry."""
        held = getattr(self, "_text_icons", None)
        if held is None:
            held = self._text_icons = {}
        if code not in held:
            try:
                texels = self._retail_font().icon(code)
            except (OSError, ValueError, IndexError, struct.error):
                return QIcon()
            picture = QImage(16, 16, QImage.Format.Format_RGBA8888)
            picture.fill(0)
            for y in range(16):
                for x in range(16):
                    (r, g, b), a = texels[y * 16 + x]
                    if a:
                        picture.setPixelColor(x, y, QColor(r, g, b))
            held[code] = QIcon(QPixmap.fromImage(picture))
        return held[code]

    def _insert_text_code(self, code, around=None):
        """A code at the cursor; with `around`, the code before what is
        selected and `around` after it, so only that much is coloured."""
        cursor = self.description.textCursor()
        if around is None or not cursor.hasSelection():
            cursor.insertText(code)
            return
        cursor.insertText(code + cursor.selectedText().replace("\u2029", "\n") + around)
        self.description.setTextCursor(cursor)

    def _card_text_menu(self, point):
        self._build_card_text_menu().exec(self.description.viewport().mapToGlobal(point))

    def _build_card_text_menu(self):
        """The box's own menu, and the codes the game reads in a card's text.
        Built apart from showing it: a menu's exec is a modal loop of its own,
        which nothing but a person can leave."""
        menu = self.description.createStandardContextMenu()
        menu.addSeparator()
        selected = self.description.textCursor().hasSelection()
        colours = menu.addMenu("Colour the selection" if selected else "Text colour")
        for code, name in enumerate(self.TEXT_COLOURS):
            action = colours.addAction(f"{name}   {{f8 0A {code:02X}}}")
            action.setIcon(self._colour_swatch(code))
            # White is the text's own colour, so it is what a colour ends with.
            action.triggered.connect(lambda _=False, c=code:
                                     self._insert_text_code(f"{{f8 0A {c:02X}}}", "{f8 0A 00}"))
        icons = menu.addMenu("Insert icon")
        for title, first, count in self.TEXT_ICONS:
            group = icons.addMenu(title)
            for code in range(first, first + count):
                action = group.addAction(f"{self._icon_name(title, code)}   {{f8 0B {code:02X}}}")
                action.setIcon(self._text_icon(code))
                action.triggered.connect(lambda _=False, c=code: self._insert_text_code(f"{{f8 0B {c:02X}}}"))
        return menu

    def update_text_count(self):
        count = _line_count(self.description.toPlainText())
        self.description_status.setText(f"{count} of 8 game lines · 20 characters per line")
        self.description_status.setStyleSheet("color:#ff7777" if count > 8 else "color:#9aacc4")
        self._render_card_text()
        if self.current: self._render_preview()
    def apply_card(self, quiet=False):
        cid = self.current
        if not cid: return True
        card = self.project.cards[cid].copy()
        card.name = self.fields["name"].text()
        card.type = self.fields["type"].currentIndex()
        monster = card.type < gamedata.TYPE_MAGIC
        card.attribute = self.fields["attribute"].currentIndex()
        card.level = self.fields["level"].value()
        card.attack = self.fields["attack"].value()
        card.defense = self.fields["defense"].value()
        card.star1 = self.fields["star1"].currentIndex()
        card.star2 = self.fields["star2"].currentIndex()
        card.frame = self.fields["frame"].currentIndex() - 1
        card.description = self.description.toPlainText()
        if not monster:
            # As the disc's: no ATK, DEF, level or stars, and the magic or
            # trap attribute (tabs.CardsTab.read_form).
            card.attack = card.defense = card.level = card.star1 = card.star2 = 0
            card.attribute = 7 if card.type == gamedata.TYPE_TRAP else 6
        password = self.fields["password"].text().strip()
        if password and not (password.isascii() and password.isdigit() and len(password) <= 8):
            self.validation.setText("Password must be up to 8 digits, or blank.")
            return False
        password = password.zfill(8) if password else ""
        changed = not card.same(self.project.cards[cid])
        added = self.project.added.get(cid)
        if added:
            key = self.key_edit.text().strip()
            if not KEY_RE.fullmatch(key) or any(x.key == key and n != cid for n, x in self.project.added.items()):
                self.validation.setText("The stable key must use letters, digits, _ or - and be unique.")
                return False
            if key != added.key:
                # Its shop rule is keyed by the identity the key spells, so
                # the rename carries the rule with it (model.set_card_key).
                self.project.set_card_key(cid, key); changed = True
            if (added.drops, added.opponents) != (self.drops.isChecked(), self.opponents.isChecked()):
                added.drops = self.drops.isChecked(); added.opponents = self.opponents.isChecked()
                changed = True
        if password != self.project.password(cid):
            self.project.set_password(cid, password); changed = True
        if cid in self.project.retail.cards:
            starchips = self.fields["starchips"].value()
            if starchips != self.project.starchip_cost(cid):
                self.project.set_starchips(cid, starchips); changed = True
        if self._store_effect(cid, card): changed = True
        # After the effect, which the default follows (tabs.CardsTab.apply).
        if self._store_equip_bonus(cid, card): changed = True
        # Only an attack trap has a threshold; a card that stops being one
        # drops the override it kept, but only once its type or effect moved.
        threshold = self.fields["trap_threshold"].value()
        active = card.type == gamedata.TYPE_TRAP and \
            self.project.trap_threshold_default(self._chosen_effect()) is not None
        if active and threshold != self._shown_threshold:
            self.project.set_trap_threshold(cid, None if threshold < 0 else threshold)
            self._shown_threshold = threshold; changed = True
        elif (not active and self.project.trap_threshold_override(cid) is not None
              and (card.type != self.project.cards[cid].type
                   or self.fields["effect"].currentText() != self._shown_effect)):
            self.project.set_trap_threshold(cid, None)
            self.fields["trap_threshold"].setValue(-1)
            self._shown_threshold = -1; changed = True
        self._shown_effect = self.fields["effect"].currentText()
        self._load_equip_bonus(cid)
        self._show_equip_bonus()
        if changed:
            self.project.cards[cid] = card
            problems = validate.validate_card(self.project, cid)
            self.statusBar().showMessage(f"Updated {self.project.card_label(cid)}")
            self._mark_dirty()
        else:
            problems = [] if quiet else validate.validate_card(self.project, cid)
        self.validation.setText("\n".join(i.message for i in problems))
        if changed:
            self.refresh_cards(select_id=cid)
            self.refresh_art_list(select_id=self.current_art_card)
            self._render_preview()
        return True
    def revert_card(self):
        cid = self.current
        if not cid: return
        self.project.revert_card(cid)
        self.show_card(cid)
        self.refresh_cards(select_id=cid)
        self.refresh_art_list(select_id=self.current_art_card)
        self.statusBar().showMessage("Restored retail card data")
        self._mark_dirty()
    def add_card(self):
        selected = self.current or self._choose_one_card("Base of the new card", sorted(self.project.retail.cards))
        if not selected or not self.apply_card(quiet=True): return
        source = self.project.cards[selected]
        base = self.project.base_of(selected)
        cid = self.project.add_card(base)
        self.project.cards[cid] = source.copy(id=cid, name=source.name + " II")
        self._mark_dirty()
        self.statusBar().showMessage(f"Added a copy: {self.project.card_label(cid)}")
        self.advanced_card_filters = {"types": set(), "attributes": set(), "bounds": {}}
        self.filter.setCurrentText("All cards")
        self.search.clear()
        self.refresh_cards(select_id=cid)
        self.refresh_art_list(select_id=cid)
    def remove_card(self):
        cid = self.current
        if cid not in self.project.added: return
        answer = QMessageBox.question(self, "Remove copy", "Remove this added card and rules that reference it?")
        if answer != QMessageBox.StandardButton.Yes: return
        self.project.remove_card(cid)
        self._mark_dirty()
        self.current = None
        self.refresh_cards(select_id=1)
        self.current_art_card = 1
        self.refresh_art_list(select_id=1)
