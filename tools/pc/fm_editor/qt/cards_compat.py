"""Compatibility for the current classic Cards-page data model.

This module is deliberately separate from the other Qt pages: it translates
the current ``monster_effects`` card data without changing classic modules.
"""
from __future__ import annotations

import struct

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QImage, QPixmap
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                               QFrame, QGridLayout, QHBoxLayout, QLabel,
                               QFormLayout, QPlainTextEdit, QPushButton, QSpinBox, QTableWidgetItem,
                               QToolButton, QVBoxLayout)


def install() -> None:
    """Make Qt's existing Effects tab read and write ``monster_effects``."""
    try:
        from .. import monster_effects as effects
    except ImportError:
        return
    from . import common as qt_common
    from .cards import CardsMixin
    from .common import _qimage, gamedata, guardian_stars, pngio
    from .. import card_view, card_text
    if getattr(CardsMixin, "_cards_compat_installed", False):
        return
    CardsMixin._cards_compat_installed = True

    # The current classic renderer exposes the ramps directly. Qt's context
    # menu was written for the later convenience method, so provide that
    # spelling without changing the shared card_text module.
    if not hasattr(card_text.RetailFont, "colours_for"):
        def colours_for(font, code):
            return font.ramps[code] if 0 <= code < len(font.ramps) else font.colours
        card_text.RetailFont.colours_for = colours_for

    # HD texture packs keep a level star in a 9x9 logical slot. Some packs
    # contain the already-trimmed star centred in that larger slot, but the
    # old compositor treats the transparent margin as part of the sprite.
    # It consequently renders only a tiny coloured dot. Tighten that one
    # sprite before the existing compositor places it; coordinates and the
    # number of stars remain exactly as the game uses them.
    original_detail_sprite = qt_common._card_detail_sprite

    def card_detail_sprite(project, wa, frame_cache, kind, index=0, scale=1):
        image = original_detail_sprite(project, wa, frame_cache, kind, index, scale)
        if kind != "level" or image is None or scale < 4:
            return image
        width, height = image.width(), image.height()
        left, top, right, bottom = width, height, -1, -1
        for y in range(height):
            for x in range(width):
                if image.pixelColor(x, y).alpha():
                    left, top = min(left, x), min(top, y)
                    right, bottom = max(right, x), max(bottom, y)
        target = 9 * scale
        if right < left or (right - left + 1 >= target * 2 // 3 and bottom - top + 1 >= target * 2 // 3):
            return image
        return image.copy(left, top, right - left + 1, bottom - top + 1).scaled(
            target, target, Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.FastTransformation)

    qt_common._card_detail_sprite = card_detail_sprite

    original_build_effects = CardsMixin._build_card_effects
    original_build_cards = CardsMixin._build_cards
    original_show_card = CardsMixin.show_card
    original_apply_card = CardsMixin.apply_card
    original_store_equip_bonus = CardsMixin._store_equip_bonus
    original_show_equip_bonus = CardsMixin._show_equip_bonus
    original_text_icon = CardsMixin._text_icon

    def picture_icon(image):
        if image is None:
            return QIcon()
        return QIcon(QPixmap.fromImage(_qimage(image.width, image.height, image.rgba)))

    def attribute_picture(wa, attribute):
        """Decode an attribute ball without importing the Tk-only helper."""
        if not 0 <= attribute < 8:
            return None
        sheet, palettes = 0xEFE800, 0xF06800
        palette = palettes + 0x1E00 + attribute * 0x20
        x, y, width, height = 16 * attribute, 128, 16, 16
        if wa is None or len(wa) < max(sheet + (y + height) * 128, palette + 32):
            return None
        rgba = bytearray()
        for row in range(height):
            for column in range(width):
                byte = wa[sheet + (y + row) * 128 + (x + column) // 2]
                index = byte >> (4 * ((x + column) & 1)) & 0xF
                word = wa[palette + index * 2] | wa[palette + index * 2 + 1] << 8
                rgba += bytes(((word & 31) * 255 // 31,
                               ((word >> 5) & 31) * 255 // 31,
                               ((word >> 10) & 31) * 255 // 31,
                               255 if index and word else 0))
        return pngio.Image(width, height, bytes(rgba))

    def text_icon(self, code):
        """Bridge classic RetailFont.icon's RGBA image to Qt's QIcon."""
        held = getattr(self, "_text_icons", None)
        if held is None:
            held = self._text_icons = {}
        if code in held:
            return held[code]
        try:
            found = self._retail_font().icon(code)
        except (IndexError, OSError, ValueError, struct.error):
            return QIcon()
        if found is None:
            return QIcon()
        # Current classic: (width, height, RGBA bytes). Keep support for the
        # newer pixel-list form as well when this adapter is reused later.
        if isinstance(found, tuple) and len(found) == 3 and isinstance(found[0], int):
            width, height, rgba = found
            icon = QIcon(QPixmap.fromImage(_qimage(width, height, rgba)))
        else:
            return original_text_icon(self, code)
        held[code] = icon
        return icon

    def field_icons(self):
        """Use the same disc sprites that the classic editor shows in fields."""
        if self.files is None:
            return
        # An imported modified BIN may replace these sheet sprites too.
        wa = getattr(self, "preview_wa", self.files.wa)
        try:
            font = card_text.RetailFont(wa)
            for kind in range(self.type_box.count()):
                code = kind if kind < gamedata.TYPE_MAGIC else 0x14 + kind - gamedata.TYPE_MAGIC
                found = font.icon(code)
                if found is not None:
                    width, height, rgba = found
                    self.type_box.setItemIcon(kind, QIcon(QPixmap.fromImage(_qimage(width, height, rgba))))
            for attribute in range(self.attribute_box.count()):
                self.attribute_box.setItemIcon(attribute, picture_icon(attribute_picture(wa, attribute)))
            for index in range(1, self.star1_box.count()):
                found = guardian_stars.disc_icon(wa, index) or guardian_stars.imported_icon(wa, index)
                if found is not None:
                    width, height, rgba = found
                    icon = QIcon(QPixmap.fromImage(_qimage(width, height, rgba)))
                    self.star1_box.setItemIcon(index, icon)
                    self.star2_box.setItemIcon(index, icon)
        except (IndexError, OSError, ValueError, pngio.PngError):
            # A partial or imported archive still leaves the text fields usable.
            return

    def build_effects(self, widget):
        original_build_effects(self, widget)
        # The Designer form wires these to the older modal handlers. Replace
        # those connections explicitly; merely replacing the class methods is
        # not enough once Qt has captured a bound method in a signal.
        for button in self.effect_buttons.values():
            try:
                button.clicked.disconnect()
            except RuntimeError:
                pass
        try:
            self.effects_table.cellDoubleClicked.disconnect()
        except RuntimeError:
            pass
        self.effect_buttons["addEffect"].setText("Add effect")
        self.effect_buttons["editEffect"].setText("Edit effect")
        self.effect_buttons["addEffect"].clicked.connect(lambda: add(self))
        self.effect_buttons["editEffect"].clicked.connect(lambda: edit(self))
        self.effect_buttons["removeEffect"].clicked.connect(lambda: remove(self))
        self.effect_buttons["effectUp"].clicked.connect(lambda: move(self, -1))
        self.effect_buttons["effectDown"].clicked.connect(lambda: move(self, 1))
        self.effects_table.cellDoubleClicked.connect(lambda *_: edit(self))
        self.effects_none = QCheckBox("None, even where another mod gives it some", self.effects_note.parentWidget())
        self.effects_none.setToolTip('Writes "monster_effects": [] so this mod explicitly removes inherited effects.')
        layout = self.effects_note.parentWidget().layout()
        layout.insertWidget(layout.indexOf(self.effects_note) + 1, self.effects_none)
        self.effects_none.toggled.connect(
            lambda checked: set_effects(self, get_effects(self), keep_empty=checked))
        # Keep editing on this tab. The older compatibility version opened a
        # modal dialog, which made adding a short effect needlessly slow.
        editor = QFrame(self.effects_note.parentWidget())
        editor.setObjectName("inlineEffectEditor")
        editor.setFrameShape(QFrame.Shape.StyledPanel)
        grid = QGridLayout(editor)
        fields, labels = {}, {}

        def line(row, title, control):
            caption = QLabel(title, editor)
            grid.addWidget(caption, row, 0)
            grid.addWidget(control, row, 1)
            fields[title] = control
            labels[title] = caption
            return control

        def choices(values, captions):
            box = QComboBox(editor)
            for value, caption in zip(values, captions):
                box.addItem(caption, value)
            return box

        when = line(0, "When", choices(effects.WHEN, effects.WHEN_LABELS))
        action = line(1, "Does", QComboBox(editor))
        target = line(2, "Whose", QComboBox(editor))
        magic = line(3, "Magic card", QComboBox(editor))
        for cid in effects.MAGIC:
            magic.addItem(self.project.card_label(cid), cid)
        only_type = line(4, "Only type", QComboBox(editor))
        only_type.addItem("Any", None)
        for name in effects.TYPE_NAMES[:gamedata.TYPE_MAGIC]:
            only_type.addItem(name, name)
        only_attribute = line(5, "Only attribute", QComboBox(editor))
        only_attribute.addItem("Any", None)
        for name in effects.ATTRIBUTE_NAMES:
            only_attribute.addItem(name, name)
        attack = line(6, "ATK", QSpinBox(editor))
        defense = line(7, "DEF", QSpinBox(editor))
        amount = line(8, "LP", QSpinBox(editor))
        for spin in (attack, defense):
            spin.setRange(-effects.BOOST_MAX, effects.BOOST_MAX)
            spin.setSingleStep(100)
        amount.setRange(1, effects.AMOUNT_MAX)
        amount.setSingleStep(100)
        hint = QLabel(editor)
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#9aacc4")
        grid.addWidget(hint, 9, 0, 1, 2)
        problem = QLabel(editor)
        problem.setWordWrap(True)
        problem.setStyleSheet("color:#f08080")
        grid.addWidget(problem, 10, 0, 1, 2)
        buttons_row = QHBoxLayout()
        save = QPushButton("Add effect", editor)
        cancel = QPushButton("Cancel", editor)
        buttons_row.addWidget(save)
        buttons_row.addWidget(cancel)
        buttons_row.addStretch(1)
        grid.addLayout(buttons_row, 11, 0, 1, 2)

        def refill(box, values, all_values, captions, wanted):
            blocked = box.blockSignals(True)
            box.clear()
            for value in values:
                box.addItem(captions[all_values.index(value)], value)
            box.setCurrentIndex(max(0, box.findData(wanted)))
            box.blockSignals(blocked)

        def follows():
            selected_when = when.currentData()
            hint.setText(effects.WHEN_HINTS[effects.WHEN.index(selected_when)])
            refill(action, effects.actions(selected_when), effects.DO, effects.DO_LABELS,
                   action.currentData() or "boost")
            selected_action = action.currentData()
            refill(target, effects.targets(selected_when, selected_action), effects.TARGET, effects.TARGET_LABELS,
                   target.currentData() or effects.default_target(selected_when, selected_action))
            shown = {"When", "Does"}
            if selected_action == "magic":
                shown.add("Magic card")
            elif selected_action in effects.FILTERED:
                shown.update(("Whose", "Only type", "Only attribute"))
                if selected_action == "boost":
                    shown.update(("ATK", "DEF"))
            else:
                shown.add("LP")
            for title, control in fields.items():
                labels[title].setVisible(title in shown)
                control.setVisible(title in shown)

        def save_effect():
            made = {"when": when.currentData(), "do": action.currentData()}
            if made["do"] == "magic":
                made["card"] = magic.currentData()
            elif made["do"] in effects.FILTERED:
                made["target"] = target.currentData()
                if only_type.currentData(): made["type"] = only_type.currentData()
                if only_attribute.currentData(): made["attribute"] = only_attribute.currentData()
                if made["do"] == "boost":
                    if attack.value(): made["attack"] = attack.value()
                    if defense.value(): made["defense"] = defense.value()
            else:
                made["amount"] = amount.value()
            normal = effects.normalize(made, self.project.resolve)
            if normal is None:
                problem.setText("The game cannot use that effect. A boost needs ATK or DEF.")
                return
            rows = get_effects(self)
            index = editor.property("effect_index")
            if isinstance(index, int) and 0 <= index < len(rows):
                rows[index] = normal
                selected = index
            else:
                rows.append(normal)
                selected = len(rows) - 1
            set_effects(self, rows)
            self.effects_table.selectRow(selected)

        def cancel_edit():
            row, rows = self.effects_table.currentRow(), get_effects(self)
            begin_effect_edit(self, rows[row] if 0 <= row < len(rows) else None,
                              row if 0 <= row < len(rows) else None)

        when.currentIndexChanged.connect(follows)
        action.currentIndexChanged.connect(follows)
        save.clicked.connect(save_effect)
        cancel.clicked.connect(cancel_edit)
        self._inline_effect_editor = {"frame": editor, "fields": fields, "labels": labels,
                                      "when": when, "action": action, "target": target,
                                      "magic": magic, "type": only_type, "attribute": only_attribute,
                                      "attack": attack, "defense": defense, "amount": amount,
                                      "problem": problem, "save": save, "follows": follows}
        layout.insertWidget(layout.indexOf(self.effects_none) + 1, editor)
        self.effects_table.itemSelectionChanged.connect(lambda: select_effect_from_list(self))

    def begin_effect_edit(self, effect=None, index=None):
        """Show one editable effect directly beneath the list."""
        editor = self._inline_effect_editor
        value = effects.normalize(effect, self.project.resolve) if effect else None
        value = value or {"when": "summon", "do": "boost", "target": "self", "attack": 500}
        editor["frame"].setProperty("effect_index", index)
        editor["frame"].setProperty("card_id", self.current)
        editor["problem"].clear()
        editor["when"].setCurrentIndex(max(0, editor["when"].findData(value["when"])))
        editor["follows"]()
        editor["action"].setCurrentIndex(max(0, editor["action"].findData(value["do"])))
        editor["follows"]()
        for key in ("target", "magic", "type", "attribute"):
            wanted = value.get({"magic": "card"}.get(key, key))
            editor[key].setCurrentIndex(max(0, editor[key].findData(wanted)))
        editor["attack"].setValue(value.get("attack", 0))
        editor["defense"].setValue(value.get("defense", 0))
        editor["amount"].setValue(value.get("amount", 500))
        editor["save"].setText("Save effect" if index is not None else "Add effect")
        editor["frame"].show()

    def select_effect_from_list(self):
        row, rows = self.effects_table.currentRow(), get_effects(self)
        if 0 <= row < len(rows):
            begin_effect_edit(self, rows[row], row)

    def build_cards(self, parent):
        original_build_cards(self, parent)
        self._effects_tab_index = next(
            (index for index in range(self.card_data_tabs.count())
             if self.card_data_tabs.tabText(index) == "Effects"), -1)
        # The shared application sheet deliberately has no generic tab rule.
        # On Fusion this leaves the pane's bottom edge to the platform style,
        # which is invisible against the Cards page.  Give this full-height
        # editor pane an explicit four-sided frame.
        self.card_data_tabs.setStyleSheet("""
            QTabWidget::pane {
                background: #0b1220;
                border: 1px solid #26374c;
                top: -1px;
            }
            QTabBar::tab {
                background: #101b2b;
                color: #aebfd6;
                border: 1px solid #26374c;
                border-bottom: 0;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 4px 12px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #0b1220;
                color: #f3f7fc;
                border-bottom: 1px solid #0b1220;
            }
        """)
        # Keep these project-only fields in this compatibility layer.  The
        # Designer form remains usable by the tracked Qt editor on its own.
        identity = self.cards_form.findChild(QFormLayout, "identityForm")
        name_colour = QComboBox(self.cards_form)
        name_colour.setObjectName("nameColourCombo")
        name_colour.setToolTip("The colour used for this card's name in the game details.")
        name_colour.addItem("Retail / default", None)
        for index, label in enumerate(("White", "Yellow", "Blue", "Green", "Grey", "Orange", "Red", "Unused")):
            name_colour.addItem(f"{label} ({index})", index)
        identity.addRow("Name colour", name_colour)
        self.name_colour = name_colour

        passwords = self.cards_form.findChild(QGridLayout, "passwordGrid")
        notes_label = QLabel("Notes", self.cards_form)
        notes = QPlainTextEdit(self.cards_form)
        notes.setObjectName("cardNotesEdit")
        notes.setPlaceholderText("Private notes about this card")
        notes.setToolTip("Saved in the mod for the author. The game does not display it.")
        notes.setFixedHeight(88)
        passwords.addWidget(notes_label, 2, 0, 1, 2)
        passwords.addWidget(notes, 3, 0, 1, 2)
        self.card_notes = notes
        field_icons(self)

    def show_card(self, cid):
        original_show_card(self, cid)
        # The disc leaves an unused attribute byte on non-monster records.
        # Dragon Capture Jar is a Magic card whose retail byte happens to be
        # 7; the game ignores it.  Display the semantic value the editor will
        # save instead of labelling a Magic card as a Trap.
        card = self.project.cards.get(cid) if self.project else None
        effects_tab = getattr(self, "_effects_tab_index", -1)
        if effects_tab >= 0:
            monster = card is not None and card.is_monster()
            self.card_data_tabs.setTabVisible(effects_tab, monster)
            if not monster and self.card_data_tabs.currentIndex() == effects_tab:
                self.card_data_tabs.setCurrentIndex(0)
        if card is not None and not card.is_monster():
            self.attribute_box.setCurrentIndex(
                7 if card.type == gamedata.TYPE_TRAP else 6)
        if hasattr(self, "card_notes"):
            self.card_notes.setPlainText(self.project.notes.get(cid, "") if cid else "")
        if hasattr(self, "name_colour"):
            colour = card_name_colour(self, cid)
            self.name_colour.setCurrentIndex(max(0, self.name_colour.findData(colour)))
        field_icons(self)

    def card_name_colour(self, cid):
        """The effective own-mod name ramp for one card, or the retail ramp."""
        rules = self.project.other.get("card_text_colors") if self.project else None
        cards = rules.get("cards") if isinstance(rules, dict) else None
        colour = None
        if isinstance(cards, list):
            for rule in cards:
                if not isinstance(rule, dict) or self.project.resolve(rule.get("card")) != cid:
                    continue
                value = rule.get("name")
                if isinstance(value, int) and not isinstance(value, bool) and 0 <= value < 8:
                    colour = value
        return colour

    def store_name_colour(self, cid, wanted):
        """Write just this card's ``card_text_colors.name`` rule.

        Description and guardian-star colour values in a shared rule stay
        intact.  Removing the selector value removes only the name override.
        """
        before = card_name_colour(self, cid)
        if wanted == before:
            return False
        table = self.project.other.get("card_text_colors")
        if not isinstance(table, dict):
            table = {}
            self.project.other["card_text_colors"] = table
        cards = table.get("cards")
        if not isinstance(cards, list):
            cards = []
            table["cards"] = cards
        matching = [rule for rule in cards if isinstance(rule, dict)
                    and self.project.resolve(rule.get("card")) == cid]
        target = matching[-1] if matching else None
        if wanted is None:
            if target is not None:
                target.pop("name", None)
                # A rule that contained no other setting was only this
                # selector, so remove it rather than leaving a no-op entry.
                if set(target) == {"card"}:
                    cards.remove(target)
        elif target is None:
            cards.append({"card": self.project.ref(cid), "name": wanted})
        else:
            target["name"] = wanted
        if not cards and set(table) == {"cards"}:
            self.project.other.pop("card_text_colors", None)
        return True

    def apply_card(self, quiet=False):
        """Save Qt's normal card fields, then its compatibility-only fields."""
        cid = self.current
        # The normal apply path refreshes the form when card data changed.
        # Preserve these uncommitted compatibility controls before that can
        # repopulate them from the project.
        notes = self.card_notes.toPlainText() if hasattr(self, "card_notes") else ""
        name_colour = self.name_colour.currentData() if hasattr(self, "name_colour") else None
        if not original_apply_card(self, quiet):
            return False
        if not cid or self.project is None:
            return True
        notes_changed = notes != self.project.notes.get(cid, "") and (notes.strip() or cid in self.project.notes)
        if notes_changed:
            self.project.set_notes(cid, notes)
        colour_changed = hasattr(self, "name_colour") and store_name_colour(self, cid, name_colour)
        if notes_changed or colour_changed:
            self._mark_dirty()
            self.refresh_cards(select_id=cid)
            self.statusBar().showMessage(f"Updated {self.project.card_label(cid)}")
        return True

    def render_full_description(self):
        """Render the complete in-game information panel, not a text fallback."""
        label = getattr(self, "card_text_preview", None)
        if label is None or self.files is None or not self.current:
            return
        try:
            archive = getattr(self, "preview_wa", self.files.wa)
            key = (id(self.files.slus), id(archive))
            cached = getattr(self, "_game_card_view", None)
            if cached is None or cached[0] != key:
                cached = (key, card_view.CardView(self.files.slus, archive))
                self._game_card_view = cached
            names = guardian_stars.choices(self.project.other.get("guardian_stars"))
            star_names = {index: name for index, name in enumerate(names) if index and name}
            image = cached[1].render(
                self.type_box.currentIndex(), self.star1_box.currentIndex(), self.star2_box.currentIndex(),
                self.description.toPlainText(), scale=2, star_names=star_names)
            label.setText("")
            label.setPixmap(QPixmap.fromImage(_qimage(image.width, image.height, image.rgba)))
        except (IndexError, KeyError, OSError, ValueError, struct.error, pngio.PngError) as problem:
            label.setPixmap(QPixmap())
            label.setText(str(problem))

    def store_equip_bonus(self, cid, card):
        """Resolve an edited equip's default from the edited card itself.

        The Qt form stores the bonus before its caller replaces
        ``project.cards[cid]``.  That meant changing a card into an equip, or
        changing its inherited effect, used the *old* card when choosing the
        +500/+1000/default value.  Temporarily exposing the edited record
        gives the existing storage code the same state it will save.
        """
        previous = self.project.cards.get(cid)
        if previous is None:
            return original_store_equip_bonus(self, cid, card)
        self.project.cards[cid] = card
        try:
            return original_store_equip_bonus(self, cid, card)
        finally:
            self.project.cards[cid] = previous

    def show_equip_bonus(self):
        """Keep an equip's effective ATK/DEF values directly editable."""
        original_show_equip_bonus(self)
        equip = self.fields["type"].currentIndex() == gamedata.TYPE_EQUIP and self.project is not None
        if not equip or not self.current:
            return
        for key, points in zip(("equip_attack", "equip_defense"), self.project.equip_bonus_of(self.current)):
            box = self.fields[key]
            box.setSpecialValueText("")
            if box.value() == self.BONUS_NONE:
                box.setValue(points)

    def load_equip_bonus(self, cid):
        """Show +500/+1000/default numbers instead of the hidden sentinel."""
        if self.project is None:
            return
        for key, points in zip(("equip_attack", "equip_defense"), self.project.equip_bonus_of(cid)):
            box = self.fields[key]
            box.setSpecialValueText("")
            box.setValue(points)

    def get_effects(self, cid=None):
        cid = self.current if cid is None else cid
        if not cid or cid not in self.project.cards:
            return []
        return list(self.project.monster_effects_of(cid)[0])

    def set_effects(self, rows, keep_empty=False):
        self.project.set_monster_effects(self.current, rows, keep_empty=keep_empty)
        self._mark_dirty()
        refresh(self)

    def words(self, effect):
        normal = effects.normalize(effect, self.project.resolve)
        if normal is None:
            return "?", "(not one the game takes) " + effects.describe_raw(effect)
        return effects.when_label(normal["when"]), effects.describe(normal, self.project.card_label)

    def refresh(self):
        table = self.effects_table
        rows = get_effects(self)
        table.setRowCount(len(rows))
        for row, effect in enumerate(rows):
            when, does = words(self, effect)
            for column, value in enumerate((str(row + 1), when, does)):
                table.setItem(row, column, QTableWidgetItem(value))
        card = self.project.cards.get(self.current) if self.current else None
        inherited = bool(self.current in self.project.added and self.current and
                         "monster_effects" not in self.project.added[self.current].extra)
        retail = bool(self.current and self.current not in self.project.added)
        extra = self.project.card_extra.get(self.current, {}) if retail else {}
        none = retail and extra.get("monster_effects") == []
        if hasattr(self, "effects_none"):
            blocked = self.effects_none.blockSignals(True)
            self.effects_none.setChecked(none)
            self.effects_none.setVisible(retail and not rows)
            self.effects_none.setEnabled(bool(card and card.is_monster()))
            self.effects_none.blockSignals(blocked)
        editor = getattr(self, "_inline_effect_editor", None)
        if editor is not None and self.current and editor["frame"].property("card_id") != self.current:
            begin_effect_edit(self)
        if not card or not card.is_monster():
            note = "Only a monster can have monster effects."
        elif inherited and rows:
            note = "Its base's effects: changing them gives this card a list of its own."
        else:
            problems = effects.problems(rows, self.project.resolve)
            note = "\n".join(problems) if problems else \
                "Effects resolve in order. The game shows their result only through the card text."
        self.effects_note.setText(note)
        buttons(self)

    def buttons(self):
        card = self.project.cards.get(self.current) if self.current else None
        enabled = bool(card and card.is_monster())
        row, count = self.effects_table.currentRow(), self.effects_table.rowCount()
        chosen = 0 <= row < count
        for name, on in (("addEffect", enabled and count < effects.MAX_EFFECTS),
                         ("editEffect", enabled and chosen), ("removeEffect", enabled and chosen),
                         ("effectUp", enabled and chosen and row > 0),
                         ("effectDown", enabled and chosen and row + 1 < count)):
            self.effect_buttons[name].setEnabled(on)

    def edit_dialog(self, effect):
        """The same choices as the classic Monster effect dialog."""
        effect = effects.normalize(effect, self.project.resolve) or {
            "when": "summon", "do": "boost", "target": "self", "attack": 500}
        dialog = QDialog(self)
        dialog.setWindowTitle("Monster effect")
        body, grid = QVBoxLayout(dialog), QGridLayout()
        body.addLayout(grid)
        rows = {}

        def line(number, title, control):
            caption = QLabel(title, dialog)
            grid.addWidget(caption, number, 0)
            grid.addWidget(control, number, 1)
            rows[title] = (caption, control)
            return control

        def choices(values, labels):
            box = QComboBox(dialog)
            for value in values:
                box.addItem(labels[values.index(value)], value)
            return box

        when = line(0, "When", choices(list(effects.WHEN), list(effects.WHEN_LABELS)))
        action = line(1, "Does", QComboBox(dialog))
        target = line(2, "Whose", QComboBox(dialog))
        magic = line(3, "Magic card", QComboBox(dialog))
        for cid in effects.MAGIC:
            magic.addItem(self.project.card_label(cid), cid)
        type_box = line(4, "Only type", QComboBox(dialog))
        type_box.addItem("Any", None)
        for name in effects.TYPE_NAMES[:20]:
            type_box.addItem(name, name)
        attribute = line(5, "Only attribute", QComboBox(dialog))
        attribute.addItem("Any", None)
        for name in effects.ATTRIBUTE_NAMES:
            attribute.addItem(name, name)
        attack = line(6, "ATK", QSpinBox(dialog))
        defense = line(7, "DEF", QSpinBox(dialog))
        amount = line(8, "LP", QSpinBox(dialog))
        for box in (attack, defense):
            box.setRange(-effects.BOOST_MAX, effects.BOOST_MAX)
            box.setSingleStep(100)
        amount.setRange(1, effects.AMOUNT_MAX)
        amount.setSingleStep(100)
        hint = QLabel(dialog)
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#9aacc4")
        grid.addWidget(hint, 9, 0, 1, 2)
        problem = QLabel(dialog)
        problem.setStyleSheet("color:#f08080")
        problem.setWordWrap(True)
        body.addWidget(problem)

        when.setCurrentIndex(max(0, when.findData(effect["when"])))
        magic.setCurrentIndex(max(0, magic.findData(effect.get("card", effects.MAGIC[0]))))
        type_box.setCurrentIndex(max(0, type_box.findData(effect.get("type"))))
        attribute.setCurrentIndex(max(0, attribute.findData(effect.get("attribute"))))
        attack.setValue(effect.get("attack", 0))
        defense.setValue(effect.get("defense", 0))
        amount.setValue(effect.get("amount", 500))

        def refill(box, values, all_values, labels, wanted):
            box.blockSignals(True)
            box.clear()
            for value in values:
                box.addItem(labels[all_values.index(value)], value)
            box.setCurrentIndex(max(0, box.findData(wanted)))
            box.blockSignals(False)

        def follows():
            selected_when = when.currentData()
            hint.setText(effects.WHEN_HINTS[effects.WHEN.index(selected_when)])
            refill(action, effects.actions(selected_when), effects.DO, effects.DO_LABELS,
                   action.currentData() or effect["do"])
            selected_action = action.currentData()
            refill(target, effects.targets(selected_when, selected_action), effects.TARGET, effects.TARGET_LABELS,
                   target.currentData() or effect.get("target"))
            visible = {"When", "Does"}
            if selected_action == "magic":
                visible.add("Magic card")
            elif selected_action in effects.FILTERED:
                visible.update(("Whose", "Only type", "Only attribute"))
                if selected_action == "boost":
                    visible.update(("ATK", "DEF"))
            else:
                visible.add("LP")
            for title, (caption, control) in rows.items():
                caption.setVisible(title in visible)
                control.setVisible(title in visible)

        when.currentIndexChanged.connect(follows)
        action.currentIndexChanged.connect(follows)
        follows()
        buttons_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
                                       dialog)
        body.addWidget(buttons_box)
        buttons_box.rejected.connect(dialog.reject)

        def accept():
            result = {"when": when.currentData(), "do": action.currentData()}
            if result["do"] == "magic":
                result["card"] = magic.currentData()
            elif result["do"] in effects.FILTERED:
                result["target"] = target.currentData()
                if type_box.currentData(): result["type"] = type_box.currentData()
                if attribute.currentData(): result["attribute"] = attribute.currentData()
                if result["do"] == "boost":
                    if attack.value(): result["attack"] = attack.value()
                    if defense.value(): result["defense"] = defense.value()
            else:
                result["amount"] = amount.value()
            normal = effects.normalize(result, self.project.resolve)
            if normal is None:
                problem.setText("The game cannot use that effect. A boost needs ATK or DEF.")
                return
            dialog.setProperty("effect", normal)
            dialog.accept()

        buttons_box.accepted.connect(accept)
        return dialog.property("effect") if dialog.exec() == QDialog.DialogCode.Accepted else None

    def add(self):
        begin_effect_edit(self)

    def edit(self):
        row, rows = self.effects_table.currentRow(), get_effects(self)
        if not 0 <= row < len(rows):
            return
        begin_effect_edit(self, rows[row], row)

    def remove(self):
        row, rows = self.effects_table.currentRow(), get_effects(self)
        if 0 <= row < len(rows):
            del rows[row]; set_effects(self, rows)

    def move(self, delta):
        row, rows = self.effects_table.currentRow(), get_effects(self)
        if 0 <= row < len(rows) and 0 <= row + delta < len(rows):
            rows[row], rows[row + delta] = rows[row + delta], rows[row]
            set_effects(self, rows); self.effects_table.selectRow(row + delta)

    CardsMixin._card_effects = get_effects
    CardsMixin._build_card_effects = build_effects
    CardsMixin._build_cards = build_cards
    CardsMixin.show_card = show_card
    CardsMixin.apply_card = apply_card
    CardsMixin._render_card_text = render_full_description
    CardsMixin._store_equip_bonus = store_equip_bonus
    CardsMixin._show_equip_bonus = show_equip_bonus
    CardsMixin._load_equip_bonus = load_equip_bonus
    CardsMixin._text_icon = text_icon
    CardsMixin._set_card_effects = set_effects
    CardsMixin._effect_words = words
    CardsMixin._refresh_card_effects = refresh
    CardsMixin._card_effect_buttons = buttons
    CardsMixin._ask_card_effect = edit_dialog
    CardsMixin._add_card_effect = add
    CardsMixin._edit_card_effect = edit
    CardsMixin._remove_card_effect = remove
    CardsMixin._move_card_effect = move
