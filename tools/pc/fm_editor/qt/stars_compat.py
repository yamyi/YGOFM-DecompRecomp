"""Presentation fixes for the Guardian Stars page.

Kept separate from ``stars.py`` so the modern editor can remain compatible
with the baseline editor without changing tracked page code.
"""
from __future__ import annotations


def install() -> None:
    """Keep Guardian Star matrix headers readable as slots are added."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFontMetrics
    from PySide6.QtWidgets import QHeaderView

    from .stars import StarsMixin

    if getattr(StarsMixin, "_stars_compat_installed", False):
        return
    StarsMixin._stars_compat_installed = True

    original_draw = StarsMixin._draw_star_matrix

    def draw_star_matrix(self, *args, **kwargs):
        result = original_draw(self, *args, **kwargs)
        matrix = self.workspace_controls["Guardian Stars"]["matrix"]
        header = matrix.horizontalHeader()
        names = [self.stars_model.name(star)
                 for star in range(1, self.stars_model.count + 1)]

        # The label has a 20px icon, margins and a little breathing room.
        # Stretch mode made it illegible as soon as the mod had extra stars.
        metrics = QFontMetrics(header.font())
        width = max(92, *(metrics.horizontalAdvance(name) + 48 for name in names))
        header.setMinimumSectionSize(width)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        for column in range(matrix.columnCount()):
            header.resizeSection(column, width)

        row_header = matrix.verticalHeader()
        row_width = max(142, *(metrics.horizontalAdvance(f"{index} {name}") + 40
                               for index, name in enumerate(names, 1)))
        row_header.setMinimumWidth(row_width)
        row_header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft |
                                      Qt.AlignmentFlag.AlignVCenter)
        return result

    StarsMixin._draw_star_matrix = draw_star_matrix
