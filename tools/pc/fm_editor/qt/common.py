"""What the Qt pages share: the window's stylesheet, the small widgets of its
own (the flow layout, the map canvas, the card spin box, the fusion
delegate), and the helpers that draw a card or read a field.

A page module beside this one holds one page's own code, and `window.py`
mixes them into `ModernEditor`. The engine underneath is the Tk window's
(`model.py`, `manifest.py`, ...), with no Qt in it.
"""
from __future__ import annotations

import sys
import copy
import copy
import struct
import json
import re
from pathlib import Path

from PySide6.QtCore import Qt, QSize, QRect, QPoint, QFile, QIODevice, QTimer, QEvent
from PySide6.QtGui import QColor, QFont, QIcon, QImage, QPainter, QPainterPath, QPalette, QPen, QPixmap
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFileDialog, QHeaderView, QDialogButtonBox, QInputDialog,
    QButtonGroup, QDialog, QFormLayout, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox,
    QPushButton, QScrollArea, QSpinBox, QSplitter, QStackedWidget, QTableWidget, QTableWidgetItem,
    QListWidget, QListWidgetItem, QListView, QTreeWidget, QStyledItemDelegate, QStyle, QStyleOptionViewItem, QTextEdit, QPlainTextEdit,
    QVBoxLayout, QWidget, QAbstractItemView, QRadioButton, QGroupBox, QTabBar, QTabWidget, QLayout, QSizePolicy, QMenu,
    QToolButton)
from PySide6.QtUiTools import QUiLoader

from .. import art, disc, gamedata, manifest, validate, pools as poolmath, bulk_fusions, guardian_stars, card_text, ttf, settings, importer, ygomods, packs as packmath, pngio
from .. import campaign_map as cm
from .. import limits
from .. import fixed_decks
from .. import starter_pools
from .. import map_art, pngio
from ..gamedata import (ATTRIBUTE_NAMES, CARD_COUNT, FRAME_NAMES, FUSION_GROUPS, STAR_NAMES, TYPE_NAMES, DUELIST_NAMES, POOLS,
                       POOL_LABELS, POOL_TOTAL, DECK_SIZE, DECK_COPY_LIMIT, STARTER_WEIGHT_LIMIT,
                       exodia_piece)
from ..model import KEY_RE, Project, StarterDeck

PC_TOOLS = Path(__file__).resolve().parents[2]
if str(PC_TOOLS) not in sys.path:
    sys.path.insert(0, str(PC_TOOLS))
import extract_images as image_extract  # noqa: E402


