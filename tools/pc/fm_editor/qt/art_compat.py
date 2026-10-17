"""Compatibility behavior for the PySide Art workspace.

The Designer form remains responsible for its layout.  This bridge supplies
small interactions that the classic Art tab exposes without modifying shared
art or manifest code.
"""
from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QMessageBox


class _ImportOnDoubleClick(QObject):
    """Open the matching import action when an Art preview is double-clicked."""

    def __init__(self, open_import, parent):
        super().__init__(parent)
        self._open_import = open_import

    def eventFilter(self, _watched, event):
        if (event.type() == QEvent.Type.MouseButtonDblClick
                and event.button() == Qt.MouseButton.LeftButton):
            self._open_import()
            return True
        return False


def install() -> None:
    """Install Art-only interaction and error-reporting compatibility."""
    from .art import ArtMixin

    if getattr(ArtMixin, "_art_compat_installed", False):
        return
    ArtMixin._art_compat_installed = True

    original_build_art_page = ArtMixin._build_art_page
    original_save_art_image = ArtMixin._save_art_image

    def build_art_page(self, parent):
        result = original_build_art_page(self, parent)
        filters = []
        for part, previews in self.art_previews.items():
            for preview in previews.values():
                preview.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                hook = _ImportOnDoubleClick(
                    lambda p=part: self.import_art(p), preview)
                preview.installEventFilter(hook)
                filters.append(hook)
        # Keep Python references because Qt does not own filters installed on
        # a widget strongly enough for their callbacks to be reliable.
        self._art_preview_import_filters = filters
        return result

    def save_art_image(self, cid, part, image, source):
        try:
            return original_save_art_image(self, cid, part, image, source)
        except OSError as problem:
            QMessageBox.critical(
                self, "Could not export artwork",
                f"Could not write the artwork file: {problem}")

    ArtMixin._build_art_page = build_art_page
    ArtMixin._save_art_image = save_art_image
