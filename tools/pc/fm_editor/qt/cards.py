"""The Cards page."""
from __future__ import annotations

from .common import *      # noqa: F401,F403
from .common import (_qimage, _line_count, _pairs_text, _parse_pairs, _whole,
                     _card_image)      # noqa: F401


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
        self.notes = widget(QTextEdit, "notesEdit")
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
        }
        # Password and Starchips share Card Data's two columns, so the right
        # one starts where Attribute, Frame, DEF and Guardian Star 2 do. Their
        # grid is its own, and without this the password field takes the width
        # it likes and pushes Starchips out of line.
        password_grid = page.findChild(QGridLayout, "passwordGrid")
        for column in (0, 1):
            password_grid.setColumnStretch(column, 1)
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
        for box in (self.type_box, self.attribute_box, self.star1_box, self.star2_box, self.frame_box):
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
        for field in (self.attribute_box, self.star1_box, self.star2_box, self.frame_box):
            field.currentIndexChanged.connect(self._render_preview)
        for field in (self.level_box, self.attack_box, self.defense_box):
            field.valueChanged.connect(self._render_preview)
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
        self._set_monster_fields_enabled(True)
        self.fields["frame"].setCurrentIndex(card.frame + 1)
        self.fields["password"].setText(self.project.password(cid))
        # The Password screen sells the disc's cards and knows nothing of an
        # added one, so there is no price to put on it.
        sold = cid in self.project.retail.cards
        self.fields["starchips"].setValue((self.project.starchip_cost(cid) or 0) if sold else 0)
        self.fields["starchips"].setEnabled(sold)
        self.fields["starchips"].setSpecialValueText("free" if sold else "not sold there")
        self.description.setPlainText(card.description)
        self.notes.setPlainText(self.project.notes.get(cid, ""))
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
        self.extra_info.setText("Kept as written in mod.json: " + ", ".join(sorted(extra)) if extra else "")
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
            self._render_preview()

    # What the card was before the mod: the same fields as Card Data, in the
    # same order and two columns, set smaller and read-only under the picture.
    REFERENCE_ROWS = (("Name",), ("Type", "Attribute"), ("Level", "Frame"),
                      ("ATK", "DEF"), ("Guardian Star 1", "Guardian Star 2"),
                      ("Password", "Starchips"))
    REFERENCE_QSS = """
QLabel#referenceCaption { color: #8aa0bd; font-size: 10px; }
QLabel#referenceValue { background: #162337; border: 1px solid #2a3d55; border-radius: 5px;
  padding: 2px 6px; color: #dce6f4; font-size: 11px; }
QLabel#referenceTitle { color: #c9d8ed; font-weight: 600; }
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
        for row, names in enumerate(self.REFERENCE_ROWS):
            for col, name in enumerate(names):
                caption = QLabel(name)
                caption.setObjectName("referenceCaption")
                value = QLabel("—")
                value.setObjectName("referenceValue")
                value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                span = 2 if len(names) == 1 else 1
                grid.addWidget(caption, row * 2, col, 1, span)
                grid.addWidget(value, row * 2 + 1, col, 1, span)
                self.reference_values[name] = value
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
        }
        for name, value in shown.items():
            self.reference_values[name].setText(value)
            self.reference_values[name].setToolTip(value)

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
    def update_text_count(self):
        count = _line_count(self.description.toPlainText())
        self.description_status.setText(f"{count} of 8 game lines · 20 characters per line")
        self.description_status.setStyleSheet("color:#ff7777" if count > 8 else "color:#9aacc4")
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
            if key != added.key or added.drops != self.drops.isChecked() or added.opponents != self.opponents.isChecked():
                added.key = key; added.drops = self.drops.isChecked(); added.opponents = self.opponents.isChecked()
                changed = True
        notes = self.notes.toPlainText()
        if notes != self.project.notes.get(cid, ""):
            self.project.set_notes(cid, notes); changed = True
        if password != self.project.password(cid):
            self.project.set_password(cid, password); changed = True
        if cid in self.project.retail.cards:
            starchips = self.fields["starchips"].value()
            if starchips != self.project.starchip_cost(cid):
                self.project.set_starchips(cid, starchips); changed = True
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
