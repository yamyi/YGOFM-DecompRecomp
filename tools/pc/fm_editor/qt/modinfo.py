"""The Mod info page."""
from __future__ import annotations

from .common import *      # noqa: F401,F403
from .common import (_qimage, _line_count, _pairs_text, _parse_pairs, _whole,
                     _card_image)      # noqa: F401


class ModinfoMixin:
    SETTING_TYPES = ("bool", "int", "choice", "key")
    SETTING_KIND_HINTS = {"bool": "Default: 1 is on, 0 off.",
                          "int": "A whole number from Lowest to Highest (0-100 when left empty).",
                          "choice": "Default: the number of the choice, from 0.",
                          "key": "Default: a pad-button mask (Select 1 ... Square 32768)."}

    def _style_mod_info_page(self, page, get, controls):
        """The page's own look: the two JSON boxes as panels, written in the
        fixed-width face the Tk window writes them in, and the slack to them
        rather than to a label."""
        boxes = page.layout().itemAt(3).layout()
        page_layout = page.layout()
        for index in range(page_layout.count()):
            page_layout.setStretch(index, 1 if page_layout.itemAt(index).layout() is boxes else 0)
        # pageSummaryLabel is not reachable by name: the form gives it the
        # objectName "muted" so the window's own stylesheet draws it.
        for label in ("modSettingsHint", "modOtherHint"):
            get(QLabel, label).setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        for title in ("modSettingsEditLabel", "modOtherEditLabel"):
            get(QLabel, title).setStyleSheet("font-size:16px;font-weight:650;color:#f3f7fc")
        for muted in ("modSettingsHint", "modOtherHint", "modFolderLabel", "modApiLabel", "modSettingsListHint"):
            get(QLabel, muted).setStyleSheet("color:#9aacc4")
        for panel in ("modSettingsPanel", "modOtherPanel"):
            get(QFrame, panel).setStyleSheet(
                f"QFrame#{panel} {{ background:#101b2b; border:1px solid #26374c; border-radius:10px; }}")
        mono = QFont("Monospace", 10)
        mono.setStyleHint(QFont.StyleHint.TypeWriter)
        for box in ("settings", "other"):
            controls[box].setFont(mono)
        controls["settings_tree"].header().setStretchLastSection(False)
        controls["settings_tree"].header().resizeSection(0, 110)
        controls["settings_tree"].header().resizeSection(1, 150)
        controls["settings_tree"].header().resizeSection(2, 60)
        controls["settings_tree"].header().resizeSection(3, 90)
    def _shown_other(self) -> dict:
        """The keys the Other box shows: all but the editor's own pages'."""
        return {key: value for key, value in self.project.other.items()
                if key not in self.MOD_INFO_OWNED}
    def _refresh_mod_info(self):
        c=self.workspace_controls.get("Mod info")
        if not c:return
        info=self.project.info
        for key in ("id","name","version","author"):c[key].setText(getattr(info,key))
        c["description"].setPlainText(info.description)
        c["settings"].setPlainText(json.dumps(info.settings,indent=2,ensure_ascii=False) if info.settings else "")
        other=self._shown_other()
        c["other"].setPlainText(json.dumps(other,indent=2,ensure_ascii=False) if other else "")
        source=self.project.source_dir
        c["folder"].setText(f"Folder: {source}" if source else "Not saved yet")
        c["status"].setText("")
        self._fill_settings_tree()
        self._fill_mod_api()
    def _apply_mod_info(self):
        c=self.workspace_controls.get("Mod info")
        if not c:return True
        try:
            mod_id=c["id"].text().strip()
            if not validate.MOD_ID_RE.fullmatch(mod_id):raise ValueError("ID must use 1–63 letters, digits, hyphens, or underscores.")
            settings=json.loads(c["settings"].toPlainText()) if c["settings"].toPlainText().strip() else []
            other=json.loads(c["other"].toPlainText()) if c["other"].toPlainText().strip() else {}
            if not isinstance(settings,list):raise ValueError("Settings must be a JSON list.")
            if not isinstance(other,dict):raise ValueError("Other mod data must be a JSON object.")
            reserved=set(other)&self.MOD_INFO_RESERVED
            if reserved:raise ValueError(f"Edit {', '.join(sorted(reserved))} in the editor's own pages.")
        except ValueError as error:
            c["status"].setText(str(error));c["status"].setStyleSheet("color:#ff8f87");return False
        info=self.project.info
        before=(info.id,info.name,info.version,info.author,info.description,info.settings,dict(self.project.other))
        info.id=mod_id;info.name=c["name"].text();info.version=c["version"].text().strip()
        info.author=c["author"].text();info.description=c["description"].toPlainText()
        info.settings=settings
        # The pages of the editor's own keep theirs; the box never showed them.
        for key in self.MOD_INFO_OWNED:
            if key in self.project.other:
                other[key]=self.project.other[key]
        self.project.other=other
        after=(info.id,info.name,info.version,info.author,info.description,info.settings,dict(self.project.other))
        c["status"].setText("Changes applied." if after!=before else "No changes to apply.")
        c["status"].setStyleSheet("color:#7fd49b" if after!=before else "color:#9aacc4")
        if after!=before:
            self._mark_dirty()
            self._fill_mod_api()
        return True

    # --- settings: the structured list ---------------------------------------------

    def _typed_settings(self):
        """The settings as the JSON box has them; None when it does not read."""
        c = self.workspace_controls.get("Mod info")
        if not c:
            return None
        text = c["settings"].toPlainText().strip()
        try:
            settings = json.loads(text) if text else []
        except ValueError:
            return None
        return settings if isinstance(settings, list) else None

    def _setting_users(self) -> dict:
        """Setting key -> how many of the mod's entries it switches ("setting")."""
        counts = {}

        def walk(value):
            if isinstance(value, dict):
                key = value.get("setting")
                if isinstance(key, str):
                    counts[key] = counts.get(key, 0) + 1
                for item in value.values():
                    walk(item)
            elif isinstance(value, list):
                for item in value:
                    walk(item)
        try:
            built = manifest.build(self.project)
        except Exception:       # a half-made form elsewhere: count what the project holds
            built = {}
        built.pop("settings", None)
        walk(built)
        return counts

    def _chosen_setting_index(self):
        c = self.workspace_controls.get("Mod info")
        if not c:
            return None
        items = c["settings_tree"].selectedItems()
        return items[0].data(0, Qt.ItemDataRole.UserRole) if items else None

    def _fill_settings_tree(self):
        c = self.workspace_controls.get("Mod info")
        if not c or self.project is None:
            return
        tree, hint = c["settings_tree"], c["settings_list_hint"]
        chosen = self._chosen_setting_index()
        tree.clear()
        settings = self._typed_settings()
        if settings is None:
            hint.setText("The JSON page does not read as a list: fix it there.")
            hint.setStyleSheet("color:#ff8f87")
            return
        users = self._setting_users()
        for i, setting in enumerate(settings):
            if not isinstance(setting, dict):
                item = QTreeWidgetItem(["?", "(not an object: edit the JSON)", "", "", ""])
                item.setData(0, Qt.ItemDataRole.UserRole, i)
                tree.addTopLevelItem(item)
                continue
            kind = setting.get("type", "int")
            default = setting.get("default", 0)
            if kind == "bool":
                default = "on" if default else "off"
            elif kind == "choice" and isinstance(setting.get("choices"), list) and \
                    isinstance(default, int) and 0 <= default < len(setting["choices"]):
                default = setting["choices"][default]
            used = users.get(setting.get("key"), 0)
            item = QTreeWidgetItem([str(setting.get("key", "")), str(setting.get("label", "")), str(kind),
                                    str(default),
                                    f"{used} {'entry' if used == 1 else 'entries'}" if used else ""])
            item.setData(0, Qt.ItemDataRole.UserRole, i)
            tree.addTopLevelItem(item)
            if chosen == i:
                item.setSelected(True)
        hint.setStyleSheet("color:#9aacc4")
        hint.setText("An entry of fusions, equips or rituals with \"setting\": its key is used only while that "
                     "setting is on. Code mods read them with host->setting.")

    def _write_settings(self, settings, select=None):
        """The list into the JSON box, and into the mod."""
        c = self.workspace_controls["Mod info"]
        c["settings"].setPlainText(json.dumps(settings, indent=2, ensure_ascii=False) if settings else "")
        applied = self._apply_mod_info()
        self._fill_settings_tree()
        if select is not None:
            tree = c["settings_tree"]
            for i in range(tree.topLevelItemCount()):
                found = tree.topLevelItem(i)
                if found.data(0, Qt.ItemDataRole.UserRole) == select:
                    tree.setCurrentItem(found)
                    tree.scrollToItem(found)
                    break
        return applied

    def _add_setting(self):
        settings = self._typed_settings()
        if settings is None:
            return
        taken = {s.get("key") for s in settings if isinstance(s, dict)}
        n = 1
        while f"option{n}" in taken:
            n += 1
        self._setting_dialog("Add a setting", {"key": f"option{n}", "label": f"Option {n}", "type": "bool",
                                               "default": 0}, None)

    def _edit_setting(self):
        settings, i = self._typed_settings(), self._chosen_setting_index()
        if settings is None or i is None or not isinstance(settings[i], dict):
            return
        self._setting_dialog("Setting", dict(settings[i]), i)

    def _remove_setting(self):
        settings, i = self._typed_settings(), self._chosen_setting_index()
        if settings is None or i is None:
            return
        key = settings[i].get("key") if isinstance(settings[i], dict) else None
        used = self._setting_users().get(key, 0)
        if used and QMessageBox.question(
                self, "Remove setting",
                f"{used} of the mod's entries name \"{key}\"; without the setting they are never used. Remove it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        settings.pop(i)
        self._write_settings(settings, min(i, len(settings) - 1) if settings else None)

    def _move_setting(self, step):
        settings, i = self._typed_settings(), self._chosen_setting_index()
        if settings is None or i is None or not 0 <= i + step < len(settings):
            return
        settings[i], settings[i + step] = settings[i + step], settings[i]
        self._write_settings(settings, i + step)

    def _setting_dialog(self, title, setting, index):
        """A setting's fields; keys the dialog has none for stay as written."""
        source = QFile(str(UI_DIR / "setting_dialog.ui"))
        if not source.open(QIODevice.OpenModeFlag.ReadOnly):
            raise RuntimeError(f"Could not open setting_dialog.ui: {source.errorString()}")
        dialog = QUiLoader().load(source, self)
        source.close()
        dialog.setWindowTitle(title)
        key_edit = dialog.findChild(QLineEdit, "settingKeyEdit")
        label_edit = dialog.findChild(QLineEdit, "settingLabelEdit")
        type_combo = dialog.findChild(QComboBox, "settingTypeCombo")
        default_edit = dialog.findChild(QLineEdit, "settingDefaultEdit")
        min_edit = dialog.findChild(QLineEdit, "settingMinEdit")
        max_edit = dialog.findChild(QLineEdit, "settingMaxEdit")
        step_edit = dialog.findChild(QLineEdit, "settingStepEdit")
        suffix_edit = dialog.findChild(QLineEdit, "settingSuffixEdit")
        choices_edit = dialog.findChild(QPlainTextEdit, "settingChoicesEdit")
        description_edit = dialog.findChild(QLineEdit, "settingDescriptionEdit")
        restart_check = dialog.findChild(QCheckBox, "settingRestartCheck")
        hint_label = dialog.findChild(QLabel, "settingHintLabel")
        error_label = dialog.findChild(QLabel, "settingErrorLabel")
        form = dialog.findChild(QFormLayout, "settingForm")
        error_label.setStyleSheet("color:#ff8f87")

        key_edit.setText(str(setting.get("key", "")))
        label_edit.setText(str(setting.get("label", "")))
        type_combo.setCurrentText(setting.get("type", "int"))
        default_edit.setText(str(setting.get("default", 0)))
        for widget, name in ((min_edit, "min"), (max_edit, "max"), (step_edit, "step")):
            widget.setText(str(setting[name]) if name in setting else "")
        suffix_edit.setText(str(setting.get("suffix", "")))
        choices_edit.setPlainText("\n".join(str(choice) for choice in setting.get("choices", []) or []))
        description_edit.setText(str(setting.get("description", "")))
        restart_check.setChecked(bool(setting.get("restart")))

        def update_visibility():
            kind = type_combo.currentText()
            for widget in (min_edit, max_edit, step_edit, suffix_edit):
                visible = kind == "int"
                widget.setVisible(visible)
                label = form.labelForField(widget)
                if label is not None:
                    label.setVisible(visible)
            visible = kind == "choice"
            choices_edit.setVisible(visible)
            label = form.labelForField(choices_edit)
            if label is not None:
                label.setVisible(visible)
            hint_label.setText(self.SETTING_KIND_HINTS.get(kind, ""))
        type_combo.currentTextChanged.connect(update_visibility)
        update_visibility()

        def attempt():
            key = key_edit.text().strip()
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,63}", key) or key == "order":
                return "the key is 1-63 letters, digits, _ or - (not \"order\")"
            settings = self._typed_settings()
            if settings is None:
                return "the JSON page does not read as a list: fix it there first"
            if any(isinstance(s, dict) and s.get("key") == key for n, s in enumerate(settings) if n != index):
                return f"another setting has the key \"{key}\""
            kind = type_combo.currentText()
            out = dict(setting)
            out.update(key=key, label=label_edit.text().strip() or key, type=kind)
            for name, widget in (("default", default_edit), ("min", min_edit), ("max", max_edit), ("step", step_edit)):
                text = widget.text().strip()
                if name != "default" and (kind != "int" or not text):
                    out.pop(name, None)
                    continue
                try:
                    out[name] = int(text or "0")
                except ValueError:
                    return f"{name} is a whole number"
            choices = [line.strip() for line in choices_edit.toPlainText().splitlines() if line.strip()]
            if kind == "choice":
                if len(choices) < 2:
                    return "a choice setting has two choices at least"
                if not 0 <= out["default"] < len(choices):
                    return f"the default is the number of a choice, 0 to {len(choices) - 1}"
                out["choices"] = choices
            else:
                out.pop("choices", None)
            if kind == "int" and suffix_edit.text().strip():
                out["suffix"] = suffix_edit.text().strip()
            else:
                out.pop("suffix", None)
            if kind == "int" and "min" in out and "max" in out and out["min"] > out["max"]:
                return "Lowest is more than Highest"
            description = description_edit.text().strip()
            if description:
                out["description"] = description
            else:
                out.pop("description", None)
            if restart_check.isChecked():
                out["restart"] = True
            else:
                out.pop("restart", None)
            if index is None:
                settings.append(out)
            else:
                settings[index] = out
            if not self._write_settings(settings, len(settings) - 1 if index is None else index):
                c = self.workspace_controls["Mod info"]
                return c["status"].text() or "Mod info's other fields cannot be applied"
            return None

        def on_ok():
            problem = attempt()
            if problem:
                error_label.setText(problem)
                return
            dialog.accept()

        dialog.findChild(QPushButton, "settingCancelButton").clicked.connect(dialog.reject)
        dialog.findChild(QPushButton, "settingOkButton").clicked.connect(on_ok)
        dialog.exec()
        dialog.deleteLater()

    # --- the game the mod needs ----------------------------------------------------

    def _mod_api_text(self) -> str:
        """Which game the mod needs, as the page says it."""
        if self.project is None:
            return ""
        try:
            built = manifest.build(self.project)
        except Exception:       # a half-made form elsewhere: said when it is applied
            return ""
        needed, reasons = compat.required(built, self.project)
        problems = compat.problems(built, self.project)
        if problems:
            return "Mod API requirement is incomplete: " + "; ".join(problems) + ". See Problems."
        written = built.get("min_api")
        if isinstance(written, bool) or not isinstance(written, int):
            written = None
        if not needed and written is None:
            return "Mod API: it uses nothing newer than the game v0.2.0 has, so it needs no \"min_api\"."
        api = max(needed, written or 0)
        text = f"Mod API {api} (\"min_api\"): {compat.release_text(api)}; an older game refuses it as needing a newer one."
        if needed and needed >= api:
            text += " Raised on save to what the mod uses: " + "; ".join(reasons) + "."
        else:
            text += " As written in the other keys."
        return text

    def _fill_mod_api(self):
        c = self.workspace_controls.get("Mod info")
        if c is not None:
            c["api"].setText(self._mod_api_text())
