"""Interactive, non-blocking orbit preview of a card's disc model.

The classic duel-board editor draws its software 3D renderer as short raster
slices.  The card-model preview uses the same rasterizer and follows that
pattern here: Qt receives events between slices, so opening or rotating a
model never stalls the editor.
"""
from __future__ import annotations

import time

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout

from .. import disc, map_view, monster_view, pngio
from .common import _qimage

# Matches the duel board's small UI-render time budget.  ``raster_steps``
# itself yields after a bounded amount of pixel work, so a single step stays
# short even for detailed monsters.
RENDER_SLICE = .008
RASTER_STEP = 3_000
# The stored models include extremities near the bounding radius.  Leave a
# deliberate border so the dialog's reset view always contains the whole one.
FIT_SCALE = .34


def _render_steps(model, yaw: float, pitch: float, zoom: float, size: tuple[int, int]):
    """Yield while producing the card model picture with the game pipeline.

    ``monster_view.render`` intentionally remains the simple synchronous API
    used by non-Qt tools.  Keeping this cooperative adapter in ``qt`` lets the
    modern editor remain independent from the original editor while using the
    duel board's proven sliced-rasterizer workflow.
    """
    matrix = map_view.rotation_yxz(pitch * 4096 / 360, yaw * 4096 / 360, 0)
    width, height = size
    scale = min(size) * FIT_SCALE * zoom / model.radius
    faces = []
    for polygon_index, (vertices, uvs, clut, page) in enumerate(model.polygons):
        # Preparing a detailed model can also take time.  Yield before the
        # raster pass too, exactly as the board editor yields its work.
        if polygon_index and polygon_index % 48 == 0:
            yield
        points = []
        for vertex, uv in zip(vertices, uvs):
            x, y, z = monster_view.transform(
                matrix, tuple(vertex[index] - model.centre[index] for index in range(3)))
            points.append((width / 2 + x * scale, height / 2 + y * scale, z,
                           uv & 255, uv >> 8, 1.))
        # Match the game's back-face rejection and monster_view.render().
        if (points[1][0] - points[0][0]) * (points[2][1] - points[0][1]) - \
                (points[2][0] - points[0][0]) * (points[1][1] - points[0][1]) <= 0:
            continue
        for triangle in ((0, 1, 2),) if len(points) == 3 else ((0, 1, 2), (1, 3, 2)):
            faces.append(([points[index] for index in triangle], page, clut, None))

    background = bytes((16, 26, 42, 255))
    pixels = [background] * (width * height)
    # A byte-per-pixel id buffer is all raster_steps needs for a model whose
    # faces have no selectable parts.  It avoids a separate depth allocation;
    # raster_steps maintains its own depth ownership just as _rasterize does.
    yield from map_view.raster_steps(size, faces, model.vram, pixels, step=RASTER_STEP)
    return pngio.Image(width, height, b"".join(pixels))