APP_QSS = """
QMainWindow, QWidget { background: #0b1220; color: #e5edf8; }
QWidget#root { background: #0b1220; color: #e5edf8; }
QMenuBar { background: #101b2b; color: #e5edf8; border-bottom: 1px solid #26374c; }
QMenuBar::item:selected, QMenu::item:selected { background: #1b3151; color: #ffffff; }
QMenu { background: #101b2b; color: #e5edf8; border: 1px solid #30435c; }
QWidget#topbar { background: #101b2b; border: 1px solid #26374c; border-radius: 10px; }
QWidget#sidebar { background: #101b2b; border: 1px solid #26374c; border-radius: 10px; }
QFrame#panel { background: #101b2b; border: 1px solid #26374c; border-radius: 10px; }
QWidget#artSectionCard { background: #101b2b; border: 1px solid #26374c; border-radius: 11px; }
/* The title sits in the margin above the frame, so the margin has to be
   taller than a line of it: at 14px it was drawn over the row above. */
QGroupBox { border: 1px solid #2a3d55; border-radius: 10px; margin-top: 20px;
  padding: 12px 8px 8px; background: #0f1a2a; color: #c9d8ed; font-weight: 600; }
/* The title needs the group's own ground behind it, or the frame's top
   border is drawn straight through the words. */
QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; left: 12px;
  padding: 0 5px; color: #aebfd6; background: #0f1a2a; }
QLabel#artPreviewImage { background: #0b1220; border: 1px solid #26374c; border-radius: 8px; }
QLabel { background: transparent; color: #dce6f4; }
QLabel#heading { font-size: 16px; font-weight: 650; color: #f3f7fc; }
QLabel#muted { color: #9aacc4; }
QLabel#artPartHeading { color: #f3f7fc; font-size: 13pt; font-weight: 650; padding: 4px 2px; }
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox { background: #162337; color: #e5edf8; border: 1px solid #344862;
  border-radius: 6px; padding: 7px 9px; selection-background-color: #246df2; }
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QSpinBox:focus { border: 1px solid #3984ff; }
/* A list of forty duelists or seven hundred cards opened as tall as the
   screen. combobox-popup: 0 makes the popup a list that scrolls, so
   maxVisibleItems is honoured and it is never taller than that. */
QComboBox { combobox-popup: 0; }
/* The pool a duelist's list shows, as tabs over it. */
QTabBar#duelistPoolTabs::tab { background: #142236; color: #9aacc4; border: 1px solid #26374c;
  border-bottom: 0; border-top-left-radius: 7px; border-top-right-radius: 7px; padding: 7px 14px;
  margin-right: 3px; }
QTabBar#duelistPoolTabs::tab:hover { background: #1b3151; color: #dce6f4; }
QTabBar#duelistPoolTabs::tab:selected { background: #216cf1; border-color: #216cf1; color: #ffffff;
  font-weight: 600; }
/* The popup is its own window: without this its frame is drawn light. */
QComboBox QAbstractItemView { background: #162337; color: #e5edf8; border: 1px solid #344862;
  border-radius: 6px; outline: 0; padding: 3px;
  selection-background-color: #1e64df; selection-color: #ffffff; }
QComboBox QAbstractItemView::item { min-height: 24px; padding: 3px 6px; border-radius: 4px; }
QComboBox QAbstractItemView::item:hover { background: #1b3151; }
/* A gutter on the handle keeps the bar off the last column's text. */
QScrollBar:vertical { background: transparent; width: 14px; margin: 0; border: 0; }
QScrollBar::handle:vertical { background: #2c3e57; border-radius: 4px; min-height: 30px;
  margin: 2px 2px 2px 6px; }
QScrollBar:horizontal { background: transparent; height: 14px; margin: 0; border: 0; }
QScrollBar::handle:horizontal { background: #2c3e57; border-radius: 4px; min-width: 30px;
  margin: 6px 2px 2px 2px; }
QScrollBar::handle:hover { background: #3d5577; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; border: 0; background: none; }
QScrollBar::add-page, QScrollBar::sub-page { background: none; }
QTableWidget { background: #101b2b; alternate-background-color: #142236; color: #dce6f4;
  gridline-color: #26374c; border: 1px solid #26374c; border-radius: 6px; selection-background-color: #1e64df;
  selection-color: #ffffff; }
QHeaderView::section { background: #162337; color: #aebfd6; border: 0; border-bottom: 1px solid #26374c;
 padding: 7px; font-weight: 600; }
QTreeWidget { background: #101b2b; alternate-background-color: #142236; color: #dce6f4;
  border: 1px solid #26374c; border-radius: 6px; selection-background-color: #1e64df;
  selection-color: #ffffff; }
QTreeWidget::item { padding: 4px 2px; }
QPushButton#fusionSortHeader { background: transparent; border: 0; color: #aebfd6; padding: 4px 7px;
  text-align: left; font-weight: 600; }
QPushButton#fusionSortHeader:hover { color: #ffffff; background: #162337; }
QPushButton { background: #162337; color: #dce6f4; border: 1px solid #344862; border-radius: 6px;
 padding: 8px 13px; }
QPushButton:hover { background: #1b3151; border-color: #4f6b90; }
QPushButton:checked { background: #216cf1; border-color: #3984ff; color: #ffffff; }
QPushButton#primary { background: #216cf1; border-color: #216cf1; color: white; font-weight: 600; }
QPushButton#primary:hover { background: #155bda; }
QPushButton:disabled { color: #75849a; }
QCheckBox, QRadioButton { spacing: 8px; }
QCheckBox::indicator, QRadioButton::indicator,
QAbstractItemView::indicator {
  width: 14px; height: 14px; border: 1px solid #ffffff;
  background: #0b1220;
}
QCheckBox::indicator, QAbstractItemView::indicator { border-radius: 3px; }
QRadioButton::indicator { border-radius: 8px; }
QCheckBox::indicator:checked, QAbstractItemView::indicator:checked {
  background: #3984ff;
}
QCheckBox::indicator:indeterminate, QAbstractItemView::indicator:indeterminate {
  background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
    stop:0 #0b1220, stop:0.35 #0b1220, stop:0.36 #3984ff,
    stop:0.64 #3984ff, stop:0.65 #0b1220, stop:1 #0b1220);
}
QRadioButton::indicator:checked {
  background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5,
    stop:0 #3984ff, stop:0.55 #3984ff, stop:0.56 #0b1220, stop:1 #0b1220);
}
QStatusBar { background: #101b2b; color: #9aacc4; border-top: 1px solid #26374c; }
QSplitter::handle { background: transparent; width: 8px; }
QSplitter#workspaceSplitter::handle { background: #152236; width: 16px; margin: 4px 3px; border-radius: 3px; }
QScrollArea { border: 0; background: transparent; }
QToolTip { background: #20314a; color: white; border: 0; padding: 5px; }
"""


