"""Compatibility additions for the PySide Fusions page.

The game accepts every valid card as a fusion result.  This module keeps that
more capable game behavior while making the planner limitation clear.
"""
from __future__ import annotations

from PySide6.QtWidgets import (QDialog, QFormLayout, QHBoxLayout, QLabel,
                               QMessageBox, QPushButton)


def install() -> None:
    """Install focused Fusion behavior without changing shared model code."""
    from .fusions import FusionsMixin

    if getattr(FusionsMixin, "_fusions_compat_installed", False):
        return
    FusionsMixin._fusions_compat_installed = True
    original_refresh_fusions = FusionsMixin._refresh_fusions

    def effective_result(self, pair):
        """Return the result this pair currently has, including retail data."""
        removes = set(self.project.active_removes())
        own = self.project.own_fusion(pair, removes)
        if own is not None:
            return own
        if pair in self.project.fusions:
            return self.project.fusions[pair] or None
        retail = self.project.retail.fusions.get(pair)
        if self.project.fusion_remove_all or retail in removes:
            return None
        return retail

    def refresh_fusions(self, *args, **kwargs):
        result = original_refresh_fusions(self, *args, **kwargs)
        controls = getattr(self, "workspace_controls", {}).get("Fusions", {})
        page = controls.get("page")
        button = page.findChild(QPushButton, "toggleAllFusionsButton") if page else None
        if button is not None:
            restoring = self.project.fusion_remove_all
            button.setText("Restore disc fusions" if restoring else "Remove all fusions…")
            button.setToolTip(
                "Restore the retail table while keeping explicit mod rules."
                if restoring else
                "Disable every fusion, including explicit mod and card-list rules.")
        return result

    def edit_fusion(self, *_args, add=False):
        pairs = self._selected_fusion_pairs() if not add else []
        if len(pairs) > 1:
            results = {self._effective_fusion_result(pair) for pair in pairs}
            selected = results.pop() if len(results) == 1 else None
            chosen = self._choose_one_card(
                f"Change result of {len(pairs)} selected fusions to…", selected=selected)
            if not chosen:
                return
            for first, second in pairs:
                self.project.set_fusion(first, second, chosen)
            self._mark_dirty()
            self._refresh_fusions()
            self.statusBar().showMessage(
                f"Changed the result of {len(pairs)} fusion rules to "
                f"{self.project.card_label(chosen)}")
            return

        pair = None if add else (pairs[0] if pairs else None)
        if not add and pair is None:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Add fusion" if add else "Edit fusion")
        form = QFormLayout(dialog)
        first = self._card_combo(dialog, pair[0] if pair else None)
        second = self._card_combo(dialog, pair[1] if pair else None)
        result = self._card_combo(dialog, self._effective_fusion_result(pair) if pair else None)
        form.addRow("Card A", first)
        form.addRow("Card B", second)
        form.addRow("Result", result)
        advisory = QLabel()
        advisory.setWordWrap(True)
        advisory.setStyleSheet("color:#f2c04c")
        form.addRow(advisory)
        actions = QHBoxLayout()
        apply = QPushButton("Apply")
        cancel = QPushButton("Cancel")
        actions.addWidget(apply)
        actions.addWidget(cancel)
        form.addRow(actions)
        problem = QLabel()
        problem.setWordWrap(True)
        problem.setStyleSheet("color:#ff7777")
        form.addRow(problem)

        def update_advisory(*_ignored):
            cid = self._combo_card_id(result)
            card = self.project.cards.get(cid)
            advisory.setText(
                "This result is not a Monster. The game accepts it, but "
                "automatic fusion planning does not select non-Monster results."
                if card is not None and not card.is_monster() else "")

        result.currentTextChanged.connect(update_advisory)
        update_advisory()
        apply.clicked.connect(dialog.accept)
        cancel.clicked.connect(dialog.reject)
        while True:
            if not dialog.exec():
                return
            new_pair = (self._combo_card_id(first), self._combo_card_id(second))
            new_result = self._combo_card_id(result)
            if all(new_pair) and new_result:
                break
            problem.setText("Name three cards (a number, a name, or pick one from the list).")
        if pair and self.project.pair(*new_pair) != pair:
            self.project.set_fusion(pair[0], pair[1], None)
        self.project.set_fusion(*new_pair, new_result)
        self._mark_dirty()
        if add:
            controls = self.workspace_controls["Fusions"]
            controls["changed"].setChecked(False)
            controls["search"].setText(self.project.cards[new_pair[0]].name)
        self._refresh_fusions()

    def toggle_all_fusions(self):
        restoring = self.project.fusion_remove_all
        title = "Restore disc fusions" if restoring else "Remove all fusions"
        detail = (
            "Restore the retail fusion table? Explicit mod rules remain in place."
            if restoring else
            "Remove every fusion rule, including mod and card-list rules? "
            "You can restore the disc table afterward, but removed mod rules "
            "will not be restored.")
        answer = QMessageBox.question(
            self, title, detail,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        if restoring:
            self.project.restore_disc_fusions()
        else:
            self.project.remove_all_fusions()
        self._mark_dirty()
        self._refresh_fusions()
        self._refresh_bulk_fusion_plan()
        self.statusBar().showMessage(
            "Restored the disc fusion table." if restoring else "Removed all fusion rules.")

    FusionsMixin._effective_fusion_result = effective_result
    FusionsMixin._refresh_fusions = refresh_fusions
    FusionsMixin._edit_fusion = edit_fusion
    FusionsMixin._toggle_all_fusions = toggle_all_fusions