class ModelCanvas(QLabel):
    doubleClicked = Signal()
    # A compact interaction image gives quick feedback while the pointer is
    # moving.  The complete idle frame is scheduled after the gesture stops.
    FRAME_INTERVAL = 40
    INTERACTIVE_SIDE = 160
    IDLE_MIN_SIDE = 192
    IDLE_MAX_SIDE = 288

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(240, 260)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        self.setToolTip("Drag to rotate · Scroll to zoom · Double-click for a larger view\nStored disc pose; battle animations are not played.")
        self.loaded = None
        self.setWordWrap(True)
        self.setStyleSheet("background:#101a2a;border-radius:7px;padding:8px")
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.model = None
        self.yaw, self.pitch, self.zoom = 30., -10., 1.
        self.drag = None
        self.interacting = False
        self._work = None
        self._work_timer = QTimer(self)
        self._work_timer.setSingleShot(True)
        self._work_timer.timeout.connect(self._render_step)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.render)
        self.settle_timer = QTimer(self)
        self.settle_timer.setSingleShot(True)
        self.settle_timer.timeout.connect(self._settle)

    def _cancel_render(self):
        """Discard the current incomplete frame; it is for an old pose."""
        self._work = None
        self._work_timer.stop()

    def show_card(self, project, files, cid):
        self.timer.stop()
        self.settle_timer.stop()
        self._cancel_render()
        if not cid:
            self.loaded = None
            self.model = None
            self.clear()
            self.setText("Select a card to view its 3D model.")
            return
        model_id = monster_view.model_card(project, cid)
        source = getattr(files, "model_source", None) or files.source
        key = (source, model_id)
        if key == self.loaded and self.model is not None:
            return
        self.loaded = key
        self.model = None
        self.clear()
        self.setText("Loading 3D model…")
        try:
            # Loading a single MODEL.MRG record is small compared with the
            # rasterization.  The costly render below is always sliced.
            self.model = monster_view.MonsterModel(monster_view.read_record(source, model_id))
            self.reset()
        except (OSError, ValueError, disc.GameFilesError) as error:
            self.setText(str(error))

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag = None
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            self.doubleClicked.emit()
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

    def _side(self):
        if self.interacting:
            return self.INTERACTIVE_SIDE
        return max(self.IDLE_MIN_SIDE, min(
            self.IDLE_MAX_SIDE, max(self.contentsRect().width(), self.contentsRect().height())))

    def render(self):
        """Queue the latest frame instead of rasterizing in Qt's event slot."""
        if self.model is None:
            return
        side = self._side()
        key = (self.loaded, id(self.model), self.yaw, self.pitch, self.zoom, side)
        if self._work is not None and self._work[0] == key:
            return
        self._work = (key, _render_steps(self.model, self.yaw, self.pitch, self.zoom, (side, side)))
        # Show an immediate neutral frame while the first slices are queued.
        # Besides avoiding a perceived blank/frozen control, this keeps the
        # old preview contract: selecting the 3D mode immediately owns a
        # concrete pixmap, then replaces it with the finished model.
        current = self.pixmap()
        if current is None or current.isNull():
            placeholder = QPixmap(side, side)
            placeholder.fill(Qt.GlobalColor.transparent)
            self.setPixmap(placeholder.scaled(
                self.contentsRect().size(), Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation))
        self._work_timer.start(0)

    def _render_step(self):
        """Advance a render for at most one duel-board-sized UI time slice."""
        if self._work is None:
            return
        key, steps = self._work
        started = time.perf_counter()
        try:
            next(steps)
            while time.perf_counter() - started < RENDER_SLICE:
                next(steps)
        except StopIteration as done:
            if self._work is None or self._work[0] != key:
                return
            self._work = None
            picture = done.value
            pixmap = QPixmap.fromImage(_qimage(picture.width, picture.height, picture.rgba))
            self.setPixmap(pixmap.scaled(
                self.contentsRect().size(), Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))
            return
        except (ValueError, IndexError, KeyError) as error:
            if self._work is not None and self._work[0] == key:
                self._work = None
                self.setText(str(error))
            return
        # QTimer posts this after pending input and paint events, which is the
        # crucial difference from the old full synchronous render().
        if self._work is not None and self._work[0] == key:
            self._work_timer.start(0)

    def reset(self):
        self.interacting = False
        self.settle_timer.stop()
        self.yaw, self.pitch, self.zoom = 30., -10., 1.
        self.render()

    def _settle(self):
        self.interacting = False
        self.render()

    def _interactive_render(self):
        self.interacting = True
        self.settle_timer.start(140)
        if not self.timer.isActive():
            self.timer.start(self.FRAME_INTERVAL)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.timer.start(60)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        if self.drag is not None:
            delta = event.position() - self.drag
            self.drag = event.position()
            self.yaw = (self.yaw + delta.x() * .6) % 360
            self.pitch = max(-89., min(89., self.pitch - delta.y() * .6))
            self._interactive_render()

    def mouseReleaseEvent(self, event):
        self.drag = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.settle_timer.start(140)

    def wheelEvent(self, event):
        self.zoom = max(.25, min(4., self.zoom * 1.15 ** (event.angleDelta().y() / 120)))
        self._interactive_render()
        event.accept()


class MonsterDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("3D View")
        self.resize(520, 570)
        layout = QVBoxLayout(self)
        self.title = QLabel()
        self.title.setWordWrap(True)
        layout.addWidget(self.title)
        self.canvas = ModelCanvas(self)
        layout.addWidget(self.canvas, 1)
        hint = QLabel("Drag to rotate · Scroll to zoom\nDisc model in its stored pose; battle animations are not played.")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        buttons = QHBoxLayout()
        reset = QPushButton("Reset view")
        reset.clicked.connect(self.canvas.reset)
        buttons.addWidget(reset)
        buttons.addStretch()
        close = QPushButton("Close")
        close.clicked.connect(self.close)
        buttons.addWidget(close)
        layout.addLayout(buttons)

    def show_card(self, project, files, cid):
        title = project.card_label(cid) if cid else "3D View"
        if cid:
            model_id = monster_view.model_card(project, cid)
            if model_id in project.retail.cards:
                title += "\nModel: " + project.retail.cards[model_id].name
        self.title.setText(title)
        self.canvas.show_card(project, files, cid)