def _qimage(width: int, height: int, rgba: bytes) -> QImage:
    return QImage(rgba, width, height, width * 4, QImage.Format.Format_RGBA8888).copy()


def _line_count(text: str) -> int:
    return validate.text_lines(text)


# What a row's state is drawn in, light and dark: theme.TAGS, kept here so the
# Qt frontend needs no tkinter. "glitch" is the retail table's odd fusions.
# What the game draws larger at Internal 2x and 4x (art_tab.INTERNAL).
ART_INTERNAL = {"art": 2, "thumbnail": 4}

STATE_COLOURS = {
    "changed": ("#1a5fb4", "#8ab4f8"),
    "added": ("#26a269", "#7fd49b"),
    "removed": ("#c01c28", "#ff8f87"),
    "glitch": ("#865e3c", "#e0ae78"),
    "own list": ("#1a5fb4", "#8ab4f8"),
    "notes": ("#9c6500", "#f2c04c"),
    "error": ("#c01c28", "#ff8f87"),
    "warning": ("#9c6500", "#f2c04c"),
}


PACK_LISTED = ("(default)", "yes", "no")
PACK_SHOPS_RULE = "(shop's)"            # "when_nothing_left" left to "pack_shop"


def _pairs_text(value) -> str:
    """{name: n} as "name=n, name=n" for a one-line field."""
    return ", ".join(f"{k}={v}" for k, v in value.items()) if isinstance(value, dict) else ""


def _parse_pairs(text: str, what: str) -> dict:
    """"name=n, ..." back; ValueError saying what is wrong."""
    out = {}
    for part in [p.strip() for p in text.replace(";", ",").split(",") if p.strip()]:
        if "=" not in part:
            raise ValueError(f"{what}: \"{part}\" is not name=number")
        name, n = [x.strip() for x in part.rsplit("=", 1)]
        if not name or not n.lstrip("-").isdigit():
            raise ValueError(f"{what}: \"{part}\" is not name=number")
        out[name] = int(n)
    return out


def _whole(text: str, what: str, low: int, high: int, blank=None):
    text = text.strip()
    if not text:
        return blank
    if not text.lstrip("-").isdigit() or not low <= int(text) <= high:
        raise ValueError(f"{what} is a whole number, {low} to {high}")
    return int(text)


# Tables that are not lists, and so have nothing to sort by: the grid of
# duelist portraits, the guardian-star matrix named on both axes, the three
# whose cells hold live spin boxes and combos (Qt keeps a cell widget at its
# row and column rather than with the item, so a sort would leave every
# control a row away from the line it belongs to), the two whose rows *are*
# the order the game reads (a pack's tiers and slots), and the fusion list,
# which sorts a million rules at the source because the table shows the
# first three thousand of them.
UNSORTED_TABLES = frozenset({"duelistTable", "matrixTable", "duelistLpTable",
                             "packContentsTable", "packTierTable", "packSlotTable",
                             "fusionTable"})


