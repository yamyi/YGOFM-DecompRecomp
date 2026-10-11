"""Keep expensive HD image decoding out of interactive paint events."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor


def install():
    from .common import QSize, Qt, QPixmap, QTimer, _qimage
    from .map import MapMixin
    from .. import art

    if getattr(MapMixin, "_performance_compat_installed", False):
        return
    MapMixin._performance_compat_installed = True

    def fusion_card_pixmap(self, cid):
        if cid is None or self.files is None:
            return None
        if cid in self.fusion_art_cache:
            return self.fusion_art_cache[cid]
        pending = getattr(self, "_fusion_art_pending", None)
        if pending is None:
            pending = self._fusion_art_pending = {}
        if cid in pending:
            return None
        executor = getattr(self, "_fusion_art_executor", None)
        if executor is None:
            executor = self._fusion_art_executor = ThreadPoolExecutor(
                max_workers=2, thread_name_prefix="fm-fusion-art")
        project, wa = self.project, self.preview_wa

        def decode():
            try:
                return art.in_game(project, wa, cid, "art", 1)
            except (IndexError, KeyError, OSError, ValueError, art.pngio.PngError):
                return None

        future = pending[cid] = executor.submit(decode)

        def collect():
            if not future.done():
                QTimer.singleShot(15, collect)
                return
            pending.pop(cid, None)
            try:
                image = future.result()
            except BaseException:
                image = None
            if image is not None:
                pixmap = QPixmap.fromImage(_qimage(image.width, image.height, image.rgba))
                self.fusion_art_cache[cid] = pixmap.scaled(
                    QSize(56, 58), Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.FastTransformation)
            controls = getattr(self, "workspace_controls", {}).get("Fusions", {})
            listing = controls.get("image_list")
            if listing is not None:
                listing.viewport().update()
            # The table uses the same lazy art cache through its delegate.
            # Repaint it when this worker has finished so it replaces the
            # short loading marker without rebuilding all fusion rows.
            table = controls.get("table")
            if table is not None:
                table.viewport().update()

        QTimer.singleShot(0, collect)
        return None

    MapMixin._fusion_card_pixmap = fusion_card_pixmap
