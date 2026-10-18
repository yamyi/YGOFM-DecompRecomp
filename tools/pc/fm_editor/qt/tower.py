"""The Tower page (a port of tower_tab.TowerTab's configuration, floors and
tower-only duelists; the Stage picker and story artwork are not wired up in
this build yet -- use the [scene: ...]/[left: ...]/[right: ...] syntax in the
story boxes directly)."""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

from .common import *      # noqa: F401,F403
from .common import (_qimage, _line_count, _pairs_text, _parse_pairs, _whole,
                     _card_image)      # noqa: F401
from .. import bust as bustm, duelist_rules, pngio, roster, tower, tower_art


class TowerMixin:
    @contextmanager
    def _tower_fill(self):
        """While any part of this reads as "filling": widgets wired to
        commit on change must not, or loading a floor would mark fields
        "touched" and write back half of what it just read. A counter, not a
        flag, since filling the page nests (refresh fills the floor list,
        which shows a floor, which sets fields of its own)."""
        self.tower_filling = getattr(self, "tower_filling", 0) + 1
        try:
            yield
        finally:
            self.tower_filling -= 1

    def _build_tower_page(self, page, get, controls):
        c = {
            "enabled": get(QCheckBox, "towerEnabledCheck"),
            "status": get(QLabel, "towerStatusLabel"),
            "name": get(QLineEdit, "towerNameEdit"),
            "label": get(QLineEdit, "towerMenuButtonEdit"),
            "music": get(QLineEdit, "towerMusicEdit"),
            "unlock": get(QComboBox, "towerUnlockCombo"),
            "unlock_beat": get(QLineEdit, "unlockBeatEdit"),
            "unlock_wins": get(QLineEdit, "unlockWinsEdit"),
            "unlock_story": get(QLineEdit, "unlockStoryEdit"),
            "unlock_card": get(QLineEdit, "unlockCardEdit"),
            "unlock_copies": get(QSpinBox, "unlockCopiesSpin"),
            "ending_seen": get(QCheckBox, "endingSeenCheck"),
            "on_lose": get(QComboBox, "onLoseCombo"),
            "scene": get(QComboBox, "defaultSceneCombo"),
            "dim": get(QCheckBox, "dimCharacterCheck"),
            "on_leave": get(QComboBox, "onLeaveCombo"),
            "drops": get(QComboBox, "cardDropsCombo"),
            "save_states": get(QCheckBox, "allowSaveStatesCheck"),
            "cheats": get(QCheckBox, "allowCheatsCheck"),
            "intro": get(QPlainTextEdit, "introStoryEdit"),
            "ending": get(QPlainTextEdit, "endingStoryEdit"),
            "lose": get(QPlainTextEdit, "loseStoryEdit"),
            "only_list": get(QListWidget, "towerOnlyDuelistsList"),
            "floor_tree": get(QTreeWidget, "floorsTree"),
            "floor_opponent": get(QComboBox, "floorOpponentCombo"),
            "floor_field": get(QComboBox, "floorFieldCombo"),
            "player_lp": get(QLineEdit, "playerLpEdit"),
            "opponent_lp": get(QLineEdit, "opponentLpEdit"),
            "no_fusions": get(QCheckBox, "noFusionsCheck"),
            "no_equips": get(QCheckBox, "noEquipsCheck"),
            "checkpoint": get(QCheckBox, "checkpointCheck"),
            "unlock_opponent": get(QCheckBox, "unlockOpponentCheck"),
            "unlock_opponent_hint": get(QLabel, "unlockOpponentHint"),
            "reward_cards": get(QLineEdit, "rewardCardsEdit"),
            "reward_starchips": get(QLineEdit, "rewardStarchipsEdit"),
            "reward_unlocks": get(QLineEdit, "rewardUnlocksEdit"),
            "reward_unlock_pick": get(QComboBox, "rewardUnlockDuelistCombo"),
            "floor_deck": get(QPlainTextEdit, "floorDeckEdit"),
            "before_duel": get(QPlainTextEdit, "beforeDuelStoryEdit"),
            "after_win": get(QPlainTextEdit, "afterWinStoryEdit"),
            "stage_scene": get(QComboBox, "stageSceneCombo"),
            "stage_character": get(QComboBox, "stageCharacterCombo"),
            "stage_side": get(QComboBox, "stageSideCombo"),
            "stage_expression": get(QSpinBox, "stageExpressionSpin"),
            "stage_flip": get(QCheckBox, "stageFlipCheck"),
            "stage_duelist": get(QComboBox, "stageDuelistCombo"),
            "stage_bust_expression": get(QComboBox, "stageBustExpressionCombo"),
            "scene_preview": get(QLabel, "stageScenePreview"),
            "character_preview": get(QLabel, "stageCharacterPreview"),
            "only_keys": [],
        }
        controls.update(c)
        self.tower_floors = []
        self.tower_current = None
        self.tower_kept = {}
        self.tower_written = None
        self.tower_shown = None
        self.tower_top_shown = None
        self.tower_unlock_touched = False
        self.tower_guide_dialog = None
        self.tower_filling = 0
        self.tower_art_cache = {}
        self.tower_bust_shown = False
        self.tower_last_story = "intro"      # which story box the Stage inserts into

        get(QComboBox, "defaultSceneCombo").addItems(list(tower.SCENE_NAMES))
        get(QComboBox, "defaultSceneCombo").setCurrentText("")

        # The Stage: scenes, the campaign's characters and a duelist's own
        # bust, inserted as [scene: ...]/[left: ...]/[right: ...] before the
        # line the cursor is on, in whichever story box was last focused.
        scenes = list(tower.SCENE_NAMES) + [str(m * 100 + i) for m, count in ((1, 42), (2, 13)) for i in range(count)]
        c["stage_scene"].addItems(scenes)
        c["stage_scene"].setCurrentText(tower.SCENE_NAMES[tower.SCENE_DEFAULT])
        characters = [str(n) for n in range(1, tower.CHARACTERS + 1) if n not in tower.EMPTY_CHARACTERS]
        c["stage_character"].addItems(characters)
        c["stage_character"].setCurrentText("1")
        for key in ("intro", "ending", "lose", "before_duel", "after_win"):
            c[key].installEventFilter(self)
        c["stage_scene"].currentTextChanged.connect(self._tower_preview)
        c["stage_character"].currentTextChanged.connect(lambda *_: self._tower_show_kind(False))
        c["stage_duelist"].currentTextChanged.connect(
            lambda *_: (self._tower_bust_expressions(), self._tower_show_kind(True)))
        c["stage_bust_expression"].currentTextChanged.connect(lambda *_: self._tower_show_kind(True))
        get(QPushButton, "insertSceneButton").clicked.connect(
            lambda: self._tower_insert(f"[scene: {c['stage_scene'].currentText()}]"))
        get(QPushButton, "scenePngButton").clicked.connect(self._tower_scene_png)
        get(QPushButton, "insertCharacterButton").clicked.connect(self._tower_character)
        get(QPushButton, "insertOpponentButton").clicked.connect(
            lambda: self._tower_insert(f"[{c['stage_side'].currentText()}: opponent]"))
        get(QPushButton, "insertNobodyButton").clicked.connect(
            lambda: self._tower_insert(f"[{c['stage_side'].currentText()}: none]"))
        get(QPushButton, "characterPngButton").clicked.connect(self._tower_character_png)
        get(QPushButton, "insertBustButton").clicked.connect(self._tower_bust)

        get(QPushButton, "guideButton").clicked.connect(self._tower_show_guide)
        get(QPushButton, "exampleButton").clicked.connect(self._tower_start_example)
        c["enabled"].toggled.connect(self._tower_toggle)
        c["unlock_opponent"].toggled.connect(self._tower_unlock_touched)
        c["reward_unlocks"].setReadOnly(True)
        get(QPushButton, "addRewardUnlockButton").clicked.connect(self._tower_add_unlock)
        get(QPushButton, "removeRewardUnlockButton").clicked.connect(self._tower_remove_unlock)
        get(QPushButton, "addFloorButton").clicked.connect(self._add_tower_floor)
        get(QPushButton, "removeFloorButton").clicked.connect(self._remove_tower_floor)
        get(QPushButton, "moveFloorUpButton").clicked.connect(lambda: self._move_tower_floor(-1))
        get(QPushButton, "moveFloorDownButton").clicked.connect(lambda: self._move_tower_floor(1))
        c["floor_tree"].itemSelectionChanged.connect(self._tower_pick_floor)
        c["only_list"].itemChanged.connect(self._commit_tower)

        # Every other field commits on change, as the Tk tab's FocusOut/
        # Return/<<ComboboxSelected>>/checkbutton "command" bindings do.
        for key in ("name", "label", "music", "unlock_beat", "unlock_wins", "unlock_story", "unlock_card",
                    "player_lp", "opponent_lp", "reward_cards", "reward_starchips"):
            c[key].textChanged.connect(self._commit_tower)
        for key in ("unlock_copies",):
            c[key].valueChanged.connect(self._commit_tower)
        for key in ("ending_seen", "dim", "no_fusions", "no_equips", "checkpoint", "save_states", "cheats"):
            c[key].toggled.connect(self._commit_tower)
        for key in ("unlock", "on_lose", "scene", "on_leave", "drops", "floor_opponent", "floor_field"):
            c[key].currentTextChanged.connect(self._commit_tower)
        for key in ("intro", "ending", "lose", "floor_deck", "before_duel", "after_win"):
            c[key].textChanged.connect(self._commit_tower)

    # --- the tower's own settings ------------------------------------------------------

    @staticmethod
    def _tower_drops_shown(value) -> str:
        """The drops as the game reads them: 1-99, "player", else the default."""
        if isinstance(value, str) and value.lower() == "player":
            return "player"
        if isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= tower.DROPS_MAX:
            return str(value)
        return str(tower.DROPS_DEFAULT)

    def _tower_top_form(self) -> tuple:
        c = self.workspace_controls["Tower"]
        return (c["name"].text(), c["label"].text(), c["music"].text().strip(), c["unlock"].currentText(),
               c["unlock_beat"].text().strip(), c["unlock_wins"].text().strip(), c["unlock_story"].text().strip(),
               c["unlock_card"].text().strip(), c["unlock_copies"].value(), c["ending_seen"].isChecked(),
               c["on_lose"].currentText(), c["on_leave"].currentText(), c["drops"].currentText().strip(),
               c["save_states"].isChecked(), c["cheats"].isChecked(), c["scene"].currentText().strip(),
               c["dim"].isChecked(), c["intro"].toPlainText(), c["ending"].toPlainText(), c["lose"].toPlainText())

    def _refresh_tower(self):
        c = self.workspace_controls.get("Tower")
        if not c or self.project is None:
            return
        with self._tower_fill():
            value = self.project.other.get("tower")
            written = value if isinstance(value, dict) else {}
            c["enabled"].setChecked(value is not None)
            self.tower_written = value
            self.tower_kept = {k: tower.copy(v) for k, v in written.items() if k not in tower.TOWER_KEYS}
            c["name"].setText(str(written.get("name", "")))
            c["label"].setText(str(written.get("label", "")))
            c["music"].setText("" if written.get("music") is None else str(written["music"]))
            unlock = written.get("unlock")
            c["unlock"].setCurrentText("conditions" if isinstance(unlock, dict) else
                                       unlock if unlock in ("always", "after_ending") else "always")
            conditions = unlock if isinstance(unlock, dict) else {}
            for key, widget in (("beat", c["unlock_beat"]), ("wins", c["unlock_wins"]),
                                ("story", c["unlock_story"]), ("card", c["unlock_card"])):
                widget.setText("" if conditions.get(key) is None else str(conditions[key]))
            copies = conditions.get("copies")
            c["unlock_copies"].setValue(copies if isinstance(copies, int) and not isinstance(copies, bool)
                                        and 0 <= copies <= 250 else 0)
            c["ending_seen"].setChecked(conditions.get("after_ending") is True)
            c["on_lose"].setCurrentText(written.get("on_lose") if written.get("on_lose") in ("checkpoint", "restart")
                                        else "checkpoint")
            scene = written.get("scene")
            number = tower.scene_number(scene) if scene is not None else None
            c["scene"].setCurrentText("" if scene is None else tower.scene_label(number) if number is not None
                                      else str(scene))
            c["dim"].setChecked(written.get("dim") is True)
            leave = str(written.get("on_leave", "resume")).lower()
            c["on_leave"].setCurrentText(leave if leave in tower.ON_LEAVE else "resume")
            c["drops"].setCurrentText(self._tower_drops_shown(written.get("drops")))
            c["save_states"].setChecked(written.get("save_states") is not False)
            c["cheats"].setChecked(written.get("cheats") is not False)
            for key, widget in (("intro", c["intro"]), ("ending", c["ending"]), ("lose", c["lose"])):
                widget.setPlainText(tower.story_text(written.get(key)))
            floors = written.get("floors")
            self.tower_floors = [tower.copy(f) if isinstance(f, dict) else f for f in floors] \
                if isinstance(floors, list) else []
            self.tower_current = 0 if self.tower_floors else None
            names = duelist_rules.references(self.project)
            for key in ("floor_opponent", "reward_unlock_pick"):
                c[key].clear()
                c[key].addItems(names)
            c["floor_opponent"].setCurrentText("")
            only_keys = [e.key for e in roster.copies(self.project)]
            identities = [roster.identity(self.project, roster.find(self.project, key)) for key in only_keys]
            self._populate_checkable_list(c["only_list"], identities)
            c["only_keys"] = only_keys
            marked = set(tower.tower_only(self.project))
            for index, key in enumerate(only_keys):
                if key in marked:
                    c["only_list"].item(index).setCheckState(Qt.CheckState.Checked)
        self._fill_tower_floors()
        self._show_tower_floor()
        self.tower_top_shown = self._tower_top_form()
        self.tower_art_cache.clear()
        self._tower_fill_bust_duelists()
        self._tower_preview()
        self._tower_report()

    def _tower_toggle(self):
        if self.tower_filling or self.project is None:
            return
        c = self.workspace_controls["Tower"]
        if c["enabled"].isChecked() and not self.tower_floors:
            self.tower_floors = [tower.new_floor()]
            self.tower_current = 0
            self._fill_tower_floors()
            self._show_tower_floor()
        self._commit_tower()

    def _tower_start_example(self):
        if self.project is None:
            return
        if self.project.other.get("tower") is not None and QMessageBox.question(
                self, "Start from an example", "Replace this mod's tower with the example?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        self.project.other["tower"] = tower.example_tower()
        self._refresh_tower()
        self._mark_dirty()

    def _tower_show_guide(self):
        if self.tower_guide_dialog is not None and self.tower_guide_dialog.isVisible():
            self.tower_guide_dialog.raise_()
            return
        dialog = QDialog(self)
        self.tower_guide_dialog = dialog
        dialog.setWindowTitle("How to build a tower")
        dialog.resize(640, 560)
        layout = QVBoxLayout(dialog)
        text = QTextEdit()
        text.setReadOnly(True)
        html = "".join(f"<p><b>{head}</b><br>{body}</p>" for head, body in tower.GUIDE)
        html += "<p>Every key, with an example: notes/tower-mode.md.</p>"
        text.setHtml(html)
        layout.addWidget(text)
        buttons = QHBoxLayout()
        start = QPushButton("Start from an example")
        start.clicked.connect(self._tower_start_example)
        close = QPushButton("Close")
        close.clicked.connect(dialog.close)
        buttons.addWidget(start)
        buttons.addStretch(1)
        buttons.addWidget(close)
        layout.addLayout(buttons)
        dialog.show()

    def _tower_build(self):
        """The tower as the manifest writes it, over the tower's own keys
        the form does not show. A port of tower_tab.py's _build()."""
        c = self.workspace_controls["Tower"]
        if not c["enabled"].isChecked():
            return None
        written = self.tower_written if isinstance(self.tower_written, dict) else None
        if written is not None and self.tower_top_shown == self._tower_top_form():
            out = tower.copy(written)
            if "floors" in out or self.tower_floors:
                out["floors"] = [tower.copy(f) for f in self.tower_floors]
            return out
        out = {}
        for key, widget in (("name", c["name"]), ("label", c["label"])):
            text = widget.text().strip()
            if text:
                out[key] = text
        music = c["music"].text().strip()
        if music:
            try:
                out["music"] = int(music, 0)
            except ValueError:
                out["music"] = music
        kind = c["unlock"].currentText()
        if kind == "after_ending":
            out["unlock"] = "after_ending"
        elif kind == "conditions":
            conditions = {}
            if c["ending_seen"].isChecked():
                conditions["after_ending"] = True
            for key, widget in (("beat", c["unlock_beat"]), ("wins", c["unlock_wins"]),
                                ("story", c["unlock_story"]), ("card", c["unlock_card"])):
                text = widget.text().strip()
                if text:
                    conditions[key] = int(text) if text.isdigit() else text
            copies = c["unlock_copies"].value()
            if copies:
                conditions["copies"] = copies
            out["unlock"] = conditions
        if c["on_lose"].currentText() == "restart":
            out["on_lose"] = "restart"
        scene = c["scene"].currentText().strip()
        if scene:
            old = written.get("scene") if written is not None else None
            number = tower.scene_number(scene)
            out["scene"] = old if old is not None and tower.scene_number(old) == number else \
                number if isinstance(number, int) and scene.isdigit() else scene
        if c["dim"].isChecked():
            out["dim"] = True
        if c["on_leave"].currentText() in ("checkpoint", "restart"):
            out["on_leave"] = c["on_leave"].currentText()
        drops = c["drops"].currentText().strip().lower()
        old_drops = written.get("drops") if written is not None else None
        if drops == "player":
            out["drops"] = old_drops if str(old_drops).lower() == "player" else "player"
        elif drops.isdigit() and 1 <= int(drops) <= tower.DROPS_MAX and int(drops) != tower.DROPS_DEFAULT:
            out["drops"] = int(drops)
        c["drops"].blockSignals(True)
        c["drops"].setCurrentText(self._tower_drops_shown(out.get("drops")))
        c["drops"].blockSignals(False)
        for key, widget in (("save_states", c["save_states"]), ("cheats", c["cheats"])):
            if not widget.isChecked():
                out[key] = False
        for key, widget in (("intro", c["intro"]), ("ending", c["ending"]), ("lose", c["lose"])):
            text = widget.toPlainText()
            value = tower.story_value(text)
            if value is not None:
                old = written.get(key) if written is not None else None
                out[key] = old if tower.same_story(old, text) else value
        out["floors"] = [tower.copy(f) for f in self.tower_floors]
        out.update(self.tower_kept)
        return out

    def _commit_tower(self, *_args, stored=False):
        # *_args: this is wired directly to several signals (toggled,
        # textChanged, valueChanged, currentTextChanged, itemChanged), each
        # of which calls it with its own emitted value; only an explicit
        # keyword call (remove/move's stored=True) is meant to reach `stored`.
        if self.project is None or self.tower_filling:
            return True
        c = self.workspace_controls["Tower"]
        if not stored:
            self._store_tower_floor()
        before = self.project.other.get("tower")
        after = self._tower_build()
        # Untouched, the tower stays as the mod wrote it: every edit commits,
        # and rebuilding it would reorder its keys and mark the mod changed.
        if after is not None and before is not None and tower.copy(after) == before:
            after = before
        if after is None:
            self.project.other.pop("tower", None)
        else:
            self.project.other["tower"] = after
        changed = after != before
        only_list, only_keys = c["only_list"], c.get("only_keys", [])
        selected = {only_keys[i] for i in range(only_list.count())
                   if only_list.item(i).checkState() == Qt.CheckState.Checked} if only_keys else set()
        for key in only_keys:
            changed = tower.set_tower_only(self.project, key, key in selected) or changed
        self._tower_report()
        if changed:
            self._mark_dirty()
        return True

    def _tower_report(self):
        c = self.workspace_controls.get("Tower")
        if not c or self.project is None:
            return
        problems = tower.check(self.project.other.get("tower"), lambda name: roster.named(self.project, name),
                               lambda name: self.project.resolve(name),
                               lambda name: roster.bust_of(self.project, roster.named(self.project, name)),
                               lambda name: roster.shows_bust(self.project, roster.named(self.project, name)))
        c["status"].setText("\n".join(f"{level}: {where}: {message}" for level, where, message in problems))
        c["status"].setStyleSheet("color:#ff8f87" if problems else "color:#7fd49b")
        tree = c["floor_tree"]
        for index in range(tree.topLevelItemCount()):
            item = tree.topLevelItem(index)
            n = item.data(0, Qt.ItemDataRole.UserRole)
            if n is not None and n < len(self.tower_floors) and isinstance(self.tower_floors[n], dict):
                for column, value in enumerate(self._tower_floor_row(self.tower_floors[n]), start=1):
                    item.setText(column, value)

    # --- the Stage: pickers that write a story's bracketed lines -----------------------

    def _tower_photo(self, key, image, size):
        if image is None:
            return None
        if key not in self.tower_art_cache:
            pixmap = QPixmap.fromImage(_qimage(image.width, image.height, image.rgba))
            self.tower_art_cache[key] = pixmap.scaled(QSize(*size), Qt.AspectRatioMode.KeepAspectRatio,
                                                      Qt.TransformationMode.SmoothTransformation)
        return self.tower_art_cache[key]

    def _tower_show_kind(self, bust: bool):
        """The picture beside the pickers: the campaign character chosen, or
        the duelist's bust in the expression chosen."""
        self.tower_bust_shown = bust
        self._tower_preview()

    def _tower_bust_names(self) -> dict:
        """{the name a story uses: the duelist} of every duelist with a bust."""
        out = {}
        if self.project is None:
            return out
        for d in range(1, len(self.project.pools)):
            if roster.bust_of(self.project, d) is not None:
                out[roster.shown_name(self.project, d)] = d
        for e in roster.copies(self.project):
            if e.bust is not None:
                out[roster.identity(self.project, e)] = e
        return out

    def _tower_fill_bust_duelists(self):
        c = self.workspace_controls["Tower"]
        names = list(self._tower_bust_names())
        current = c["stage_duelist"].currentText()
        c["stage_duelist"].blockSignals(True)
        c["stage_duelist"].clear()
        c["stage_duelist"].addItems(names)
        if names:
            c["stage_duelist"].setCurrentText(current if current in names else names[0])
        c["stage_duelist"].blockSignals(False)
        self._tower_bust_expressions()

    def _tower_bust_expressions(self):
        c = self.workspace_controls["Tower"]
        who = self._tower_bust_names().get(c["stage_duelist"].currentText())
        b = roster.bust_of(self.project, who) if who is not None else None
        names = [e.name for e in bustm.order(b)] if b is not None else []
        current = c["stage_bust_expression"].currentText()
        c["stage_bust_expression"].blockSignals(True)
        c["stage_bust_expression"].clear()
        c["stage_bust_expression"].addItems(names)
        if names:
            c["stage_bust_expression"].setCurrentText(current if current in names else names[0])
        c["stage_bust_expression"].blockSignals(False)
        if self.tower_bust_shown:
            self._tower_preview()

    def _tower_bust(self):
        c = self.workspace_controls["Tower"]
        who, expression = c["stage_duelist"].currentText().strip(), c["stage_bust_expression"].currentText().strip()
        if not who:
            return
        words = who + (f" expression {expression}" if expression and " " not in expression else
                       f' expression "{expression}"' if expression else "")
        self._tower_insert(f"[{c['stage_side'].currentText()}: {words}]")

    def _tower_preview(self, *_args):
        """The chosen scene and character, made from the player's disc now
        (tower_art.py) and kept in memory; nothing of the disc's is written."""
        c = self.workspace_controls.get("Tower")
        if not c:
            return
        wa = self.files.wa if getattr(self, "files", None) is not None else None
        if self.tower_bust_shown:
            who = self._tower_bust_names().get(c["stage_duelist"].currentText())
            b = roster.bust_of(self.project, who) if who is not None else None
            e = bustm.find(b, c["stage_bust_expression"].currentText()) if b is not None else None
            image = bustm.picture(e.image) if e is not None else None
            pixmap = self._tower_photo(("bust", e.image), image, (96, 96)) if image is not None else None
            c["character_preview"].setPixmap(pixmap if pixmap is not None else QPixmap())
            c["character_preview"].setText("" if pixmap is not None else "(none)")
        if wa is None:
            return
        number = tower.scene_number(c["stage_scene"].currentText())
        if isinstance(number, int):
            scene = (number // 100) << 8 | (number % 100 // 10) << 4 | number % 10
            pixmap = self._tower_photo(("scene", number), tower_art.scene_image(wa, scene), (160, 80))
            c["scene_preview"].setPixmap(pixmap if pixmap is not None else QPixmap())
            c["scene_preview"].setText("" if pixmap is not None else "(none)")
        if self.tower_bust_shown:
            return
        text = c["stage_character"].currentText()
        character = int(text) if text.isdigit() else 0
        pixmap = self._tower_photo(("character", character), tower_art.character_image(wa, character), (96, 96))
        c["character_preview"].setPixmap(pixmap if pixmap is not None else QPixmap())
        c["character_preview"].setText("" if pixmap is not None else "(none)")

    def _tower_insert(self, directive: str):
        """A bracketed line before the line the cursor is on, in the story
        last clicked."""
        c = self.workspace_controls["Tower"]
        widget = c.get(self.tower_last_story)
        if widget is None:
            return
        cursor = widget.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
        cursor.insertText(directive + "\n")
        widget.setTextCursor(cursor)
        self._commit_tower()

    def _tower_character(self):
        c = self.workspace_controls["Tower"]
        expression = str(c["stage_expression"].value())
        words = c["stage_character"].currentText() + (f" expression {expression}" if expression != "0" else "")
        self._tower_insert(f"[{c['stage_side'].currentText()}: {words}]")

    def _tower_mod_png(self, title: str):
        """A PNG for the mod: its path inside the mod's folder, or, from
        elsewhere, copied into the mod's tower/ when it is saved."""
        path, _ = QFileDialog.getOpenFileName(self, title, "", "PNG pictures (*.png);;All files (*)")
        if not path or self.project is None:
            return None
        return self._tower_use_png(path)

    def _tower_use_png(self, path):
        try:
            data = Path(path).read_bytes()
            pngio.decode(data)
        except (OSError, pngio.PngError) as problem:
            QMessageBox.critical(self, "Picture", f"{path} cannot be used: {problem}")
            return None
        source = getattr(self.project, "source_dir", None)
        if source:
            try:
                return Path(path).resolve().relative_to(Path(source).resolve()).as_posix()
            except ValueError:
                pass
        stem, n = Path(path).stem, 1
        name = f"tower/{stem}.png"
        while name in self.project.files and self.project.files[name] != data:      # another picture's name
            n += 1
            name = f"tower/{stem}-{n}.png"
        self.project.files[name] = data
        return name

    def _tower_scene_png(self):
        name = self._tower_mod_png("A scene for the story (drawn at 320 x 160)")
        if name:
            self._tower_insert(f"[scene: {name}]")

    def _tower_character_png(self):
        c = self.workspace_controls["Tower"]
        name = self._tower_mod_png("A character for the story (up to 256 x 256, standing on the box)")
        if name:
            flip = " flip" if c["stage_flip"].isChecked() else ""
            self._tower_insert(f"[{c['stage_side'].currentText()}: {name}{flip}]")

    # --- the tower's own duelists -------------------------------------------------------

    def _tower_add_unlock(self):
        c = self.workspace_controls["Tower"]
        pick = c["reward_unlock_pick"].currentText().strip()
        if not pick:
            return
        names = [n.strip() for n in c["reward_unlocks"].text().split(",") if n.strip()]
        if pick not in names:
            names.append(pick)
        c["reward_unlocks"].setText(", ".join(names))
        self._commit_tower()

    def _tower_remove_unlock(self):
        c = self.workspace_controls["Tower"]
        names = [n.strip() for n in c["reward_unlocks"].text().split(",") if n.strip()]
        c["reward_unlocks"].setText(", ".join(names[:-1]))
        self._commit_tower()

    # --- the floors list --------------------------------------------------------------

    @staticmethod
    def _tower_floor_row(floor) -> tuple:
        rules = []
        if floor.get("no_fusions") is True:
            rules.append("no fusions")
        if floor.get("no_equips") is True:
            rules.append("no equips")
        if floor.get("life_points") is not None:
            rules.append("LP")
        if floor.get("deck") is not None:
            rules.append("deck")
        if floor.get("checkpoint") is True:
            rules.append("checkpoint")
        field = tower.terrain_of(floor.get("field"))
        return (str(floor.get("duelist", "")),
               tower.TERRAINS[field] if field is not None else str(floor.get("field")), ", ".join(rules))

    def _fill_tower_floors(self):
        c = self.workspace_controls["Tower"]
        tree = c["floor_tree"]
        with self._tower_fill():
            tree.clear()
            for index, floor in enumerate(self.tower_floors):
                row = self._tower_floor_row(floor) if isinstance(floor, dict) else ("(not an object)", "", "")
                item = QTreeWidgetItem([str(index + 1), *row])
                item.setData(0, Qt.ItemDataRole.UserRole, index)
                tree.addTopLevelItem(item)
            if self.tower_current is not None and self.tower_current < len(self.tower_floors):
                tree.setCurrentItem(tree.topLevelItem(self.tower_current))

    def _tower_duelist_of_floor(self):
        c = self.workspace_controls["Tower"]
        text = c["floor_opponent"].currentText().strip()
        return roster.named(self.project, text) if self.project is not None and text else None

    def _tower_unlock_default(self) -> bool:
        """Whether a floor that does not say so lets its opponent into Free
        Duel: a duelist the mod adds as the tower's own, yes; any other, no."""
        e = self._tower_duelist_of_floor()
        return e is not None and not isinstance(e, int) and getattr(e, "extra", {}).get("tower_only") is True

    def _tower_unlock_touched(self):
        if self.tower_filling:
            return
        self.tower_unlock_touched = True
        self._commit_tower()

    def _tower_unlock_note(self):
        c = self.workspace_controls["Tower"]
        e = self._tower_duelist_of_floor()
        if e is None:
            text = ""
        elif not isinstance(e, int) and e.extra.get("tower_only") is True:
            text = "This opponent is the tower's own: hidden in Free Duel until it is beaten (if ticked)."
        else:
            text = "Ticked, beating it puts this opponent on the Free Duel grid."
        c["unlock_opponent_hint"].setText(text)

    def _tower_floor_form(self) -> tuple:
        c = self.workspace_controls["Tower"]
        return (c["floor_opponent"].currentText().strip(), c["floor_field"].currentText(),
               c["player_lp"].text().strip(), c["opponent_lp"].text().strip(), c["no_fusions"].isChecked(),
               c["no_equips"].isChecked(), c["checkpoint"].isChecked(), c["unlock_opponent"].isChecked(),
               c["reward_cards"].text().strip(), c["reward_starchips"].text().strip(),
               c["reward_unlocks"].text().strip(), c["floor_deck"].toPlainText(), c["before_duel"].toPlainText(),
               c["after_win"].toPlainText())

    def _show_tower_floor(self):
        c = self.workspace_controls["Tower"]
        floor = self.tower_floors[self.tower_current] if self.tower_current is not None and \
            self.tower_current < len(self.tower_floors) else {}
        floor = floor if isinstance(floor, dict) else {}
        with self._tower_fill():
            c["floor_opponent"].setCurrentText(str(floor.get("duelist", "")))
            field = tower.terrain_of(floor.get("field"))
            c["floor_field"].setCurrentText(tower.TERRAINS[field] if field is not None else "none")
            lp = floor.get("life_points")
            sides = lp if isinstance(lp, dict) else {"player": lp, "opponent": lp} if lp is not None else {}
            c["player_lp"].setText("" if sides.get("player") is None else str(sides["player"]))
            c["opponent_lp"].setText("" if sides.get("opponent") is None else str(sides["opponent"]))
            c["no_fusions"].setChecked(floor.get("no_fusions") is True)
            c["no_equips"].setChecked(floor.get("no_equips") is True)
            c["checkpoint"].setChecked(floor.get("checkpoint") is True)
            reward = floor.get("reward") if isinstance(floor.get("reward"), dict) else {}
            cards = []
            for key in ("card", "cards"):
                value = reward.get(key)
                cards += value if isinstance(value, list) else [] if value is None else [value]
            c["reward_cards"].setText(tower.names_text(cards))
            c["reward_starchips"].setText("" if reward.get("starchips") is None else str(reward["starchips"]))
            c["reward_unlocks"].setText(tower.names_text(reward.get("unlock_duelist")))
            self.tower_unlock_touched = False
            c["unlock_opponent"].setChecked(
                floor["unlock_opponent"] is True if isinstance(floor.get("unlock_opponent"), bool)
                else self._tower_unlock_default())
            self._tower_unlock_note()
            c["floor_deck"].setPlainText(tower.deck_text(floor.get("deck")))
            c["before_duel"].setPlainText(tower.story_text(floor.get("before")))
            c["after_win"].setPlainText(tower.story_text(floor.get("after")))
        self.tower_shown = (self.tower_current, self._tower_floor_form())

    def _read_tower_floor(self) -> dict:
        """The form's floor, over the floor's own keys the form does not
        show. A port of tower_tab.py's _read_floor()."""
        c = self.workspace_controls["Tower"]
        old = self.tower_floors[self.tower_current] if self.tower_current is not None and \
            self.tower_current < len(self.tower_floors) else {}
        old = old if isinstance(old, dict) else {}
        floor = {k: tower.copy(v) for k, v in old.items() if k not in tower.FLOOR_KEYS}
        duelist = c["floor_opponent"].currentText().strip()
        floor["duelist"] = int(duelist) if duelist.isdigit() else duelist
        field = c["floor_field"].currentText()
        if field and field != "none":
            same = "field" in old and tower.terrain_of(old["field"]) == tower.terrain_of(field)
            floor["field"] = old["field"] if same else field
        sides = {}
        for side, widget in (("player", c["player_lp"]), ("opponent", c["opponent_lp"])):
            text = widget.text().strip()
            if text:
                sides[side] = int(text) if text.isdigit() else text
        if sides:
            floor["life_points"] = sides["player"] if len(sides) == 2 and sides["player"] == sides["opponent"] \
                else sides
        for key, widget in (("no_fusions", c["no_fusions"]), ("no_equips", c["no_equips"])):
            if widget.isChecked():
                floor[key] = True
        deck = tower.deck_value(c["floor_deck"].toPlainText())
        if deck is not None:
            floor["deck"] = deck if old.get("deck") is None or tower.deck_value(tower.deck_text(old["deck"])) != deck \
                else old["deck"]
        reward = {k: tower.copy(v) for k, v in (old.get("reward") or {}).items()
                 if isinstance(old.get("reward"), dict) and k not in tower.REWARD_KEYS}
        cards = tower.names_value(c["reward_cards"].text())
        if cards is not None:
            reward["cards"] = cards if isinstance(cards, list) else [cards]
        chips = c["reward_starchips"].text().strip()
        if chips:
            reward["starchips"] = int(chips) if chips.isdigit() else chips
        duelists = tower.names_value(c["reward_unlocks"].text())
        if duelists is not None:
            reward["unlock_duelist"] = duelists
        if reward:
            floor["reward"] = reward
        if c["checkpoint"].isChecked():
            floor["checkpoint"] = True
        # Written when the mod had it or the box was ticked or unticked by
        # hand; else the box follows the opponent's default (a tower-only
        # one unlocks, any other not) as the opponent changes.
        unlock = c["unlock_opponent"].isChecked()
        if "unlock_opponent" in old or self.tower_unlock_touched:
            floor["unlock_opponent"] = unlock
        else:
            c["unlock_opponent"].blockSignals(True)
            c["unlock_opponent"].setChecked(self._tower_unlock_default())
            c["unlock_opponent"].blockSignals(False)
            self._tower_unlock_note()
        for key, widget in (("before", c["before_duel"]), ("after", c["after_win"])):
            text = widget.toPlainText()
            value = tower.story_value(text)
            if value is not None:
                floor[key] = old[key] if tower.same_story(old.get(key), text) else value
        order = list(tower.FLOOR_KEYS)
        return {**{k: floor[k] for k in order if k in floor}, **{k: v for k, v in floor.items() if k not in order}}

    def _store_tower_floor(self):
        if self.tower_current is not None and self.tower_current < len(self.tower_floors):
            if self.tower_shown == (self.tower_current, self._tower_floor_form()):
                return
            self.tower_floors[self.tower_current] = self._read_tower_floor()
            self.tower_shown = (self.tower_current, self._tower_floor_form())

    def _tower_pick_floor(self):
        if self.tower_filling:
            return
        c = self.workspace_controls["Tower"]
        items = c["floor_tree"].selectedItems()
        if not items:
            return
        index = items[0].data(0, Qt.ItemDataRole.UserRole)
        if index == self.tower_current:
            return
        self._commit_tower()
        self.tower_current = index
        self._show_tower_floor()

    def goto_tower_floor(self, index: int):
        """Problems -> Tower: select the floor an issue is about, as
        _tower_pick_floor does for a click."""
        c = self.workspace_controls.get("Tower")
        if not c or not 0 <= index < c["floor_tree"].topLevelItemCount():
            return
        item = c["floor_tree"].topLevelItem(index)
        if item is not None:
            c["floor_tree"].setCurrentItem(item)

    def _add_tower_floor(self):
        if self.project is None:
            return
        c = self.workspace_controls["Tower"]
        self._store_tower_floor()
        if len(self.tower_floors) >= tower.TOWER_MAX_FLOORS:
            c["status"].setText(f"A tower has at most {tower.TOWER_MAX_FLOORS} floors")
            return
        self.tower_floors.append(tower.new_floor())
        self.tower_current = len(self.tower_floors) - 1
        if not c["enabled"].isChecked():
            c["enabled"].setChecked(True)      # floors is non-empty now: _tower_toggle only re-commits
        self._fill_tower_floors()
        self._show_tower_floor()
        self._commit_tower()

    def _remove_tower_floor(self):
        if self.tower_current is None or self.tower_current >= len(self.tower_floors):
            return
        del self.tower_floors[self.tower_current]
        self.tower_current = min(self.tower_current, len(self.tower_floors) - 1) if self.tower_floors else None
        self._fill_tower_floors()
        self._show_tower_floor()
        self._commit_tower(stored=True)

    def _move_tower_floor(self, step):
        if self.tower_current is None:
            return
        self._store_tower_floor()
        to = self.tower_current + step
        if not 0 <= to < len(self.tower_floors):
            return
        self.tower_floors[self.tower_current], self.tower_floors[to] = \
            self.tower_floors[to], self.tower_floors[self.tower_current]
        self.tower_current = to
        if self.tower_shown is not None:
            self.tower_shown = (to, self.tower_shown[1])      # the same floor, still in the form
        self._fill_tower_floors()
        self._commit_tower(stored=True)