def _sort_number(text):
    """The number a cell reads as, or None when it does not read as one.

    Covers what the pages put in a column: "1500", "003", "12.50%", "+500",
    "-200". A cell holding words, or the em dash that stands for "unset",
    has no number and falls back to its text.
    """
    found = re.fullmatch(r"\s*([+-]?\d+(?:[.,]\d+)?)\s*%?\s*", text or "")
    return float(found.group(1).replace(",", ".")) if found else None


class TableItem(QTableWidgetItem):
    """A cell that sorts the way its column reads.

    QTableWidgetItem compares the text it shows, which puts 10 before 9 and
    900 after 1500. These compare the number behind the text where both
    cells have one, the text otherwise, and a checkbox column -- whose cells
    hold no text at all -- by what is ticked.
    """

    def __lt__(self, other):
        if not isinstance(other, QTableWidgetItem):
            return NotImplemented
        mine, theirs = self.text(), other.text()
        if not mine and not theirs:
            return int(self.checkState().value) < int(other.checkState().value)
        left, right = _sort_number(mine), _sort_number(theirs)
        if left is None or right is None:
            return mine.casefold() < theirs.casefold()
        return left < right


COMBO_ROWS = 12                 # what a popup shows before it scrolls


def short_popup(combo, rows: int = COMBO_ROWS):
    """Keep a long list from opening as tall as the screen."""
    combo.setMaxVisibleItems(rows)
    return combo


def allow_sorting(table):
    """Let a click on a column header sort the list under it."""
    if table.objectName() in UNSORTED_TABLES:
        return False
    header = table.horizontalHeader()
    header.setSectionsClickable(True)
    header.setSortIndicatorShown(True)
    table.setSortingEnabled(True)
    return True


def sort_paused(table):
    """Take a list's sort off while it is refilled, handing back what it was.

    Qt re-sorts after every setItem, so a fill that walks row by row finds
    its later cells landing on whatever row the sort has moved into the way.
    Pass what this returns to `sort_resumed` once the rows are in.
    """
    header = table.horizontalHeader()
    held = (table.isSortingEnabled(), header.sortIndicatorSection(), header.sortIndicatorOrder())
    table.setSortingEnabled(False)
    return held


def sort_resumed(table, held):
    """Put back the sort `sort_paused` took off, over the rows now in the list."""
    sorting, column, order = held
    table.setSortingEnabled(sorting)
    if sorting and 0 <= column < table.columnCount():
        table.sortItems(column, order)


def sort_keeps_filter(table, refilter):
    """Hide again, after a sort, the rows a search had hidden.

    setRowHidden marks a row number rather than the line in it, so a sort
    that moves the lines leaves the marks behind on whatever landed there.
    The page's own filter runs once the sort has settled, which is a turn of
    the event loop later: the view does its sorting on this same signal.
    """
    table.horizontalHeader().sortIndicatorChanged.connect(
        lambda *_: QTimer.singleShot(0, refilter))


