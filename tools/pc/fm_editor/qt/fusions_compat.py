"""Compatibility additions for the Qt Fusions page.

Kept separate from the tracked page so the modern editor can receive focused
behaviour improvements without changing its shared implementation.
"""
from __future__ import annotations


def install() -> None:
    """Let Change result apply one selected result to several fusion rows."""
    from .fusions import FusionsMixin

    if getattr(FusionsMixin, "_fusions_compat_installed", False):
        return
    FusionsMixin._fusions_compat_installed = True
    original_edit_fusion = FusionsMixin._edit_fusion

    def edit_fusion(self, *_args, add=False):
        pairs = self._selected_fusion_pairs() if not add else []
        if len(pairs) < 2:
            return original_edit_fusion(self, *_args, add=add)

        # When every selected pair already has the same result, put it first
        # in the chooser.  Mixed results deliberately start unselected.
        results = {self.project.fusions.get(pair) for pair in pairs}
        selected = results.pop() if len(results) == 1 else None
        result = self._choose_one_card(
            f"Change result of {len(pairs)} selected fusions to…", selected=selected)
        if not result:
            return
        for first, second in pairs:
            self.project.set_fusion(first, second, result)
        self._mark_dirty()
        self._refresh_fusions()
        self.statusBar().showMessage(
            f"Changed the result of {len(pairs)} fusion rules to {self.project.card_label(result)}")

    FusionsMixin._edit_fusion = edit_fusion
