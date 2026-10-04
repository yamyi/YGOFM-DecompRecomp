"""Interactive orbit preview of a card's disc model."""
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout

from .. import disc, monster_view
from .common import _qimage


class ModelCanvas(QLabel):
    doubleClicked = Signal()
    FRAME_INTERVAL = 1000 // 60
    INTERACTIVE_SIDE = 160

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
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.render)
        self.settle_timer = QTimer(self)
        self.settle_timer.setSingleShot(True)
        self.settle_timer.timeout.connect(self._settle)
        self.interacting = False

    def show_card(self, project, files, cid):
        self.timer.stop()
        if not cid:
            self.loaded = None
            self.model = None
            self.clear()
            self.setText("Select a card to view its 3D model.")
            return
        model_id = monster_view.model_card(project, cid)
        source = getattr(files, "model_source", None) or files.source
        key = (source, model_id)
        if key == self.loaded:
            return
        self.loaded = key
        self.model = None
        self.clear()
        try:
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

    def render(self):
        if self.model is None:
            return
        # This is a software renderer.  During a gesture it draws a compact
        # frame every 16 ms; the idle redraw restores the full preview.
        side = self.INTERACTIVE_SIDE if self.interacting else max(
            192, min(288, max(self.contentsRect().width(), self.contentsRect().height())))
        picture = monster_view.render(self.model, self.yaw, self.pitch, self.zoom, (side, side))
        self.setPixmap(QPixmap.fromImage(_qimage(picture.width, picture.height, picture.rgba)).scaled(
            self.contentsRect().size(), Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation))

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