class PoolTypeBar(QWidget):
    """What a pool is made of, as one bar in the kinds' colours."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parts = []
        self.setFixedHeight(10)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def show_counts(self, parts):
        self.parts = [(count, colour) for count, colour in parts if count > 0]
        self.update()

    def paintEvent(self, event):
        total = sum(count for count, _colour in self.parts)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        rect = self.rect().adjusted(0, 0, -1, -1)
        radius = rect.height() / 2
        if not total:
            painter.setBrush(QColor("#162337"))
            painter.drawRoundedRect(rect, radius, radius)
            return
        # One rounded run, the parts cut out of it: the ends stay round
        # however many kinds the pool has.
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)
        painter.setClipPath(path)
        left = rect.left()
        for index, (count, colour) in enumerate(self.parts):
            width = rect.width() - (left - rect.left()) if index == len(self.parts) - 1 \
                else round(rect.width() * count / total)
            painter.setBrush(QColor(colour))
            painter.drawRect(left, rect.top(), width, rect.height())
            left += width


class FlowLayout(QLayout):
    """Left to right, wrapping onto another line when the room runs out (Qt's
    own flow-layout example). The Packs page's card actions sit on one line
    where there is room for them and on two where there is not, rather than
    being drawn over the panel beside them."""

    def __init__(self, parent=None, spacing=8):
        super().__init__(parent)
        self._items = []
        self.setSpacing(spacing)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index):
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._lay(QRect(0, 0, width, 0), apply=False)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._lay(rect, apply=True)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        return size + QSize(margins.left() + margins.right(), margins.top() + margins.bottom())

    def _lay(self, rect, apply):
        margins = self.contentsMargins()
        area = rect.adjusted(margins.left(), margins.top(), -margins.right(), -margins.bottom())
        x, y, line = area.x(), area.y(), 0
        for item in self._items:
            wanted = item.sizeHint()
            if line and x + wanted.width() > area.right() + 1:
                x, y, line = area.x(), y + line + self.spacing(), 0
            if apply:
                item.setGeometry(QRect(QPoint(x, y), wanted))
            x += wanted.width() + self.spacing()
            line = max(line, wanted.height())
        return y + line - rect.y() + margins.bottom()


class MapCanvas(QLabel):
    """The map screen and the overview, drawn into a pixmap. Hit testing is by
    the rectangles the drawing leaves behind (the Tk canvas uses item tags)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.targets = []       # (kind, index, QRect), last drawn on top
        self.on_press = None
        self.on_move = None
        self.on_release = None
        self.surface = None     # the drawing at its own size, whatever is shown
        self.setMouseTracking(False)

    def set_surface(self, pixmap):
        """Show the drawing, shrunk to fit when the panel is narrower than it."""
        self.surface = pixmap
        self._fit()

    def _fit(self):
        if self.surface is None:
            return
        if self.width() >= self.surface.width() and self.height() >= self.surface.height():
            self.setPixmap(self.surface)
            return
        self.setPixmap(self.surface.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                           Qt.TransformationMode.SmoothTransformation))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit()

    def at(self, point):
        """`point` in the drawing's own pixels: it is centred and may be shrunk."""
        shown = self.pixmap()
        if shown is None or self.surface is None or shown.isNull() or not shown.width():
            return point
        left = (self.width() - shown.width()) // 2
        top = (self.height() - shown.height()) // 2
        scale = self.surface.width() / shown.width()
        return QPoint(round((point.x() - left) * scale), round((point.y() - top) * scale))

    def hit(self, point):
        for kind, index, rect in reversed(self.targets):
            if rect.adjusted(-2, -2, 2, 2).contains(point):
                return kind, index
        return None

    def mousePressEvent(self, event):
        if self.on_press is not None and event.button() == Qt.MouseButton.LeftButton:
            self.on_press(self.at(event.position().toPoint()))

    def mouseMoveEvent(self, event):
        if self.on_move is not None:
            self.on_move(self.at(event.position().toPoint()))

    def mouseReleaseEvent(self, event):
        if self.on_release is not None and event.button() == Qt.MouseButton.LeftButton:
            self.on_release(self.at(event.position().toPoint()))


class CardIdSpinBox(QSpinBox):
    """Display card IDs with at least three digits."""

    def textFromValue(self, value: int) -> str:
        return f"{value:03d}"


def _card_plate(inks, scale: int):
    """The title texture's non-zero inks over the card frame.

    A title record stores index zero as transparent.  Keeping it transparent
    here lets the frame's bevel show through as it does in the card viewer.
    """
    image = art.plate_image(inks, background=art.GOLD)
    rgba = bytearray(image.rgba)
    for index, ink in enumerate(inks):
        if not ink:
            rgba[index * 4 + 3] = 0
    return pngio.scale_nearest(pngio.Image(image.width, image.height, bytes(rgba)), scale)


def _card_title(project: Project, wa: bytes, cid: int, frame_cache: dict, scale: int):
    """The card record's title, or the title the PC game generates for a name."""
    try:
        state = art.state(project)
        if (cid, "title") in state.images:
            image, _ = art.shown_image(project, wa, cid, "title")
            return None if image is None else pngio.scale_nearest(image, scale)
        if not art.own_name(project, cid):
            return _card_plate(art.disc_plate_inks(wa, project.base_of(cid)), scale)
    except (IndexError, KeyError, OSError, ValueError, art.pngio.PngError):
        return None

    key = ("card-title-serif-font",)
    if key not in frame_cache:
        try:
            path = packmath.serif_path()
            frame_cache[key] = ttf.Font(path) if path else None
        except (OSError, ttf.FontError):
            frame_cache[key] = None
    face = frame_cache[key]
    if face is None:
        return None
    return _card_plate(packmath.name_plate_inks(project.cards[cid].name, face), scale)


