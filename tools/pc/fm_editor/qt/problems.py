"""The Problems page, and going to what a line is about."""
from __future__ import annotations

from .common import *      # noqa: F401,F403
from .common import (_qimage, _line_count, _pairs_text, _parse_pairs, _whole,
                     _card_image)      # noqa: F401


class ProblemsMixin:
    def _other_mods_folder(self):
        """The folder of mods this one is checked against: one chosen here,
        kept in the editor's settings as the Tk window keeps it, else the
        player's own (validate.mod_folders)."""
        chosen = settings.load().get("other_mods")
        return [Path(chosen)] if chosen else None

    def _choose_other_mods(self):
        folder = QFileDialog.getExistingDirectory(
            self, "A folder of mods to check this one against",
            str((self._other_mods_folder() or [self.mods_dir()])[0]))
        if folder:
            settings.save("other_mods", folder)
            self._check_other_mods()

    def _check_other_mods(self):
        """Where this mod meets the others installed (validate.cross_mod).
        Asked for once, the Problems page keeps showing them."""
        self.workspace_controls["Problems"]["cross"] = True
        self._refresh_problems()

    def _cross_mod_issues(self):
        """(issues, what to say): never let another mod's manifest stop this
        one being checked, as the Tk Conflicts tab does not."""
        try:
            return validate.cross_mod(self.project, self._other_mods_folder())
        except Exception as problem:      # noqa: BLE001 - any mod on disk, however written
            return [], f"The other mods could not be checked: {type(problem).__name__}: {problem}"

    def _refresh_problems(self):
        c=self.workspace_controls["Problems"];issues=validate.validate(self.project);table=c["table"]
        if c.get("cross"):
            others, said = self._cross_mod_issues()
            issues = issues + others
            c["others"].setText(said)
        c["issues"]=issues
        held=sort_paused(table);table.setRowCount(len(issues))
        for row,issue in enumerate(issues):
            for col,value in enumerate((issue.level.title(),issue.area+" · "+issue.where,issue.message)):
                item=TableItem(str(value))
                item.setData(Qt.ItemDataRole.UserRole,row)      # which issue the line is, once a sort has moved it
                self._tint_state(item,issue.level)      # the level's ink, as the Tk tree's tags draw it
                table.setItem(row,col,item)
        sort_resumed(table,held)
        errors=len(validate.errors(issues))
        notes=sum(1 for issue in issues if issue.level=="note")      # cross_mod: changes that agree
        warnings=len(issues)-errors-notes
        said=f"{errors} error(s) · {warnings} warning(s)"+(f" · {notes} note(s)" if notes else "")
        c["summary"].setText(said if issues else "No problems found.")
        c["summary"].setStyleSheet("color:#ff8f87" if errors else "color:#f2c04c" if warnings
                                   else "color:#7fd49b")
    def _open_problem(self, row, _column=0):
        """Problems: a double-clicked line goes to what it is about."""
        controls = self.workspace_controls["Problems"]
        issues = controls.get("issues") or []
        # Which issue the line is, rather than which row it sits on: the
        # column headers sort this list like any other.
        item = controls["table"].item(row, 0)
        index = item.data(Qt.ItemDataRole.UserRole) if item is not None else row
        if index is not None and 0 <= index < len(issues):
            self.go_to(issues[index])
    def go_to(self, issue):
        """Show what a validation issue is about, as App.go_to does for the Tk
        window. The pages the modern editor has no form for yet are named
        instead of jumped to."""
        area, target = issue.area, issue.target
        if area == "Other mods":
            # Not a place in this mod: it is where this mod and another meet
            # (validate.cross_mod), so the line itself is what there is to say.
            self.statusBar().showMessage(f"{issue.where}: {issue.message}", 15000)
            return
        if area == "Starter pools":
            self.select_workspace("Starter decks")
            if self.current_workspace == "Starter decks":
                self.goto_starter_pool(target if isinstance(target, int) else 0)
            return
        if area == "Map":
            self.select_workspace("Campaign")
            if self.current_workspace == "Campaign":
                self.goto_map_place(target if isinstance(target, int) else 0)
            return
        if area not in self.workspace_indices:
            self.statusBar().showMessage(
                f"{area}: {issue.where} — this page is not in the modern editor yet; "
                "its data is under Mod info as JSON.")
            return
        self.select_workspace(area)
        if self.current_workspace != area:      # a pending edit refused to leave its page
            return
        if area == "Cards" and target:
            self.goto_card(target)
        elif area == "Art" and target:
            self.goto_art(target)
        elif area == "Fusions" and target:
            controls = self.workspace_controls["Fusions"]
            controls["changed"].setChecked(False)
            controls["search"].setText(str(target[0]))
        elif area == "Equips" and target:
            controls = self.workspace_controls["Equips"]
            controls["search"].clear()
            self._select_table_id(controls["equips"], target)
        elif area == "Rituals" and target:
            controls = self.workspace_controls["Rituals"]
            controls["search"].clear()
            self._select_table_id(controls["cards"], target)
        elif area == "Duelists" and target:
            self.goto_duelist(*target)
        elif area == "Starter decks" and isinstance(target, int):
            controls = self.workspace_controls["Starter decks"]
            controls["starter_tabs"].setCurrentIndex(0)
            self._select_table_id(controls["decks"], target)
        elif area == "Packs" and isinstance(target, int):
            self.goto_pack(target)
