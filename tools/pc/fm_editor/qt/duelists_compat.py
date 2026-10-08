"""Visual compatibility refinements for the modern Duelists page."""
from __future__ import annotations


def install() -> None:
    """Use the card-frame family colours in pool statistics."""
    from .duelists import DuelistsMixin

    if getattr(DuelistsMixin, "_duelists_compat_installed", False):
        return
    DuelistsMixin._duelists_compat_installed = True

    # Keep the order used by the type bar.  These values deliberately match
    # the card families rather than the unrelated previous dashboard colours.
    DuelistsMixin.STAT_KINDS = (
        ("Monsters", "#eac54a"),  # yellow
        ("Equips", "#75d68a"),    # light green
        ("Magic", "#23784e"),     # dark green
        ("Traps", "#9b3569"),     # dark pink
        ("Rituals", "#4d8fe8"),   # blue
    )

    original_refresh = DuelistsMixin._refresh_duelists

    def refresh_duelists(self, *args, **kwargs):
        result = original_refresh(self, *args, **kwargs)
        controls = self.workspace_controls.get("Duelists")
        if not controls:
            return result

        # The tab host gets all flexible space.  The compact total remains in
        # a fixed, right-aligned slot, so it cannot make the drop-pool tabs
        # collapse into their scroll arrows.
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QHBoxLayout, QSizePolicy

        page = controls["page"]
        header = page.findChild(QHBoxLayout, "duelistPoolHeader")
        # The bar is created directly in the Designer-provided host.
        host = controls["pool"].parentWidget()
        summary = controls["summary"]
        if header is not None:
            header.setSpacing(12)
            header.setStretch(0, 1)
            header.setStretch(1, 0)
        host.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        host.setMinimumWidth(470)
        summary.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        summary.setFixedWidth(132)
        summary.setAlignment(Qt.AlignmentFlag.AlignRight |
                             Qt.AlignmentFlag.AlignVCenter)
        return result

    DuelistsMixin._refresh_duelists = refresh_duelists