def _draw_hd_card_title(painter: QPainter, name: str, scale: int):
    """The port's HD path: set the card name anew instead of enlarging its plate."""
    painter.save()
    font = QFont("Times New Roman")
    font.setPixelSize(13 * scale)
    painter.setFont(font)
    width = painter.fontMetrics().horizontalAdvance(name)
    if width > 90 * scale:
        # art.c fits an overlong title in the same 90 texels as the disc
        # plate.  QFont stretch preserves that rule for the Qt preview.
        font.setStretch(max(1, round(100 * 90 * scale / width)))
        painter.setFont(font)
    painter.setPen(QColor("#211503"))
    painter.drawText(15 * scale, 25 * scale, name)
    painter.restore()


def _draw_card_details(painter: QPainter, project: Project, wa: bytes, cid: int, frame_cache: dict, scale: int):
    """Draw the data the game layers over a card's frame and illustration."""
    card = project.cards[cid]
    has_custom_title = (cid, "title") in art.state(project).images
    if scale >= 2 and not has_custom_title:
        _draw_hd_card_title(painter, card.name, scale)
    else:
        title = _card_title(project, wa, cid, frame_cache, scale)
        if title is not None:
            painter.drawImage(QRect(12 * scale, 14 * scale, 96 * scale, 14 * scale),
                              _qimage(title.width, title.height, title.rgba))

    if not card.is_monster():
        return

    painter.save()
    # func_80028B08 starts at x=119 and steps left by nine texels for each
    # level icon.  The red rim and yellow centre retain the game's visual
    # hierarchy while the card frame supplies the surrounding texture.
    star_font = QFont("DejaVu Sans")
    star_font.setPixelSize(max(5, 7 * scale))
    painter.setFont(star_font)
    for index in range(max(0, min(12, card.level))):
        x = (119 - 9 * index) * scale
        painter.setPen(QPen(QColor("#b72b1d"), max(1, scale)))
        painter.setBrush(QColor("#e7492c"))
        painter.drawEllipse(QRect(x, 32 * scale, 8 * scale, 8 * scale))
        painter.setPen(QColor("#ffd74d"))
        painter.drawText(QRect(x, 31 * scale, 8 * scale, 9 * scale),
                         Qt.AlignmentFlag.AlignCenter, "★")

    # Attribute is a separate card-view sprite.  Keep its circular medallion
    # and colour on the face, rather than adding the attribute as text in the
    # separate information panel.
    painter.setPen(QPen(QColor("#f6d36a"), max(1, scale)))
    painter.setBrush(QColor("#211b0c"))
    painter.drawEllipse(QRect(110 * scale, 13 * scale, 16 * scale, 16 * scale))

    # The retail card viewer draws four 6x13 digit tiles at these positions.
    # The labels occupy the left half of the same stat plate.
    label_font = QFont("DejaVu Serif")
    label_font.setPixelSize(max(6, 7 * scale))
    label_font.setStretch(85)
    painter.setFont(label_font)
    painter.setPen(QColor("#251804"))
    painter.drawText(77 * scale, 169 * scale, "ATK")
    painter.drawText(77 * scale, 183 * scale, "DFD")
    digit_font = QFont("DejaVu Serif")
    digit_font.setPixelSize(max(8, 11 * scale))
    digit_font.setStretch(80)
    painter.setFont(digit_font)
    painter.drawText(98 * scale, 169 * scale, f"{card.attack:04d}")
    painter.drawText(98 * scale, 183 * scale, f"{card.defense:04d}")
    painter.restore()


