"""Full one-to-five-tribute Rituals editor for the PySide frontend.

The classic editor remains untouched.  This module replaces only its Qt page
and supplies the later ritual model/schema helpers at runtime.
"""
from __future__ import annotations

from copy import deepcopy

from PySide6.QtCore import QEvent, QObject


_ORIGIN_TEXT = {
    "field": "Monsters on the player's side of the field are used as tributes.",
    "hand": "Monster cards in the player's hand are used as tributes.",
    "both": "Monsters from the field or hand can be used as tributes.",
}
_CONDITIONS = (
    ("Monster type", "type", None), ("Fusion group", "fusion_group", None),
    ("ATK at least", "min_attack", (0, 9999, 1000)),
    ("ATK at most", "max_attack", (0, 9999, 9999)),
    ("DEF at least", "min_defense", (0, 9999, 1000)),
    ("DEF at most", "max_defense", (0, 9999, 9999)),
    ("Level at least", "min_level", (0, 12, 1)),
    ("Level at most", "max_level", (0, 12, 12)),
    ("DEF above ATK", "defense_gt_attack", None),
    ("Is this card (or a copy)", "card", None),
)
_CONDITION_LABEL = {key: label for label, key, _number in _CONDITIONS}


def install() -> None:
    """Install the modern Rituals page without touching the classic editor."""
    from .common import (
        ATTRIBUTE_NAMES, FUSION_GROUPS, TYPE_NAMES, QFile, QIODevice, QUiLoader,
        QAbstractItemView, QCheckBox, QComboBox, QHeaderView, QHBoxLayout, QLabel, QLineEdit, QPixmap,
        QPushButton, QRadioButton, QSpinBox, QStackedWidget, QTableWidget, QTableWidgetItem,
        QToolButton, QVBoxLayout, Qt, UI_DIR, QWidget, _card_image,
        decorate_type_items,
    )
    from .rituals import RitualsMixin
    from .window import ModernEditor
    from .. import manifest

    if getattr(ModernEditor, "_full_rituals_compat_installed", False):
        return
    ModernEditor._full_rituals_compat_installed = True

    # ``origin/master`` still serializes exactly three tributes and reads the
    # summoned monster at tuple index 3.  The game framework's ritual schema
    # accepts one through five, so preserve that newer schema in Qt only.
    def build_rituals(project):
        entries = []
        retail = project.retail.rituals
        for ritual in sorted(set(retail) | set(project.rituals)):
            now = project.rituals.get(ritual)
            changed = (retail.get(ritual) != now or ritual in project.ritual_requirements
                       or ritual in project.ritual_from)
            if not changed:
                continue
            if now is None:
                entries.append({"card": project.ref(ritual), "result": None})
                continue
            entry = {"card": project.ref(ritual), "result": project.ref(now[-1])}
            if ritual in project.ritual_from:
                entry["tributes_from"] = project.ritual_from[ritual]
            requirements = project.ritual_requirements.get(ritual)
            if requirements:
                tributes = []
                for requirement in requirements:
                    body = dict(requirement)
                    if body.get("card"):
                        body["card"] = project.ref(body["card"])
                    else:
                        body.pop("card", None)
                    tributes.append(body)
                entry["tributes"] = tributes
            else:
                entry["tributes"] = [project.ref(card) for card in now[:-1]]
            entries.append(entry)
        return entries + project.kept["rituals"]

    original_read_rituals = manifest.read_rituals
    def read_rituals(project, entries, messages):
        """Read newer variable-length rules, then defer legacy rules intact."""
        if not isinstance(entries, list):
            return original_read_rituals(project, entries, messages)
        legacy, modern = [], []
        for entry in entries:
            if isinstance(entry, dict) and isinstance(entry.get("tributes"), list) and (
                    len(entry["tributes"]) != 3 or "tributes_from" in entry):
                modern.append(entry)
            else:
                legacy.append(entry)
        original_read_rituals(project, legacy, messages)
        for index, entry in enumerate(modern):
            ritual = project.resolve(entry.get("card"))
            where = f"rituals[{index}]"
            tributes = entry.get("tributes")
            result = project.resolve(entry.get("result"))
            origin = entry.get("tributes_from", "field")
            if not ritual or not project.is_ritual(ritual) or not result or not isinstance(tributes, list) or not 1 <= len(tributes) <= 5 or origin not in ("field", "hand", "both"):
                messages.append(f"{where}: invalid one-to-five tribute ritual; kept as written")
                project.kept["rituals"].append(entry)
                continue
            requirements = []
            valid = True
            for tribute in tributes:
                if isinstance(tribute, dict):
                    row = dict(tribute)
                    if row.get("card"):
                        row["card"] = project.resolve(row["card"])
                    if not row or row.get("card") == 0:
                        valid = False
                    requirements.append(row)
                else:
                    card = project.resolve(tribute)
                    valid &= bool(card)
                    requirements.append({"card": card} if card else {})
            if not valid:
                messages.append(f"{where}: names a card the editor cannot place; kept as written")
                project.kept["rituals"].append(entry)
                continue
            project.set_ritual(ritual, requirements, result, origin)

    manifest.build_rituals = build_rituals
    manifest.read_rituals = read_rituals

    def widget(page, cls, name):
        found = page.findChild(cls, name)
        if found is None:
            raise RuntimeError(f"Rituals form is missing {name!r}")
        return found

    class _TributeSlotClickFilter(QObject):
        """Turn an entire tribute card slot into its selection target."""
        def __init__(self, callback, parent):
            super().__init__(parent)
            self.callback = callback

        def eventFilter(self, watched, event):
            if event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
                self.callback()
                return True
            return False

    def build_page(self, name, parent):
        if name != "Rituals":
            return original_build_page(self, name, parent)
        source = QFile(str(UI_DIR / "rituals_page.ui"))
        if not source.open(QIODevice.OpenModeFlag.ReadOnly):
            raise RuntimeError(f"Could not open Rituals form: {source.errorString()}")
        page = QUiLoader().load(source, parent)
        source.close()
        if page is None:
            raise RuntimeError("Could not load Rituals form")
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(page)
        self.workspace_forms[name] = page
        controls = {"page": page, "cards": widget(page, QTableWidget, "ritualTable"),
                    "search": widget(page, QLineEdit, "ritualSearchEdit"),
                    "source_filter": widget(page, QComboBox, "ritualSourceFilter"),
                    "state_filter": widget(page, QComboBox, "ritualStateFilter"),
                    "result": widget(page, QComboBox, "ritualResultCardCombo"),
                    "specific": widget(page, QComboBox, "specificTributeCardCombo"),
                    "condition_card": widget(page, QComboBox, "conditionCardCombo"),
                    "conditions": widget(page, QTableWidget, "conditionsTable"),
                    "condition_type": widget(page, QComboBox, "conditionTypeCombo"),
                    "condition_group": widget(page, QComboBox, "conditionFusionGroupCombo"),
                    "condition_number": widget(page, QSpinBox, "conditionNumberSpin"),
                    "condition_stack": widget(page, QStackedWidget, "conditionEditorStack"),
                    "count": widget(page, QLabel, "ritualCountLabel"),
                    "slots": [widget(page, QLabel, f"tributeSlot{i}Preview") for i in range(1, 6)],
                    "slot_summaries": [widget(page, QLabel, f"tributeSlot{i}Summary") for i in range(1, 6)],
                    "slot_frames": [widget(page, QWidget, f"tributeSlot{i}") for i in range(1, 6)],
                    "slot_buttons": [widget(page, QPushButton, f"selectTribute{i}Button") if i <= 3
                                     else widget(page, QPushButton, f"addTribute{i}Button") for i in range(1, 6)]}
        self.workspace_controls[name] = controls
        # The preview must never be larger than the layout has reserved for
        # it.  Otherwise its pixels can run into the result name below.
        result_preview = widget(page, QLabel, "ritualResultPreview")
        result_preview.setFixedSize(result_preview.minimumSize())
        result_name = widget(page, QLabel, "ritualResultNameLabel")
        result_name.setWordWrap(True)
        result_name.setMinimumHeight(28)
        self.ritual_current = None
        # Retain the old public staging map for extensions that used it.  The
        # full page normally edits ``_ritual_drafts`` instead.
        self.ritual_pending = {}
        self._ritual_drafts = {}
        self._ritual_selected_tribute = 0
        self._ritual_selected_condition = None
        cards = controls["cards"]
        cards.setColumnCount(4)
        cards.setHorizontalHeaderLabels(["ID", "Ritual card", "Tributes", "State"])
        cards.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        cards.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        header = cards.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        for column, width in ((0, 54), (1, 190), (2, 80), (3, 92)):
            cards.setColumnWidth(column, width)
        # A condition may have a long label (for example “Is this card (or a
        # copy)”).  Fixed columns and single-line rows prevent the first row
        # from being cut in half when the editor is at its normal height.
        conditions = controls["conditions"]
        conditions.setWordWrap(False)
        conditions.verticalHeader().setDefaultSectionSize(30)
        conditions.verticalHeader().setMinimumSectionSize(30)
        condition_header = conditions.horizontalHeader()
        condition_header.setStretchLastSection(False)
        for column, width in ((0, 210), (1, 82), (3, 42)):
            conditions.setColumnWidth(column, width)
            condition_header.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
        # The direct value control fills the condition row, matching the
        # reference editor rather than using a separate inspector below.
        condition_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        conditions.setMinimumHeight(250)
        for combo in (controls["result"], controls["specific"], controls["condition_card"]):
            combo.setEditable(True)
            combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
            combo.setMaxVisibleItems(18)
        controls["condition_type"].addItems(TYPE_NAMES[:20])
        controls["condition_group"].addItems(FUSION_GROUPS)
        decorate_type_items(self, controls["condition_type"])
        self._ritual_refill_cards()
        cards.itemSelectionChanged.connect(self._select_ritual)
        controls["search"].textChanged.connect(self._filter_ritual_cards)
        controls["source_filter"].currentIndexChanged.connect(lambda *_: self._filter_ritual_cards())
        controls["state_filter"].currentIndexChanged.connect(lambda *_: self._filter_ritual_cards())
        controls["result"].currentIndexChanged.connect(self._ritual_result_changed)
        controls["specific"].currentIndexChanged.connect(self._ritual_specific_changed)
        # Match the reference card-strip proportions: cards are the primary
        # interaction target, with enough room for their captions below.
        for frame, preview, summary in zip(controls["slot_frames"], controls["slots"], controls["slot_summaries"]):
            frame.setMinimumWidth(112)
            preview.setFixedSize(100, 115)
            summary.setMinimumHeight(34)
            summary.setMaximumHeight(42)
        # The recipe overview uses clickable card slots.  The selected card
        # is identified by its border, not a redundant Edit/Editing button.
        controls["slot_click_filters"] = []
        for index, button in enumerate(controls["slot_buttons"]):
            button.hide()
            selector = _TributeSlotClickFilter(
                lambda n=index: self._select_or_add_tribute(n), page)
            controls["slot_click_filters"].append(selector)
            for target in (controls["slot_frames"][index], controls["slots"][index], controls["slot_summaries"][index]):
                target.installEventFilter(selector)
                target.setCursor(Qt.CursorShape.PointingHandCursor)
        # Condition choices now live in a dedicated picker dialog.
        widget(page, QComboBox, "addConditionCombo").hide()
        controls["condition_stack"].hide()
        controls["conditions"].horizontalHeader().hide()
        controls["conditions"].setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        for name_, callback in (
            ("previousTributeButton", lambda: self._select_or_add_tribute(self._ritual_selected_tribute - 1)),
            ("nextTributeButton", lambda: self._select_or_add_tribute(self._ritual_selected_tribute + 1)),
            ("removeSelectedTributeButton", self._remove_selected_tribute),
            ("addConditionButton", self._add_ritual_condition),
            ("clearConditionsButton", self._clear_ritual_conditions),
            ("applyRitualButton", self._apply_ritual_selector_recipe),
            ("giveOwnRecipeButton", self._give_own_ritual_recipe),
            ("removeRecipeButton", self._remove_ritual),
            ("revertRitualButton", self._revert_ritual),
            ("addRitualButton", self._add_ritual_recipe),
            ("duplicateRitualButton", self._duplicate_ritual_recipe),
            ("deleteRitualButton", self._remove_ritual),
            ("changeRitualResultButton", self._choose_ritual_result),
            ("chooseSpecificTributeCardButton", self._choose_specific_tribute),
            ("chooseConditionCardButton", self._choose_condition_card),
            ("openRitualCardButton", self._open_ritual_card),
        ):
            widget(page, QPushButton, name_).clicked.connect(callback)
        widget(page, QRadioButton, "specificCardModeRadio").clicked.connect(
            lambda: self._ritual_set_mode("specific"))
        widget(page, QRadioButton, "ruleBasedModeRadio").clicked.connect(
            lambda: self._ritual_set_mode("rule"))
        for origin, name_ in (("field", "originFieldRadio"), ("hand", "originHandRadio"), ("both", "originBothRadio")):
            widget(page, QRadioButton, name_).toggled.connect(
                lambda checked, value=origin: checked and self._ritual_origin_changed(value))
        controls["conditions"].itemSelectionChanged.connect(self._select_ritual_condition)
        controls["condition_type"].currentTextChanged.connect(lambda value: self._set_condition_value(value))
        controls["condition_group"].currentTextChanged.connect(lambda value: self._set_condition_value(value))
        controls["condition_number"].valueChanged.connect(lambda value: self._set_condition_value(value))
        widget(page, QCheckBox, "conditionDefenseAboveAttackCheck").toggled.connect(
            lambda value: self._set_condition_value(bool(value)))
        self._refresh_rituals()

    def _ritual_refill_cards(self):
        controls = self.workspace_controls.get("Rituals")
        if not controls:
            return
        choices = [(cid, self.project.card_label(cid)) for cid in self.project.monsters()]
        if controls.get("card_choices") == choices:
            return
        controls["card_choices"] = choices
        for combo in (controls["result"], controls["specific"], controls["condition_card"]):
            chosen = combo.currentData()
            combo.blockSignals(True)
            combo.clear(); combo.addItem("Choose a monster…", None)
            for cid, label in choices:
                combo.addItem(label, cid)
            at = combo.findData(chosen)
            combo.setCurrentIndex(at if at >= 0 else 0)
            combo.blockSignals(False)

    def _ritual_recipe(self, ritual):
        """Return a modifiable effective recipe and whether it belongs to this card."""
        found = self.project.ritual_recipe(ritual)
        if found is None:
            return None
        tributes, result, origin = found
        direct = ritual in self.project.rituals
        return [dict(row) for row in tributes], result, origin, direct

    def _ritual_draft(self, ritual, create=False):
        draft = self._ritual_drafts.get(ritual)
        if draft is not None:
            return draft
        found = self._ritual_recipe(ritual)
        if found is None:
            if not create:
                return None
            monsters = self.project.monsters()
            result = monsters[0] if monsters else 0
            draft = {"tributes": [{"min_attack": 0} for _ in range(3)], "result": result,
                     "origin": "field", "own": True}
        else:
            tributes, result, origin, own = found
            draft = {"tributes": tributes, "result": result, "origin": origin, "own": own}
        self._ritual_drafts[ritual] = draft
        return draft

    def _ritual_state(self, ritual):
        if ritual not in self.project.rituals and ritual in self.project.added:
            return "uses base recipe" if self._ritual_recipe(ritual) else "no recipe"
        state = self.project.ritual_status(ritual)
        if ritual in getattr(self.project, "ritual_from", {}):
            state = state or "changed"
        return state or "stock"

    def _ritual_draft_changed(self, ritual, draft):
        found = self._ritual_recipe(ritual)
        if found is None:
            return True
        tributes, result, origin, _own = found
        return (draft["tributes"] != tributes or draft["result"] != result
                or draft["origin"] != origin)

    def _refresh_rituals(self):
        controls = self.workspace_controls.get("Rituals")
        if not controls:
            return
        self._ritual_refill_cards()
        table = controls["cards"]
        previous = getattr(self, "ritual_current", None)
        table.blockSignals(True); table.setRowCount(0)
        for ritual in self.project.ritual_cards():
            found = self._ritual_recipe(ritual)
            row = table.rowCount(); table.insertRow(row)
            ident = QTableWidgetItem(f"{ritual:03d}")
            ident.setData(Qt.ItemDataRole.UserRole, ritual)
            table.setItem(row, 0, ident)
            table.setItem(row, 1, QTableWidgetItem(self.project.cards[ritual].name))
            table.setItem(row, 2, QTableWidgetItem(str(len(found[0])) if found else "—"))
            state = self._ritual_state(ritual)
            item = QTableWidgetItem(state.title())
            if state != "stock": self._tint_state(item, "removed" if state == "no recipe" else state)
            table.setItem(row, 3, item)
        table.blockSignals(False)
        controls["count"].setText(f"{table.rowCount()} ritual{'s' if table.rowCount() != 1 else ''}")
        if previous is not None:
            self._select_table_id(table, previous)
        if table.currentRow() < 0 and table.rowCount():
            table.selectRow(0)
        self.ritual_current = self._selected_ritual()
        self._filter_ritual_cards()
        self._refresh_ritual_detail()

    def _selected_ritual(self):
        table = self.workspace_controls["Rituals"]["cards"]
        row = table.currentRow()
        item = table.item(row, 0) if row >= 0 and not table.isRowHidden(row) else None
        return item.data(Qt.ItemDataRole.UserRole) if item is not None else None

    def _select_ritual(self):
        if getattr(self, "_loading_workspace", False):
            return
        self.ritual_current = self._selected_ritual()
        self._ritual_selected_tribute = 0
        self._ritual_selected_condition = None
        self._refresh_ritual_detail()

    def _filter_ritual_cards(self, *_):
        controls = self.workspace_controls.get("Rituals")
        if not controls:
            return
        query = controls["search"].text().strip().casefold()
        wanted_origin = controls["source_filter"].currentIndex()
        wanted_state = controls["state_filter"].currentText().casefold()
        table = controls["cards"]
        for row in range(table.rowCount()):
            ritual = table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            found = self._ritual_recipe(ritual)
            state = self._ritual_state(ritual)
            match = not query or query in self.project.cards[ritual].name.casefold() or query in str(ritual)
            if wanted_origin:
                origin = found[2] if found else "field"
                match &= origin == ("field", "hand", "both")[wanted_origin - 1]
            if wanted_state != "all states":
                match &= wanted_state == state
            table.setRowHidden(row, not match)

    def _set_ritual_preview(self, label, cid, empty="—"):
        """Draw within the label's designed card slot, never its provisional size.

        Qt lays out this page after the initial refresh.  Scaling against
        ``label.size()`` during that refresh could retain a large pixmap while
        the label later shrank to its fixed slot, visually covering the card
        name or the controls below it.
        """
        label.setPixmap(QPixmap())
        if not cid or self.files is None:
            label.setText(empty); return
        try:
            image = _card_image(self.project, self.files.wa, cid, self.frame_cache)
            # The minimum size is the actual reserved card slot.  Maximum
            # size is only an allowance for the layout and can be taller,
            # which was making the pixmap overlap the caption below it.
            limit = label.minimumSize()
            if limit.width() <= 0 or limit.height() <= 0:
                limit = label.size()
            label.setPixmap(image.scaled(limit, Qt.AspectRatioMode.KeepAspectRatio,
                                         Qt.TransformationMode.FastTransformation))
            label.setText("")
        except (OSError, ValueError, IndexError, KeyError):
            label.setText("Preview unavailable")

    def _refresh_ritual_detail(self):
        controls = self.workspace_controls.get("Rituals")
        if not controls:
            return
        page, ritual = controls["page"], getattr(self, "ritual_current", None)
        labels = {name: widget(page, QLabel, name) for name in (
            "ritualHeadingLabel", "ritualIdLabel", "ritualStateLabel", "ritualStatusLabel",
            "ritualRecipeSummaryLabel", "tributeCountStatusLabel", "tributeOriginHintLabel",
            "selectedTributeLabel", "ruleBasedSummary", "recipeSentenceLabel", "ritualErrorLabel",
            "ritualCardNameEditLabel", "ritualResultNameLabel")}
        if ritual not in self.project.cards:
            labels["ritualHeadingLabel"].setText("Select a ritual card")
            return
        draft = self._ritual_draft(ritual)
        found = self._ritual_recipe(ritual)
        labels["ritualHeadingLabel"].setText(f"Ritual: {self.project.cards[ritual].name}")
        labels["ritualIdLabel"].setText(f"ID {ritual}")
        state = self._ritual_state(ritual)
        labels["ritualStateLabel"].setText(f"State: {state.title()}")
        widget(page, QLineEdit, "ritualCardNameEdit").setText(self.project.cards[ritual].name)
        labels["ritualCardNameEditLabel"].setText(self.project.cards[ritual].name)
        card_id = widget(page, QSpinBox, "ritualCardIdSpin"); card_id.blockSignals(True); card_id.setValue(ritual); card_id.blockSignals(False)
        self._set_ritual_preview(widget(page, QLabel, "ritualCardPreview"), ritual, "Ritual card preview")
        if draft is None:
            labels["ritualStatusLabel"].setText("This ritual has no recipe. Give it one to configure its tributes.")
            labels["ritualRecipeSummaryLabel"].setText("No recipe")
            return
        tributes, result, origin = draft["tributes"], draft["result"], draft["origin"]
        selected = min(max(0, self._ritual_selected_tribute), len(tributes) - 1)
        self._ritual_selected_tribute = selected
        labels["ritualStatusLabel"].setText(
            "Pending changes" if self._ritual_draft_changed(ritual, draft)
            else "The game's own recipe.")
        labels["ritualRecipeSummaryLabel"].setText(f"{len(tributes)} tribute{'s' if len(tributes) != 1 else ''} → {self.project.card_label(result)}")
        labels["tributeCountStatusLabel"].setText(f"{len(tributes)} / 5 tributes")
        labels["tributeOriginHintLabel"].setText(_ORIGIN_TEXT[origin])
        for value, name in (("field", "originFieldRadio"), ("hand", "originHandRadio"), ("both", "originBothRadio")):
            radio = widget(page, QRadioButton, name); radio.blockSignals(True); radio.setChecked(value == origin); radio.blockSignals(False)
        result_combo = controls["result"]; result_combo.blockSignals(True); result_combo.setCurrentIndex(max(0, result_combo.findData(result))); result_combo.blockSignals(False)
        self._set_ritual_preview(widget(page, QLabel, "ritualResultPreview"), result, "Result preview")
        labels["ritualResultNameLabel"].setText(self.project.card_label(result))
        for index in range(5):
            exists = index < len(tributes)
            preview, summary, button = controls["slots"][index], controls["slot_summaries"][index], controls["slot_buttons"][index]
            if exists:
                requirement = tributes[index]
                cid = requirement.get("card") if set(requirement) == {"card"} else None
                self._set_ritual_preview(preview, cid, "Rule")
                summary.setText(self._ritual_tribute_text(requirement))
                button.setEnabled(True)
            else:
                preview.setPixmap(QPixmap()); preview.setText("+")
                summary.setText("Add tribute")
                button.setEnabled(index == len(tributes) and len(tributes) < 5)
            frame = controls["slot_frames"][index]
            if exists and index == selected:
                frame.setStyleSheet("QFrame { border: 2px solid #247cff; border-radius: 6px; }")
            elif exists:
                frame.setStyleSheet("QFrame { border: 1px solid #304866; border-radius: 6px; }")
            else:
                frame.setStyleSheet("QFrame { border: 1px dashed #4a6f93; border-radius: 6px; }")
        labels["selectedTributeLabel"].setText(f"Editing: Tribute {selected + 1} of {len(tributes)}")
        widget(page, QPushButton, "previousTributeButton").setEnabled(selected > 0)
        widget(page, QPushButton, "nextTributeButton").setEnabled(selected + 1 < len(tributes))
        widget(page, QPushButton, "removeSelectedTributeButton").setEnabled(len(tributes) > 1)
        req = tributes[selected]
        specific = set(req) == {"card"}
        for value, name in ((True, "specificCardModeRadio"), (False, "ruleBasedModeRadio")):
            radio = widget(page, QRadioButton, name); radio.blockSignals(True); radio.setChecked(value == specific); radio.blockSignals(False)
        controls["condition_stack"].setCurrentIndex(0)
        specific_combo = controls["specific"]; specific_combo.blockSignals(True); specific_combo.setCurrentIndex(max(0, specific_combo.findData(req.get("card")))); specific_combo.blockSignals(False)
        specific_preview = widget(page, QLabel, "specificCardPreview")
        specific_change = widget(page, QPushButton, "chooseSpecificTributeCardButton")
        self._set_ritual_preview(specific_preview, req.get("card"), "Selected card preview")
        labels["ruleBasedSummary"].setText(self._ritual_tribute_text(req))
        labels["ruleBasedSummary"].setVisible(not specific)
        for control in (specific_preview, specific_combo, specific_change):
            control.setVisible(specific)
        controls["conditions"].setEnabled(not specific)
        widget(page, QPushButton, "clearConditionsButton").setEnabled(not specific)
        labels["recipeSentenceLabel"].setText(
            f"Play {self.project.cards[ritual].name} with {len(tributes)} tribute{'s' if len(tributes) != 1 else ''} {origin} to summon {self.project.card_label(result)}.")
        self._refresh_ritual_conditions()

    def _ritual_tribute_text(self, requirement):
        parts = []
        if requirement.get("card"): parts.append(self.project.card_label(requirement["card"]))
        if requirement.get("type") is not None: parts.append(str(requirement["type"]))
        if requirement.get("fusion_group") is not None: parts.append(f"Group: {requirement['fusion_group']}")
        for key, text in (("min_attack", "ATK ≥ {}"), ("max_attack", "ATK ≤ {}"),
                          ("min_defense", "DEF ≥ {}"), ("max_defense", "DEF ≤ {}"),
                          ("min_level", "Level ≥ {}"), ("max_level", "Level ≤ {}")):
            if key in requirement: parts.append(text.format(requirement[key]))
        if requirement.get("defense_gt_attack"): parts.append("DEF > ATK")
        return " · ".join(parts) or "Any monster"

    def _select_or_add_tribute(self, index):
        ritual = getattr(self, "ritual_current", None)
        draft = self._ritual_draft(ritual) if ritual in self.project.cards else None
        if draft is None: return
        if index >= len(draft["tributes"]):
            if len(draft["tributes"]) >= 5: return
            draft["tributes"].append({"min_attack": 0})
            index = len(draft["tributes"]) - 1
        self._ritual_selected_tribute = index
        self._ritual_selected_condition = None
        self._refresh_ritual_detail()

    def _remove_selected_tribute(self):
        draft = self._ritual_draft(getattr(self, "ritual_current", None))
        if draft is None or len(draft["tributes"]) <= 1: return
        draft["tributes"].pop(self._ritual_selected_tribute)
        self._ritual_selected_tribute = min(self._ritual_selected_tribute, len(draft["tributes"]) - 1)
        self._ritual_selected_condition = None
        self._refresh_ritual_detail()

    def _ritual_set_mode(self, mode):
        draft = self._ritual_draft(getattr(self, "ritual_current", None))
        if draft is None: return
        req = draft["tributes"][self._ritual_selected_tribute]
        if mode == "specific":
            cid = req.get("card") or (self.project.monsters()[0] if self.project.monsters() else 0)
            req.clear(); req["card"] = cid
        elif set(req) == {"card"}:
            card = self.project.cards.get(req["card"])
            req.clear(); req["type"] = TYPE_NAMES[card.type] if card and card.is_monster() else TYPE_NAMES[0]
        self._ritual_selected_condition = None
        self._refresh_ritual_detail()

    def _ritual_result_changed(self, _=None):
        draft = self._ritual_draft(getattr(self, "ritual_current", None))
        if draft is not None and not getattr(self, "_loading_workspace", False):
            found = self.workspace_controls["Rituals"]["result"].currentData()
            if found: draft["result"] = found; self._refresh_ritual_detail()

    def _ritual_specific_changed(self, _=None):
        draft = self._ritual_draft(getattr(self, "ritual_current", None))
        if draft is not None:
            found = self.workspace_controls["Rituals"]["specific"].currentData()
            if found and set(draft["tributes"][self._ritual_selected_tribute]) == {"card"}:
                draft["tributes"][self._ritual_selected_tribute]["card"] = found
                self._refresh_ritual_detail()

    def _ritual_origin_changed(self, origin):
        draft = self._ritual_draft(getattr(self, "ritual_current", None))
        if draft is not None: draft["origin"] = origin; self._refresh_ritual_detail()

    def _refresh_ritual_conditions(self):
        """Render conditions as direct, editable rows in the selected tribute.

        The reference page keeps every rule visible and editable.  It does
        not split a selected row into a second inspector beneath the table.
        """
        controls = self.workspace_controls["Rituals"]
        table = controls["conditions"]
        draft = self._ritual_draft(getattr(self, "ritual_current", None))
        if draft is None:
            return
        requirement = draft["tributes"][self._ritual_selected_tribute]
        table.blockSignals(True)
        table.clearContents()
        table.setRowCount(0)
        for key, value in requirement.items():
            row = table.rowCount()
            table.insertRow(row)
            table.setRowHeight(row, 34)
            label = QTableWidgetItem(_CONDITION_LABEL.get(key, key))
            label.setData(Qt.ItemDataRole.UserRole, key)
            table.setItem(row, 0, label)
            operator = QLabel("")
            operator.setAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setCellWidget(row, 1, operator)
            if key == "type":
                editor = QComboBox(table)
                editor.addItems(TYPE_NAMES[:20])
                editor.setCurrentIndex(max(0, editor.findText(str(value))))
                decorate_type_items(self, editor)
                editor.currentTextChanged.connect(lambda item, k=key: self._set_ritual_condition_direct(k, item))
            elif key == "fusion_group":
                editor = QComboBox(table)
                editor.addItems(FUSION_GROUPS)
                editor.setCurrentIndex(max(0, editor.findText(str(value))))
                editor.currentTextChanged.connect(lambda item, k=key: self._set_ritual_condition_direct(k, item))
            elif key == "card":
                editor = QComboBox(table)
                for cid, label_text in controls["card_choices"]:
                    editor.addItem(label_text, cid)
                editor.setCurrentIndex(max(0, editor.findData(value)))
                editor.currentIndexChanged.connect(lambda _index, box=editor, k=key: self._set_ritual_condition_direct(k, box.currentData()))
            elif key == "defense_gt_attack":
                editor = QCheckBox("Require DEF > ATK", table)
                editor.setChecked(bool(value))
                editor.toggled.connect(lambda checked, k=key: self._set_ritual_condition_direct(k, bool(checked)))
            else:
                operator.setText("≥" if key.startswith("min_") else "≤")
                _label, _stored, number = next(item for item in _CONDITIONS if item[1] == key)
                editor = QSpinBox(table)
                editor.setRange(number[0], number[1])
                editor.setValue(int(value))
                editor.valueChanged.connect(lambda amount, k=key: self._set_ritual_condition_direct(k, amount))
            table.setCellWidget(row, 2, editor)
            remove = QToolButton(table)
            remove.setText("×")
            remove.setToolTip("Remove this condition")
            remove.setAutoRaise(True)
            remove.setFixedSize(26, 26)
            remove.clicked.connect(lambda _checked=False, k=key: self._remove_ritual_condition(k))
            action = QWidget(table)
            action_layout = QHBoxLayout(action)
            action_layout.setContentsMargins(0, 1, 0, 1)
            action_layout.addStretch(1)
            action_layout.addWidget(remove)
            action_layout.addStretch(1)
            table.setCellWidget(row, 3, action)
        table.blockSignals(False)

    def _set_ritual_condition_direct(self, key, value):
        draft = self._ritual_draft(getattr(self, "ritual_current", None))
        if draft is None:
            return
        requirement = draft["tributes"][self._ritual_selected_tribute]
        if requirement.get(key) == value:
            return
        requirement[key] = value
        self._refresh_ritual_detail()

    def _select_ritual_condition(self):
        controls = self.workspace_controls["Rituals"]; table = controls["conditions"]
        row = table.currentRow(); item = table.item(row, 0) if row >= 0 else None
        key = item.data(Qt.ItemDataRole.UserRole) if item else None
        self._ritual_selected_condition = key
        stack = controls["condition_stack"]
        if not key: stack.setCurrentIndex(0); return
        draft = self._ritual_draft(self.ritual_current); value = draft["tributes"][self._ritual_selected_tribute][key]
        if key == "type": page, field = 1, controls["condition_type"]
        elif key == "fusion_group": page, field = 2, controls["condition_group"]
        elif key == "card": page, field = 4, controls["condition_card"]
        elif key == "defense_gt_attack": page, field = 5, widget(controls["page"], QCheckBox, "conditionDefenseAboveAttackCheck")
        else: page, field = 3, controls["condition_number"]
        stack.setCurrentIndex(page); field.blockSignals(True)
        if isinstance(field, QComboBox): field.setCurrentIndex(max(0, field.findData(value) if key == "card" else field.findText(str(value))))
        elif isinstance(field, QSpinBox): field.setValue(int(value))
        else: field.setChecked(bool(value))
        field.blockSignals(False)

    def _set_condition_value(self, value):
        key = getattr(self, "_ritual_selected_condition", None)
        draft = self._ritual_draft(getattr(self, "ritual_current", None))
        if not key or draft is None: return
        draft["tributes"][self._ritual_selected_tribute][key] = value
        self._refresh_ritual_detail()

    def _add_ritual_condition(self):
        """Choose one or more missing conditions in a compact modal picker."""
        from PySide6.QtWidgets import QDialog, QDialogButtonBox

        draft = self._ritual_draft(getattr(self, "ritual_current", None))
        if draft is None:
            return
        requirement = draft["tributes"][self._ritual_selected_tribute]
        available = [(label, key, number) for label, key, number in _CONDITIONS if key not in requirement]
        if not available:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Add ritual conditions")
        dialog.setMinimumWidth(390)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Select every condition this tribute must meet:", dialog))
        choices = []
        for label, key, number in available:
            check = QCheckBox(label, dialog)
            layout.addWidget(check)
            choices.append((check, key, number))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, dialog)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        added = []
        for check, key, number in choices:
            if not check.isChecked():
                continue
            if key == "type": requirement[key] = TYPE_NAMES[0]
            elif key == "fusion_group": requirement[key] = FUSION_GROUPS[0]
            elif key == "card": requirement[key] = self.project.monsters()[0] if self.project.monsters() else 0
            elif key == "defense_gt_attack": requirement[key] = True
            else: requirement[key] = number[2]
            added.append(key)
        if added:
            self._ritual_selected_condition = added[0]
            self._refresh_ritual_detail()

    def _remove_ritual_condition(self, key):
        draft = self._ritual_draft(getattr(self, "ritual_current", None))
        if draft is not None:
            draft["tributes"][self._ritual_selected_tribute].pop(key, None)
            self._ritual_selected_condition = None
            self._refresh_ritual_detail()

    def _clear_ritual_conditions(self):
        draft = self._ritual_draft(getattr(self, "ritual_current", None))
        if draft is not None:
            draft["tributes"][self._ritual_selected_tribute].clear()
            self._ritual_selected_condition = None
            self._refresh_ritual_detail()

    def _choose_ritual_result(self):
        chosen = self._choose_one_card("Summoned ritual monster", ids=self.project.monsters(), selected=self.workspace_controls["Rituals"]["result"].currentData())
        if chosen:
            self._ritual_draft(self.ritual_current)["result"] = chosen; self._refresh_ritual_detail()

    def _choose_specific_tribute(self):
        chosen = self._choose_one_card("Specific ritual tribute", ids=self.project.monsters(), selected=self.workspace_controls["Rituals"]["specific"].currentData())
        if chosen:
            draft = self._ritual_draft(self.ritual_current); draft["tributes"][self._ritual_selected_tribute] = {"card": chosen}; self._refresh_ritual_detail()

    def _choose_condition_card(self):
        chosen = self._choose_one_card("Ritual condition card", ids=self.project.monsters(), selected=self.workspace_controls["Rituals"]["condition_card"].currentData())
        if chosen:
            draft = self._ritual_draft(self.ritual_current); draft["tributes"][self._ritual_selected_tribute]["card"] = chosen; self._refresh_ritual_detail()

    def _validate_ritual_draft(self, draft):
        if not 1 <= len(draft["tributes"]) <= 5: return "A ritual needs between one and five tributes."
        if not draft["result"] in self.project.monsters(): return "Choose a monster to summon."
        for number, req in enumerate(draft["tributes"], 1):
            if not req: return f"Tribute {number} needs at least one condition."
            if req.get("card") and req["card"] not in self.project.monsters(): return f"Tribute {number} must name a monster."
            for low, high, noun in (("min_attack", "max_attack", "ATK"), ("min_defense", "max_defense", "DEF"), ("min_level", "max_level", "level")):
                if low in req and high in req and req[low] > req[high]: return f"Tribute {number}: minimum {noun} exceeds maximum."
        return ""

    def _apply_ritual_selector_recipe(self, *_):
        ritual = getattr(self, "ritual_current", None); draft = self._ritual_draft(ritual)
        if ritual not in self.project.cards or draft is None: return
        legacy = self.ritual_pending.pop(ritual, None)
        if legacy is not None:
            values = tuple(legacy)
            if len(values) >= 2 and all(values):
                draft = {"tributes": [{"card": card} for card in values[:-1]],
                         "result": values[-1], "origin": "field", "own": True}
                self._ritual_drafts[ritual] = draft
        error = self._validate_ritual_draft(draft)
        label = widget(self.workspace_controls["Rituals"]["page"], QLabel, "ritualErrorLabel")
        if error: label.setText(error); self.statusBar().showMessage(error, 5000); return
        self.project.set_ritual(ritual, draft["tributes"], draft["result"], draft["origin"])
        self._ritual_drafts.pop(ritual, None); label.setText("")
        self._mark_dirty(); self._refresh_rituals()

    def _give_own_ritual_recipe(self):
        ritual = getattr(self, "ritual_current", None)
        if ritual not in self.project.cards: return
        self._ritual_drafts.pop(ritual, None)
        self._ritual_draft(ritual, create=True)
        self._refresh_ritual_detail()

    def _remove_ritual(self):
        ritual = getattr(self, "ritual_current", None)
        if ritual not in self.project.cards: return
        self.project.remove_ritual(ritual); self._ritual_drafts.pop(ritual, None)
        self._mark_dirty(); self._refresh_rituals()

    def _revert_ritual(self):
        ritual = getattr(self, "ritual_current", None)
        if ritual not in self.project.cards: return
        self.project.revert_ritual(ritual); self._ritual_drafts.pop(ritual, None)
        self._mark_dirty(); self._refresh_rituals()

    def _add_ritual_recipe(self):
        ritual = self._choose_one_card("Choose a ritual card", ids=self.project.ritual_cards())
        if ritual:
            self._select_table_id(self.workspace_controls["Rituals"]["cards"], ritual)
            self.ritual_current = ritual; self._give_own_ritual_recipe()

    def _duplicate_ritual_recipe(self):
        source = getattr(self, "ritual_current", None)
        if source not in self.project.cards: return
        target = self._choose_one_card("Copy recipe to ritual card", ids=[cid for cid in self.project.ritual_cards() if cid != source])
        draft = self._ritual_draft(source)
        if target and draft:
            self._ritual_drafts[target] = deepcopy(draft)
            self._select_table_id(self.workspace_controls["Rituals"]["cards"], target)
            self.ritual_current = target; self._refresh_ritual_detail()

    def _open_ritual_card(self):
        ritual = getattr(self, "ritual_current", None)
        if ritual in self.project.cards and hasattr(self, "show_card"):
            self.select_workspace("Cards")
            self.show_card(ritual)

    original_build_page = ModernEditor._build_workspace_page
    ModernEditor._build_workspace_page = build_page
    RitualsMixin._fill_ritual_cards = _ritual_refill_cards
    RitualsMixin._refresh_rituals = _refresh_rituals
    RitualsMixin._select_ritual = _select_ritual
    RitualsMixin._filter_ritual_cards = _filter_ritual_cards
    RitualsMixin._refresh_ritual_detail = _refresh_ritual_detail
    RitualsMixin._selected_ritual = _selected_ritual
    RitualsMixin._ritual_recipe_text = lambda self, ritual: self._ritual_tribute_text(self._ritual_recipe(ritual)[0][0]) if self._ritual_recipe(ritual) else "—"
    RitualsMixin._stage_ritual_selector_recipe = lambda self, *_: None
    RitualsMixin._apply_ritual_selector_recipe = _apply_ritual_selector_recipe
    RitualsMixin._remove_ritual = _remove_ritual
    RitualsMixin._revert_ritual = _revert_ritual
    for name, method in {
        "_ritual_refill_cards": _ritual_refill_cards, "_ritual_recipe": _ritual_recipe,
        "_ritual_draft": _ritual_draft, "_ritual_state": _ritual_state,
        "_ritual_draft_changed": _ritual_draft_changed,
        "_set_ritual_preview": _set_ritual_preview, "_ritual_tribute_text": _ritual_tribute_text,
        "_select_or_add_tribute": _select_or_add_tribute, "_remove_selected_tribute": _remove_selected_tribute,
        "_ritual_set_mode": _ritual_set_mode, "_ritual_result_changed": _ritual_result_changed,
        "_ritual_specific_changed": _ritual_specific_changed, "_ritual_origin_changed": _ritual_origin_changed,
        "_refresh_ritual_conditions": _refresh_ritual_conditions, "_select_ritual_condition": _select_ritual_condition,
        "_set_condition_value": _set_condition_value, "_set_ritual_condition_direct": _set_ritual_condition_direct,
        "_add_ritual_condition": _add_ritual_condition,
        "_remove_ritual_condition": _remove_ritual_condition, "_clear_ritual_conditions": _clear_ritual_conditions,
        "_choose_ritual_result": _choose_ritual_result, "_choose_specific_tribute": _choose_specific_tribute,
        "_choose_condition_card": _choose_condition_card, "_validate_ritual_draft": _validate_ritual_draft,
        "_give_own_ritual_recipe": _give_own_ritual_recipe, "_add_ritual_recipe": _add_ritual_recipe,
        "_duplicate_ritual_recipe": _duplicate_ritual_recipe, "_open_ritual_card": _open_ritual_card,
    }.items():
        setattr(RitualsMixin, name, method)