def _card_image(project: Project, wa: bytes, cid: int, frame_cache: dict, scale: int = 1) -> QPixmap:
    """Compose the full 140x196 card sprite from its atlas fragments."""
    card = project.cards[cid]
    frame_index = card.shown_frame()
    texture_key = (frame_index, id(wa), "texture")
    if texture_key not in frame_cache:
        palette = image_extract.read_palette(wa, 0xF06800 + (8 + frame_index) * 0x200, 256)
        width, height, rgba = image_extract.decode(wa, 0xEE6800, 64, 256, 8, palette)
        face = _qimage(width, height, rgba)
        right_width, right_height, right_rgba = image_extract.decode(
            wa, 0xEE6800 + 16 * image_extract.SECTOR, 64, 256, 8, palette)
        frame_cache[texture_key] = (face, _qimage(right_width, right_height, right_rgba))

    is_monster = card.is_monster()
    frame_key = (frame_index, id(wa), "monster" if is_monster else "non-monster")
    if frame_key not in frame_cache:
        atlas, right_atlas = frame_cache[texture_key]
        # Merge the 128x192 face, both right-side pieces, and both bottom
        # pieces before drawing the image into the preview label.
        frame = QImage(140, 196, QImage.Format.Format_ARGB32_Premultiplied)
        frame.fill(QColor(0, 0, 0, 0))
        painter = QPainter(frame)
        painter.drawImage(QRect(0, 0, 128, 192), atlas, QRect(0, 0, 128, 192))
        # Four right strips are packed left-to-right: front top-right, back
        # top-right, front bottom-right, back bottom-right.
        right_top = right_atlas.copy(4, 0, 12, 128)
        right_bottom = right_atlas.copy(36, 0, 12, 68)
        painter.drawImage(QRect(128, 0, 12, 128), right_top)
        painter.drawImage(QRect(128, 128, 12, 68), right_bottom)
        if not is_monster:
            painter.drawImage(QRect(0, 144, 128, 48), atlas, QRect(0, 208, 128, 48))
        # Keep the existing lower outline and extend it with 62px left and
        # middle pieces plus the four-pixel corner at the right.
        bottom = atlas.copy(0, 0, 128, 4).flipped(Qt.Orientation.Vertical)
        bottom_left = bottom.copy(0, 0, 62, 4)
        bottom_middle = bottom.copy(62, 0, 62, 4)
        painter.drawImage(QRect(0, 192, 64, 4), bottom_left)
        painter.drawImage(QRect(64, 192, 64, 4), bottom_middle)
        painter.end()
        frame_cache[frame_key] = frame

    scale = 4 if scale >= 4 else 1
    out = QImage(140 * scale, 196 * scale, QImage.Format.Format_ARGB32_Premultiplied)
    out.fill(QColor(0, 0, 0, 0))
    p = QPainter(out)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
    p.drawImage(QRect(0, 0, 140 * scale, 196 * scale), frame_cache[frame_key])

    try:
        picture = art.in_game(project, wa, cid, "art", scale)
        if picture:
            # These are the frame atlas' actual transparent art-window bounds;
            # art.in_game supplies the same 102x96 texel size used by the game.
            p.drawImage(QRect(19 * scale, 50 * scale, 102 * scale, 96 * scale),
                        _qimage(picture.width, picture.height, picture.rgba))
    except (OSError, ValueError, art.pngio.PngError):
        pass

    _draw_card_details(p, project, wa, cid, frame_cache, scale)

    p.end()
    return QPixmap.fromImage(out)


class FusionImageDelegate(QStyledItemDelegate):
    """Paint fusion cards as a grid or as image-and-name rows."""

    def __init__(self, image_for_card, parent=None):
        super().__init__(parent)
        self.image_for_card = image_for_card

    def sizeHint(self, option, index):
        view = self.parent()
        if view is not None and view.viewMode() == QListView.ViewMode.IconMode:
            width = view.gridSize().width() or max(420, view.viewport().width() // 3)
            return QSize(width, 190)
        return QSize(max(700, option.rect.width()), 82)

    def paint(self, painter, option, index):
        painter.save()
        rect = option.rect
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        is_grid = self.parent() is not None and self.parent().viewMode() == QListView.ViewMode.IconMode
        painter.fillRect(rect, QColor("#1e64df") if selected else
                         (QColor("#142236") if index.row() % 2 else QColor("#101b2b")))
        painter.setPen(QColor("#30445e"))
        painter.drawRect(rect.adjusted(0, 0, -1, -1))

        pair = index.data(Qt.ItemDataRole.UserRole)
        outcome = index.data(int(Qt.ItemDataRole.UserRole) + 1)
        names = index.data(int(Qt.ItemDataRole.UserRole) + 2) or ("?", "?", "No fusion")
        state = index.data(int(Qt.ItemDataRole.UserRole) + 3) or "Stock"
        atk = index.data(int(Qt.ItemDataRole.UserRole) + 4) or 0
        defense = index.data(int(Qt.ItemDataRole.UserRole) + 5) or 0
        # The state's own ink, as the Tk list's row tags colour it (#6).
        state_ink = index.data(int(Qt.ItemDataRole.UserRole) + 6)
        state_pen = QColor(state_ink) if state_ink else None
        ids = (pair[0], pair[1], outcome) if pair else (None, None, None)
        fg = QColor("#ffffff") if selected else QColor("#dce6f4")
        painter.setPen(fg)

        if is_grid:
            slot_width = rect.width() / 3.0
            centers = tuple(round(rect.x() + slot_width * (i + 0.5)) for i in range(3))
            image_y = rect.y() + 10
            for pos, (cid, name, center) in enumerate(zip(ids, names, centers)):
                target = QRect(center - 34, image_y, 68, 66)
                self._draw_card(painter, target, cid)
                name_rect = QRect(round(rect.x() + slot_width * pos + 5), image_y + 72,
                                  max(1, round(slot_width - 10)), 48)
                text_flags = (int(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop) |
                              int(Qt.TextFlag.TextWordWrap))
                painter.drawText(name_rect, text_flags, name)
                if pos < 2:
                    painter.setPen(QColor("#aebfd6"))
                    painter.drawText(QRect(round(rect.x() + slot_width * (pos + 1) - 12), image_y,
                                           24, 66), Qt.AlignmentFlag.AlignCenter,
                                     "+" if pos == 0 else "→")
            painter.setPen(state_pen or QColor("#93a6bf"))
            painter.drawText(QRect(rect.x() + 10, rect.bottom() - 24, rect.width() - 20, 18),
                             Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, state)
        else:
            gap = 12
            separator = 28
            status_width = 84
            stat_width = 70
            image_width = 46
            usable = max(210, rect.width() - 24 - 3 * (image_width + gap) - 2 * separator
                         - status_width - 2 * stat_width)
            text_width = usable // 3
            x = rect.x() + 12
            y = rect.y() + (rect.height() - 58) // 2
            for pos, (cid, name) in enumerate(zip(ids, names)):
                target = QRect(x, y, image_width, 58)
                self._draw_card(painter, target, cid)
                label = QRect(x + image_width + 6, rect.y() + 4,
                              text_width, rect.height() - 8)
                painter.drawText(label, Qt.AlignmentFlag.AlignVCenter, name)
                x += image_width + 6 + text_width
                if pos < 2:
                    painter.setPen(QColor("#aebfd6"))
                    painter.drawText(QRect(x, y, separator, 58), Qt.AlignmentFlag.AlignCenter,
                                     "+" if pos == 0 else "→")
                    x += separator
                    painter.setPen(fg)
            for value in (atk, defense):
                painter.setPen(fg)
                painter.drawText(QRect(x, rect.y() + 4, stat_width, rect.height() - 8),
                                 Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
                                 str(value))
                x += stat_width
            status_rect = QRect(rect.right() - status_width - 12, rect.y() + 4,
                                status_width, rect.height() - 8)
            painter.setPen(state_pen or QColor("#aebfd6"))
            painter.drawText(status_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                             state)
        painter.restore()

    def _draw_card(self, painter, target, cid):
        painter.fillRect(target, QColor("#0b1220"))
        pixmap = self.image_for_card(cid) if cid is not None else None
        if pixmap is not None and not pixmap.isNull():
            painter.drawPixmap(target, pixmap)
        else:
            painter.setPen(QColor("#718198"))
            painter.drawText(target, Qt.AlignmentFlag.AlignCenter, "—")



# The forms live with the editor, not with this package.
UI_DIR = Path(__file__).resolve().parents[1] / "ui"
