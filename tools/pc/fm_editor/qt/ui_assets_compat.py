"""Use the modern editor's Assets entry as PR #297's UI / Graphics page.

This compatibility module stays separate from master-tracked editor files.
"""
from __future__ import annotations

from .common import *  # noqa: F401,F403
from .common import _qimage, _card_frame_background
from PySide6.QtCore import QObject, QEvent
from .. import art, board_art, board_model, card_text, duel_screen, gamedata, packs, pngio, ttf, ui_assets, ui_rules
import contextlib
import json
import re
import shutil
import subprocess
import sys
import threading

ELEMENTS = (("lp_opponent", "Opponent LP"), ("lp_player", "Player LP"),
            ("field", "FIELD box"), ("card_bar", "Card bar"),
            ("hand_cursor", "Hand cursor"), ("field_cursor", "Field cursor"))
PARTS = (("name", "Name"), ("atk", "ATK"), ("def", "DEF"),
         ("type", "Type icon"), ("stars", "Stars"), ("kind", "Kind"))


def _clear(layout):
    while layout.count():
        item = layout.takeAt(0)
        if item.widget(): item.widget().deleteLater()
        elif item.layout(): _clear(item.layout())


def _line(placeholder=""):
    field = QLineEdit(); field.setPlaceholderText(placeholder); return field


def _spin(low, high, suffix=""):
    field = QSpinBox(); field.setRange(low, high); field.setSuffix(suffix); return field


def _heading(layout, title, note):
    text = QLabel(title); text.setObjectName("heading"); layout.addWidget(text)
    text = QLabel(note); text.setObjectName("muted"); text.setWordWrap(True); layout.addWidget(text)


def _object(root, name):
    value = root.get(name)
    if not isinstance(value, dict): root[name] = value = {}
    return value


def _put(holder, key, value, default=None):
    if value == default or value in (None, ""): holder.pop(key, None)
    else: holder[key] = value


def install():
    from .assets import AssetsMixin
    if getattr(AssetsMixin, "_ui_assets_compat", False): return
    AssetsMixin._ui_assets_compat = True

    def build(self, page, controls):
        """Build the supplied UI shell and retain the complete asset editor.

        All scene-oriented tabs are declared in ``ui/assets_page.ui``.
        The catalogue editor remains a visible tab after Build Deck, rather
        than being replaced by a static mock-up.  This keeps the modern UI
        independent of the classic editor while preserving every existing
        replacement workflow.
        """
        # ``window._build_workspace_page`` has already loaded this complete
        # Designer form.  Reusing it avoids a second overlapping tab widget
        # and leaves every position and control defined by assets_page.ui.
        shell = page
        tabs = _asset_widget(shell, QTabWidget, "uiPageTabs")
        frames_tab = _asset_widget(shell, QWidget, "FramesPage")
        build_deck_tab = _asset_widget(shell, QWidget, "BuildDeckAssetsTab")
        assets_tab = _asset_widget(shell, QWidget, "AssetsPage")
        _build_template_framework(self, assets_tab, controls)
        _build_build_deck_tab(self, build_deck_tab, controls)
        controls.update(shell=shell, tabs=tabs, assets_tab=assets_tab, frames_tab=frames_tab)
        _apply_reference_skin(shell, tabs, assets_tab)
        _wire_ui_tabs(self, shell, controls)
        _wire_frames_tab(self, frames_tab, controls)
        tabs.setCurrentIndex(0)
        return shell

    def duel(self): return _object(_object(self.project.other, "ui"), "duel")

    def _load(self):
        c = self.workspace_controls.get("UI", {}); root = self.project.other
        if not c: return
        title = root.get("title") if isinstance(root.get("title"), dict) else {}; menu = root.get("menu") if isinstance(root.get("menu"), dict) else {}; value = self._ui_duel().get(c["element"].currentData(), {}); value = value if isinstance(value, dict) else {}
        keys = ("title_background", "title_intro", "title_song", "menu_scale", "menu_tint", "x", "y", "scale", "tint", "hide", "label", "digits", "image", "width", "height")
        for key in keys: c[key].blockSignals(True)
        for key, field in (("background", "title_background"), ("intro", "title_intro"), ("song", "title_song")): c[field].setText(str(title.get(key, "")))
        c["menu_scale"].setValue(menu.get("scale", 100) if isinstance(menu.get("scale", 100), int) else 100); c["menu_tint"].setText(str(menu.get("tint", "")))
        for key in ("x", "y", "width", "height"): c[key].setValue(value.get(key, 0) if isinstance(value.get(key, 0), int) else 0)
        c["scale"].setValue(value.get("scale", 100) if isinstance(value.get("scale", 100), int) else 100)
        for key in ("tint", "label", "digits", "image"): c[key].setText(str(value.get(key, "")))
        c["hide"].setChecked(bool(value.get("hide", False)))
        for key in keys: c[key].blockSignals(False)
        _load_part(self)

    def _load_part(self):
        c = self.workspace_controls.get("UI", {})
        if not c: return
        element = self._ui_duel().get(c["element"].currentData(), {}); value = element.get(c["part"].currentData(), {}) if isinstance(element, dict) else {}; value = value if isinstance(value, dict) else {}
        for key in ("part_x", "part_y", "part_spacing", "part_tint", "part_hide"): c[key].blockSignals(True)
        c["part_x"].setValue(value.get("x", 0) if isinstance(value.get("x", 0), int) else 0); c["part_y"].setValue(value.get("y", 0) if isinstance(value.get("y", 0), int) else 0); c["part_spacing"].setValue(value.get("spacing", 0) if isinstance(value.get("spacing", 0), int) else 0); c["part_tint"].setText(str(value.get("tint", ""))); c["part_hide"].setChecked(bool(value.get("hide", False)))
        for key in ("part_x", "part_y", "part_spacing", "part_tint", "part_hide"): c[key].blockSignals(False)

    def _write(self):
        c = self.workspace_controls["UI"]; root = self.project.other; title = _object(root, "title")
        for key, field in (("background", "title_background"), ("intro", "title_intro"), ("song", "title_song")): _put(title, key, c[field].text().strip())
        if not title: root.pop("title", None)
        menu = _object(root, "menu"); _put(menu, "scale", c["menu_scale"].value(), 100); _put(menu, "tint", c["menu_tint"].text().strip())
        if not menu: root.pop("menu", None)
        duel = self._ui_duel(); element = duel.setdefault(c["element"].currentData(), {})
        for key in ("x", "y"): _put(element, key, c[key].value(), 0)
        _put(element, "scale", c["scale"].value(), 100)
        for key in ("tint", "label", "digits", "image"): _put(element, key, c[key].text().strip())
        _put(element, "hide", c["hide"].isChecked(), False)
        for key in ("width", "height"): _put(element, key, c[key].value(), 0)
        part = element.setdefault(c["part"].currentData(), {})
        _put(part, "x", c["part_x"].value(), 0); _put(part, "y", c["part_y"].value(), 0); _put(part, "spacing", c["part_spacing"].value(), 0); _put(part, "tint", c["part_tint"].text().strip()); _put(part, "hide", c["part_hide"].isChecked(), False)
        if not part: element.pop(c["part"].currentData(), None)
        if not element: duel.pop(c["element"].currentData(), None)
        if not root.get("ui", {}).get("duel"): root.pop("ui", None)

    def _reset(self): self._ui_duel().pop(self.workspace_controls["UI"]["element"].currentData(), None); _load(self); self._mark_dirty()
    def _revert(self):
        for key in ("ui", "title", "menu"): self.project.other.pop(key, None)
        _load(self); self._mark_dirty()
    def refresh(self):
        _refresh_template(self)
        _refresh_ui_tabs(self)
        _refresh_frames_tab(self)

    AssetsMixin._build_assets_page = build; AssetsMixin._refresh_assets = refresh; AssetsMixin._ui_duel = duel


def _apply_reference_skin(shell, tabs, assets_tab):
    """Apply the four-tab UI Assets presentation from the supplied reference."""
    title = shell.findChild(QLabel, "pageTitleLabel")
    summary = shell.findChild(QLabel, "pageSummaryLabel")
    # The supplied all-tabs form has no page-level heading.  Older versions
    # did, so keep this optional instead of failing while the editor starts.
    if title is not None:
        title.setText("▣  UI Assets")
        title.setStyleSheet("font-size: 25px; font-weight: 700; color: #f3f8ff;")
    if summary is not None:
        summary.setText("Replace named interface graphics used by menus, icons, and duel screens.")
        summary.setStyleSheet("color: #aabbd2; font-size: 13px;")
    index = tabs.indexOf(assets_tab)
    tabs.tabBar().setTabVisible(index, True)
    tabs.setDocumentMode(False)
    # The reference puts a generously sized asset inspector beside each live
    # preview.  Explicit stretch factors prevent Qt's preview minimum size from
    # collapsing the inspector on normal desktop resolutions.
    for layout_name, left, right in (("titleScreenLayout", 3, 2), ("menusLayout", 5, 4), ("duelLayout", 3, 2)):
        layout = shell.findChild(QHBoxLayout, layout_name)
        if layout is not None:
            layout.setStretch(0, left); layout.setStretch(1, right)
    for splitter_name, sizes in (("titleRightSplitter", (360, 340)), ("menuRightSplitter", (390, 310)), ("duelRightSplitter", (440, 280))):
        splitter = shell.findChild(QSplitter, splitter_name)
        if splitter is not None: splitter.setSizes(list(sizes))
    shell.setStyleSheet("""
        QWidget#UiAssetsPage { background: #061625; color: #e6eefb; }
        QFrame#titlePreviewPanel, QFrame#titleElementsPanel, QFrame#titlePropertiesPanel,
        QFrame#menuPreviewPanel, QFrame#menuStructurePanel, QFrame#menuPropertiesPanel,
        QFrame#duelPreviewPanel, QFrame#duelElementsPanel, QFrame#duelPropertiesPanel,
        QFrame#boardPreviewPanel, QFrame#boardPartsPanel, QFrame#boardPropertiesPanel {
            background: #0a1c2e; border: 1px solid #1c4665; border-radius: 8px; }
        QLabel { color: #dbe8f9; }
        QLabel#titlePreviewTitle, QLabel#menuPreviewTitle, QLabel#duelPreviewTitle,
        QLabel#boardPreviewTitle, QLabel#boardPartsTitle, QLabel#boardPropertiesTitle,
        QLabel#titleElementsTitle, QLabel#titlePropertiesTitle, QLabel#menuStructureTitle,
        QLabel#menuPropertiesTitle, QLabel#duelElementsTitle, QLabel#duelPropertiesTitle {
            font-size: 16px; font-weight: 700; color: #f3f8ff; }
        QTabWidget::pane { border: 1px solid #173852; background: #071827; border-radius: 8px; }
        QTabBar::tab { background: #0b2236; color: #d6e4f5; border: 1px solid #204762;
            border-radius: 5px; min-width: 96px; padding: 10px 18px; margin-right: 6px; }
        QTabBar::tab:selected { background: #0878eb; border-color: #1e9cff; color: white; }
        QTreeWidget, QLineEdit, QComboBox, QSpinBox, QPlainTextEdit { background: #09192a;
            color: #e6eefb; border: 1px solid #28506e; border-radius: 5px; padding: 5px; }
        QTreeWidget::item { height: 31px; border-bottom: 1px solid #183650; }
        QTreeWidget#titleElementsTree::item { height: 50px; }
        QTreeWidget::item:selected { background: #0c79ee; color: white; }
        QPushButton { background: #112a43; color: #e7f0ff; border: 1px solid #2c5577;
            border-radius: 5px; padding: 7px 12px; min-height: 18px; }
        QPushButton:hover { background: #173c60; border-color: #2e98ef; }
        QPushButton:pressed { background: #075cb5; }
        QPushButton#replaceBoardPartButton, QPushButton#addMenuButtonButton, QPushButton#addTitlePictureButton,
        QPushButton#addTitleTextButton { background: #0878eb; border-color: #1da1ff; color: white; font-weight: 600; }
        QCheckBox { color: #dceafd; spacing: 7px; }
        QSplitter::handle { background: #12344d; }
    """)
    # Reference-style terrain selectors remain synchronized with the original combo box.
    board_layout = shell.findChild(QHBoxLayout, "boardFieldSelectorLayout")
    combo = shell.findChild(QComboBox, "boardFieldCombo")
    caption = shell.findChild(QLabel, "boardFieldLabel")
    if board_layout is not None and combo is not None and shell.findChild(QWidget, "boardTerrainPills") is None:
        holder = QWidget(shell); holder.setObjectName("boardTerrainPills"); pills = QHBoxLayout(holder); pills.setContentsMargins(0, 0, 0, 0); pills.setSpacing(6)
        buttons = []
        for terrain in board_art.TERRAINS:
            button = QPushButton(board_art.TERRAIN_LABELS[terrain], holder); button.setCheckable(True); button.setMinimumWidth(105)
            button.clicked.connect(lambda checked=False, name=terrain: combo.setCurrentIndex(combo.findData(name) if combo.findData(name) >= 0 else board_art.TERRAINS.index(name)))
            pills.addWidget(button); buttons.append((terrain, button))
        board_layout.insertWidget(0, holder, 1); caption.hide(); combo.hide()
        def sync_pills(_=None):
            chosen = combo.currentData() or board_art.TERRAINS[combo.currentIndex()]
            for terrain, button in buttons: button.setChecked(terrain == chosen)
        combo.currentIndexChanged.connect(sync_pills); sync_pills()


def _scene_widget(shell, name):
    value = shell.findChild(QWidget, name)
    if value is None:
        raise RuntimeError(f"UI Assets tabs form is missing {name!r}")
    return value


def _set_value(widget, value):
    widget.blockSignals(True)
    if isinstance(widget, (QSpinBox, QComboBox)):
        if isinstance(widget, QComboBox):
            index = widget.findData(value)
            widget.setCurrentIndex(index if index >= 0 else 0)
        else:
            widget.setValue(int(value))
    elif isinstance(widget, QCheckBox):
        widget.setChecked(bool(value))
    else:
        widget.setText(str(value))
    widget.blockSignals(False)


class _PreviewEvents(QObject):
    """Mouse bridge for the 320×240 preview canvases."""
    def __init__(self, editor, kind, parent):
        super().__init__(parent); self.editor, self.kind = editor, kind

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            _preview_press(self.editor, self.kind, watched, event.position()); return True
        if event.type() == QEvent.Type.MouseMove and event.buttons() & Qt.MouseButton.LeftButton:
            _preview_drag(self.editor, self.kind, watched, event.position()); return True
        if event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
            _preview_release(self.editor, self.kind); return True
        if event.type() == QEvent.Type.KeyPress:
            return _preview_nudge(self.editor, self.kind, event.key(), 8 if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else 1)
        if event.type() == QEvent.Type.Wheel and self.kind == "duel":
            _preview_wheel(self.editor, event.angleDelta().y()); return True
        if event.type() == QEvent.Type.Resize:
            _rescale_preview_label(watched)
        return False


class _BoardEvents(QObject):
    """Mouse bridge for the Duel board's 3D preview: middle-drag orbits it,
    Shift or Ctrl held pans it, the wheel zooms, a double middle click or
    "Game's view" puts the duel's own camera back, and a left click on the
    board picks the part under it (ui_board.py's press/motion/release/wheel)."""
    def __init__(self, editor, parent):
        super().__init__(parent); self.editor = editor

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.MouseButtonPress and event.button() in (
                Qt.MouseButton.MiddleButton, Qt.MouseButton.LeftButton):
            _board_press(self.editor, watched, event); return True
        if event.type() == QEvent.Type.MouseMove and event.buttons() & Qt.MouseButton.MiddleButton:
            _board_motion(self.editor, watched, event); return True
        if event.type() == QEvent.Type.MouseButtonRelease and event.button() in (
                Qt.MouseButton.MiddleButton, Qt.MouseButton.LeftButton):
            _board_release(self.editor, watched, event); return True
        if event.type() == QEvent.Type.MouseButtonDblClick and event.button() == Qt.MouseButton.MiddleButton:
            _board_reset_view(self.editor); return True
        if event.type() == QEvent.Type.Wheel:
            _board_wheel(self.editor, event.angleDelta().y()); return True
        if event.type() == QEvent.Type.Resize:
            _rescale_preview_label(watched)
        return False


def _preview_point(label, position):
    scale = min(label.width() / 320, label.height() / 240)
    if scale <= 0: return 0, 0
    left, top = (label.width() - 320 * scale) / 2, (label.height() - 240 * scale) / 2
    return (position.x() - left) / scale, (position.y() - top) / scale


def _preview_key(boxes, point):
    x, y = point
    for key, (left, top, width, height) in reversed(list(boxes.items())):
        if left <= x <= left + width and top <= y <= top + height:
            return key
    return None


def _preview_press(editor, kind, label, position):
    c = editor.workspace_controls.get("UI", {})
    point, key = _preview_point(label, position), _preview_key(c.get(f"{kind}_boxes", {}), _preview_point(label, position))
    if key is None: return
    if kind == "title":
        c["title_selected"] = key; _refresh_title(editor)
    elif kind == "menu":
        c["menu_selected"] = key; _refresh_menu(editor)
    else:
        c["duel_selected"] = key; _refresh_duel(editor)
    c["preview_drag"] = {"kind": kind, "key": key, "point": point, "moved": False}


def _draw_preview_kind(editor, kind):
    if kind == "title":
        _draw_title(editor)
    elif kind == "menu":
        _draw_menu(editor)
    else:
        _draw_duel(editor)


def _queue_preview_redraw(editor, kind):
    """Coalesce mouse moves into one preview composition per display frame.

    Qt delivers every pointer event on the GUI thread.  The original editor's
    Canvas moves a cached item immediately; these previews compose a complete
    image, so drawing each raw event starves subsequent pointer events.
    """
    c = editor.workspace_controls.get("UI", {})
    timers = c.setdefault("preview_render_timers", {})
    timer = timers.get(kind)
    if timer is None:
        preview = c.get(f"{kind}_preview")
        if preview is None:
            return
        timer = timers[kind] = QTimer(preview)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda selected=kind: _draw_preview_kind(editor, selected))
    if not timer.isActive():
        timer.start(16)


def _preview_drag(editor, kind, label, position):
    c, drag = editor.workspace_controls.get("UI", {}), editor.workspace_controls.get("UI", {}).get("preview_drag")
    if not isinstance(drag, dict) or drag.get("kind") != kind: return
    x, y = _preview_point(label, position); start_x, start_y = drag["point"]
    dx, dy = round(x - start_x), round(y - start_y)
    if not dx and not dy: return
    key = drag["key"]
    if kind == "title":
        if key == "background": return
        target = _title_target(editor, True)
        default_x, default_y = (160, 220) if key.startswith("text:") else ((160, 120) if key.startswith("picture:") else (0, 0))
        target["x"] = _as_int(drag.setdefault("x", target.get("x", default_x)), default_x) + dx
        target["y"] = _as_int(drag.setdefault("y", target.get("y", default_y)), default_y) + dy
    elif kind == "menu":
        # Not "if not target" -- a fresh item's target is a real but empty
        # {} (entries.setdefault), so that check always aborted the drag.
        if _menu_item(editor) is None: return
        target = _menu_target(editor, True)
        target["x"] = _as_int(drag.setdefault("x", target.get("x", 0))) + dx
        target["y"] = _as_int(drag.setdefault("y", target.get("y", 0))) + dy
    else:
        name, part = _duel_path(key)
        target = _duel_target(editor, True)
        if part is not None:
            target["x"] = _as_int(drag.setdefault("x", target.get("x", 0))) + dx
            target["y"] = _as_int(drag.setdefault("y", target.get("y", 0))) + dy
        else:
            moves = ui_rules.MOVES.get(name, "")
            if "x" in moves: target["x"] = _as_int(drag.setdefault("x", target.get("x", 0))) + dx
            if "y" in moves: target["y"] = _as_int(drag.setdefault("y", target.get("y", 0))) + dy
    drag["moved"] = True
    _queue_preview_redraw(editor, kind)


def _preview_nudge(editor, kind, key, amount):
    directions = {Qt.Key.Key_Left: (-amount, 0), Qt.Key.Key_Right: (amount, 0), Qt.Key.Key_Up: (0, -amount), Qt.Key.Key_Down: (0, amount)}
    if key not in directions: return False
    dx, dy = directions[key]; c = editor.workspace_controls.get("UI", {})
    if kind == "title":
        chosen = c.get("title_selected", "")
        if chosen == "background": return True
        target = _title_target(editor, True)
        base_x, base_y = (160, 220) if chosen.startswith("text:") else ((160, 120) if chosen.startswith("picture:") else (0, 0))
        target["x"], target["y"] = _as_int(target.get("x"), base_x) + dx, _as_int(target.get("y"), base_y) + dy
        editor._mark_dirty(); _refresh_title(editor)
    elif kind == "menu":
        if _menu_item(editor) is None: return True
        target = _menu_target(editor, True)
        target["x"], target["y"] = _as_int(target.get("x")) + dx, _as_int(target.get("y")) + dy
        editor._mark_dirty(); _refresh_menu(editor)
    else:
        name, part = _duel_path(c.get("duel_selected", "")); target = _duel_target(editor, True)
        if part is not None or "x" in ui_rules.MOVES.get(name, ""):
            target["x"] = _as_int(target.get("x")) + dx
        if part is not None or "y" in ui_rules.MOVES.get(name, ""):
            target["y"] = _as_int(target.get("y")) + dy
        editor._mark_dirty(); _refresh_duel(editor)
    return True


def _preview_wheel(editor, delta):
    c = editor.workspace_controls.get("UI", {}); name, part = _duel_path(c.get("duel_selected", ""))
    if part is not None or name not in ui_rules.SIZED or not delta: return
    target = _duel_target(editor, True); step = 10 if delta > 0 else -10
    target["scale"] = max(25, min(ui_rules.element_scale_max(name, target), _as_int(target.get("scale"), 100) + step))
    editor._mark_dirty(); _refresh_duel(editor)


def _preview_release(editor, kind):
    c = editor.workspace_controls.get("UI", {})
    drag = c.pop("preview_drag", None)
    timer = c.get("preview_render_timers", {}).get(kind)
    if timer is not None and timer.isActive():
        timer.stop()
    if not isinstance(drag, dict) or not drag.get("moved"): return
    editor._mark_dirty()
    if kind == "title": _refresh_title(editor)
    elif kind == "menu": _refresh_menu(editor)
    else: _refresh_duel(editor)


def _outline(image, box):
    if box is None: return image
    from PySide6.QtGui import QPainter, QPen
    surface = QImage(image.rgba, image.width, image.height, image.width * 4, QImage.Format.Format_RGBA8888).copy()
    painter = QPainter(surface); painter.setPen(QPen(QColor("#1686ff"), 2)); painter.drawRect(*map(round, box)); painter.end()
    return pngio.Image(image.width, image.height, bytes(surface.bits()))


_COMPARE_KEYS = ("title", "menu", "ui")


@contextlib.contextmanager
def _comparing_view(editor):
    """While a "Hold: the game's" button is held: the mod's own "title",
    "menu" and "ui" keys out of the way, so a page's normal draw shows the
    game's retail look (ui_tab.py's retail_view/draw_compared -- one shared
    flag here too, since only one page's preview is ever drawn at a time)."""
    c = editor.workspace_controls.get("UI", {})
    if not c.get("comparing"):
        yield False
        return
    other = editor.project.other
    saved = {key: other.pop(key) for key in _COMPARE_KEYS if key in other}
    try:
        yield True
    finally:
        other.update(saved)


def _compare_badge(image):
    """The game's own look, marked (ui_tab.py's draw_compared's corner note)."""
    surface = QImage(image.rgba, image.width, image.height, image.width * 4, QImage.Format.Format_RGBA8888).copy()
    painter = QPainter(surface)
    painter.fillRect(0, 0, 96, 22, QColor("#000000"))
    painter.setPen(QPen(QColor("#ffd34d"), 1)); painter.drawRect(0, 0, 95, 21)
    painter.setPen(QColor("#ffd34d")); painter.setFont(QFont("Sans", 9))
    painter.drawText(QRect(0, 0, 96, 22), Qt.AlignmentFlag.AlignCenter, "The game's")
    painter.end()
    return pngio.Image(image.width, image.height, bytes(surface.bits()))


def _hold_compare(editor, held):
    """Any page's "Hold: the game's" button: show the game's own look while
    held, back to the mod's when let go. One flag for the whole workspace,
    since the classic editor's button is a single one shared by every page."""
    c = editor.workspace_controls["UI"]
    if held == c.get("comparing", False): return
    c["comparing"] = held
    if held:
        c["compare_board_art"] = getattr(editor.project, "board_art", None)
        editor.project.board_art = board_art.BoardArt()
    else:
        saved = c.pop("compare_board_art", None)
        editor.project.board_art = saved if saved is not None else board_art.BoardArt()
    _draw_title(editor); _draw_menu(editor); _draw_duel(editor)
    _queue_board_render(editor, _board_terrain(c), force=True)


def _set_preview_pixmap(label, pixmap, fallback=""):
    """Show `pixmap` on a preview label, fit to it now and kept for a later
    resize: the full-resolution pixmap is stashed on the label itself (a
    rescale needs no redraw) and reapplied by _rescale_preview_label."""
    if pixmap is None or pixmap.isNull():
        label.setProperty("_fullPixmap", None)
        label.setPixmap(QPixmap()); label.setText(fallback)
        return
    label.setProperty("_fullPixmap", pixmap)
    label.setText("")
    label.setPixmap(pixmap.scaled(label.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                  Qt.TransformationMode.FastTransformation))


def _rescale_preview_label(label):
    """The label's own stashed pixmap, fit to its (now different) size --
    on a window/panel resize, so a preview does not wait on the next edit
    to stop being letterboxed or cropped."""
    pixmap = label.property("_fullPixmap")
    if not isinstance(pixmap, QPixmap) or pixmap.isNull(): return
    label.setPixmap(pixmap.scaled(label.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                  Qt.TransformationMode.FastTransformation))


def _canvas(label, title, lines=()):
    """Draw a quick, sharp 320×240 page overview without blocking Qt's UI."""
    from PySide6.QtGui import QFont, QPainter
    image = QImage(320, 240, QImage.Format.Format_RGBA8888)
    image.fill(QColor("#07111f"))
    painter = QPainter(image)
    painter.setPen(QColor("#87a3c6")); painter.setFont(QFont("Sans", 14, QFont.Weight.Bold))
    painter.drawText(QRect(16, 16, 288, 34), Qt.AlignmentFlag.AlignCenter, title)
    painter.setFont(QFont("Sans", 9))
    for row, text in enumerate(lines[:10]):
        painter.drawText(QRect(40, 62 + row * 16, 240, 15), Qt.AlignmentFlag.AlignLeft, text)
    painter.end()
    _set_preview_pixmap(label, QPixmap.fromImage(image))


def _png_preview(label, image, fallback):
    if image is None:
        _set_preview_pixmap(label, None, fallback); return
    _set_preview_pixmap(label, QPixmap.fromImage(_qimage(image.width, image.height, image.rgba)))


def _ui_section(editor, key, create=False):
    value = editor.project.other.get(key)
    if isinstance(value, dict):
        return value
    if create:
        value = {}
        editor.project.other[key] = value
        return value
    return {}


def _ui_strings(value):
    """Every string stored by the UI configuration.

    Imported Title, Menu, and Duel PNGs all live under ``ui/``.  A removal
    may leave an otherwise valid file behind, so find paths still mentioned
    anywhere in the surviving configuration before queuing a file deletion.
    """
    if isinstance(value, str):
        return {value}
    if isinstance(value, dict):
        return set().union(*(_ui_strings(item) for item in value.values())) if value else set()
    if isinstance(value, list):
        return set().union(*(_ui_strings(item) for item in value)) if value else set()
    return set()


def _drop_ui_orphans(editor):
    """Remove unreferenced imported UI PNGs without disturbing shared ones."""
    project = editor.project
    used = _ui_strings(project.other)
    for name in tuple(project.files):
        if name.startswith("ui/") and name not in used:
            project.files.pop(name, None)
            project.deleted_files.add(name)


def _commit_ui(editor):
    _drop_ui_orphans(editor)
    editor._mark_dirty()
    _refresh_ui_tabs(editor)


def _store_ui_png(editor, stem, path=None):
    if path is None:
        path, _ = QFileDialog.getOpenFileName(editor, "Choose PNG", "", "PNG images (*.png)")
    if not path:
        return None
    try:
        image = pngio.read(path)
    except (OSError, ValueError, pngio.PngError) as problem:
        QMessageBox.critical(editor, "UI Assets", f"That PNG cannot be read: {problem}")
        return None
    base = re.sub(r"[^a-z0-9_-]+", "-", stem.casefold()).strip("-") or "image"
    name, number = f"ui/{base}.png", 2
    while name in editor.project.files:
        name = f"ui/{base}-{number}.png"; number += 1
    editor.project.files[name] = pngio.encode(image)
    return name


def _ui_image(editor, name):
    if not isinstance(name, str) or not name:
        return None
    try:
        if name in editor.project.files:
            return pngio.decode(editor.project.files[name])
        if editor.project.source_dir:
            return pngio.read(Path(editor.project.source_dir) / name)
    except (OSError, ValueError, pngio.PngError):
        pass
    return None


def _export_ui_png(editor, image, suggested_name):
    """Export a selected UI graphic with the same PNG path used by Board."""
    if image is None:
        QMessageBox.information(editor, "UI Assets", "The selected asset has no picture to export.")
        return
    path, _ = QFileDialog.getSaveFileName(editor, "Export UI asset", suggested_name, "PNG images (*.png)")
    if not path:
        return
    try:
        pngio.write(path, image)
    except OSError as problem:
        QMessageBox.critical(editor, "UI Assets", f"Could not export the PNG: {problem}")


def _colour(text, default="#FFFFFF"):
    value = str(text).strip()
    if re.fullmatch(r"#[0-9a-fA-F]{6}", value):
        return value.upper()
    return default


# ``card_layout.frame_styles`` is deliberately edited here rather than through
# the named-asset catalogue.  It is a layout rule read by the card viewer and
# duel renderer, while the catalogue is a texture replacement registry.
# Keep the schema in one table, matching ui_frames.py without importing its
# Tkinter UI module into the PySide application.
_FRAME_PARTS = (
    ("frame", "Frame image", ("image",), (0, 0, 140, 196), False, True, True),
    ("back", "Back image", ("back_image",), (0, 0, 140, 196), False, True, True),
    ("hand", "Duel hand image", ("hand_image",), (0, 0, 52, 60), False, False, True),
    ("field", "Face-up field image", ("field_image",), (0, 0, 40, 56), False, False, True),
    ("field_back", "Face-down field image", ("field_back_image",), (0, 0, 40, 56), False, False, True),
    ("library", "Library icon", ("library_icon",), (0, 0, 24, 32), False, False, True),
    ("digits", "Digit strip", ("digits",), (0, 0, 10, 12), False, True, True),
    ("title", "Card name", ("title",), (12, 14, 96, 14), True, False, False),
    ("art", "Artwork", ("art",), (19, 50, 102, 96), True, True, False),
    ("stars", "Level stars", ("stars",), (119, 32, 56, 9), True, False, False),
    ("attribute", "Attribute icon", ("attribute",), (110, 13, 16, 16), True, True, False),
    ("atk", "ATK value", ("digits", "atk"), (117, 163, 10, 12), True, True, False),
    ("def", "DEF value", ("digits", "def"), (117, 177, 10, 12), True, True, False),
    ("atk_label", "ATK label", ("atk_label",), (74, 162, 16, 8), True, True, True),
    ("dfd_label", "DFD label", ("dfd_label",), (74, 173, 16, 8), True, True, True),
    ("magic_label", "Magic-card caption", ("type_label", "magic"), (84, 35, 56, 16), True, True, True),
    ("equip_label", "Equip-card caption", ("type_label", "equip"), (84, 35, 56, 16), True, True, True),
    ("ritual_label", "Ritual-card caption", ("type_label", "ritual"), (84, 35, 56, 16), True, True, True),
    ("trap_label", "Trap-card caption", ("type_label", "trap"), (84, 35, 56, 16), True, True, True),
    ("spell_icon", "Spell/trap icon", ("spell", "icon"), (110, 13, 16, 16), True, True, False),
    ("hand_art", "Hand artwork", ("hand", "art"), (6, 6, 40, 32), True, True, False),
    ("hand_atk", "Hand ATK", ("hand", "atk"), (14, 40, 8, 8), True, True, False),
    ("hand_def", "Hand DEF", ("hand", "def"), (14, 48, 8, 8), True, True, False),
    ("hand_atk_label", "Hand ATK label", ("hand", "atk_label"), (5, 40, 8, 8), True, True, False),
    ("hand_dfd_label", "Hand DFD label", ("hand", "dfd_label"), (5, 48, 8, 8), True, True, False),
)
_FRAME_SPEC = {item[0]: item for item in _FRAME_PARTS}
_FRAME_DIRECT = {"frame", "back", "hand", "field", "field_back", "library"}
_FRAME_IMAGE = {"digits", "atk_label", "dfd_label", "magic_label", "equip_label", "ritual_label", "trap_label"}
_FRAME_MOVABLE = {part[0] for part in _FRAME_PARTS if part[0] not in _FRAME_DIRECT}
# gamedata.FRAME_NAMES order (cards.c frame_names): equip draws as magic,
# the same rule gamedata.type_frame uses for a card's own shown_frame().
_FRAME_INDEX = {"monster": 0, "magic": 1, "equip": 1, "trap": 2, "ritual": 3}

# Retail card-view sprites live in WA_MRG.MRG.  These three extractors are
# copied from card_icons.py instead of importing it: card_icons also imports
# Tkinter for the classic editor's PhotoImage adapter, which the PySide build
# must not require.
_CARD_SHEET, _CARD_PALETTES = 0xEFE800, 0xF06800
_BALL_PALETTE, _STAR_PALETTE, _LABEL_PALETTE = 0x1E00, 0x1180, 0x11E0
_frame_title_faces = {}
_frame_title_images = {}
_FRAME_RENDER_SCALE = 4


def _frame_vram_picture(wa, base, u, v, width, height, palette):
    if not wa or len(wa) < max(base + (v + height) * 128, palette + 32):
        return None
    rgba = bytearray()
    for y in range(height):
        for x in range(width):
            texel = u + x
            index = wa[base + (v + y) * 128 + texel // 2] >> (4 * (texel & 1)) & 15
            word = wa[palette + 2 * index] | wa[palette + 2 * index + 1] << 8
            rgba += bytes(((word & 31) << 3, (word >> 5 & 31) << 3,
                           (word >> 10 & 31) << 3, 0 if index == 0 or word == 0 else 255))
    return pngio.Image(width, height, bytes(rgba)) if any(rgba[3::4]) else None


def _frame_attribute(wa, index):
    return _frame_vram_picture(wa, _CARD_SHEET, 16 * index, 128, 16, 16,
                               _CARD_PALETTES + _BALL_PALETTE + 0x20 * index) if 0 <= index < 8 else None


def _frame_star(wa):
    return _frame_vram_picture(wa, _CARD_SHEET, 0, 144, 9, 9, _CARD_PALETTES + _STAR_PALETTE)


def _frame_caption(wa, kind):
    row = {"magic": 158, "trap": 174, "ritual": 158, "equip": 190}.get(kind)
    return _frame_vram_picture(wa, _CARD_SHEET, 0, row, 56, 16,
                               _CARD_PALETTES + _LABEL_PALETTE) if row is not None else None


# The hand's stat overlay is not text: duel_card_frame_draw.c samples these
# 8x8 sprites from the duel boot texture page. Keep a small decoded VRAM
# cache so the Hand preview uses the same digits, sword and shield as game.
_HAND_SHEETS = {}


def _hand_sprite(wa, u, v, width=8, height=8):
    if not wa:
        return None
    key = id(wa)
    sheet = _HAND_SHEETS.get(key)
    if sheet is None:
        sheet = _HAND_SHEETS[key] = ui_assets.DuelArt(wa)
    if not sheet.ok:
        return None
    source = ("frame-hand-sprite", u, v, width, height)
    return sheet._cached(source, lambda: sheet.vram.sprite(896, 256, 8, 256, 241, u, v, width, height))


def _duel_cell(wa, u, v, frame_index, w=52, h=60):
    """One 52x60 cell of the duel hand/field sprite page: the same VRAM page
    and per-kind palette row scheme as duel_screen.HAND_FRAME/HAND_CLUT, just
    a different (u, v) within it."""
    if not wa:
        return None
    key = id(wa)
    sheet = _HAND_SHEETS.get(key)
    if sheet is None:
        sheet = _HAND_SHEETS[key] = ui_assets.DuelArt(wa)
    if not sheet.ok:
        return None
    page_x, page_y, bits, _u, _v, _w, _h = duel_screen.HAND_FRAME
    clut_x, clut_y = duel_screen.HAND_CLUT
    source = ("frame-duel-cell", u, v, w, h, frame_index)
    return sheet._cached(source, lambda: sheet.vram.sprite(page_x, page_y, bits, clut_x, clut_y + frame_index, u, v, w, h))


def _hand_frame_background(wa, frame_index):
    """The plain 52x60 hand-card plate (duel_screen.HAND_FRAME/HAND_CLUT),
    the same disc pixels hand_card() composes a duel hand with."""
    page_x, page_y, bits, u, v, w, h = duel_screen.HAND_FRAME
    return _duel_cell(wa, u, v, frame_index, w, h)


# The face-down and face-up field cells sit one 52x60 cell away from the hand
# on the same duel VRAM page: face-down at (56, 128), one cell right of the
# hand and shared by every card kind; face-up at (0, 192) for a monster or
# (56, 192) for anything else (a monster's cell keeps room for its own
# ATK/DEF plaque, which a non-monster field card never shows).
def _field_back_frame_background(wa, frame_index):
    return _duel_cell(wa, 56, 128, frame_index)


def _field_frame_background(wa, frame_index, is_monster):
    return _duel_cell(wa, 0 if is_monster else 56, 192, frame_index)


_BACK_SHEETS = {}


def _card_back_background(wa, frame_index):
    """The plain 140x192 card-back plate: the Library atlas' "right" page
    (0xEE6800 + 16 sectors, the same page _card_frame_background crops the
    front's own 12px right-edge trim from) holds the back's right edge and
    the top half of its swirl body in its lower half; the next page over
    (+32 sectors) continues that same swirl, cut off at its own top edge,
    for the bottom half. Confirmed by stacking the two: the spiral lines up
    exactly across the page boundary."""
    if not wa:
        return None
    key = (id(wa), frame_index)
    if key in _BACK_SHEETS:
        return _BACK_SHEETS[key]
    clut_offset = 0xF06800 + (8 + frame_index) * 0x200
    try:
        palette = image_extract.read_palette(wa, clut_offset, 256)
        right_w, right_h, right_rgba = image_extract.decode(wa, 0xEE6800 + 16 * image_extract.SECTOR, 64, 256, 8, palette)
        foot_w, foot_h, foot_rgba = image_extract.decode(wa, 0xEE6800 + 32 * image_extract.SECTOR, 64, 256, 8, palette)
    except (IndexError, ValueError, struct.error):
        return None
    right, foot = pngio.Image(right_w, right_h, right_rgba), pngio.Image(foot_w, foot_h, foot_rgba)
    main_top, main_bottom = pngio.crop(right, 0, 128, 128, 128), pngio.crop(foot, 0, 0, 128, 64)
    edge_top, edge_bottom = pngio.crop(right, 16, 0, 12, 128), pngio.crop(right, 48, 0, 12, 64)
    frame = QImage(140, 192, QImage.Format.Format_ARGB32_Premultiplied)
    frame.fill(QColor(0, 0, 0, 0))
    painter = QPainter(frame)
    painter.drawImage(QRect(0, 0, 128, 128), _qimage(main_top.width, main_top.height, main_top.rgba))
    painter.drawImage(QRect(0, 128, 128, 64), _qimage(main_bottom.width, main_bottom.height, main_bottom.rgba))
    painter.drawImage(QRect(128, 0, 12, 128), _qimage(edge_top.width, edge_top.height, edge_top.rgba))
    painter.drawImage(QRect(128, 128, 12, 64), _qimage(edge_bottom.width, edge_bottom.height, edge_bottom.rgba))
    painter.end()
    _BACK_SHEETS[key] = frame
    return frame


_LIBRARY_ICON_SHEETS = {}
# Library_DrawCardGrid's own retail fallback (func_80029EC4.c) reads a fixed
# 12x14-ish cell, tinted per card kind by its own 16-entry (4bpp) palette
# row; the row index was found empirically, not from a documented table --
# each one visually confirmed against the kind it names (monster gold+red,
# magic green, trap pink, ritual blue), not assumed from their spacing.
_LIBRARY_ICON_OFFSET, _LIBRARY_ICON_CLUT = 17713152, 17733120
_LIBRARY_ICON_ROW = {0: 3, 1: 6, 2: 8, 3: 10}   # monster, magic, trap, ritual


def _library_icon_background(wa, frame_index):
    """The plain Library-grid card icon, tinted for `frame_index`."""
    if not wa:
        return None
    row = _LIBRARY_ICON_ROW.get(frame_index)
    if row is None:
        return None
    key = (id(wa), frame_index)
    if key in _LIBRARY_ICON_SHEETS:
        return _LIBRARY_ICON_SHEETS[key]
    try:
        palette = image_extract.read_palette(wa, _LIBRARY_ICON_CLUT + row * 0x20, 16)
        w, h, rgba = image_extract.decode(wa, _LIBRARY_ICON_OFFSET, 64, 128, 4, palette)
    except (IndexError, ValueError, struct.error):
        return None
    icon = pngio.crop(pngio.Image(w, h, rgba), 96, 112, 12, 14)
    _LIBRARY_ICON_SHEETS[key] = icon
    return icon


def _frame_sized(image, width, height):
    return pngio.scale_to(image, width, height) if image is not None and image.size != (width, height) else image


def _frame_text_picture(font, text, width, height, color):
    if not font or not text:
        return None
    cells = [font.cell(character) for character in text]
    native_w, native_h = max(1, len(cells) * card_text.CELL_W), card_text.CELL_H
    rgba = bytearray(native_w * native_h * 4)
    try:
        rgb = tuple(int(color[index:index + 2], 16) for index in (1, 3, 5))
    except (TypeError, ValueError):
        rgb = (255, 255, 255)
    for column, cell in enumerate(cells):
        if cell is None:
            continue
        for y in range(card_text.CELL_H):
            for x in range(card_text.CELL_W):
                if cell[y * card_text.CELL_W + x]:
                    at = (y * native_w + column * card_text.CELL_W + x) * 4
                    rgba[at:at + 4] = bytes((*rgb, 255))
    return _frame_sized(pngio.Image(native_w, native_h, bytes(rgba)), width, height)


def _frame_title_picture(text, width, height, color):
    """CardArt_TitlePicture's four-times title plate for the Frames preview.

    The original Frames page keeps this 4x plate until it is painted onto its
    zoomed preview.  Reducing it to a 96x14 image first loses the game's
    antialiasing and makes the title look like the 8x12 UI font.
    """
    if not text:
        return None
    key = (text, max(1, width), max(1, height), color)
    if key in _frame_title_images:
        return _frame_title_images[key]
    try:
        face = _frame_title_face()
        if face is None:
            return None
        inks = packs.name_plate_inks(text, face, _FRAME_RENDER_SCALE)
    except (ttf.FontError, OSError, ValueError, IndexError, KeyError):
        return None
    if inks is None:
        return None
    try:
        rgb = tuple(int(color[index:index + 2], 16) for index in (1, 3, 5))
    except (TypeError, ValueError):
        rgb = (255, 255, 255)
    factor = _FRAME_RENDER_SCALE
    rgba = bytearray(96 * factor * 14 * factor * 4)
    for index, ink in enumerate(inks):
        if ink:
            alpha = round(255 * art.INK_SHARE[ink]) if ink < len(art.INK_SHARE) else 0
            rgba[index * 4:index * 4 + 4] = bytes((*rgb, alpha))
    picture = _frame_sized(pngio.Image(96 * factor, 14 * factor, bytes(rgba)),
                           max(1, width) * factor, max(1, height) * factor)
    _frame_title_images[key] = picture
    return picture


def _frame_title_face():
    """The same Times-style TTF search as the classic Frames preview.

    The game's title generator wants Times.  Some Linux systems resolve it to
    a CFF font, which the small shared TTF reader cannot load; fall back to a
    real TrueType serif face before using the game-font fallback.
    """
    candidates = [packs.serif_path()]
    command = shutil.which("fc-match")
    if command:
        for family in ("Liberation Serif:regular", "Noto Serif:regular", "serif:regular"):
            try:
                candidates.append(subprocess.run([command, "-f", "%{file}", family], capture_output=True,
                                                 text=True, timeout=5).stdout.strip())
            except (OSError, subprocess.SubprocessError):
                continue
    for path in candidates:
        if not path or not Path(path).is_file():
            continue
        try:
            face = _frame_title_faces.get(path)
            if face is None:
                face = _frame_title_faces[path] = ttf.Font(path)
            return face
        except (ttf.FontError, OSError, ValueError):
            continue
    return None


def _frame_digit_cell(strip, digit):
    if strip is None or not 0 <= digit <= 9:
        return None
    column, row = digit % 5, digit // 5 + 2
    return pngio.crop(strip, column * 40, row * 48, 40, 48)


def _frame_draw_picture(painter, image, box):
    if image is not None:
        painter.drawImage(box, _qimage(image.width, image.height, image.rgba))


def _frame_layout(editor, create=False):
    # Holding the retail-comparison button affects preview rendering only.  It
    # must never temporarily remove card_layout from the live project.
    frames = editor.workspace_controls.get("UI", {}).get("frames", {})
    if frames.get("retail_preview") and not create:
        return {}
    value = editor.project.other.get("card_layout")
    if isinstance(value, dict):
        return value
    if create:
        editor.project.other["card_layout"] = value = {}
        return value
    return {}


def _frame_styles(editor, create=False):
    layout = _frame_layout(editor, create)
    value = layout.get("frame_styles")
    if isinstance(value, dict):
        return value
    if create:
        layout["frame_styles"] = value = {}
        return value
    return {}


def _frame_style(editor, create=False):
    name = _frame_style_name(editor)
    styles = _frame_styles(editor, create)
    value = styles.get(name)
    if isinstance(value, dict):
        return value
    if create:
        styles[name] = value = {"hand_color": "gold"}
        if len(styles) == 1:
            _frame_layout(editor, True).setdefault("default_style", name)
        return value
    return {}


def _frame_style_name(editor):
    c = editor.workspace_controls["UI"]["frames"]
    item = c["style"].currentItem()
    return (item.text().strip() if item is not None else c.get("style_name", "custom")) or "custom"


def _frame_part(editor, key, create=False):
    style = _frame_style(editor, create)
    path = _FRAME_SPEC[key][2]
    if key in _FRAME_DIRECT:
        return style
    for name in path:
        value = style.get(name)
        if not isinstance(value, dict):
            if not create:
                return {}
            style[name] = value = {}
        style = value
    return style


def _frame_size_owner(editor, key, create=False):
    # The digit sprite has one shared glyph size for ATK and DEF, exactly as
    # the runtime does.  Its positions remain independently editable.
    if key in ("atk", "def"):
        style = _frame_style(editor, create)
        value = style.get("digits")
        if not isinstance(value, dict) and create:
            style["digits"] = value = {}
        return value if isinstance(value, dict) else {}
    return _frame_style(editor, create) if key in _FRAME_DIRECT else _frame_part(editor, key, create)


def _frame_rect(editor, key):
    _, _, _, default, _, _, _ = _FRAME_SPEC[key]
    part = _frame_part(editor, key)
    owner = _frame_size_owner(editor, key)
    return (_as_int(part.get("x"), default[0]), _as_int(part.get("y"), default[1]),
            max(1, _as_int(owner.get("width"), default[2])), max(1, _as_int(owner.get("height"), default[3])))


def _frame_asset(editor, key):
    style = _frame_style(editor)
    if key in _FRAME_DIRECT:
        value = style.get(_FRAME_SPEC[key][2][0])
    elif key in _FRAME_IMAGE:
        value = _frame_part(editor, key).get("image")
    else:
        value = None
    return value if isinstance(value, str) else None


def _set_frame_asset(editor, key, image):
    if key in _FRAME_DIRECT:
        _put(_frame_style(editor, True), _FRAME_SPEC[key][2][0], image)
    elif key in _FRAME_IMAGE:
        _put(_frame_part(editor, key, True), "image", image)


def _frame_commit(editor):
    _drop_frame_orphans(editor)
    editor._mark_dirty()
    _refresh_frames_tab(editor)


def _drop_frame_orphans(editor):
    used = _ui_strings(editor.project.other)
    for name in tuple(editor.project.files):
        if name.startswith("frames/") and name not in used:
            editor.project.files.pop(name, None)
            editor.project.deleted_files.add(name)


def _queue_frame_redraw(editor):
    """Limit drag repainting to the display cadence instead of every event."""
    c = editor.workspace_controls["UI"]["frames"]
    timer = c.get("drag_render_timer")
    if timer is None:
        timer = c["drag_render_timer"] = QTimer(c["preview"])
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: _draw_frames(editor))
    if not timer.isActive():
        timer.start(16)


class _FramePreviewEvents(QObject):
    def __init__(self, editor, parent):
        super().__init__(parent); self.editor = editor

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            point = _frame_preview_point(watched, event.position())
            key = _preview_key(self.editor.workspace_controls["UI"]["frames"].get("boxes", {}), point)
            if key:
                c = self.editor.workspace_controls["UI"]["frames"]
                x, y, _, _ = _frame_rect(self.editor, key)
                c["selected"] = key
                c["drag"] = {"key": key, "origin": point, "x": x, "y": y, "moved": False}
                _refresh_frames_tab(self.editor)
            return True
        if event.type() == QEvent.Type.MouseMove and event.buttons() & Qt.MouseButton.LeftButton:
            c = self.editor.workspace_controls["UI"]["frames"]; drag = c.get("drag")
            if not drag: return True
            key = drag["key"]
            if key not in _FRAME_MOVABLE: return True
            x, y = _frame_preview_point(watched, event.position())
            origin_x, origin_y = drag["origin"]
            next_x, next_y = drag["x"] + round(x - origin_x), drag["y"] + round(y - origin_y)
            current_x, current_y, _, _ = _frame_rect(self.editor, key)
            if (next_x, next_y) == (current_x, current_y): return True
            part, default = _frame_part(self.editor, key, True), _FRAME_SPEC[key][3]
            _put(part, "x", next_x, default[0]); _put(part, "y", next_y, default[1])
            drag["moved"] = True
            _queue_frame_redraw(self.editor)
            return True
        if event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
            c = self.editor.workspace_controls["UI"]["frames"]; drag = c.pop("drag", None)
            timer = c.get("drag_render_timer")
            if timer is not None and timer.isActive(): timer.stop()
            if drag and drag["moved"]: _frame_commit(self.editor)
            return True
        if event.type() == QEvent.Type.Wheel:
            c = self.editor.workspace_controls["UI"]["frames"]; key = c.get("selected", "frame")
            if _FRAME_SPEC[key][5]:
                owner = _frame_size_owner(self.editor, key, True); _, _, width, height = _frame_rect(self.editor, key); default = _FRAME_SPEC[key][3]
                step = 4 if event.angleDelta().y() > 0 else -4
                _put(owner, "width", max(1, min(140, width + step)), default[2]); _put(owner, "height", max(1, min(196, height + step)), default[3])
                _frame_commit(self.editor)
            return True
        if event.type() == QEvent.Type.Resize: _rescale_preview_label(watched)
        return False


def _frame_preview_point(label, position):
    scale = min(label.width() / 140, label.height() / 196)
    if scale <= 0: return 0, 0
    return ((position.x() - (label.width() - 140 * scale) / 2) / scale,
            (position.y() - (label.height() - 196 * scale) / 2) / scale)


def _frame_preview_kind(controls):
    for key, name in (("magic", "magicRadio"), ("equip", "equipRadio"),
                      ("ritual", "ritualRadio"), ("trap", "trapRadio")):
        if _frames_widget(controls["form"], QRadioButton, name).isChecked():
            return key
    return "monster"


def _frames_widget(form, kind, name):
    value = form.findChild(kind, name)
    if value is None:
        raise RuntimeError(f"Frames form is missing {name}")
    return value


def _wire_frames_tab(editor, form, controls):
    from PySide6.QtWidgets import QListWidget, QTreeWidget
    c = {
        "form": form, "style": _frames_widget(form, QListWidget, "frameStyleList"),
        "parts": _frames_widget(form, QTreeWidget, "partsTree"),
        "preview": _frames_widget(form, QLabel, "cardCanvas"),
        "x": _frames_widget(form, QSpinBox, "xSpin"), "y": _frames_widget(form, QSpinBox, "ySpin"),
        "width": _frames_widget(form, QSpinBox, "widthSpin"), "height": _frames_widget(form, QSpinBox, "heightSpin"),
        "visible": _frames_widget(form, QCheckBox, "hiddenCheck"),
        "image": _frames_widget(form, QLabel, "imagePathLabel"),
        "kind_rule": _frames_widget(form, QComboBox, "kindCombo"),
        "type_rule": _frames_widget(form, QComboBox, "typeCombo"),
        "card_rule": _frames_widget(form, QLineEdit, "specificCardInput"),
        "selected": "frame", "style_name": "custom", "loading": False, "boxes": {},
    }
    controls["frames"] = c
    c["face_group"] = QButtonGroup(form)
    for name in ("frontRadio", "backRadio"):
        c["face_group"].addButton(_frames_widget(form, QRadioButton, name))
    c["preview_kind_group"] = QButtonGroup(form)
    for name in ("monsterRadio", "magicRadio", "equipRadio", "ritualRadio", "trapRadio"):
        c["preview_kind_group"].addButton(_frames_widget(form, QRadioButton, name))
    _frames_widget(form, QRadioButton, "frontRadio").setChecked(True)
    _frames_widget(form, QRadioButton, "monsterRadio").setChecked(True)
    for combo, values in ((c["kind_rule"], (("monster", "Monster"), ("effect_monster", "Effect monster"), ("magic", "Magic"), ("equip", "Equip"), ("ritual", "Ritual"), ("trap", "Trap"))),):
        combo.clear()
        for value, label in values: combo.addItem(label, value)
    c["type_rule"].clear()
    for type_id, name in enumerate(TYPE_NAMES):
        if name: c["type_rule"].addItem(name, name)
    bridge = _FramePreviewEvents(editor, c["preview"])
    c["preview"].setMouseTracking(True); c["preview"].setFocusPolicy(Qt.FocusPolicy.StrongFocus); c["preview"].installEventFilter(bridge); c["events"] = bridge
    c["parts"].currentItemChanged.connect(lambda item, _: _frame_select(editor, item))
    c["style"].currentItemChanged.connect(lambda item, _: _frame_style_changed(editor, item))
    for name in ("frontRadio", "backRadio", "monsterRadio", "magicRadio", "equipRadio", "ritualRadio", "trapRadio"):
        _frames_widget(form, QRadioButton, name).toggled.connect(lambda _: _draw_frames(editor))
    c["card_rule"].textChanged.connect(lambda _: _draw_frames(editor))
    for field in (c["x"], c["y"], c["width"], c["height"]): field.valueChanged.connect(lambda _: _frame_geometry_changed(editor))
    c["visible"].toggled.connect(lambda _: _frame_geometry_changed(editor))
    _frames_widget(form, QPushButton, "newStyleButton").clicked.connect(lambda: _frame_new_style(editor))
    _frames_widget(form, QPushButton, "deleteStyleButton").clicked.connect(lambda: _frame_delete_style(editor))
    _frames_widget(form, QPushButton, "chooseImageButton").clicked.connect(lambda: _frame_import(editor))
    _frames_widget(form, QPushButton, "exportImageButton").clicked.connect(lambda: _frame_export(editor))
    _frames_widget(form, QPushButton, "removeImageButton").clicked.connect(lambda: _frame_clear_image(editor))
    _frames_widget(form, QPushButton, "resetElementButton").clicked.connect(lambda: _frame_reset_part(editor))
    _frames_widget(form, QPushButton, "setGlobalDefaultButton").clicked.connect(lambda: _frame_assign(editor, "default", True))
    _frames_widget(form, QPushButton, "resetGlobalDefaultButton").clicked.connect(lambda: _frame_assign(editor, "default", False))
    _frames_widget(form, QPushButton, "applyKindButton").clicked.connect(lambda: _frame_assign(editor, "kind", True))
    _frames_widget(form, QPushButton, "resetKindButton").clicked.connect(lambda: _frame_assign(editor, "kind", False))
    _frames_widget(form, QPushButton, "applyTypeButton").clicked.connect(lambda: _frame_assign(editor, "type", True))
    _frames_widget(form, QPushButton, "resetTypeButton").clicked.connect(lambda: _frame_assign(editor, "type", False))
    _frames_widget(form, QPushButton, "applyCardButton").clicked.connect(lambda: _frame_assign(editor, "card", True))
    _frames_widget(form, QPushButton, "resetCardButton").clicked.connect(lambda: _frame_assign(editor, "card", False))
    _frames_widget(form, QPushButton, "browseCardButton").clicked.connect(lambda: _frame_browse_card(editor))
    _frames_widget(form, QPushButton, "revertRetailButton").clicked.connect(lambda: _frame_revert_all(editor))
    hold = _frames_widget(form, QPushButton, "showRetailButton")
    hold.pressed.connect(lambda: _frame_hold(editor, True)); hold.released.connect(lambda: _frame_hold(editor, False))
    # A workspace switch also ends visual comparison if the platform does not
    # deliver a mouse-release event to the hold button.
    editor.pages.currentChanged.connect(lambda _: _frame_hold(editor, False))
    _refresh_frames_tab(editor)


def _frame_select(editor, item):
    if item is None or editor.workspace_controls["UI"]["frames"].get("loading"):
        return
    key = item.data(0, Qt.ItemDataRole.UserRole)
    if key in _FRAME_SPEC:
        editor.workspace_controls["UI"]["frames"]["selected"] = key
        _refresh_frames_tab(editor)


def _frame_style_changed(editor, item):
    c = editor.workspace_controls["UI"]["frames"]
    if item is not None:
        c["style_name"] = item.text()
    if not c.get("loading"):
        _refresh_frames_tab(editor)


def _refresh_frames_tab(editor):
    c = editor.workspace_controls.get("UI", {}).get("frames")
    if not c or c.get("loading"):
        return
    c["loading"] = True
    try:
        styles = _frame_styles(editor); names = list(styles) or ["custom"]
        current = _frame_style_name(editor)
        if current not in names: current = names[0]
        c["style_name"] = current
        c["style"].blockSignals(True); c["style"].clear(); c["style"].addItems(names)
        c["style"].setCurrentRow(names.index(current)); c["style"].blockSignals(False)
        from PySide6.QtWidgets import QTreeWidgetItem
        tree = c["parts"]; tree.blockSignals(True); tree.clear(); chosen = None
        groups = (("Main", _FRAME_PARTS[:2] + _FRAME_PARTS[6:20]), ("Hand", _FRAME_PARTS[2:3] + _FRAME_PARTS[20:]),
                  ("Field", _FRAME_PARTS[3:5]), ("Library", _FRAME_PARTS[5:6]))
        for label, parts in groups:
            root = QTreeWidgetItem([label]); root.setFlags(root.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            tree.addTopLevelItem(root)
            for key, part_label, *_ in parts:
                item = QTreeWidgetItem([part_label]); item.setData(0, Qt.ItemDataRole.UserRole, key); root.addChild(item)
                if key == c["selected"]: chosen = item
        tree.expandAll(); tree.setCurrentItem(chosen or tree.topLevelItem(0).child(0)); tree.blockSignals(False)
        key = c["selected"]; spec = _FRAME_SPEC[key]; x, y, width, height = _frame_rect(editor, key)
        for name, value in (("x", x), ("y", y), ("width", width), ("height", height)):
            c[name].blockSignals(True); c[name].setValue(value); c[name].blockSignals(False)
        can_move, can_size = key in _FRAME_MOVABLE, spec[5]
        for name, enabled in (("x", can_move), ("y", can_move), ("width", can_size), ("height", can_size)):
            c[name].setEnabled(enabled)
        part = _frame_part(editor, key)
        c["visible"].blockSignals(True); c["visible"].setChecked(bool(part.get("hide", False))); c["visible"].setEnabled(spec[4]); c["visible"].blockSignals(False)
        c["image"].setText(_frame_asset(editor, key) or "Uses the game's artwork")
        c["image"].setEnabled(spec[6])
        has_image = _frame_asset(editor, key) is not None
        _frames_widget(c["form"], QPushButton, "chooseImageButton").setEnabled(spec[6])
        for name in ("exportImageButton", "removeImageButton"):
            _frames_widget(c["form"], QPushButton, name).setEnabled(spec[6] and has_image)
        _frames_widget(c["form"], QLabel, "elementName").setText(spec[1])
        _frames_widget(c["form"], QLabel, "styleProperty").setText(current)
        _draw_frames(editor)
    finally:
        c["loading"] = False


def _draw_frames(editor):
    c = editor.workspace_controls.get("UI", {}).get("frames")
    if not c: return
    # Frames are composed at the same four-times internal resolution that the
    # game uses for HD card names.  Logical coordinates remain console pixels,
    # so the editor fields and hit-testing still exactly match the original.
    image = QImage(140 * _FRAME_RENDER_SCALE, 196 * _FRAME_RENDER_SCALE,
                   QImage.Format.Format_RGBA8888)
    image.fill(QColor("#06111e"))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
    painter.scale(_FRAME_RENDER_SCALE, _FRAME_RENDER_SCALE)
    selected = c.get("selected", "frame")
    if selected == "hand" or selected.startswith("hand_"):
        _draw_hand_template(editor, painter, c)
        painter.end(); _set_preview_pixmap(c["preview"], QPixmap.fromImage(image)); return
    if selected in {"field", "field_back"}:
        _draw_field_template(editor, painter, c, selected)
        painter.end(); _set_preview_pixmap(c["preview"], QPixmap.fromImage(image)); return
    if selected == "library":
        _draw_library_template(editor, painter, c)
        painter.end(); _set_preview_pixmap(c["preview"], QPixmap.fromImage(image)); return
    face = _frames_widget(c["form"], QRadioButton, "frontRadio").isChecked()
    kind = _frame_preview_kind(c)
    wa = getattr(getattr(editor, "files", None), "wa", None)
    painter.fillRect(0, 0, 140, 196, QColor("#06080d")); c["boxes"] = {}
    base = "frame" if face else "back"
    bx, by, bw, bh = _frame_rect(editor, base)
    c["boxes"][base] = (bx, by, bw, bh)
    frame_image = _ui_image(editor, _frame_asset(editor, base))
    if frame_image is not None:
        _frame_draw_picture(painter, frame_image, QRect(bx, by, bw, bh))
    elif base == "frame" and wa:
        plate = _card_frame_background(editor.project, wa, _FRAME_INDEX[kind], kind == "monster",
                                       c.setdefault("retail_frame_cache", {}), _FRAME_RENDER_SCALE)
        painter.drawImage(QRect(bx, by, bw, bh), plate)
    elif base == "back" and _card_back_background(wa, _FRAME_INDEX[kind]) is not None:
        painter.drawImage(QRect(bx, by, bw, bh), _card_back_background(wa, _FRAME_INDEX[kind]))
    else:
        painter.fillRect(bx, by, bw, bh, QColor("#35415b")); painter.setPen(QColor("#9da9bf")); painter.drawRect(bx, by, bw, bh)
    if not face:
        _draw_frame_selected_outline(painter, c); painter.end(); _set_preview_pixmap(c["preview"], QPixmap.fromImage(image)); return

    # This is the same 140×196 card-view composition as the classic Frames
    # page: retail art, VRAM star/attribute/caption sprites, the game font,
    # and its title plate.  It deliberately does not use generic Qt text.
    try: font = card_text.RetailFont(wa) if wa else None
    except ValueError: font = None
    retail_art = art.in_game(editor.project, wa, _frame_card_id(editor) or 1, "art", _FRAME_RENDER_SCALE) if wa else None
    star_icon, attribute_icon = _frame_star(wa), _frame_attribute(wa, 0)
    caption_key = f"{kind}_label" if kind != "monster" else None
    caption = _frame_caption(wa, kind) if caption_key else None
    parts = [("art", "#245175", "CARD ART"), ("title", "#ffffff", "Blue-eyes White Dragon")]
    if kind == "monster":
        parts += [("stars", "#ffcf41", ""), ("attribute", "#ffe171", ""), ("atk", "#211503", "3000"),
                  ("def", "#211503", "2500"), ("atk_label", "#211503", "ATK"), ("dfd_label", "#211503", "DFD")]
    else:
        label_text = {"magic_label": "Normal Magic Card", "equip_label": "Equip Magic Card",
                      "ritual_label": "Ritual Magic Card", "trap_label": "Trap Card"}[caption_key]
        parts += [("spell_icon", "#ffe171", ""), (caption_key, "#111111", label_text)]
        attribute_icon = _frame_attribute(wa, 7 if kind == "trap" else 6)
    digits_image = _ui_image(editor, _frame_asset(editor, "digits"))
    for key, color, text in parts:
        part = _frame_part(editor, key); can_hide = _FRAME_SPEC[key][4]
        x, y, width, height = _frame_rect(editor, key)
        if key in ("atk", "def"):
            step = _as_int(_frame_part(editor, "digits").get("step"), width)
            width = (len(text) - 1) * step + width; x -= width // 2; y -= height // 2
        box = QRect(x, y, width, height); c["boxes"][key] = (x, y, width, height)
        if can_hide and part.get("hide") is True:
            painter.setPen(QPen(QColor("#999999"), 1, Qt.PenStyle.DashLine)); painter.drawRect(box); continue
        asset = _ui_image(editor, _frame_asset(editor, key))
        if asset is not None:
            _frame_draw_picture(painter, asset, box)
        elif key == "art" and retail_art is not None:
            _frame_draw_picture(painter, retail_art, box)
        elif key == "art":
            painter.fillRect(box, QColor(color)); painter.setPen(QColor("#b9c7da")); painter.drawRect(box)
        elif key == "stars" and star_icon is not None:
            for number in range(12): _frame_draw_picture(painter, star_icon, QRect(x - number * 9, y, 9, 9))
            c["boxes"][key] = (x - 99, y, 108, 9)
        elif key in ("attribute", "spell_icon") and attribute_icon is not None:
            _frame_draw_picture(painter, attribute_icon, box)
        elif key == caption_key and caption is not None:
            _frame_draw_picture(painter, caption, box)
        elif key in ("atk", "def") and digits_image is not None:
            step = _as_int(_frame_part(editor, "digits").get("step"), _frame_rect(editor, key)[2])
            glyph_w, glyph_h = _frame_rect(editor, key)[2:]
            for number, character in enumerate(text):
                _frame_draw_picture(painter, _frame_digit_cell(digits_image, int(character)), QRect(x + number * step, y, glyph_w, glyph_h))
        elif key in ("atk_label", "dfd_label", "atk", "def"):
            # The retail font's 8x12 glyph cells, scaled down into this
            # small a box, blur into unreadable blobs (three letters in
            # 16x8, or four digits squeezed into one glyph's own width, are
            # already tighter than the cell size on their own). Vector text
            # stays crisp at any box size, the same reason the name gets its
            # own HD plate instead of the retail font's cells. The game's
            # own HD path reproduces its serif pixel font's exact shape
            # rather than substituting a system face; _draw_hd_card_title
            # already approximates that with Times New Roman for the name,
            # so match it here too instead of a generic sans-serif.
            painter.setPen(QColor(color))
            label_font = QFont("Times New Roman"); label_font.setBold(True)
            label_font.setPixelSize(max(5, round(box.height() * 0.85)))
            painter.setFont(label_font)
            painter.drawText(box, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)
        else:
            picture = _frame_title_picture(text, box.width(), box.height(), color) if key == "title" else _frame_text_picture(font, text, box.width(), box.height(), color)
            if picture is not None:
                _frame_draw_picture(painter, picture, box)
            else:
                painter.setPen(QColor(color)); painter.setFont(QFont("Serif", max(6, box.height() - 2)))
                painter.drawText(box, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)
    _draw_frame_selected_outline(painter, c)
    painter.end(); _set_preview_pixmap(c["preview"], QPixmap.fromImage(image))


def _draw_frame_selected_outline(painter, controls):
    chosen = controls.get("selected")
    if chosen in controls.get("boxes", {}):
        painter.setPen(QPen(QColor("#1686ff"), 2)); painter.drawRect(QRect(*controls["boxes"][chosen]))


def _draw_hand_template(editor, painter, c):
    """Preview the duel hand's 52x60 sprite as duel_card_frame_draw.c composes
    it: retail artwork, and the game's own sword/shield/digit-row sprites,
    rather than the 140x196 main-card layout or generic placeholder shapes."""
    left, top, width, height = (140 - 52) // 2, (196 - 60) // 2, 52, 60
    c["boxes"] = {}
    box = QRect(left, top, width, height)
    c["boxes"]["hand"] = (box.x(), box.y(), box.width(), box.height())
    wa = getattr(getattr(editor, "files", None), "wa", None)
    hand_asset = _ui_image(editor, _frame_asset(editor, "hand"))
    if hand_asset is not None:
        _frame_draw_picture(painter, hand_asset, box)
    else:
        plate = _hand_frame_background(wa, _FRAME_INDEX[_frame_preview_kind(c)])
        if plate is not None: _frame_draw_picture(painter, plate, box)
        else: painter.fillRect(box, QColor("#665328"))
    retail_art = art.in_game(editor.project, wa, _frame_card_id(editor) or 1, "art", _FRAME_RENDER_SCALE) if wa else None
    ax, ay, aw, ah = _frame_rect(editor, "hand_art")
    art_box = QRect(left + ax, top + ay, aw, ah)
    c["boxes"]["hand_art"] = (art_box.x(), art_box.y(), art_box.width(), art_box.height())
    if _frame_part(editor, "hand_art").get("hide") is True:
        painter.setPen(QPen(QColor("#999999"), 1, Qt.PenStyle.DashLine)); painter.drawRect(art_box)
    elif retail_art is not None:
        _frame_draw_picture(painter, retail_art, art_box)
    else:
        painter.fillRect(art_box, QColor("#245175")); painter.setPen(QColor("#b9c7da")); painter.drawRect(art_box)
    # The hand's ATK/DEF markers are the duel screen's own sword, shield, and
    # digit-row sprites (8x8/8x16 source cells), not generic text or icons.
    for key, (u, v) in (("hand_atk_label", (120, 112)), ("hand_dfd_label", (120, 120))):
        bx, by, bw, bh = _frame_rect(editor, key)
        key_box = QRect(left + bx, top + by, bw, bh)
        c["boxes"][key] = (key_box.x(), key_box.y(), key_box.width(), key_box.height())
        if _frame_part(editor, key).get("hide") is True:
            painter.setPen(QPen(QColor("#999999"), 1, Qt.PenStyle.DashLine)); painter.drawRect(key_box); continue
        icon = _hand_sprite(wa, u, v)
        if icon is not None: _frame_draw_picture(painter, icon, key_box)
        else:
            painter.fillRect(key_box, QColor("#9da9bf")); painter.setPen(QColor("#dfe8f6")); painter.drawRect(key_box)
    for key, text in (("hand_atk", "3000"), ("hand_def", "2500")):
        bx, by, bw, bh = _frame_rect(editor, key)
        if _frame_part(editor, key).get("hide") is True:
            key_box = QRect(left + bx, top + by, bw * len(text), bh)
            painter.setPen(QPen(QColor("#999999"), 1, Qt.PenStyle.DashLine)); painter.drawRect(key_box)
            c["boxes"][key] = (key_box.x(), key_box.y(), key_box.width(), key_box.height())
            continue
        for index, character in enumerate(text):
            digit = _hand_sprite(wa, 8 * int(character), 88)
            cell = QRect(left + bx + index * bw, top + by, bw, bh)
            if digit is not None: _frame_draw_picture(painter, digit, cell)
            else: painter.fillRect(cell, QColor("#ffffff"))
        c["boxes"][key] = (left + bx, top + by, bw * len(text), bh)
    chosen = c.get("selected")
    if chosen in c["boxes"]:
        painter.setPen(QPen(QColor("#1686ff"), 2)); painter.drawRect(QRect(*c["boxes"][chosen]))


def _draw_library_template(editor, painter, c):
    """Preview the independent 24x32 Library grid icon at its game size.
    With no custom replacement, fall back to the real grid plate: the same
    disc pixels Library_DrawCardGrid's own retail fallback draws
    (func_80029EC4.c), one per card kind."""
    width, height = 24, 32
    left, top = (140 - width) // 2, (196 - height) // 2
    painter.fillRect(left, top, width, height, QColor("#55446f")); c["boxes"] = {}
    box = QRect(left, top, width, height)
    c["boxes"]["library"] = (box.x(), box.y(), box.width(), box.height())
    asset = _ui_image(editor, _frame_asset(editor, "library"))
    if asset is not None:
        painter.drawImage(box, _qimage(asset.width, asset.height, asset.rgba))
    else:
        wa = getattr(getattr(editor, "files", None), "wa", None)
        plate = _library_icon_background(wa, _FRAME_INDEX[_frame_preview_kind(c)])
        if plate is not None: _frame_draw_picture(painter, plate, box)
        else: painter.setPen(QColor("#9ab2cf")); painter.drawRect(box)
    chosen = c.get("selected")
    if chosen in c["boxes"]:
        painter.setPen(QPen(QColor("#1686ff"), 2)); painter.drawRect(QRect(*c["boxes"][chosen]))


def _draw_field_template(editor, painter, c, key):
    """Preview the independent 40x56 on-field render target (face-up or
    face-down) at its game size.  With no custom replacement, fall back to
    the real duel-board plate: a monster's own for "field" (a non-monster's
    for anything else), the one shared plate for "field_back"."""
    width, height = 40, 56
    left, top = (140 - width) // 2, (196 - height) // 2
    painter.fillRect(left, top, width, height, QColor("#305273")); c["boxes"] = {}
    box = QRect(left, top, width, height)
    c["boxes"][key] = (box.x(), box.y(), box.width(), box.height())
    asset = _ui_image(editor, _frame_asset(editor, key))
    if asset is not None:
        painter.drawImage(box, _qimage(asset.width, asset.height, asset.rgba))
    else:
        wa = getattr(getattr(editor, "files", None), "wa", None)
        kind = _frame_preview_kind(c)
        plate = (_field_back_frame_background(wa, _FRAME_INDEX[kind]) if key == "field_back"
                else _field_frame_background(wa, _FRAME_INDEX[kind], kind == "monster"))
        if plate is not None: _frame_draw_picture(painter, plate, box)
        else: painter.setPen(QColor("#9ab2cf")); painter.drawRect(box)
    chosen = c.get("selected")
    if chosen in c["boxes"]:
        painter.setPen(QPen(QColor("#1686ff"), 2)); painter.drawRect(QRect(*c["boxes"][chosen]))


def _frame_geometry_changed(editor):
    c = editor.workspace_controls["UI"]["frames"]
    if c.get("loading"): return
    key, spec = c["selected"], _FRAME_SPEC[c["selected"]]
    part = _frame_part(editor, key, True); owner = _frame_size_owner(editor, key, True); default = spec[3]
    if key in _FRAME_MOVABLE:
        _put(part, "x", c["x"].value(), default[0]); _put(part, "y", c["y"].value(), default[1])
    if spec[5]:
        _put(owner, "width", c["width"].value(), default[2]); _put(owner, "height", c["height"].value(), default[3])
    if spec[4]: _put(part, "hide", c["visible"].isChecked(), False)
    _frame_commit(editor)


def _frame_new_style(editor):
    c = editor.workspace_controls["UI"]["frames"]
    name, accepted = QInputDialog.getText(editor, "New frame style", "Style name (for mod.json):")
    name = re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_")
    if not accepted or not name: return
    _frame_styles(editor, True).setdefault(name, {"hand_color": "gold"}); c["style_name"] = name; _frame_commit(editor)


def _frame_delete_style(editor):
    c = editor.workspace_controls["UI"]["frames"]; name = _frame_style_name(editor); styles = _frame_styles(editor)
    if name not in styles: return
    if QMessageBox.question(editor, "Delete frame style", f'Delete frame style "{name}"? Its assignments will be cleared.') != QMessageBox.StandardButton.Yes: return
    layout = _frame_layout(editor, True); styles.pop(name, None)
    if layout.get("default_style") == name: layout.pop("default_style", None)
    defaults = layout.get("default_styles")
    if isinstance(defaults, dict):
        for group in ("kinds", "types"):
            values = defaults.get(group)
            if isinstance(values, dict):
                for value in [key for key, value in values.items() if value == name]: values.pop(value, None)
    for extra in (*editor.project.card_extra.values(), *(added.extra for added in editor.project.added.values())):
        if extra.get("frame_style") == name: extra.pop("frame_style", None)
    _frame_commit(editor)


def _frame_import(editor):
    key = editor.workspace_controls["UI"]["frames"]["selected"]
    if not _FRAME_SPEC[key][6]: return
    path, _ = QFileDialog.getOpenFileName(editor, "Import frame image", "", "PNG images (*.png)")
    if not path: return
    try: image = pngio.read(path)
    except (OSError, ValueError, pngio.PngError) as problem: QMessageBox.critical(editor, "Frame image", str(problem)); return
    stem = re.sub(r"[^a-z0-9_-]+", "-", f"{_frame_style_name(editor)}-{key}".casefold()).strip("-")
    name, suffix = f"frames/{stem}.png", 2
    while name in editor.project.files: name = f"frames/{stem}-{suffix}.png"; suffix += 1
    editor.project.files[name] = pngio.encode(image); editor.project.deleted_files.discard(name); _set_frame_asset(editor, key, name); _frame_commit(editor)


def _frame_export(editor):
    key = editor.workspace_controls["UI"]["frames"]["selected"]; image = _ui_image(editor, _frame_asset(editor, key))
    _export_ui_png(editor, image, f"{key}.png")


def _frame_clear_image(editor):
    key = editor.workspace_controls["UI"]["frames"]["selected"]; _set_frame_asset(editor, key, None); _frame_commit(editor)


def _frame_reset_part(editor):
    key = editor.workspace_controls["UI"]["frames"]["selected"]
    if key in _FRAME_DIRECT: _frame_style(editor, True).pop(_FRAME_SPEC[key][2][0], None)
    else: _frame_part(editor, key, True).clear()
    _frame_commit(editor)


def _frame_card_id(editor):
    text = editor.workspace_controls["UI"]["frames"]["card_rule"].text().strip()
    match = re.match(r"(\d+)(?:\s|$)", text)
    if match:
        return int(match.group(1))
    needle = text.casefold()
    return next((card_id for card_id, card in editor.project.cards.items() if card.name.casefold() == needle), 0)


def _frame_browse_card(editor):
    choices = [f"{card_id} {card.name}" for card_id, card in sorted(editor.project.cards.items())]
    chosen, accepted = QInputDialog.getItem(editor, "Specific card", "Card:", choices, editable=False)
    if accepted and chosen:
        editor.workspace_controls["UI"]["frames"]["card_rule"].setText(chosen)


def _frame_assign(editor, level, enabled):
    c = editor.workspace_controls["UI"]["frames"]; style = _frame_style_name(editor); layout = _frame_layout(editor, enabled)
    if level == "default":
        if enabled: layout["default_style"] = style
        else: layout.pop("default_style", None)
    elif level in {"kind", "type"}:
        key = c[f"{level}_rule"].currentData() or c[f"{level}_rule"].currentText()
        defaults = layout.setdefault("default_styles", {}) if enabled else layout.get("default_styles", {})
        group = defaults.setdefault(f"{level}s", {}) if enabled else defaults.get(f"{level}s", {})
        if isinstance(group, dict):
            if enabled: group[key] = style
            else: group.pop(key, None)
    else:
        card_id = _frame_card_id(editor)
        if card_id not in editor.project.cards: return
        if enabled:
            target = (editor.project.added[card_id].extra if card_id in editor.project.added
                      else editor.project.card_extra.setdefault(card_id, {}))
            target["frame_style"] = style
        else:
            target = (editor.project.added[card_id].extra if card_id in editor.project.added
                      else editor.project.card_extra.get(card_id))
            if target is not None: target.pop("frame_style", None)
    _frame_commit(editor)


def _frame_revert_all(editor):
    editor.project.other.pop("card_layout", None)
    for extra in (*editor.project.card_extra.values(), *(added.extra for added in editor.project.added.values())): extra.pop("frame_style", None)
    _frame_commit(editor)


def _frame_hold(editor, held):
    c = editor.workspace_controls["UI"]["frames"]
    held = bool(held)
    if c.get("retail_preview", False) == held:
        return
    c["retail_preview"] = held
    _draw_frames(editor)


def _wire_ui_tabs(editor, shell, controls):
    """Connect the four UI pages to the exact data keys the classic tab edits."""
    from PySide6.QtWidgets import QTreeWidget
    c = controls
    c.update(ui_loading=False, title_selected="background", menu_selected="new_game",
             menu_number=0, duel_selected="lp_player", board_selected="floor",
             board_camera=board_model.CAMERA, board_picture=None)
    for key, name in {
        "title_tree": "titleElementsTree", "title_stack": "titlePropertiesStack",
        "title_preview": "titlePreviewCanvas", "title_menu_up": "titleWithMenuCheck",
        "title_x": "titleXSpin", "title_y": "titleYSpin", "title_tint": "titleTintEdit",
        "title_show": "titleShownCombo", "title_image": "titleImagePathEdit", "title_hidden": "titleHiddenCheck",
        "title_bg_color": "titleBackgroundColorEdit", "title_bg_picture": "titleBackgroundPictureCheck",
        "title_text": "titleTextEdit", "title_text_color": "titleTextColorEdit", "title_text_size": "titleTextSizeSpin",
        "menu_tree": "menuStructureTree", "menu_preview": "menuPreviewCanvas", "menu_mode": "menuPreviewModeCombo",
        "menu_spacing": "menuSpacingSpin", "menu_all_scale": "menuAllScaleSpin", "menu_words": "menuWordsEdit",
        "menu_action": "menuActionCombo", "menu_tint": "menuTextColorEdit", "menu_x": "menuXSpin",
        "menu_y": "menuYSpin", "menu_scale": "menuScaleSpin", "menu_hidden": "menuHiddenCheck",
        "duel_tree": "duelElementsTree", "duel_preview": "duelPreviewCanvas", "duel_name": "duelElementNameEdit",
        "duel_description": "duelElementDescriptionEdit", "duel_tint": "duelElementTintEdit",
        "duel_digits": "duelElementDigitsEdit", "duel_image": "duelElementImagePathEdit",
        "duel_hidden": "duelElementHiddenCheck", "duel_x": "duelElementXSpin", "duel_y": "duelElementYSpin",
        "duel_scale": "duelElementScaleSpin", "duel_label": "duelElementLabelEdit", "duel_spacing": "duelElementSpacingSpin",
        "duel_opponent": "duelOpponentTurnCheck", "duel_bar_kind": "duelCardBarShowsCombo",
        "board_field": "boardFieldCombo", "board_tree": "boardPartsTree", "board_preview": "boardPreviewCanvas",
        "board_part_preview": "boardPartPreview", "board_part_label": "boardSelectedPartLabel",
        "board_description": "boardSelectedPartDescription", "board_resolution": "boardPartResolutionLabel",
        "board_tint": "boardTintEdit", "board_all": "boardApplyAllFieldsCheck",
        "board_search": "boardPartSearchEdit", "board_show_outlines": "boardShowOutlinesCheck",
    }.items():
        c[key] = _scene_widget(shell, name)

    c["title_show"].clear()
    for key, label in (("always", "Always"), ("press_start", "With PUSH START"), ("menu", "With a menu up")):
        c["title_show"].addItem(label, key)
    c["menu_mode"].setItemData(0, 0); c["menu_mode"].setItemData(1, 1)
    c["duel_bar_kind"].setItemData(0, "Monster"); c["duel_bar_kind"].setItemData(1, "Magic")
    c["duel_bar_kind"].setItemData(2, "Trap")
    for kind, preview in (("title", c["title_preview"]), ("menu", c["menu_preview"]), ("duel", c["duel_preview"])):
        bridge = _PreviewEvents(editor, kind, preview)
        preview.setMouseTracking(True); preview.setFocusPolicy(Qt.FocusPolicy.StrongFocus); preview.installEventFilter(bridge)
        c[f"{kind}_events"] = bridge
    board_bridge = _BoardEvents(editor, c["board_preview"])
    c["board_preview"].setMouseTracking(True); c["board_preview"].setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    c["board_preview"].installEventFilter(board_bridge)
    c["board_events"] = board_bridge

    c["title_tree"].currentItemChanged.connect(lambda item, _: _title_select(editor, item))
    c["title_menu_up"].toggled.connect(lambda _: _draw_title(editor))
    for widget in (c["title_x"], c["title_y"]): widget.valueChanged.connect(lambda _: _title_generic_changed(editor))
    c["title_tint"].editingFinished.connect(lambda: _title_generic_changed(editor))
    c["title_show"].currentIndexChanged.connect(lambda _: _title_generic_changed(editor))
    c["title_hidden"].toggled.connect(lambda _: _title_generic_changed(editor))
    c["title_bg_color"].editingFinished.connect(lambda: _title_background_changed(editor))
    c["title_bg_picture"].toggled.connect(lambda _: _title_background_changed(editor))
    c["title_text"].editingFinished.connect(lambda: _title_text_changed(editor))
    c["title_text_color"].editingFinished.connect(lambda: _title_text_changed(editor))
    c["title_text_size"].valueChanged.connect(lambda _: _title_text_changed(editor))
    _scene_widget(shell, "addTitleTextButton").clicked.connect(lambda: _title_add_text(editor))
    _scene_widget(shell, "addTitlePictureButton").clicked.connect(lambda: _title_add_picture(editor))
    _scene_widget(shell, "removeTitleElementButton").clicked.connect(lambda: _title_remove(editor))
    _scene_widget(shell, "chooseTitleImageButton").clicked.connect(lambda: _title_choose_image(editor))
    _scene_widget(shell, "useGameTitleImageButton").clicked.connect(lambda: _title_clear_image(editor))
    _scene_widget(shell, "titleBackgroundImportButton").clicked.connect(lambda: _title_background_image(editor))
    _scene_widget(shell, "revertTitleElementButton").clicked.connect(lambda: _title_revert_element(editor))
    _scene_widget(shell, "exportTitleElementButton").clicked.connect(lambda: _title_export(editor))
    _scene_widget(shell, "revertTitlePageButton").clicked.connect(lambda: _title_revert_page(editor))
    _scene_widget(shell, "holdGameTitleButton").pressed.connect(lambda: _hold_compare(editor, True))
    _scene_widget(shell, "holdGameTitleButton").released.connect(lambda: _hold_compare(editor, False))

    c["menu_tree"].currentItemChanged.connect(lambda item, _: _menu_select(editor, item))
    c["menu_mode"].currentIndexChanged.connect(lambda _: _menu_switch(editor))
    c["menu_spacing"].valueChanged.connect(lambda _: _menu_global_changed(editor))
    c["menu_all_scale"].valueChanged.connect(lambda _: _menu_global_changed(editor))
    c["menu_words"].editingFinished.connect(lambda: _menu_item_changed(editor))
    c["menu_action"].currentIndexChanged.connect(lambda _: _menu_item_changed(editor))
    c["menu_tint"].editingFinished.connect(lambda: _menu_item_changed(editor))
    for widget in (c["menu_x"], c["menu_y"], c["menu_scale"]): widget.valueChanged.connect(lambda _: _menu_item_changed(editor))
    c["menu_hidden"].toggled.connect(lambda _: _menu_item_changed(editor))
    _scene_widget(shell, "addMenuButtonButton").clicked.connect(lambda: _menu_add(editor))
    _scene_widget(shell, "hideMenuButton").clicked.connect(lambda: _menu_toggle_hidden(editor))
    _scene_widget(shell, "removeMenuButton").clicked.connect(lambda: _menu_remove(editor))
    _scene_widget(shell, "moveMenuUpButton").clicked.connect(lambda: _menu_move(editor, -1))
    _scene_widget(shell, "moveMenuDownButton").clicked.connect(lambda: _menu_move(editor, 1))
    _scene_widget(shell, "menuInlineButton").clicked.connect(lambda: _menu_inline(editor))
    _scene_widget(shell, "chooseMenuPictureButton").clicked.connect(lambda: _menu_image(editor, "image"))
    _scene_widget(shell, "useMenuCursorPictureButton").clicked.connect(lambda: _menu_image(editor, "selected_image"))
    _scene_widget(shell, "clearMenuPictureButton").clicked.connect(lambda: _menu_clear_images(editor))
    _scene_widget(shell, "revertMenuButtonButton").clicked.connect(lambda: _menu_revert_item(editor))
    _scene_widget(shell, "exportMenuButtonButton").clicked.connect(lambda: _menu_export(editor))
    _scene_widget(shell, "revertMenuPageButton").clicked.connect(lambda: _menu_revert_page(editor))
    _scene_widget(shell, "holdGameMenuButton").pressed.connect(lambda: _hold_compare(editor, True))
    _scene_widget(shell, "holdGameMenuButton").released.connect(lambda: _hold_compare(editor, False))

    c["duel_tree"].currentItemChanged.connect(lambda item, _: _duel_select(editor, item))
    for widget in (c["duel_x"], c["duel_y"], c["duel_scale"], c["duel_spacing"]): widget.valueChanged.connect(lambda _: _duel_changed(editor))
    for widget in (c["duel_tint"], c["duel_digits"], c["duel_label"]): widget.editingFinished.connect(lambda: _duel_changed(editor))
    c["duel_hidden"].toggled.connect(lambda _: _duel_changed(editor))
    c["duel_opponent"].toggled.connect(lambda _: _draw_duel(editor))
    c["duel_bar_kind"].currentIndexChanged.connect(lambda _: _draw_duel(editor))
    _scene_widget(shell, "duelElementImportButton").clicked.connect(lambda: _duel_image(editor))
    _scene_widget(shell, "revertDuelElementButton").clicked.connect(lambda: _duel_revert_element(editor))
    _scene_widget(shell, "exportDuelElementButton").clicked.connect(lambda: _duel_export(editor))
    _scene_widget(shell, "revertDuelPageButton").clicked.connect(lambda: _duel_revert_page(editor))
    _scene_widget(shell, "holdGameDuelButton").pressed.connect(lambda: _hold_compare(editor, True))
    _scene_widget(shell, "holdGameDuelButton").released.connect(lambda: _hold_compare(editor, False))

    c["board_field"].currentIndexChanged.connect(lambda _: _board_refresh(editor))
    c["board_tree"].currentItemChanged.connect(lambda item, _: _board_select(editor, item))
    c["board_search"].textChanged.connect(lambda _: _board_filter(editor))
    c["board_tint"].editingFinished.connect(lambda: _board_tint(editor))
    c["board_show_outlines"].toggled.connect(lambda _: _board_redisplay(editor))
    _scene_widget(shell, "replaceBoardPartButton").clicked.connect(lambda: _board_replace(editor))
    _scene_widget(shell, "exportBoardPartButton").clicked.connect(lambda: _board_export(editor))
    _scene_widget(shell, "revertBoardPartButton").clicked.connect(lambda: _board_revert(editor))
    _scene_widget(shell, "revertBoardPageButton").clicked.connect(lambda: _board_revert_all(editor))
    _scene_widget(shell, "boardGameViewButton").clicked.connect(lambda: _board_reset_view(editor))
    _scene_widget(shell, "holdGameBoardButton").pressed.connect(lambda: _hold_compare(editor, True))
    _scene_widget(shell, "holdGameBoardButton").released.connect(lambda: _hold_compare(editor, False))
    _refresh_ui_tabs(editor)


def _refresh_ui_tabs(editor):
    c = editor.workspace_controls.get("UI", {})
    if not c.get("shell") or c.get("ui_loading"):
        return
    c["ui_loading"] = True
    try:
        _refresh_title(editor); _refresh_menu(editor); _refresh_duel(editor); _board_refresh(editor)
    finally:
        c["ui_loading"] = False


def _title_target(editor, create=False):
    c, chosen = editor.workspace_controls["UI"], editor.workspace_controls["UI"].get("title_selected", "background")
    title = _ui_section(editor, "title", create)
    if chosen == "background":
        return title.get("background", {}) if not create else title.setdefault("background", {})
    kind, _, index = chosen.partition(":")
    if kind == "layer":
        return title.get(index, {}) if not create else title.setdefault(index, {})
    values = title.get("images" if kind == "picture" else "text", [])
    if not isinstance(values, list) or not index.isdigit() or int(index) >= len(values):
        return {}
    return values[int(index)] if isinstance(values[int(index)], dict) else {}


def _refresh_title(editor):
    from PySide6.QtWidgets import QTreeWidgetItem
    c, tree = editor.workspace_controls["UI"], editor.workspace_controls["UI"]["title_tree"]
    title, selected = _ui_section(editor, "title"), c.get("title_selected", "background")
    valid = {"background", *(f"layer:{name}" for name in ("logo", "copyright", "prompt"))}
    images = title.get("images") if isinstance(title.get("images"), list) else []
    lines = title.get("text") if isinstance(title.get("text"), list) else []
    valid |= {f"picture:{index}" for index in range(len(images))} | {f"text:{index}" for index in range(len(lines))}
    if selected not in valid: selected = c["title_selected"] = "background"
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QHeaderView
    tree.blockSignals(True); tree.clear(); tree.setRootIsDecorated(False); tree.setIconSize(QSize(86, 43)); chosen_item = None
    tree.header().setStretchLastSection(False)
    tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
    art = _title_art(editor)
    rows = [("background", "Background", art.wall() if art.ok else None),
            ("layer:logo", "Logo", art.layer("logo")[0] if art.ok else None),
            ("layer:copyright", "Copyright line", art.layer("copyright")[0] if art.ok else None),
            ("layer:prompt", "Press Start Button", art.layer("prompt")[0] if art.ok else None)]
    for key, label, preview in rows:
        item = QTreeWidgetItem([label, "●" if _title_target_by(editor, key) else ""])
        item.setData(0, Qt.ItemDataRole.UserRole, key)
        if preview is not None:
            item.setIcon(0, QIcon(QPixmap.fromImage(_qimage(preview.width, preview.height, preview.rgba))))
        tree.addTopLevelItem(item)
        if key == selected: chosen_item = item
    if images:
        group = QTreeWidgetItem(["Added pictures", ""]); tree.addTopLevelItem(group)
        for index, item_data in enumerate(images):
            key = f"picture:{index}"; label = str(item_data.get("image") or f"Picture {index + 1}") if isinstance(item_data, dict) else f"Picture {index + 1}"
            item = QTreeWidgetItem([label.rsplit("/", 1)[-1], "●"]); item.setData(0, Qt.ItemDataRole.UserRole, key); group.addChild(item)
            if key == selected: chosen_item = item
    if lines:
        group = QTreeWidgetItem(["Words", ""]); tree.addTopLevelItem(group)
        for index, item_data in enumerate(lines):
            key = f"text:{index}"; label = str(item_data.get("text") or f"Words {index + 1}") if isinstance(item_data, dict) else f"Words {index + 1}"
            item = QTreeWidgetItem([label, "●"]); item.setData(0, Qt.ItemDataRole.UserRole, key); group.addChild(item)
            if key == selected: chosen_item = item
    tree.setCurrentItem(chosen_item); tree.blockSignals(False)
    _fill_title_form(editor); _draw_title(editor)


def _title_target_by(editor, chosen):
    current = editor.workspace_controls["UI"].get("title_selected")
    editor.workspace_controls["UI"]["title_selected"] = chosen
    value = _title_target(editor, False)
    editor.workspace_controls["UI"]["title_selected"] = current
    return value


def _title_select(editor, item):
    if editor.workspace_controls["UI"].get("ui_loading") or item is None:
        return
    key = item.data(0, Qt.ItemDataRole.UserRole)
    if isinstance(key, str): editor.workspace_controls["UI"]["title_selected"] = key; _refresh_title(editor)


def _fill_title_form(editor):
    c, selected = editor.workspace_controls["UI"], editor.workspace_controls["UI"].get("title_selected")
    value = _title_target(editor)
    if selected == "background":
        c["title_stack"].setCurrentIndex(1)
        _set_value(c["title_bg_color"], value.get("color", "#000000")); _set_value(c["title_bg_picture"], value.get("picture") is not False)
    elif selected.startswith("text:"):
        c["title_stack"].setCurrentIndex(2)
        _set_value(c["title_text"], value.get("text", "")); _set_value(c["title_text_color"], value.get("color", "#FFFFFF")); _set_value(c["title_text_size"], value.get("size", 1))
    else:
        c["title_stack"].setCurrentIndex(0)
        defaults = (160, 120) if selected.startswith("picture:") else (0, 0)
        _set_value(c["title_x"], value.get("x", defaults[0])); _set_value(c["title_y"], value.get("y", defaults[1]))
        _set_value(c["title_tint"], value.get("tint", "#FFFFFF")); _set_value(c["title_show"], value.get("show", "always")); _set_value(c["title_image"], value.get("image", "")); _set_value(c["title_hidden"], value.get("hide") is True)


def _title_art(editor):
    c = editor.workspace_controls["UI"]
    key = id(getattr(editor, "files", None))
    if c.get("title_art_key") != key:
        c["title_art_key"] = key
        c["title_art"] = ui_assets.TitleArt(ui_assets.read_su(editor.files) if getattr(editor, "files", None) else None)
    return c["title_art"]


def _as_int(value, default=0):
    return value if isinstance(value, int) and not isinstance(value, bool) else default


def _title_fit(image, maximum_w, maximum_h, width=0, height=0):
    if width and height: w, h = width, height
    elif width: w, h = width, image.height * width // max(1, image.width)
    elif height: w, h = image.width * height // max(1, image.height), height
    else:
        divisor = max(1, (image.width + maximum_w - 1) // maximum_w, (image.height + maximum_h - 1) // maximum_h)
        w, h = image.width // divisor, image.height // divisor
    return max(1, min(maximum_w, w)), max(1, min(maximum_h, h))


def _title_scaled(image, width, height):
    return pngio.scale_to(image, max(1, width), max(1, height)) if image.width <= width * 3 and image.height <= height * 3 else pngio.resample(image, max(1, width), max(1, height))


def _title_background(editor, menu=None):
    title, menu_data = _ui_section(editor, "title"), _ui_section(editor, "menu")
    data = {"picture": True, "shade": True, "tint": 0xFFFFFF, "color": None, "image": "", "dim": 128}
    if isinstance(title.get("background"), dict): data.update(title["background"])
    if menu is not None and isinstance(menu_data.get("background"), dict): data.update(menu_data["background"])
    art = _title_art(editor)
    color = ui_assets.parse_color(data.get("color"), -1)
    base = ui_assets.blank(320, 240, ((color >> 16 & 255, color >> 8 & 255, color & 255, 255) if color >= 0 else (0, 0, 0, 255)))
    picture = _ui_image(editor, data.get("image"))
    if data.get("picture") is not False:
        picture = picture or (art.wall() if art.ok else None)
        if picture is not None:
            base = ui_assets.paste(base, ui_assets.tint(_title_scaled(picture, 320, 240), ui_assets.parse_color(data.get("tint"))), 0, 0)
    if data.get("shade") is not False:
        rows = []
        for y in range(240):
            table = bytes(max(0, value - y * 255 // 239) for value in range(256))
            row = bytearray(base.rgba[y * 1280:(y + 1) * 1280].translate(table)); row[3::4] = b"\xff" * 320
            rows.append(bytes(row))
        base = pngio.Image(320, 240, b"".join(rows))
    return base, data, art


def _title_layer(editor, canvas, name, data, art, menu):
    layer = _ui_section(editor, "title").get(name)
    layer = layer if isinstance(layer, dict) else {}
    if layer.get("hide") is True or (name == "prompt" and (menu is not None or _ui_section(editor, "title").get("press_start") is False)):
        return canvas
    show = layer.get("show", "always")
    if (show == "menu" and menu is None) or (show == "press_start" and menu is not None):
        return canvas
    own = _ui_image(editor, layer.get("image"))
    dx, dy = _as_int(layer.get("x")), _as_int(layer.get("y"))
    tint = ui_assets.parse_color(layer.get("tint"))
    level = 0x58 * 255 // 0x80 if name == "prompt" else 255
    if own is not None:
        width, height = _title_fit(own, 320, 240 if name == "logo" else 120, _as_int(layer.get("width")), _as_int(layer.get("height")))
        image = ui_assets.tint(_title_scaled(own, width, height), tint, level)
        middle = ui_assets.LAYER_MIDDLES[name]
        return ui_assets.paste(canvas, image, middle[0] + dx - width // 2, middle[1] + dy - height // 2)
    if art.ok:
        image, x, y = art.layer(name)
        return ui_assets.paste(canvas, ui_assets.tint(image, tint, level), x + dx, y + dy)
    return canvas


def _title_words(canvas, lines, dim=0):
    """Draw user-added title words with Qt; game art remains pixel-accurate."""
    from PySide6.QtGui import QFont, QPainter
    surface = QImage(canvas.rgba, canvas.width, canvas.height, canvas.width * 4, QImage.Format.Format_RGBA8888).copy()
    painter = QPainter(surface)
    for line in lines if isinstance(lines, list) else []:
        if not isinstance(line, dict) or not isinstance(line.get("text"), str): continue
        size = max(1, min(8, _as_int(line.get("size"), 1)))
        painter.setFont(QFont("Sans", size * 12))
        color = QColor(_colour(line.get("color"), "#FFFFFF")); color.setAlpha(max(0, 255 - dim)); painter.setPen(color)
        align = Qt.AlignmentFlag.AlignCenter
        if line.get("align") == "left": align = Qt.AlignmentFlag.AlignLeft
        elif line.get("align") == "right": align = Qt.AlignmentFlag.AlignRight
        painter.drawText(QRect(_as_int(line.get("x"), 160) - 160, _as_int(line.get("y"), 220) - size * 7, 320, size * 14), align, line["text"])
    painter.end()
    raw = bytes(surface.bits())
    return pngio.Image(320, 240, raw)


def _menu_places(scene, number):
    shown = [item for item, visible in scene.order(number) if visible]
    scales = [scene.scale(item) for item in shown]
    spacing = _as_int(scene.menu.get("spacing"), _MENU_SPACING)
    if len(shown) <= 1: return {item["name"]: (160 + _as_int(item.get("x")), (114, 122)[number] + _as_int(item.get("y"))) for item in shown}
    reaches = [0]
    for left, right in zip(scales, scales[1:]): reaches.append(reaches[-1] + left + right)
    total = spacing * reaches[-1] // 200
    first = (114, 122)[number] - total // 2
    return {item["name"]: (160 + _as_int(item.get("x")), first + spacing * reaches[index] // 200 + _as_int(item.get("y"))) for index, item in enumerate(shown)}

def _title_layer_box(editor, name, art):
    layer = _ui_section(editor, "title").get(name)
    layer = layer if isinstance(layer, dict) else {}
    own = _ui_image(editor, layer.get("image")); dx, dy = _as_int(layer.get("x")), _as_int(layer.get("y"))
    if own is not None:
        width, height = _title_fit(own, 320, 240 if name == "logo" else 120, _as_int(layer.get("width")), _as_int(layer.get("height")))
        middle = ui_assets.LAYER_MIDDLES[name]
        return middle[0] + dx - width // 2, middle[1] + dy - height // 2, width, height
    if art.ok:
        image, x, y = art.layer(name)
        return x + dx, y + dy, image.width, image.height
    return 0, 0, 0, 0


_MENU_LABEL_H, _MENU_LABEL_PAD, _MENU_LABEL_MIN, _MENU_LABEL_MAX = 28, 14, 64, 240


def _menu_label_width(text):
    """menu_label.c's width for a label's frame at 100 (ui_title.py's label_width, without Tk)."""
    font = QFont("Times New Roman"); font.setBold(True); font.setPixelSize(17)
    width = max(_MENU_LABEL_MIN, min(_MENU_LABEL_MAX, QFontMetrics(font).horizontalAdvance(text) + 2 * _MENU_LABEL_PAD))
    return (width + 1) & ~1


def _menu_label_frame(text, selected):
    """The default button template: menu_label.c's frame for a custom label or
    button, its words drawn over it (ui_title.py's label_button + item_look)."""
    w, h = _menu_label_width(text), _MENU_LABEL_H
    image = QImage(w, h, QImage.Format.Format_RGBA8888); image.fill(QColor(0, 0, 0, 0))
    painter = QPainter(image)
    def fill(x0, y0, x1, y1, color): painter.fillRect(x0, y0, x1 - x0, y1 - y0, QColor(*color))
    if selected:
        fill(0, 0, w, h, (168, 16, 16)); fill(1, 1, w - 1, h - 1, (232, 136, 0))
        fill(2, 2, w - 2, h - 2, (168, 16, 16)); fill(3, 3, w - 3, h - 3, (40, 24, 24))
        for y, color in ((4, (104, 96, 200)), (5, (224, 224, 248)), (6, (48, 64, 184)),
                          (h - 7, (104, 96, 200)), (h - 6, (224, 224, 248)), (h - 5, (48, 64, 184))):
            fill(5, y, w - 5, y + 1, color)
    else:
        fill(0, 0, w, h, (16, 8, 16)); fill(1, 1, w - 1, h - 1, (96, 96, 8))
        fill(2, 2, w - 2, h - 2, (40, 32, 32)); fill(6, 5, w - 6, 6, (128, 120, 120))
        fill(6, h - 6, w - 6, h - 5, (128, 120, 120))
    font = QFont("Times New Roman"); font.setBold(True); font.setPixelSize(17); painter.setFont(font)
    painter.setPen(QColor("#e0f8d8" if selected else "#b0b0b0"))
    painter.drawText(image.rect(), Qt.AlignmentFlag.AlignCenter, text)
    painter.end()
    return pngio.Image(w, h, bytes(image.bits()))


def _render_title(editor, menu=None):
    c = editor.workspace_controls["UI"]
    with _comparing_view(editor) as comparing:
        base, background, art = _title_background(editor, menu)
        dim = max(0, min(128, _as_int(background.get("dim"), 128))) if menu is not None else 0
        canvas = ui_assets.subtract(base, dim)
        boxes = {"background": (0, 0, 320, 240)}
        for name in ("logo", "copyright", "prompt"):
            canvas = _title_layer(editor, canvas, name, background, art, menu)
            boxes[f"layer:{name}"] = _title_layer_box(editor, name, art)
        title = _ui_section(editor, "title")
        for image_index, entry in enumerate(title.get("images") if isinstance(title.get("images"), list) else []):
            if not isinstance(entry, dict): continue
            show = entry.get("show", "always")
            image = _ui_image(editor, entry.get("image"))
            if image is None or (show == "menu" and menu is None) or (show == "press_start" and menu is not None): continue
            width, height = _title_fit(image, 320, 240, _as_int(entry.get("width")), _as_int(entry.get("height")))
            image_x, image_y = _as_int(entry.get("x"), 160) - width // 2, _as_int(entry.get("y"), 120) - height // 2
            canvas = ui_assets.paste(canvas, ui_assets.tint(_title_scaled(image, width, height), ui_assets.parse_color(entry.get("tint"))), image_x, image_y)
            boxes[f"picture:{image_index}"] = (image_x, image_y, width, height)
        if menu is not None:
            scene = _menu_scene(editor)
            places = _menu_places(scene, menu)
            selected = c.get("menu_selected")
            for item, visible in scene.order(menu):
                if not visible: continue
                x, y = places[item["name"]]
                scale = scene.scale(item)
                is_selected = item["name"] == selected
                item_tint = ui_assets.parse_color(item.get("tint"))
                boxes[item["name"]] = (x - 48 * scale // 100, y - 14 * scale // 100, 96 * scale // 100, 28 * scale // 100)
                own_name = item.get("selected_image" if is_selected else "image")
                image = _ui_image(editor, own_name) if own_name else None
                if is_selected and image is None and item.get("image"):
                    image, level = _ui_image(editor, item.get("image")), 255
                else:
                    level = 255 if (is_selected or item.get("selected_image") or not item.get("image")) else 0x60 * 255 // 0x80
                if image is not None:
                    # A replacement picture (item_look()'s image branch): fit, scale, tint.
                    width, height = _title_fit(image, 256, 64, _as_int(item.get("width")), _as_int(item.get("height")))
                    width, height = max(1, (width * scale + 50) // 100), max(1, (height * scale + 50) // 100)
                    picture = ui_assets.tint(_title_scaled(image, width, height), item_tint, level)
                    left, top = -(width // 2), -(height // 2)
                    canvas = ui_assets.paste(canvas, picture, x + left, y + top)
                    boxes[item["name"]] = (x + left, y + top, width, height)
                elif (isinstance(item.get("label"), str) and item.get("label")) or not item.get("entry"):
                    # The default button template (item_look()'s label_button() branch):
                    # every custom button, or any entry given its own words.
                    text = item.get("label") or item["name"].split(":", 1)[-1]
                    frame = _menu_label_frame(text, is_selected)
                    width, height = max(1, (frame.width * scale + 50) // 100), max(1, (frame.height * scale + 50) // 100)
                    level = 255 if is_selected else 0x60 * 255 // 0x80
                    picture = ui_assets.tint(_title_scaled(frame, width, height), item_tint, level)
                    left, top = -(width // 2), -(height // 2)
                    canvas = ui_assets.paste(canvas, picture, x + left, y + top)
                    boxes[item["name"]] = (x + left, y + top, width, height)
                elif art.ok:
                    picture, dx, dy = art.entry(item["index"], is_selected)
                    canvas = ui_assets.paste(canvas, ui_assets.tint(picture, item_tint), x + dx, y + dy)
                    boxes[item["name"]] = (x + dx, y + dy, picture.width, picture.height)
        canvas = _title_words(canvas, title.get("text"), dim)
        for text_index, line in enumerate(title.get("text") if isinstance(title.get("text"), list) else []):
            if isinstance(line, dict):
                size = max(1, min(8, _as_int(line.get("size"), 1)))
                boxes[f"text:{text_index}"] = (_as_int(line.get("x"), 160) - 160, _as_int(line.get("y"), 220) - size * 7, 320, size * 14)
        key = c.get("menu_selected") if menu is not None else c.get("title_selected")
        canvas = _outline(canvas, boxes.get(key))
        c["menu_boxes" if menu is not None else "title_boxes"] = boxes
    if comparing: canvas = _compare_badge(canvas)
    _png_preview(c["title_preview"], canvas, "Load game files to preview the title screen")
    return canvas


def _draw_title(editor):
    c = editor.workspace_controls["UI"]
    _render_title(editor, c.get("menu_number", 0) if c["title_menu_up"].isChecked() else None)


def _draw_menu(editor):
    c = editor.workspace_controls["UI"]
    # The original menu page is the title screen with its first or second menu up.
    image = _render_title(editor, c.get("menu_number", 0))
    _png_preview(c["menu_preview"], image, "Load game files to preview the menu")
    # Rendering the menu shares the title compositor; restore the Title tab's own view.
    _draw_title(editor)


def _title_generic_changed(editor):
    c = editor.workspace_controls["UI"]
    if c.get("ui_loading") or c.get("title_selected") == "background" or c.get("title_selected", "").startswith("text:"): return
    target = _title_target(editor, True)
    _put(target, "x", c["title_x"].value(), 160 if c["title_selected"].startswith("picture:") else 0); _put(target, "y", c["title_y"].value(), 120 if c["title_selected"].startswith("picture:") else 0)
    _put(target, "tint", _colour(c["title_tint"].text()), "#FFFFFF"); _put(target, "show", c["title_show"].currentData(), "always"); _put(target, "hide", c["title_hidden"].isChecked(), False); _commit_ui(editor)


def _title_background_changed(editor):
    c = editor.workspace_controls["UI"]
    if c.get("ui_loading"): return
    target = _title_target(editor, True); _put(target, "color", _colour(c["title_bg_color"].text(), "#000000"), None); _put(target, "picture", c["title_bg_picture"].isChecked(), True); _commit_ui(editor)


def _title_text_changed(editor):
    c = editor.workspace_controls["UI"]
    if c.get("ui_loading") or not c.get("title_selected", "").startswith("text:"): return
    target = _title_target(editor, True); _put(target, "text", c["title_text"].text().strip(), None); _put(target, "color", _colour(c["title_text_color"].text()), "#FFFFFF"); _put(target, "size", c["title_text_size"].value(), 1); _commit_ui(editor)


def _title_add_text(editor):
    title = _ui_section(editor, "title", True); values = title.setdefault("text", []); values.append({"text": "Words", "x": 160, "y": 220}); editor.workspace_controls["UI"]["title_selected"] = f"text:{len(values) - 1}"; _commit_ui(editor)


def _title_add_picture(editor):
    image = _store_ui_png(editor, "title-picture")
    if image:
        title = _ui_section(editor, "title", True); values = title.setdefault("images", []); values.append({"image": image, "x": 160, "y": 120}); editor.workspace_controls["UI"]["title_selected"] = f"picture:{len(values) - 1}"; _commit_ui(editor)


def _title_choose_image(editor):
    selected = editor.workspace_controls["UI"].get("title_selected", "")
    if selected in ("background",) or selected.startswith("text:"): return
    image = _store_ui_png(editor, f"title-{selected.replace(':', '-')}")
    if image: _title_target(editor, True)["image"] = image; _commit_ui(editor)


def _title_clear_image(editor):
    target = _title_target(editor, True); target.pop("image", None); target.pop("width", None); target.pop("height", None); _commit_ui(editor)


def _title_background_image(editor):
    image = _store_ui_png(editor, "title-background")
    if image: _title_target(editor, True)["image"] = image; _commit_ui(editor)


def _title_export(editor):
    c, selected = editor.workspace_controls["UI"], editor.workspace_controls["UI"].get("title_selected", "background")
    if selected == "background":
        image, _data, _art = _title_background(editor)
    elif selected.startswith("layer:"):
        name = selected.partition(":")[2]
        value, art = _title_target(editor), _title_art(editor)
        image = _ui_image(editor, value.get("image"))
        if image is None and art.ok and name in ("logo", "copyright", "prompt"):
            image = art.layer(name)[0]
    elif selected.startswith("picture:"):
        image = _ui_image(editor, _title_target(editor).get("image"))
    elif selected.startswith("text:"):
        image = _title_words(pngio.Image(320, 240, b"\0" * (320 * 240 * 4)), [_title_target(editor)])
    else:
        image = None
    _export_ui_png(editor, image, f"title-{selected.replace(':', '-')}.png")


def _title_remove(editor):
    c, selected = editor.workspace_controls["UI"], editor.workspace_controls["UI"].get("title_selected", "")
    title = _ui_section(editor, "title", True)
    kind, _, index = selected.partition(":")
    if kind in ("picture", "text") and index.isdigit():
        values = title.get("images" if kind == "picture" else "text")
        if isinstance(values, list) and int(index) < len(values):
            del values[int(index)]
            if not values: title.pop("images" if kind == "picture" else "text", None)
    elif kind == "layer": title.pop(index, None)
    c["title_selected"] = "background"; _commit_ui(editor)


def _title_revert_element(editor):
    c, selected = editor.workspace_controls["UI"], editor.workspace_controls["UI"].get("title_selected", "")
    title = _ui_section(editor, "title")
    if selected == "background": title.pop("background", None)
    elif selected.startswith("layer:"): title.pop(selected.split(":", 1)[1], None)
    else: _title_remove(editor); return
    if not title: editor.project.other.pop("title", None)
    _commit_ui(editor)


def _title_revert_page(editor):
    title = _ui_section(editor, "title")
    keep = {key: value for key, value in title.items() if key in ("entries", "spacing")}
    if keep: editor.project.other["title"] = keep
    else: editor.project.other.pop("title", None)
    editor.workspace_controls["UI"]["title_selected"] = "background"; _commit_ui(editor)



_MENU_ENTRY_NAMES = ("new_game", "load", "duel", "trade", "options", "campaign", "free_duel", "build_deck", "library", "password", "save")
_MENU_ENTRY_TITLES = ("NEW GAME", "LOAD", "2P DUEL", "TRADE", "OPTION", "CAMPAIGN", "FREE DUEL", "BUILD DECK", "LIBRARY", "PASSWORD", "SAVE")
_MENU_ACTIONS = _MENU_ENTRY_NAMES + ("back", "notice", "quit", "debug_menu", "event", "none")
_MENU_ACTION_TITLES = {"back": "Back", "notice": "Show a notice", "quit": "Quit the game", "debug_menu": "Debug menu", "event": "Code mod event", "none": "Nothing (a buzz)"}
_MENU_SPACING = 32


def _menu_action_allowed(action, menu):
    if action in _MENU_ACTION_TITLES or action in ("new_game", "options"):
        return True
    if action not in _MENU_ENTRY_NAMES:
        return False
    return _MENU_ENTRY_NAMES.index(action) < 5 if menu == 0 else _MENU_ENTRY_NAMES.index(action) >= 5


def _menu_action_title(action):
    if action in _MENU_ENTRY_NAMES:
        return _MENU_ENTRY_TITLES[_MENU_ENTRY_NAMES.index(action)].title()
    return _MENU_ACTION_TITLES.get(action, action)


class _CompatMenuScene:
    """The classic title menu's data model without importing Tkinter."""
    def __init__(self, project):
        self.project = project
        self.title = _ui_section_from(project, "title")
        self.menu = _ui_section_from(project, "menu")
        self.mod_id = project.info.id or "mod"

    def items(self):
        entries = {}
        for source in (self.title.get("entries"), self.menu.get("entries")):
            if not isinstance(source, dict):
                continue
            for name, value in source.items():
                index = _MENU_ENTRY_NAMES.index(name) if name in _MENU_ENTRY_NAMES else -1
                if index >= 0 and isinstance(value, dict):
                    entries.setdefault(index, {}).update(value)
        out = []
        for index, name in enumerate(_MENU_ENTRY_NAMES):
            item = dict(entries.get(index, {})); item.update(name=name, index=index, menu=0 if index < 5 else 1, own=False, entry=True)
            out.append(item)
        for button in self.menu.get("buttons") if isinstance(self.menu.get("buttons"), list) else []:
            if not isinstance(button, dict) or not isinstance(button.get("id"), str):
                continue
            item = dict(button); identifier = button["id"]
            item.update(name=identifier if ":" in identifier else f"{self.mod_id}:{identifier}", index=len(out), entry=False, own=":" not in identifier, menu=1 if button.get("menu") == "second" else 0)
            out.append(item)
        return out

    def order(self, number):
        items = [item for item in self.items() if item["menu"] == number]
        given = self.menu.get("order")
        names = given.get(("first", "second")[number]) if isinstance(given, dict) else (given if number == 0 else None)
        listed = []
        for name in names if isinstance(names, list) else []:
            if not isinstance(name, str):
                continue
            full = name if name in _MENU_ENTRY_NAMES or ":" in name else f"{self.mod_id}:{name}"
            found = next((item for item in items if item["name"] == full), None)
            if found is not None and found not in listed:
                listed.append(found)
        listed += [item for item in items if item not in listed]
        shown = [item for item in listed if item.get("hide") is not True] or [item for item in listed if item["entry"]]
        return [(item, item in shown) for item in listed]

    def menu_scale(self):
        value = self.menu.get("scale", 100)
        return value if isinstance(value, int) and not isinstance(value, bool) and 25 <= value <= 400 else 100

    def scale(self, item):
        value = item.get("scale", self.menu_scale())
        return value if isinstance(value, int) and not isinstance(value, bool) and 25 <= value <= 400 else self.menu_scale()


def _ui_section_from(project, key):
    value = project.other.get(key)
    return value if isinstance(value, dict) else {}


def _menu_scene(editor):
    return _CompatMenuScene(editor.project)


def _menu_short(editor, name):
    prefix = f"{editor.project.info.id or 'mod'}:"
    return name[len(prefix):] if name.startswith(prefix) else name


def _menu_item(editor, name=None):
    name = name or editor.workspace_controls["UI"].get("menu_selected")
    if not isinstance(name, str) or name == "background": return None
    return next((item for item in _menu_scene(editor).items() if item["name"] == name), None)


def _menu_target(editor, create=False):
    item = _menu_item(editor)
    if item is None: return {}
    menu = _ui_section(editor, "menu", create)
    if item.get("entry"):
        entries = menu.get("entries")
        if not isinstance(entries, dict):
            if not create: return {}
            entries = menu["entries"] = {}
        return entries.setdefault(item["name"], {}) if create else entries.get(item["name"], {})
    buttons = menu.get("buttons")
    if not isinstance(buttons, list):
        if not create: return {}
        buttons = menu["buttons"] = []
    short = _menu_short(editor, item["name"])
    for button in buttons:
        if isinstance(button, dict) and button.get("id") == short: return button
    if create:
        value = {"id": short}; buttons.append(value); return value
    return {}


def _menu_target_for(editor, item):
    """Read a menu item's mod entry without changing the selected row."""
    c, current = editor.workspace_controls["UI"], editor.workspace_controls["UI"].get("menu_selected")
    c["menu_selected"] = item["name"]
    value = _menu_target(editor)
    c["menu_selected"] = current
    return value


def _menu_list_image(editor, item):
    """The image shown beside a Menu asset: replacement first, then retail."""
    if item is None:
        image, _data, _art = _title_background(editor, 0)
        return image
    target = _menu_target_for(editor, item)
    image = _ui_image(editor, target.get("image")) if isinstance(target, dict) else None
    if image is not None:
        return image
    title_art = _title_art(editor)
    if item.get("entry") and title_art.ok:
        return title_art.entry(item["index"], False)[0]
    return None


def _refresh_menu(editor):
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QHeaderView, QTreeWidgetItem
    c, tree = editor.workspace_controls["UI"], editor.workspace_controls["UI"]["menu_tree"]
    scene, selected = _menu_scene(editor), c.get("menu_selected", "new_game")
    valid = {"background", *(item["name"] for item in scene.items())}
    if selected not in valid: selected = c["menu_selected"] = "new_game"
    tree.blockSignals(True); tree.clear(); tree.setIconSize(QSize(82, 36)); chosen_item = None
    tree.header().setStretchLastSection(False)
    tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
    background = QTreeWidgetItem(["Menu background", "●" if _ui_section(editor, "menu").get("background") else ""])
    background.setData(0, Qt.ItemDataRole.UserRole, "background")
    preview = _menu_list_image(editor, None)
    if preview is not None: background.setIcon(0, QIcon(QPixmap.fromImage(_qimage(preview.width, preview.height, preview.rgba))))
    tree.addTopLevelItem(background)
    if selected == "background": chosen_item = background
    for number, label in ((0, "First menu"), (1, "Second menu (game loaded)")):
        group = QTreeWidgetItem([label, ""]); tree.addTopLevelItem(group)
        for item, shown in scene.order(number):
            name = item["name"]
            text = item.get("label") or (_MENU_ENTRY_TITLES[item["index"]] if item.get("entry") else _menu_short(editor, name).upper())
            changed = not item.get("entry") or any(key not in ("name", "index", "menu", "own", "entry") for key in item)
            row = QTreeWidgetItem([text if shown else f"◌ {text}", "●" if changed else ""])
            row.setData(0, Qt.ItemDataRole.UserRole, name)
            preview = _menu_list_image(editor, item)
            if preview is not None: row.setIcon(0, QIcon(QPixmap.fromImage(_qimage(preview.width, preview.height, preview.rgba))))
            group.addChild(row)
            if name == selected: chosen_item = row
    tree.expandAll(); tree.setCurrentItem(chosen_item); tree.blockSignals(False)
    _fill_menu_form(editor); _draw_menu(editor)


def _menu_select(editor, item):
    c = editor.workspace_controls["UI"]
    if c.get("ui_loading") or item is None: return
    key = item.data(0, Qt.ItemDataRole.UserRole)
    if isinstance(key, str):
        c["menu_selected"] = key
        found = _menu_item(editor, key)
        if found:
            # _set_value blocks the combo's own signal, so the preview's
            # page (menu_number) needs setting here too, or it stays stale.
            c["menu_number"] = found.get("menu", 0)
            _set_value(c["menu_mode"], c["menu_number"])
        _refresh_menu(editor)


def _fill_menu_form(editor):
    c, item = editor.workspace_controls["UI"], _menu_item(editor)
    enabled = item is not None
    for key in ("menu_words", "menu_action", "menu_tint", "menu_x", "menu_y", "menu_scale", "menu_hidden"):
        c[key].setEnabled(enabled)
    if not item: return
    target = _menu_target(editor)
    _set_value(c["menu_words"], item.get("label", "")); _set_value(c["menu_tint"], item.get("tint", "#FFFFFF"))
    _set_value(c["menu_x"], item.get("x", 0)); _set_value(c["menu_y"], item.get("y", 0)); _set_value(c["menu_scale"], _menu_scene(editor).scale(item)); _set_value(c["menu_hidden"], item.get("hide") is True)
    choices = [action for action in _MENU_ACTIONS if _menu_action_allowed(action, item.get("menu", 0))]
    if item.get("entry"): choices.insert(0, "")
    action = target.get("action") if isinstance(target, dict) else None
    c["menu_action"].blockSignals(True); c["menu_action"].clear()
    for choice in choices: c["menu_action"].addItem("Game default" if not choice else _menu_action_title(choice), choice)
    _set_value(c["menu_action"], action if action in choices else ""); c["menu_action"].blockSignals(False)
    menu = _ui_section(editor, "menu")
    _set_value(c["menu_spacing"], menu.get("spacing", _MENU_SPACING)); _set_value(c["menu_all_scale"], _menu_scene(editor).menu_scale())


def _menu_switch(editor):
    c = editor.workspace_controls["UI"]
    if c.get("ui_loading"): return
    c["menu_number"] = c["menu_mode"].currentData()
    scene = _menu_scene(editor)
    order = scene.order(c["menu_number"])
    if order and (_menu_item(editor) is None or _menu_item(editor).get("menu") != c["menu_number"]): c["menu_selected"] = order[0][0]["name"]
    _refresh_menu(editor)


def _menu_global_changed(editor):
    c = editor.workspace_controls["UI"]
    if c.get("ui_loading"): return
    menu = _ui_section(editor, "menu", True); _put(menu, "spacing", c["menu_spacing"].value(), _MENU_SPACING); _put(menu, "scale", c["menu_all_scale"].value(), 100); _commit_ui(editor)


def _menu_item_changed(editor):
    c = editor.workspace_controls["UI"]
    if c.get("ui_loading") or not _menu_item(editor): return
    target, item = _menu_target(editor, True), _menu_item(editor)
    _put(target, "label", c["menu_words"].text().strip(), None); _put(target, "tint", _colour(c["menu_tint"].text()), "#FFFFFF"); _put(target, "x", c["menu_x"].value(), 0)
    _put(target, "y", c["menu_y"].value(), None); _put(target, "scale", c["menu_scale"].value(), _menu_scene(editor).menu_scale()); _put(target, "hide", c["menu_hidden"].isChecked(), False)
    action = c["menu_action"].currentData()
    _put(target, "action", action, None)
    _commit_ui(editor)


def _menu_add(editor):
    menu = _ui_section(editor, "menu", True); buttons = menu.setdefault("buttons", []); taken = {row.get("id") for row in buttons if isinstance(row, dict)}; number = 1
    while f"button{number}" in taken: number += 1
    row = {"id": f"button{number}", "label": f"BUTTON {number}", "action": "notice", "notice": {"title": f"Button {number}", "text": "Words of your own."}}
    if editor.workspace_controls["UI"].get("menu_number") == 1: row["menu"] = "second"
    buttons.append(row); editor.workspace_controls["UI"]["menu_selected"] = f"{editor.project.info.id or 'mod'}:button{number}"; _commit_ui(editor)


def _menu_toggle_hidden(editor):
    item = _menu_item(editor)
    if item:
        target = _menu_target(editor, True); _put(target, "hide", not bool(item.get("hide")), False); _commit_ui(editor)


def _menu_move(editor, step):
    c, item = editor.workspace_controls["UI"], _menu_item(editor)
    if not item: return
    scene, number = _menu_scene(editor), item.get("menu", 0)
    names = [_menu_short(editor, row["name"]) for row, _ in scene.order(number)]
    name = _menu_short(editor, item["name"])
    if name not in names or not 0 <= names.index(name) + step < len(names): return
    index = names.index(name); names[index], names[index + step] = names[index + step], names[index]
    menu = _ui_section(editor, "menu", True); order = menu.setdefault("order", {}); order = {"first": order} if isinstance(order, list) else order; menu["order"] = order; order[("first", "second")[number]] = names; _commit_ui(editor)


def _menu_inline(editor):
    target = _menu_target(editor, True)
    if target: target.pop("x", None); target.pop("y", None); _commit_ui(editor)


def _menu_image(editor, key):
    item = _menu_item(editor)
    if not item: return
    image = _store_ui_png(editor, f"menu-{_menu_short(editor, item['name'])}" + ("-selected" if key == "selected_image" else ""))
    if image: _menu_target(editor, True)[key] = image; _commit_ui(editor)


def _menu_clear_images(editor):
    target = _menu_target(editor, True)
    if target:
        for key in ("image", "selected_image", "width", "height"): target.pop(key, None)
        _commit_ui(editor)


def _menu_export(editor):
    c, selected = editor.workspace_controls["UI"], editor.workspace_controls["UI"].get("menu_selected", "background")
    if selected == "background":
        image, _data, _art = _title_background(editor, c.get("menu_number", 0))
    else:
        image = _menu_list_image(editor, _menu_item(editor))
    _export_ui_png(editor, image, f"menu-{_menu_short(editor, selected)}.png")


def _menu_remove(editor):
    item = _menu_item(editor)
    if not item or item.get("entry") or not item.get("own"): return
    menu = _ui_section(editor, "menu", True); short = _menu_short(editor, item["name"]); menu["buttons"] = [row for row in menu.get("buttons", []) if not isinstance(row, dict) or row.get("id") != short]
    if not menu["buttons"]: menu.pop("buttons")
    editor.workspace_controls["UI"]["menu_selected"] = "new_game"; _commit_ui(editor)


def _menu_revert_item(editor):
    item = _menu_item(editor)
    if not item: return
    if item.get("entry"):
        entries = _ui_section(editor, "menu", True).get("entries", {});
        if isinstance(entries, dict): entries.pop(item["name"], None)
    else:
        target = _menu_target(editor, True); keep = {key: target[key] for key in ("id", "menu") if key in target}; target.clear(); target.update(keep)
    _commit_ui(editor)


def _menu_revert_page(editor):
    editor.project.other.pop("menu", None)
    title = _ui_section(editor, "title")
    if isinstance(title, dict):
        title.pop("entries", None); title.pop("spacing", None)
        if not title: editor.project.other.pop("title", None)
    editor.workspace_controls["UI"]["menu_selected"] = "new_game"; _commit_ui(editor)


_DUEL_DESCRIPTIONS = {
    "lp_opponent": "The top half of the life-point panel: opponent LP, COM, and deck count.",
    "lp_player": "The lower half of the life-point panel: your LP and deck count.",
    "field": "The FIELD indicator at the upper left of the duel screen.",
    "card_bar": "The strip below the hand that holds the selected card's details.",
    "hand_cursor": "The arrow under the selected card in the hand.",
    "field_cursor": "The brackets around a selected field zone.",
}


def _duel_path(key): return key.split(".", 1) if "." in key else (key, None)


def _duel_target(editor, create=False):
    key = editor.workspace_controls["UI"].get("duel_selected", "lp_player")
    name, part = _duel_path(key); root = _ui_section(editor, "ui", create)
    duel = root.get("duel") if isinstance(root.get("duel"), dict) else None
    if duel is None:
        if not create: return {}
        duel = root["duel"] = {}
    if part:
        bar = duel.get("card_bar") if isinstance(duel.get("card_bar"), dict) else None
        if bar is None:
            if not create: return {}
            bar = duel["card_bar"] = {}
        return bar.setdefault(part, {}) if create else (bar.get(part) if isinstance(bar.get(part), dict) else {})
    return duel.setdefault(name, {}) if create else (duel.get(name) if isinstance(duel.get(name), dict) else {})


def _duel_target_by(editor, key):
    c, current = editor.workspace_controls["UI"], editor.workspace_controls["UI"].get("duel_selected")
    c["duel_selected"] = key; value = _duel_target(editor); c["duel_selected"] = current
    return value


def _refresh_duel(editor):
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QHeaderView, QTreeWidgetItem
    c, tree = editor.workspace_controls["UI"], editor.workspace_controls["UI"]["duel_tree"]
    chosen = c.get("duel_selected", "lp_player")
    valid = {name for name, _label in ELEMENTS} | {f"card_bar.{part}" for part, _label in PARTS}
    if chosen not in valid: chosen = c["duel_selected"] = "lp_player"
    tree.blockSignals(True); tree.clear(); tree.setIconSize(QSize(82, 36)); selected_item = None
    tree.header().setStretchLastSection(False)
    tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
    groups = (("Life points", ELEMENTS[:2]), ("Field", (ELEMENTS[2], ELEMENTS[5])), ("Hand", (ELEMENTS[3], ELEMENTS[4])))
    for group, entries in groups:
        parent = QTreeWidgetItem([group, ""]); tree.addTopLevelItem(parent)
        for name, label in entries:
            value = _duel_target_by(editor, name)
            row = QTreeWidgetItem([label, "●" if value else ""]); row.setData(0, Qt.ItemDataRole.UserRole, name)
            preview = _duel_asset_image(editor, name)
            if preview is not None: row.setIcon(0, QIcon(QPixmap.fromImage(_qimage(preview.width, preview.height, preview.rgba))))
            parent.addChild(row)
            if name == chosen: selected_item = row
            if name == "card_bar":
                for part, part_label in PARTS:
                    key, value = f"card_bar.{part}", _duel_target_by(editor, f"card_bar.{part}")
                    child = QTreeWidgetItem([part_label, "●" if value else ""]); child.setData(0, Qt.ItemDataRole.UserRole, key)
                    preview = _duel_asset_image(editor, key)
                    if preview is not None: child.setIcon(0, QIcon(QPixmap.fromImage(_qimage(preview.width, preview.height, preview.rgba))))
                    row.addChild(child)
                    if key == chosen: selected_item = child
    tree.expandAll(); tree.setCurrentItem(selected_item); tree.blockSignals(False)
    _fill_duel_form(editor); _draw_duel(editor)


def _duel_select(editor, item):
    c = editor.workspace_controls["UI"]
    if c.get("ui_loading") or item is None: return
    key = item.data(0, Qt.ItemDataRole.UserRole)
    if isinstance(key, str): c["duel_selected"] = key; _refresh_duel(editor)


def _fill_duel_form(editor):
    c, key = editor.workspace_controls["UI"], editor.workspace_controls["UI"].get("duel_selected", "lp_player")
    name, part = _duel_path(key); value = _duel_target(editor)
    c["duel_name"].setText(dict(PARTS).get(part, part) if part else dict(ELEMENTS).get(name, name))
    c["duel_description"].setPlainText(f"Card-bar {dict(PARTS).get(part, part).casefold()}; it moves independently on the bar." if part else _DUEL_DESCRIPTIONS.get(name, ""))
    _set_value(c["duel_tint"], value.get("tint", "#FFFFFF")); _set_value(c["duel_digits"], value.get("digits", "#FFFFFF")); _set_value(c["duel_image"], value.get("image", "")); _set_value(c["duel_hidden"], value.get("hide") is True)
    _set_value(c["duel_x"], value.get("x", 0)); _set_value(c["duel_y"], value.get("y", 0)); _set_value(c["duel_scale"], value.get("scale", 100)); _set_value(c["duel_label"], value.get("label", "")); _set_value(c["duel_spacing"], value.get("spacing", 0))
    moves = ui_rules.MOVES.get(name, "xy")
    c["duel_x"].setEnabled(part is not None or "x" in moves); c["duel_y"].setEnabled(part is not None or "y" in moves); c["duel_scale"].setEnabled(part is None and name in ui_rules.SIZED)
    c["duel_digits"].setEnabled(part is None and name in ("lp_opponent", "lp_player")); c["duel_label"].setEnabled(part is None and name in ("lp_opponent", "lp_player")); c["duel_spacing"].setEnabled(part == "name")
    _scene_widget(c["shell"], "duelElementImportButton").setEnabled(part is None)


def _duel_art(editor):
    c = editor.workspace_controls["UI"]
    key = id(getattr(editor, "files", None))
    if c.get("duel_art_key") != key:
        c["duel_art_key"] = key
        c["duel_art"] = ui_assets.DuelArt(getattr(getattr(editor, "files", None), "wa", None))
    return c["duel_art"]


def _duel_font(editor):
    """The same retail font and icons used by the classic duel preview."""
    c = editor.workspace_controls["UI"]
    files = getattr(editor, "files", None)
    key = id(files)
    if c.get("duel_font_key") != key:
        c["duel_font_key"] = key
        try:
            c["duel_font"] = card_text.RetailFont(getattr(files, "wa", None))
        except (TypeError, ValueError):
            c["duel_font"] = None
    return c.get("duel_font")


def _duel_asset_image(editor, key=None):
    """A standalone picture for a Duel tree row or its Export action."""
    c = editor.workspace_controls["UI"]
    key = key or c.get("duel_selected", "lp_player")
    name, part = _duel_path(key)
    duel, art = _ui_section(editor, "ui").get("duel", {}), _duel_art(editor)
    duel = duel if isinstance(duel, dict) else {}
    if not art.ok:
        return None
    if part is None:
        value = duel.get(name) if isinstance(duel.get(name), dict) else {}
        image = _ui_image(editor, value.get("image"))
        if image is not None: return image
        turn = c.get("duel_opponent") is not None and c["duel_opponent"].isChecked()
        pieces = {"card_bar": art.card_bar(), "field": art.field(), "hand_cursor": art.hand_cursor(),
                  "field_cursor": art.field_cursor(), "lp_opponent": art.panel_half(0, turn), "lp_player": art.panel_half(1, turn)}
        return pieces.get(name)
    bar = duel.get("card_bar") if isinstance(duel.get("card_bar"), dict) else {}
    wa = getattr(getattr(editor, "files", None), "wa", None)
    try:
        pictures = [(image, x, y) for image, x, y, image_part in duel_screen.bar_words(editor.project, wa, art, _duel_font(editor), 9, bar) if image_part == part]
    except (AttributeError, IndexError, KeyError, OSError, ValueError):
        pictures = []
    if not pictures: return None
    left, top = min(x for _image, x, _y in pictures), min(y for _image, _x, y in pictures)
    right = max(x + image.width for image, x, _y in pictures); bottom = max(y + image.height for image, _x, y in pictures)
    out = pngio.Image(right - left, bottom - top, b"\0" * ((right - left) * (bottom - top) * 4))
    for image, x, y in pictures: out = ui_assets.paste(out, image, x - left, y - top)
    return out


def _duel_element_at(name, value, rect):
    x, y, width, height = rect
    scale = _as_int(value.get("scale"), 100) if name in ui_rules.SIZED else 100
    scale = max(25, min(400, scale))
    moves = ui_rules.MOVES.get(name, "xy")
    dx = _as_int(value.get("x")) if "x" in moves else 0
    dy = _as_int(value.get("y")) if "y" in moves else 0
    middle_x, middle_y = x + width // 2, y + height // 2
    out_w, out_h = max(1, width * scale // 100), max(1, height * scale // 100)
    return middle_x - out_w // 2 + dx, middle_y - out_h // 2 + dy, out_w, out_h


def _draw_duel(editor):
    c = editor.workspace_controls["UI"]
    with _comparing_view(editor) as comparing:
        duel = _ui_section(editor, "ui").get("duel", {})
        if not isinstance(duel, dict): duel = {}
        art = _duel_art(editor)
        board = c.get("board_render_image")
        canvas = _title_scaled(board, 320, 240) if board is not None else ui_assets.blank(320, 240, (0, 0, 0, 255))
        if not art.ok:
            _png_preview(c["duel_preview"], _compare_badge(canvas) if comparing else canvas, "Load game files to preview the duel HUD")
            return
        turn = c["duel_opponent"].isChecked()
        pieces = {"card_bar": art.card_bar(), "field": art.field(), "hand_cursor": art.hand_cursor(), "field_cursor": art.field_cursor(), "lp_opponent": art.panel_half(0, turn), "lp_player": art.panel_half(1, turn)}
        # This is the original editor's painter order: the stage, bar and its
        # words, cursors/HUD, then the dealt hand and hand cursor.
        boxes = {}
        for name in ("card_bar", "field_cursor", "field", "lp_opponent", "lp_player"):
            value = duel.get(name) if isinstance(duel.get(name), dict) else {}
            if value.get("hide") is True: continue
            x, y, width, height = _duel_element_at(name, value, ui_assets.DUEL_RECTS[name])
            boxes[name] = (x, y, width, height)
            own = _ui_image(editor, value.get("image"))
            image = _title_scaled(own, width, height) if own is not None else _title_scaled(pieces[name], width, height)
            canvas = ui_assets.paste(canvas, ui_assets.tint(image, ui_assets.parse_color(value.get("tint"))), x, y)
        # Reuse the classic hand and card-bar composition.  It has no GUI work and
        # only reads cached game sprites, so this remains quick while dragging.
        files, wa = getattr(editor, "files", None), getattr(getattr(editor, "files", None), "wa", None)
        bar = duel.get("card_bar") if isinstance(duel.get("card_bar"), dict) else {}
        bar_kind = c["duel_bar_kind"].currentData() or c["duel_bar_kind"].currentText()
        hand = (9, 20, 27, 31, 28)
        if str(bar_kind).casefold().startswith("magic"):
            cards = getattr(editor.project, "cards", {}) or {}
            magic = next((cid for cid in sorted(cards) if getattr(cards[cid], "type", None) == gamedata.TYPE_MAGIC), None)
            if magic is not None: hand = (magic,) + hand[1:]
        try:
            shown = duel_screen.bar_words(editor.project, wa, art, _duel_font(editor), hand[0], bar)
        except (AttributeError, IndexError, KeyError, OSError, ValueError):
            shown = []
        part_bounds = {}
        for image, x, y, part in shown:
            canvas = ui_assets.paste(canvas, image, x, y)
            left, top, right, bottom = part_bounds.get(part, (x, y, x + image.width, y + image.height))
            part_bounds[part] = (min(left, x), min(top, y), max(right, x + image.width), max(bottom, y + image.height))
        for part, (left, top, right, bottom) in part_bounds.items():
            boxes[f"card_bar.{part}"] = (left, top, right - left, bottom - top)
        try:
            for cid, (x, y) in zip(hand, duel_screen.HAND_AT):
                canvas = ui_assets.paste(canvas, duel_screen.hand_card(editor.project, wa, art, cid), x, y)
        except (AttributeError, IndexError, KeyError, OSError, ValueError):
            pass
        value = duel.get("hand_cursor") if isinstance(duel.get("hand_cursor"), dict) else {}
        if value.get("hide") is not True:
            x, y, width, height = _duel_element_at("hand_cursor", value, ui_assets.DUEL_RECTS["hand_cursor"])
            boxes["hand_cursor"] = (x, y, width, height)
            own = _ui_image(editor, value.get("image"))
            image = _title_scaled(own, width, height) if own is not None else _title_scaled(pieces["hand_cursor"], width, height)
            canvas = ui_assets.paste(canvas, ui_assets.tint(image, ui_assets.parse_color(value.get("tint"))), x, y)
        c["duel_boxes"] = boxes
        canvas = _outline(canvas, boxes.get(c.get("duel_selected")))
    _png_preview(c["duel_preview"], _compare_badge(canvas) if comparing else canvas, "Load game files to preview the duel HUD")


def _duel_changed(editor):
    c = editor.workspace_controls["UI"]
    if c.get("ui_loading"): return
    key = c.get("duel_selected", "lp_player"); name, part = _duel_path(key); target = _duel_target(editor, True)
    if part:
        _put(target, "spacing", c["duel_spacing"].value() if part == "name" else 0, 0)
        for field, value in (("x", c["duel_x"].value()), ("y", c["duel_y"].value())): _put(target, field, value, 0)
        _put(target, "tint", _colour(c["duel_tint"].text()), "#FFFFFF"); _put(target, "hide", c["duel_hidden"].isChecked(), False)
    else:
        moves = ui_rules.MOVES.get(name, "xy")
        if "x" in moves: _put(target, "x", c["duel_x"].value(), 0)
        if "y" in moves: _put(target, "y", c["duel_y"].value(), 0)
        if name in ui_rules.SIZED: _put(target, "scale", c["duel_scale"].value(), 100)
        _put(target, "tint", _colour(c["duel_tint"].text()), "#FFFFFF")
        if name in ("lp_opponent", "lp_player"):
            _put(target, "digits", _colour(c["duel_digits"].text()), "#FFFFFF"); _put(target, "label", c["duel_label"].text().strip(), None)
        _put(target, "hide", c["duel_hidden"].isChecked(), False)
    _commit_ui(editor)


def _duel_image(editor):
    key = editor.workspace_controls["UI"].get("duel_selected", "duel")
    if "." in key: return
    image = _store_ui_png(editor, f"duel-{key.replace('_', '-')}")
    if image: _duel_target(editor, True)["image"] = image; _commit_ui(editor)


def _duel_export(editor):
    selected = editor.workspace_controls["UI"].get("duel_selected", "lp_player")
    _export_ui_png(editor, _duel_asset_image(editor, selected), f"duel-{selected.replace('.', '-')}.png")


def _duel_revert_element(editor):
    key = editor.workspace_controls["UI"].get("duel_selected", "lp_player"); name, part = _duel_path(key); root = _ui_section(editor, "ui")
    duel = root.get("duel") if isinstance(root.get("duel"), dict) else {}
    if part:
        bar = duel.get("card_bar") if isinstance(duel.get("card_bar"), dict) else {}; bar.pop(part, None)
        if not bar: duel.pop("card_bar", None)
    else: duel.pop(name, None)
    if not duel: root.pop("duel", None)
    if not root: editor.project.other.pop("ui", None)
    _commit_ui(editor)


def _duel_revert_page(editor):
    root = _ui_section(editor, "ui")
    root.pop("duel", None)
    if not root:
        editor.project.other.pop("ui", None)
    _commit_ui(editor)
def _board_parts(c):
    key = c.get("board_selected", "floor")
    return list(board_art.FLOOR) if key == "floor" else [board_art.BY_KEY[key]] if key in board_art.BY_KEY else list(board_art.FLOOR)


def _board_terrains(c):
    current = c["board_field"].currentData() or c["board_field"].currentText().casefold()
    return list(board_art.TERRAINS) if c["board_all"].isChecked() else [current if current in board_art.TERRAINS else "normal"]


def _board_terrain(c):
    """The one field shown in the 3D preview right now."""
    terrain = c["board_field"].currentData() or "normal"
    return terrain if terrain in board_art.TERRAINS else "normal"


def _board_outline_keys(c):
    """The part(s) outlined on the 3D preview (ui_board.py's show())."""
    selected = c.get("board_selected", "floor")
    return [p.key for p in board_art.FLOOR] if selected == "floor" else [selected]


def _board_refresh(editor, force=False):
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QTreeWidgetItem
    c = editor.workspace_controls["UI"]
    field = c["board_field"]
    # The .ui form ships the combo pre-populated with plain-text items (no
    # itemData), so "already has rows" is not "already has the right rows":
    # that left every item's data None forever, and currentData() with it.
    if field.count() != len(board_art.TERRAINS) or any(field.itemData(i) not in board_art.TERRAINS for i in range(field.count())):
        field.blockSignals(True)
        kept = field.currentData() if field.currentData() in board_art.TERRAINS else None
        field.clear()
        for terrain in board_art.TERRAINS:
            field.addItem(board_art.TERRAIN_LABELS[terrain], terrain)
        field.setCurrentIndex(field.findData(kept) if kept else 0)
        field.blockSignals(False)
    terrain = _board_terrain(c)
    tree, selected = c["board_tree"], c.get("board_selected", "floor")
    if selected != "floor" and selected not in board_art.BY_KEY:
        selected = c["board_selected"] = "floor"
    tree.blockSignals(True); tree.clear(); tree.setIconSize(QSize(68, 34)); current = None
    groups = (("Floor", "floor", board_art.FLOOR), ("Walls and trim", None, board_art.WALLS))
    for label, group_key, parts in groups:
        parent = QTreeWidgetItem([label])
        parent.setData(0, Qt.ItemDataRole.UserRole, group_key)
        preview = board_art.floor_image(editor.project, terrain) if group_key == "floor" else None
        if preview is not None: parent.setIcon(0, QIcon(QPixmap.fromImage(_qimage(preview.width, preview.height, preview.rgba))))
        tree.addTopLevelItem(parent)
        if group_key == selected: current = parent
        for part in parts:
            child = QTreeWidgetItem([part.label])
            child.setData(0, Qt.ItemDataRole.UserRole, part.key)
            preview = board_art.shown(editor.project, terrain, part)
            if preview is not None: child.setIcon(0, QIcon(QPixmap.fromImage(_qimage(preview.width, preview.height, preview.rgba))))
            parent.addChild(child)
            if part.key == selected: current = child
    tree.expandAll(); tree.setCurrentItem(current); tree.blockSignals(False)
    parts = _board_parts(c)
    image = board_art.floor_image(editor.project, terrain) if selected == "floor" else board_art.shown(editor.project, terrain, parts[0])
    _png_preview(c["board_part_preview"], image, "Game texture unavailable")
    labels = "Floor" if selected == "floor" else parts[0].label
    c["board_part_label"].setText(labels)
    detail = "All five board rows as one image." if selected == "floor" else parts[0].what
    if selected != "floor" and parts[0].warnings:
        detail += " " + " ".join(parts[0].warnings)
    c["board_description"].setText(detail)
    c["board_resolution"].setText(f"{image.width} × {image.height} pixels" if image else "Game texture unavailable")
    tints = {board_art.tint_of(editor.project, terrain, part) for part in parts}
    _set_value(c["board_tint"], f"#{next(iter(tints)):06X}" if len(tints) == 1 else "#FFFFFF")
    _queue_board_render(editor, terrain, force)


_BOARD_SIZE = (480, 360)
_BOARD_DRAG_SIZE = (160, 120)   # a third the size while the camera moves -- ui_board.py's DRAG_SCALE


def _board_camera(c):
    camera = c.get("board_camera")
    return tuple(camera) if isinstance(camera, (tuple, list)) and len(camera) == 5 else board_model.CAMERA


def _board_redisplay(editor):
    """Redraw the cached render after the outline toggle changes, with no
    new 3D render needed."""
    c = editor.workspace_controls.get("UI", {})
    if c.get("board_picture") is not None:
        _board_display(editor, c["board_picture"])


def _board_display(editor, picture, full_size=True):
    """The cached 3D render redrawn with the current part(s) outlined, no
    re-render needed (a part picked, or a selection made elsewhere)."""
    c = editor.workspace_controls.get("UI", {})
    show_outlines = c.get("board_show_outlines") is None or c["board_show_outlines"].isChecked()
    shown = board_model.outline(picture, _board_outline_keys(c) if show_outlines else [], 2)
    _png_preview(c["board_preview"], shown, "Game board unavailable")
    # A low-resolution drag frame is not worth also recompositing the Duel
    # HUD preview over; that waits for the next full-size picture.
    if full_size and c.get("duel_preview") is not None:
        c["board_render_image"] = picture.image
        _draw_duel(editor)


def _queue_board_render(editor, terrain, force=False, size=None):
    """Render board geometry off the GUI thread; disc decoding can be slow."""
    c = editor.workspace_controls.get("UI", {})
    size = size or _BOARD_SIZE
    version = board_art.state(editor.project).version
    camera = _board_camera(c)
    key = (terrain, version, camera, size)
    if not force and c.get("board_render_key") == key:
        # Nothing moved: just the outline may have (a different part chosen).
        if c.get("board_picture") is not None:
            _board_display(editor, c["board_picture"], size == _BOARD_SIZE)
        return
    c["board_render_key"] = key
    if c.get("board_picture") is None:
        _canvas(c["board_preview"], "DUEL BOARD", ["Rendering preview…"])
    result = {"picture": None, "error": None}
    def render():
        try:
            if board_model.available(editor.project):
                model = board_model.board(board_art.disc(editor.project), terrain)
                pieces = board_model.pieces_of(editor.project, terrain)
                result["picture"] = board_model.render(model, pieces, camera, size)
        except Exception as problem:  # a damaged game image should not break Assets
            result["error"] = str(problem)
    worker = threading.Thread(target=render, daemon=True)
    worker.start()
    def finish():
        if worker.is_alive():
            QTimer.singleShot(15 if size != _BOARD_SIZE else 30, finish); return
        controls = editor.workspace_controls.get("UI", {})
        if controls.get("board_render_key") != key or controls.get("board_preview") is None:
            return
        if result["picture"] is not None:
            # The Duel page reuses this completed picture as its stage.
            # Rendering happened on the worker above, so selecting the Duel
            # tab never stalls the editor as the old synchronous view did.
            controls["board_picture"] = result["picture"]
            _board_display(editor, result["picture"], size == _BOARD_SIZE)
        else:
            controls["board_picture"] = None
            _canvas(controls["board_preview"], "DUEL BOARD", ["Game board unavailable", result["error"] or "Load game files to render the board."])
    QTimer.singleShot(0, finish)


def _board_request_render(editor, full_size=False):
    """Coalesce a flurry of drag/wheel moves into one render at a time: a
    small, fast picture while the camera is actively moving (ui_board.py's
    DRAG_SCALE), the real size once it settles (_board_release)."""
    c = editor.workspace_controls.get("UI", {})
    if c.get("board_render_pending"):
        return
    c["board_render_pending"] = True
    def fire():
        c["board_render_pending"] = False
        dragging = not full_size and isinstance(c.get("board_drag"), dict)
        _queue_board_render(editor, _board_terrain(c), force=full_size,
                            size=_BOARD_DRAG_SIZE if dragging else _BOARD_SIZE)
    QTimer.singleShot(16, fire)


def _board_point(label, position):
    """A preview-label point in the 3D render's own 480x360 pixels."""
    scale = min(label.width() / _BOARD_SIZE[0], label.height() / _BOARD_SIZE[1])
    if scale <= 0: return 0, 0
    left, top = (label.width() - _BOARD_SIZE[0] * scale) / 2, (label.height() - _BOARD_SIZE[1] * scale) / 2
    return (position.x() - left) / scale, (position.y() - top) / scale


def _board_press(editor, label, event):
    c = editor.workspace_controls.get("UI", {})
    point = _board_point(label, event.position())
    if event.button() == Qt.MouseButton.MiddleButton:
        kind = "pan" if event.modifiers() & (Qt.KeyboardModifier.ShiftModifier | Qt.KeyboardModifier.ControlModifier) else "turn"
        c["board_drag"] = {"kind": kind, "point": point, "camera": _board_camera(c)}
    else:
        c["board_click"] = point


def _board_motion(editor, label, event):
    c = editor.workspace_controls.get("UI", {})
    drag = c.get("board_drag")
    if not isinstance(drag, dict): return
    point = _board_point(label, event.position())
    k = board_model.frame(_BOARD_SIZE)[0]
    dx, dy = (point[0] - drag["point"][0]) / k, (point[1] - drag["point"][1]) / k
    if not dx and not dy: return
    camera = board_model.pan(drag["camera"], dx, dy) if drag["kind"] == "pan" else board_model.orbit(drag["camera"], dx, dy)
    c["board_camera"] = camera
    _board_request_render(editor)


def _board_release(editor, label, event):
    c = editor.workspace_controls.get("UI", {})
    if event.button() == Qt.MouseButton.MiddleButton:
        was_dragging = c.pop("board_drag", None) is not None
        if was_dragging: _board_request_render(editor, full_size=True)
    elif event.button() == Qt.MouseButton.LeftButton:
        point = c.pop("board_click", None)
        if point is not None: _board_pick(editor, point)


def _board_wheel(editor, delta):
    if not delta: return
    c = editor.workspace_controls.get("UI", {})
    c["board_camera"] = board_model.zoom(_board_camera(c), 1 if delta > 0 else -1)
    _board_request_render(editor)


def _board_reset_view(editor):
    """The duel's own camera again (ui_board.py's reset_camera)."""
    c = editor.workspace_controls.get("UI", {})
    c["board_camera"] = board_model.CAMERA
    _board_request_render(editor)


def _board_pick(editor, point):
    """A click on the 3D preview itself chooses the part under it."""
    c = editor.workspace_controls.get("UI", {})
    picture = c.get("board_picture")
    if picture is None: return
    key = picture.part_at(int(point[0]), int(point[1]))
    if key is None or key not in board_art.BY_KEY: return
    if key != c.get("board_selected"):
        c["board_selected"] = key
        _board_refresh(editor)


def _board_select(editor, item):
    c = editor.workspace_controls["UI"]
    if c.get("ui_loading") or item is None:
        return
    key = item.data(0, Qt.ItemDataRole.UserRole)
    if key == "floor" or key in board_art.BY_KEY:
        c["board_selected"] = key
        _board_refresh(editor)


def _board_filter(editor):
    query = editor.workspace_controls["UI"]["board_search"].text().strip().casefold()
    tree = editor.workspace_controls["UI"]["board_tree"]
    for index in range(tree.topLevelItemCount()):
        parent = tree.topLevelItem(index); visible = not query or query in parent.text(0).casefold()
        for child_index in range(parent.childCount()):
            child = parent.child(child_index)
            show = not query or query in child.text(0).casefold()
            child.setHidden(not show); visible = visible or show
        parent.setHidden(not visible)


def _board_tint(editor):
    c = editor.workspace_controls["UI"]
    if c.get("ui_loading"):
        return
    value = _colour(c["board_tint"].text(), "")
    if not value:
        QMessageBox.warning(editor, "Duel board", "Use a six-digit colour, such as #C08040.")
        _board_refresh(editor); return
    board_art.set_tint(editor.project, _board_terrains(c), _board_parts(c), int(value[1:], 16))
    editor._mark_dirty(); _board_refresh(editor, force=True)


def _board_replace(editor):
    c = editor.workspace_controls["UI"]
    path, _ = QFileDialog.getOpenFileName(editor, "Replace board texture", "", "PNG images (*.png)")
    if not path:
        return
    try:
        image = pngio.read(path)
        notes = board_art.set_floor(editor.project, _board_terrains(c), image) if c.get("board_selected") == "floor" else \
                board_art.set_piece(editor.project, _board_terrains(c), _board_parts(c)[0], image)
    except (OSError, ValueError, pngio.PngError) as problem:
        QMessageBox.critical(editor, "Duel board", f"That PNG cannot be used: {problem}")
        return
    editor._mark_dirty(); _board_refresh(editor, force=True)
    if notes:
        QMessageBox.information(editor, "Duel board", "\n".join(notes))


def _board_export(editor):
    c = editor.workspace_controls["UI"]
    terrain, part = (_board_terrains(c)[0], _board_parts(c))
    image = board_art.floor_image(editor.project, terrain) if c.get("board_selected") == "floor" else board_art.shown(editor.project, terrain, part[0])
    if image is None:
        QMessageBox.information(editor, "Duel board", "Load game files or replace this board texture before exporting it.")
        return
    path, _ = QFileDialog.getSaveFileName(editor, "Export board texture", "board.png", "PNG images (*.png)")
    if not path:
        return
    try:
        pngio.write(path, image)
    except OSError as problem:
        QMessageBox.critical(editor, "Duel board", f"Could not export the PNG: {problem}")


def _board_revert(editor):
    c = editor.workspace_controls["UI"]
    board_art.revert(editor.project, _board_terrains(c), _board_parts(c))
    editor._mark_dirty(); _board_refresh(editor, force=True)


def _board_revert_all(editor):
    board_art.revert_all(editor.project)
    editor._mark_dirty(); _board_refresh(editor, force=True)


def _catalog():
    # A frozen build has no "docs" sibling four levels up (that climbs
    # above the extraction folder); build_exe.py bundles a copy next to
    # this module instead, matching build_info.py's own frozen/source split.
    path = (Path(__file__).with_name("asset-catalog.json") if getattr(sys, "frozen", False) else
            Path(__file__).resolve().parents[4] / "docs" / "asset-catalog.json")
    try:
        values, named = json.loads(path.read_text()), {}
        for value in values:
            if not isinstance(value, dict) or not isinstance(value.get("name"), str): continue
            if value["name"].startswith(("card_art/", "thumbnails/", "nameplate/")): continue
            item = named.setdefault(value["name"], dict(value, regions=0))
            item["regions"] += 1
        return list(named.values())
    except (OSError, ValueError):
        return []


def _category(name):
    """The catalog directory is the category, including a subcategory."""
    folder, separator, _asset = name.rpartition("/")
    return folder if separator else name


def _display_category(category):
    return " / ".join(part.replace("_", " ").title() for part in category.split("/"))


def _texture_identity(entry):
    """The fields that identify one texture read by the game.

    The named asset framework uses catalogue names, while established HD
    mods use texture-pack manifest entries.  A catalogue item and a manifest
    entry describe the same read when these fields agree.
    """
    try:
        bpp = int(entry.get("bpp"))
        return (
            str(entry.get("archive", "")).upper(), int(entry.get("offset")),
            int(entry.get("words")), int(entry.get("rows")), bpp,
            int(entry.get("clut_offset")),
            int(entry.get("clut_entries", 16 if bpp == 4 else 256)),
        )
    except (TypeError, ValueError):
        return None


def _native_size(entry):
    pixels_per_word = {4: 4, 8: 2, 16: 1}.get(entry.get("bpp"), 1)
    return (int(entry.get("width", entry["words"] * pixels_per_word)),
            int(entry["rows"]))


def _atlas_crop(asset, entry):
    """The catalog region inside a larger HD pack texture, if it fits."""
    try:
        if (str(asset.get("archive", "")).upper() != str(entry.get("archive", "")).upper()
                or int(asset.get("bpp")) != int(entry.get("bpp"))
                or int(asset.get("clut_offset")) != int(entry.get("clut_offset"))):
            return None
        bpp = int(asset["bpp"])
        wanted_clut = int(asset.get("clut_entries", 16 if bpp == 4 else 256))
        found_clut = int(entry.get("clut_entries", 16 if bpp == 4 else 256))
        if wanted_clut != found_clut:
            return None
        row_bytes = int(entry.get("stride", entry["words"])) * 2
        # Catalogued regions can keep their parent atlas's stride.  Their
        # own row span is their visible width, not that inherited stride.
        asset_width, _asset_height = _native_size(asset)
        asset_bytes = (asset_width * bpp + 7) // 8
        delta = int(asset["offset"]) - int(entry["offset"])
        row, column = divmod(delta, row_bytes)
        if delta < 0 or column + asset_bytes > row_bytes or row + int(asset["rows"]) > int(entry["rows"]):
            return None
        pixels_per_byte = 8 // bpp
        width, height = _native_size(asset)
        return column * pixels_per_byte, row, width, height
    except (KeyError, TypeError, ValueError):
        return None


def _legacy_pack_entries(self):
    """Map catalogued assets to an existing texture-pack entry once.

    Forbidden Memories HD has almost two thousand texture entries.  Building
    this index when the Assets page opens avoids repeatedly scanning that
    manifest while filters, selections, and page refreshes run.
    """
    c = self.workspace_controls.get("UI", {})
    st = art.state(self.project)
    # ``or []`` made a fresh empty list for every catalogue row when a mod
    # has no texture manifest.  The identity cache below then missed 233
    # times per refresh, rebuilding the whole index on every click.
    entries = st.entries if st.entries is not None else ()
    cached = c.get("legacy_pack_index")
    if cached and cached[0] is entries:
        return cached[1]
    by_identity, pack_entries = {}, []
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("file"), str):
            continue
        pack_entries.append(entry)
        identity = _texture_identity(entry)
        if identity is not None:
            # Texture packs use the first matching entry, so mirror that.
            by_identity.setdefault(identity, entry)
    index = {}
    for asset in c.get("catalog", _catalog()):
        entry = by_identity.get(_texture_identity(asset))
        if entry is not None:
            index[asset["name"]] = (entry, None)
            continue
        # HD mods commonly replace a small icon with one larger texture
        # atlas.  Match its shared palette and source rectangle, then retain
        # the sub-rectangle for the preview.
        for candidate in pack_entries:
            crop = _atlas_crop(asset, candidate)
            if crop is not None:
                index[asset["name"]] = (candidate, crop)
                break
    c["legacy_pack_index"] = (entries, index)
    return index


def _named_asset_path(self, asset):
    folder = self.project.other.get("assets")
    if not isinstance(folder, str) or not folder:
        return None
    relative = f"{folder.rstrip('/')}/{asset['name']}.png"
    if relative in self.project.deleted_files:
        return None
    if relative in self.project.files:
        return relative
    source = self.project.source_dir
    return relative if source and (Path(source) / relative).is_file() else None


def _entry_origin(self, asset):
    """Return ``(path, origin, manifest_entry)`` for a replacement."""
    if asset is None:
        return None, None, None
    named = _named_asset_path(self, asset)
    if named:
        return named, "named", None
    match = _legacy_pack_entries(self).get(asset["name"])
    if match is not None:
        entry, _crop = match
        return f"{art.pack_dir(self.project).rstrip('/')}/{entry['file']}", "pack", entry
    return None, None, None


def _legacy_crop(self, asset):
    match = _legacy_pack_entries(self).get(asset["name"])
    return match[1] if match is not None else None


def _asset_shares_entry(self, asset, manifest_entry):
    """Whether another catalogued asset still resolves to this pack entry --
    true for siblings cropped from the same shared HD atlas."""
    return any(entry is manifest_entry and name != asset["name"]
               for name, (entry, _crop) in _legacy_pack_entries(self).items())


def _asset_shares_entry_outside(self, manifest_entry, names_in_scope):
    """Whether a catalogued asset *not* in ``names_in_scope`` still resolves
    to this pack entry -- used by a bulk revert to tell "every sibling this
    atlas has is also being reverted right now" from "something outside
    this operation still needs it", so the former can fully clear the
    entry instead of only patching pixels back to retail."""
    return any(entry is manifest_entry and name not in names_in_scope
               for name, (entry, _crop) in _legacy_pack_entries(self).items())


def _file_still_used(project, filename, except_entry):
    """Whether any OTHER manifest entry still names this PNG. Two distinct
    texture-pack entries can share one backing file even when no catalogued
    asset maps to the other one, so this checks the raw manifest rather than
    only the entries a catalog asset currently resolves to."""
    if not isinstance(filename, str):
        return False
    st = art.state(project)
    return any(isinstance(entry, dict) and entry is not except_entry and entry.get("file") == filename
               for entry in st.entries or [])


def _atlas_region(manifest_entry, crop, canvas_width, canvas_height):
    """Where ``crop`` (native pixels, from `_legacy_crop`) lands inside a PNG
    backing ``manifest_entry`` at ``canvas_width`` x ``canvas_height`` -- the
    write-side counterpart of the scaling `_select_template` does to show it."""
    source_width, source_height = _native_size(manifest_entry)
    scale_x, scale_y = canvas_width / source_width, canvas_height / source_height
    left, top = round(crop[0] * scale_x), round(crop[1] * scale_y)
    width, height = max(1, round(crop[2] * scale_x)), max(1, round(crop[3] * scale_y))
    return left, top, width, height


def _entry_for(self, asset):
    return _entry_origin(self, asset)[0]


def _named_image(self, relative):
    if not relative: return None
    try:
        if relative in self.project.files: return pngio.decode(self.project.files[relative])
        return pngio.read(Path(self.project.source_dir) / relative) if self.project.source_dir else None
    except (OSError, ValueError, pngio.PngError):
        return None


def _open_assets_folder(self):
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtCore import QUrl
    folder = self.project.other.get("assets") if self.project else None
    base = Path(self.project.source_dir) if self.project and self.project.source_dir else None
    target = base / folder if base and isinstance(folder, str) else base
    if target and target.exists():
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))
    else:
        QMessageBox.information(self, "UI assets", "This mod has no assets folder yet. Import a PNG first to create one.")


def _show_asset_help(self):
    QMessageBox.information(self, "UI asset replacement", "Select a catalogued UI texture, import a PNG replacement, then save the mod. The editor writes replacements under assets/ using the catalog name.")


def _asset_goto_tab(self, label):
    """Switch the UI/Graphics tabs to the one titled ``label``, if any."""
    tabs = self.workspace_controls.get("UI", {}).get("tabs")
    if tabs is None:
        return
    for i in range(tabs.count()):
        if tabs.tabText(i) == label:
            tabs.setCurrentIndex(i)
            return


def _asset_goto_duel_element(self, key):
    """Jump to the Duel tab with ``key`` (a duel_assets.ELEMENTS name)
    selected, as if its row in the element tree had been clicked."""
    _asset_goto_tab(self, "Duel")
    c = self.workspace_controls.get("UI", {})
    if "duel_tree" in c:
        c["duel_selected"] = key
        _refresh_duel(self)


def _asset_screen_not_catalogued(self, screen):
    QMessageBox.information(self, "UI asset replacement",
        f"The {screen} screen's own textures are not catalogued yet (unlike Duel, Title and Menus, "
        f"the port has no per-element config for {screen.lower()}), so there is nothing to jump to or "
        "replace for it specifically here.")


def _build_framework(self, page, controls, layout):
    catalog = _catalog()
    categories = sorted({item["name"].split("/", 1)[0] for item in catalog}, key=str.casefold)
    controls.clear(); controls.update(page=page, catalog=catalog, category=categories[0] if categories else "", selected=None)
    self.workspace_controls["UI"] = controls
    root = QSplitter(Qt.Orientation.Horizontal); root.setChildrenCollapsible(False); layout.addWidget(root, 1)
    category_box = QGroupBox("Asset Categories")
    category_layout = QVBoxLayout(category_box); category_layout.setContentsMargins(8, 12, 8, 8)
    categories_view = QListWidget(); categories_view.setMinimumWidth(180); categories_view.setSpacing(5)
    controls["categories"] = categories_view
    for name in categories:
        item = QListWidgetItem(_display_category(name)); item.setData(Qt.ItemDataRole.UserRole, name)
        categories_view.addItem(item)
    categories_view.setCurrentRow(0); category_layout.addWidget(categories_view); root.addWidget(category_box)
    centre = QWidget(); centre_layout = QVBoxLayout(centre); centre_layout.setContentsMargins(8, 0, 8, 0); centre_layout.setSpacing(7)
    controls["grid_heading"] = QLabel(); controls["grid_heading"].setObjectName("heading"); centre_layout.addWidget(controls["grid_heading"])
    search = _line("Search assets…"); controls["search"] = search; centre_layout.addWidget(search)
    grid = QListWidget(); grid.setViewMode(QListView.ViewMode.IconMode); grid.setResizeMode(QListView.ResizeMode.Adjust); grid.setMovement(QListView.Movement.Static); grid.setIconSize(QSize(112, 112)); grid.setGridSize(QSize(142, 154)); grid.setSpacing(8)
    grid.setStyleSheet("QListWidget::item { border: 1px solid #23415f; border-radius: 5px; padding: 4px; } QListWidget::item:selected { border: 3px solid #1677ff; background: #10294d; }")
    controls["grid"] = grid; centre_layout.addWidget(grid, 1); root.addWidget(centre)
    detail = QWidget(); detail.setMinimumWidth(620); detail_layout = QVBoxLayout(detail); detail_layout.setContentsMargins(0, 0, 0, 0); detail_layout.setSpacing(7)
    controls["name"] = QLabel("Select an asset"); controls["name"].setObjectName("heading"); detail_layout.addWidget(controls["name"])
    controls["description"] = QLabel("Choose a named UI asset to preview its retail texture and add a replacement."); controls["description"].setObjectName("muted"); controls["description"].setWordWrap(True); detail_layout.addWidget(controls["description"])
    previews = QHBoxLayout(); controls["retail"] = QLabel("Retail preview"); controls["replacement"] = QLabel("Your replacement")
    for label, title in ((controls["retail"], "Retail (PS1)"), (controls["replacement"], "Replacement (Your Mod)")):
        box = QGroupBox(title); inner = QVBoxLayout(box); label.setMinimumSize(230, 260); label.setAlignment(Qt.AlignmentFlag.AlignCenter); inner.addWidget(label); previews.addWidget(box)
    detail_layout.addLayout(previews)
    actions = QHBoxLayout(); controls["import"] = QPushButton("Import PNG…"); controls["export"] = QPushButton("Export retail…"); controls["remove"] = QPushButton("Remove"); controls["remove"].setEnabled(False)
    controls["import"].setObjectName("primary"); actions.addWidget(controls["import"]); actions.addWidget(controls["export"]); actions.addWidget(controls["remove"]); detail_layout.addLayout(actions)
    info = QGroupBox("Asset information"); info_form = QFormLayout(info); controls["path"] = QLabel("—"); controls["size"] = QLabel("—"); controls["uses"] = QLabel("—"); controls["state"] = QLabel("Retail")
    for label, key in (("Name", "path"), ("Native size", "size"), ("Used by", "uses"), ("Status", "state")): info_form.addRow(label, controls[key])
    detail_layout.addWidget(info); detail_layout.addStretch(1); root.addWidget(detail); root.setSizes([190, 440, 710])
    categories_view.currentItemChanged.connect(lambda item, _: _set_category(self, item.data(Qt.ItemDataRole.UserRole) if item else "")); search.textChanged.connect(lambda *_: _refresh_framework(self)); grid.currentItemChanged.connect(lambda item, _: _select_framework(self, item.data(Qt.ItemDataRole.UserRole) if item else None))
    controls["import"].clicked.connect(lambda: _import_framework(self)); controls["export"].clicked.connect(lambda: _export_framework(self)); controls["remove"].clicked.connect(lambda: _remove_framework(self))
    _refresh_framework(self)


def _set_category(self, category):
    self.workspace_controls["UI"]["category"] = category; _refresh_framework(self)


def _preview(label, image, fallback):
    if image is None: label.setPixmap(QPixmap()); label.setText(fallback); return
    pixmap = QPixmap.fromImage(_qimage(image.width, image.height, image.rgba))
    label.setText(""); label.setPixmap(pixmap.scaled(label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))


def _refresh_framework(self):
    c = self.workspace_controls.get("UI", {})
    if "grid" not in c: return
    query = c["search"].text().strip().lower(); category = c["category"]
    values = sorted(
        (asset for asset in c["catalog"]
         if _category(asset["name"]) == category
         and (not query or query in (asset["name"] + " " + asset.get("what", "")).lower())),
        key=lambda asset: asset["name"].casefold())
    c["grid_heading"].setText(f"Assets in {_display_category(category)}")
    grid = c["grid"]; previous = c.get("selected"); grid.blockSignals(True); grid.clear()
    pending = []
    for asset in values:
        item = QListWidgetItem(asset["name"].rsplit("/", 1)[-1].replace("_", " "))
        item.setData(Qt.ItemDataRole.UserRole, asset)
        grid.addItem(item)
        pending.append((item, asset))
        if previous and previous.get("name") == asset["name"]: grid.setCurrentItem(item)
    grid.blockSignals(False)
    if grid.currentItem() is None and grid.count(): grid.setCurrentRow(0)
    if not grid.count(): _select_framework(self, None)
    c["thumb_generation"] = c.get("thumb_generation", 0) + 1
    c["thumb_pending"] = pending
    QTimer.singleShot(0, lambda generation=c["thumb_generation"]: _load_thumbnail_batch(self, generation))


def _load_thumbnail_batch(self, generation, start=0):
    """Decode a handful of catalogue textures per event-loop turn.

    A category such as build_deck contains almost a hundred images.  Loading
    all of them before Qt can paint made selecting a category look like a
    freeze, even though only the first few thumbnails were initially visible.
    """
    c = self.workspace_controls.get("UI", {})
    if c.get("thumb_generation") != generation:
        return
    pending = c.get("thumb_pending", [])
    cache = c.setdefault("thumbnail_cache", {})
    stop = min(start + 8, len(pending))
    for item, asset in pending[start:stop]:
        icon = cache.get(asset["name"])
        if icon is None:
            retail = self._asset_retail_image(asset)
            if retail is not None:
                icon = QIcon(QPixmap.fromImage(_qimage(retail.width, retail.height, retail.rgba)).scaled(
                    112, 112, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation))
                cache[asset["name"]] = icon
        if icon is not None:
            item.setIcon(icon)
    if stop < len(pending):
        QTimer.singleShot(0, lambda: _load_thumbnail_batch(self, generation, stop))


def _select_framework(self, asset):
    c = self.workspace_controls["UI"]; c["selected"] = asset
    if asset is None:
        c["name"].setText("No asset selected"); c["description"].setText("No named assets match this category or search."); _preview(c["retail"], None, "Retail preview"); _preview(c["replacement"], None, "Replacement preview"); c["remove"].setEnabled(False); return
    entry = _entry_for(self, asset); retail = self._asset_retail_image(asset); replacement = _named_image(self, entry)
    c["name"].setText(asset["name"].rsplit("/", 1)[-1]); c["description"].setText(asset.get("what") or "Named UI texture."); c["path"].setText(asset["name"]); c["size"].setText(f"{asset.get('width', asset['words'] * (16 // asset['bpp']))} × {asset['rows']}"); c["uses"].setText(f"{_category(asset['name'])} · {asset['regions']} texture region{'s' if asset['regions'] != 1 else ''}"); c["state"].setText("Modified by this mod" if entry else "Retail"); c["remove"].setEnabled(entry is not None)
    _preview(c["retail"], retail, "Retail preview unavailable"); _preview(c["replacement"], replacement, "No replacement")


def _import_framework(self):
    c = self.workspace_controls["UI"]; asset = c.get("selected")
    if asset is None: return
    path, _ = QFileDialog.getOpenFileName(self, "Replace UI asset", "", "PNG images (*.png)")
    if not path: return
    try: image = pngio.read(path)
    except (OSError, ValueError, pngio.PngError) as problem: QMessageBox.critical(self, "Could not import UI asset", str(problem)); return
    folder = self.project.other.get("assets")
    if not isinstance(folder, str) or not folder:
        folder = "assets"; self.project.other["assets"] = folder
    self.project.files[f"{folder.rstrip('/')}/{asset['name']}.png"] = pngio.encode(image)
    self._mark_dirty(); _select_framework(self, asset)


def _export_framework(self):
    asset = self.workspace_controls["UI"].get("selected")
    if asset is None: return
    image = _named_image(self, _entry_for(self, asset)) or self._asset_retail_image(asset)
    if image is None: QMessageBox.warning(self, "Export UI asset", "The retail texture cannot be decoded."); return
    path, _ = QFileDialog.getSaveFileName(self, "Export UI asset", asset["name"].rsplit("/", 1)[-1] + ".png", "PNG images (*.png)")
    if path: pngio.write(path, image)


def _remove_framework(self):
    c = self.workspace_controls["UI"]; asset = c.get("selected"); path = _entry_for(self, asset) if asset else None
    if path is None: return
    self.project.files.pop(path, None)
    folder = self.project.other.get("assets")
    if isinstance(folder, str) and not any(name.startswith(folder.rstrip("/") + "/") for name in self.project.files): self.project.other.pop("assets", None)
    self._mark_dirty(); _select_framework(self, asset)



def _asset_widget(form, kind, name):
    value = form.findChild(kind, name)
    if value is None:
        raise RuntimeError(f"Assets form is missing {name}")
    return value


def _build_template_framework(self, page, controls):
    from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem
    form = page
    # Card frames have a dedicated editor tab.  Keep them out of the
    # generic asset catalogue so the two workflows do not overlap.
    catalog = [item for item in _catalog() if not item["name"].startswith("card_frames/")]
    categories = sorted({_category(item["name"]) for item in catalog}, key=str.casefold)
    controls.clear()
    controls.update(page=page, form=form, catalog=catalog, category="__all__",
                    selected=None, filter_mode="all", preview_scale=2)
    self.workspace_controls["UI"] = controls

    tree = _asset_widget(form, QTreeWidget, "assetCategoryTree")
    tree.clear()
    all_item = QTreeWidgetItem(["All"])
    all_item.setData(0, Qt.ItemDataRole.UserRole, "__all__")
    tree.addTopLevelItem(all_item)
    # Keep the hierarchy from asset-catalog.json.  A root can own assets of
    # its own as well as subcategories, such as Card Frames / Frame Magic.
    nodes = {}
    for category in categories:
        parent = None
        for index, component in enumerate(category.split("/")):
            path = "/".join(category.split("/")[:index + 1])
            item = nodes.get(path)
            if item is None:
                item = QTreeWidgetItem([component.replace("_", " ").title()])
                if parent is None:
                    tree.addTopLevelItem(item)
                else:
                    parent.addChild(item)
                nodes[path] = item
            parent = item
        nodes[category].setData(0, Qt.ItemDataRole.UserRole, category)
    for path, item in nodes.items():
        if path not in categories:
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
    tree.expandAll()
    tree.setCurrentItem(all_item)
    table = _asset_widget(form, QTableWidget, "assetTable")
    table.setColumnCount(3)
    table.setHorizontalHeaderLabels(["Asset", "Method", "State"])
    table.horizontalHeader().setStretchLastSection(False)
    table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
    table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

    revert_selected = _asset_widget(form, QPushButton, "revertSelectedAssetButton")
    controls.update(
        tree=tree, category_search=_asset_widget(form, QLineEdit, "assetCategorySearch"), table=table,
        all=_asset_widget(form, QPushButton, "allAssetsFilterButton"),
        modified=_asset_widget(form, QPushButton, "modifiedAssetsFilterButton"),
        retail=_asset_widget(form, QPushButton, "retailAssetsFilterButton"),
        name=_asset_widget(form, QLabel, "selectedAssetName"),
        description=_asset_widget(form, QLabel, "selectedAssetUse"),
        retail_preview=_asset_widget(form, QLabel, "retailPreview"),
        replacement_preview=_asset_widget(form, QLabel, "modPreview"),
        import_=_asset_widget(form, QPushButton, "replaceSelectedAssetButton"),
        export=_asset_widget(form, QPushButton, "exportAssetButton"),
        remove=revert_selected,
        path=_asset_widget(form, QLabel, "assetFilenameValue"),
        size=_asset_widget(form, QLabel, "assetSizeValue"),
        uses=_asset_widget(form, QLabel, "assetMethodValue"),
        state=_asset_widget(form, QLabel, "assetStatus"),
        replacement_info=_asset_widget(form, QLabel, "assetStatusNote"),
    )
    controls["remove"].setEnabled(False)
    _asset_widget(form, QPushButton, "importAssetButton").clicked.connect(lambda: _import_template(self))
    controls["import_"].clicked.connect(lambda: _import_template(self))
    controls["export"].clicked.connect(lambda: _export_template(self))
    _asset_widget(form, QPushButton, "revertAssetButton").clicked.connect(lambda: _remove_template(self))
    controls["remove"].clicked.connect(lambda: _remove_template(self))
    _asset_widget(form, QPushButton, "openAssetFileButton").clicked.connect(lambda: _open_assets_folder(self))
    _asset_widget(form, QPushButton, "uiModGuideButton").clicked.connect(lambda: _show_asset_help(self))
    _asset_widget(form, QPushButton, "revertAllUiButton").clicked.connect(lambda: _revert_template(self))
    _asset_widget(form, QPushButton, "applyAssetsButton").clicked.connect(self.save_mod)
    # The unified Designer form does not include the old optional preview
    # action.  Bind it when a future form supplies it, without requiring
    # Python to create a replacement control.
    preview_button = form.findChild(QPushButton, "previewAssetsModButton")
    if preview_button is not None:
        preview_button.clicked.connect(self.preview_manifest)
    _asset_widget(form, QPushButton, "locationCardView").clicked.connect(lambda: self.select_workspace("Art"))
    _asset_widget(form, QPushButton, "locationBuildDeck").clicked.connect(lambda: _asset_goto_tab(self, "Build Deck"))
    _asset_widget(form, QPushButton, "locationDuelHand").clicked.connect(lambda: _asset_goto_duel_element(self, "hand_cursor"))
    _asset_widget(form, QPushButton, "locationDuelField").clicked.connect(lambda: _asset_goto_duel_element(self, "field_cursor"))
    _asset_widget(form, QPushButton, "locationLibrary").clicked.connect(lambda: _asset_screen_not_catalogued(self, "Library"))
    _asset_widget(form, QPushButton, "locationPassword").clicked.connect(lambda: _asset_screen_not_catalogued(self, "Password"))
    for scale, name in ((1, "preview1xButton"), (2, "preview2xButton"), (4, "preview4xButton")):
        button = _asset_widget(form, QPushButton, name)
        button.clicked.connect(lambda _checked=False, value=scale: _set_template_scale(self, value))
    for mode, button in (("all", controls["all"]), ("modified", controls["modified"]), ("retail", controls["retail"])):
        button.clicked.connect(lambda _checked=False, value=mode: _set_template_filter(self, value))
    tree.currentItemChanged.connect(lambda item, _: _set_template_category(self, item.data(0, Qt.ItemDataRole.UserRole) if item else ""))
    controls["category_search"].textChanged.connect(lambda value: _filter_template_categories(self, value))
    table.itemSelectionChanged.connect(lambda: _select_template_row(self))
    _refresh_template(self)


def _set_template_category(self, category):
    self.workspace_controls["UI"]["category"] = category
    _refresh_template(self)


def _filter_template_categories(self, text):
    tree = self.workspace_controls["UI"]["tree"]
    wanted = text.strip().casefold()
    def filter_item(item):
        own = wanted in item.text(0).casefold()
        child = any(filter_item(item.child(index)) for index in range(item.childCount()))
        item.setHidden(bool(wanted and not own and not child))
        return own or child
    for row in range(tree.topLevelItemCount()):
        filter_item(tree.topLevelItem(row))


def _set_template_filter(self, mode):
    c = self.workspace_controls["UI"]
    c["filter_mode"] = mode
    for key in ("all", "modified", "retail"):
        c[key].setChecked(key == mode)
    _refresh_template(self)


def _set_template_scale(self, scale):
    c = self.workspace_controls["UI"]
    c["preview_scale"] = scale
    form = c["form"]
    for value, name in ((1, "preview1xButton"), (2, "preview2xButton"), (4, "preview4xButton")):
        _asset_widget(form, QPushButton, name).setChecked(value == scale)
    _select_template(self, c.get("selected"))


def _template_values(self):
    c = self.workspace_controls.get("UI", {})
    mode, category = c.get("filter_mode", "all"), c.get("category")
    values = []
    for asset in c.get("catalog", []):
        entry = _entry_for(self, asset)
        if category != "__all__" and _category(asset["name"]) != category:
            continue
        if mode == "modified" and not entry:
            continue
        if mode == "retail" and entry:
            continue
        values.append((asset, entry))
    return sorted(values, key=lambda value: value[0]["name"].casefold())


def _refresh_template(self):
    c = self.workspace_controls.get("UI", {})
    table = c.get("table")
    if table is None:
        return
    previous = c.get("selected")
    table.blockSignals(True); table.setRowCount(0)
    values = _template_values(self)
    for row, (asset, entry) in enumerate(values):
        _path, origin, _manifest_entry = _entry_origin(self, asset)
        table.insertRow(row)
        name = asset["name"].rsplit("/", 1)[-1].replace("_", " ")
        method = "Texture pack" if origin == "pack" else "Named asset"
        for column, value in enumerate((name, method, "Modified" if entry else "Retail")):
            item = QTableWidgetItem(value)
            if column == 0:
                item.setData(Qt.ItemDataRole.UserRole, asset)
            if column == 2:
                item.setForeground(QColor("#6bdd9a" if entry else "#aebfd6"))
            table.setItem(row, column, item)
        if previous and previous.get("name") == asset["name"]:
            table.selectRow(row)
    table.blockSignals(False)
    if table.currentRow() < 0 and table.rowCount():
        table.selectRow(0)
    if table.rowCount():
        # Selection signals were blocked while rows were replaced, so the
        # current row can now point at a different catalog item.
        _select_template_row(self)
    else:
        _select_template(self, None)


def _select_template_row(self):
    table = self.workspace_controls["UI"]["table"]
    item = table.item(table.currentRow(), 0) if table.currentRow() >= 0 else None
    _select_template(self, item.data(Qt.ItemDataRole.UserRole) if item else None)


def _template_preview(label, image, fallback, scale, asset=None):
    """Show an asset at a fixed visual size using the selected detail tier.

    This follows the card HD preview and Art pages: the 1x, 2x, and 4x
    controls choose how much source detail is sampled, never how large the
    asset becomes in the editor.
    """
    if image is None:
        label.setPixmap(QPixmap()); label.setText(fallback); return
    image_width = image.width() if isinstance(image, QImage) else image.width
    image_height = image.height() if isinstance(image, QImage) else image.height
    if asset is None:
        native_width, native_height = image_width, image_height
    else:
        pixels_per_word = {4: 4, 8: 2, 16: 1}.get(asset.get("bpp"), 1)
        native_width = int(asset.get("width", asset["words"] * pixels_per_word))
        native_height = int(asset.get("rows", image.height))
    available = max(1, min(image_width // max(1, native_width),
                           image_height // max(1, native_height)))
    detail = min(scale, available)
    if isinstance(image, QImage):
        sampled = image.scaled(native_width * detail, native_height * detail,
                               Qt.AspectRatioMode.IgnoreAspectRatio,
                               Qt.TransformationMode.FastTransformation)
        pixmap = QPixmap.fromImage(sampled)
    else:
        sampled = pngio.resample(image, native_width * detail, native_height * detail)
        pixmap = QPixmap.fromImage(_qimage(sampled.width, sampled.height, sampled.rgba))
    label.setText("")
    # The view itself is a 4x native canvas, capped by the fixed Designer
    # preview panel.  A 16x16 sort icon therefore appears at 64x64 instead
    # of being blurred across a 300px pane; 1x/2x/4x above still changes the
    # sampled source detail, not the visible dimensions.
    canvas = QSize(native_width * 4, native_height * 4).boundedTo(label.size())
    label.setPixmap(pixmap.scaled(canvas,
                                  Qt.AspectRatioMode.KeepAspectRatio,
                                  Qt.TransformationMode.FastTransformation))


def _select_template(self, asset):
    c = self.workspace_controls["UI"]; c["selected"] = asset
    if asset is None:
        c["name"].setText("No UI asset selected")
        c["description"].setText("Choose an asset from the selected catalog category.")
        _template_preview(c["retail_preview"], None, "Retail preview", 1)
        _template_preview(c["replacement_preview"], None, "Replacement preview", 1)
        c["remove"].setEnabled(False); return
    entry, origin, _manifest_entry = _entry_origin(self, asset)
    cache = c.setdefault("preview_image_cache", {})
    pending = c.setdefault("preview_image_loading", set())
    retail_cache = c.setdefault("retail_preview_cache", {})
    retail_pending = c.setdefault("retail_preview_loading", set())
    retail_key = asset["name"]
    retail_loading = retail_key not in retail_cache
    retail = retail_cache.get(retail_key)
    loading = entry is not None and entry not in cache
    replacement = cache.get(entry) if entry is not None else None
    crop = _legacy_crop(self, asset) if origin == "pack" else None
    if replacement is not None and crop is not None:
        native_width, native_height = _native_size(asset)
        source_width, source_height = _native_size(_manifest_entry)
        source_width_px = replacement.width() if isinstance(replacement, QImage) else replacement.width
        source_height_px = replacement.height() if isinstance(replacement, QImage) else replacement.height
        scale_x = source_width_px / source_width
        scale_y = source_height_px / source_height
        left, top = round(crop[0] * scale_x), round(crop[1] * scale_y)
        width, height = max(1, round(native_width * scale_x)), max(1, round(native_height * scale_y))
        replacement = (replacement.copy(left, top, width, height)
                       if isinstance(replacement, QImage) else
                       pngio.crop(replacement, left, top, width, height))
    scale = c.get("preview_scale", 2)
    c["name"].setText(asset["name"].rsplit("/", 1)[-1])
    description = asset.get("what") or "Named UI texture."
    if origin == "pack":
        description += " Loaded from this mod's texture pack" + (" atlas." if crop else ".")
    c["description"].setText(description)
    c["path"].setText(entry or f"assets/{asset['name']}.png")
    c["size"].setText(f"{asset.get('width', asset['words'] * (16 // asset['bpp']))} × {asset['rows']}")
    c["uses"].setText(f"{_display_category(_category(asset['name']))} · {asset['regions']} region{'s' if asset['regions'] != 1 else ''}")
    detail = "1×" if scale == 1 else f"up to {scale}×"
    c["replacement_info"].setText(
        f"{replacement.width() if isinstance(replacement, QImage) else replacement.width} × "
        f"{replacement.height() if isinstance(replacement, QImage) else replacement.height} PNG · {detail} detail"
        if replacement else "Loading replacement…" if loading else "No replacement")
    c["remove"].setEnabled(entry is not None)
    _template_preview(c["retail_preview"], retail,
                      "Loading retail preview…" if retail_loading else "Retail preview unavailable", 1, asset)
    _template_preview(c["replacement_preview"], replacement,
                      "Loading replacement…" if loading else "No replacement", scale, asset)
    if loading and entry not in pending:
        _load_preview_image(self, entry, asset)
    if retail_loading and retail_key not in retail_pending:
        _load_retail_preview_image(self, asset)


def _load_preview_image(self, entry, asset):
    """Decode a potentially multi-megabyte replacement away from the UI."""
    c = self.workspace_controls.get("UI", {})
    pending = c.setdefault("preview_image_loading", set())
    if entry in pending:
        return
    pending.add(entry)
    result = {}

    def read():
        # QImage's native PNG decoder does this in Qt/C++ instead of walking
        # a large HD atlas in Python while it holds the GIL.  Returning the
        # QImage is safe; only QPixmap creation remains on the UI thread.
        try:
            if entry in self.project.files:
                result["image"] = QImage.fromData(self.project.files[entry])
            else:
                source = Path(self.project.source_dir) / entry if self.project.source_dir else None
                result["image"] = QImage(str(source)) if source else QImage()
            if result["image"].isNull():
                result["image"] = None
        except (OSError, ValueError):
            result["image"] = None

    thread = threading.Thread(target=read, name="fm-editor-asset-preview", daemon=True)
    thread.start()

    def complete():
        if thread.is_alive():
            QTimer.singleShot(15, complete)
            return
        current = self.workspace_controls.get("UI", {})
        cache = current.setdefault("preview_image_cache", {})
        current.setdefault("preview_image_loading", set()).discard(entry)
        cache[entry] = result.get("image")
        # Keep the cache bounded while retaining the most recently decoded
        # images.  This avoids a large HD pack growing memory unboundedly.
        if len(cache) > 16:
            cache.pop(next(iter(cache)))
        selected = current.get("selected")
        # QTableWidget stores the asset dictionary through QVariant.  Reading it
        # back can produce a new Python dict, so object identity is not stable.
        # Compare the catalog key instead or a completed background request can
        # leave the current preview on its temporary "Loading…" placeholder.
        if selected and selected.get("name") == asset.get("name"):
            _select_template(self, selected)

    QTimer.singleShot(0, complete)


def _load_retail_preview_image(self, asset):
    """Decode the disc texture outside the selection handler as well.

    Most catalogued UI textures are small, but frame atlases and some full
    screen elements are not.  Decoding either side of a comparison in a
    table-selection signal makes the editor feel unresponsive on HD mods.
    """
    c = self.workspace_controls.get("UI", {})
    key = asset["name"]
    pending = c.setdefault("retail_preview_loading", set())
    if key in pending:
        return
    pending.add(key)
    result = {}

    def read():
        try:
            result["image"] = self._asset_retail_image(asset)
        except (IndexError, KeyError, OSError, TypeError, ValueError, pngio.PngError):
            result["image"] = None

    thread = threading.Thread(target=read, name="fm-editor-retail-preview", daemon=True)
    thread.start()

    def complete():
        if thread.is_alive():
            QTimer.singleShot(15, complete)
            return
        current = self.workspace_controls.get("UI", {})
        cache = current.setdefault("retail_preview_cache", {})
        current.setdefault("retail_preview_loading", set()).discard(key)
        cache[key] = result.get("image")
        if len(cache) > 32:
            cache.pop(next(iter(cache)))
        selected = current.get("selected")
        if selected and selected.get("name") == asset.get("name"):
            _select_template(self, selected)

    QTimer.singleShot(0, complete)


def _asset_paths(project, folder):
    """All saved and pending named assets, minus queued removals."""
    if not isinstance(folder, str) or not folder:
        return set()
    prefix = folder.rstrip("/") + "/"
    removed = project.deleted_files
    paths = {name for name in project.files if name.startswith(prefix) and name not in removed}
    source = Path(project.source_dir) if project.source_dir else None
    if source:
        base = source / folder
        if base.is_dir():
            for item in base.rglob("*"):
                if item.is_file() and not item.is_symlink():
                    paths.add(item.relative_to(source).as_posix())
    return paths - removed


def _remember_asset_removal(project, path):
    project.files.pop(path, None)
    project.deleted_files.add(path)


def _import_template(self):
    c = self.workspace_controls["UI"]; asset = c.get("selected")
    if asset is None: return
    path, _ = QFileDialog.getOpenFileName(self, "Replace UI asset", "", "PNG images (*.png)")
    if not path: return
    try: image = pngio.read(path)
    except (OSError, ValueError, pngio.PngError) as problem:
        QMessageBox.critical(self, "Could not import UI asset", str(problem)); return
    _path, origin, manifest_entry = _entry_origin(self, asset)
    if origin == "pack" and manifest_entry is not None:
        # Preserve the mod's existing pack contract.  The entry already
        # points at this file, and Project.files is written before the pack
        # manifest on Save / Save As.
        relative = f"{art.pack_dir(self.project).rstrip('/')}/{manifest_entry['file']}"
        crop = _legacy_crop(self, asset)
        if crop is not None:
            # This asset is only one region of a larger shared atlas PNG.
            # Paste the replacement into its own corner instead of
            # overwriting the whole file, which would wipe every other
            # catalogued texture that file also backs.
            base = _named_image(self, relative)
            if base is None:
                QMessageBox.critical(self, "Could not import UI asset",
                                      "This mod's shared texture atlas could not be read; nothing was changed.")
                return
            left, top, width, height = _atlas_region(manifest_entry, crop, base.width, base.height)
            if (image.width, image.height) != (width, height):
                image = pngio.scale_to(image, width, height)
            image = pngio.paste(base, image, left, top)
    else:
        folder = self.project.other.get("assets")
        if not isinstance(folder, str) or not folder:
            folder = "assets"; self.project.other["assets"] = folder
        relative = f"{folder.rstrip('/')}/{asset['name']}.png"
    self.project.files[relative] = pngio.encode(image)
    self.project.deleted_files.discard(relative)
    c.get("preview_image_cache", {}).pop(relative, None)
    self._mark_dirty(); _refresh_template(self)


def _export_template(self):
    asset = self.workspace_controls["UI"].get("selected")
    if asset is None: return
    path, origin, manifest_entry = _entry_origin(self, asset)
    image = _named_image(self, path)
    if image is not None:
        crop = _legacy_crop(self, asset) if origin == "pack" else None
        if crop is not None:
            # Only the selected catalog region of a larger shared atlas,
            # not the whole backing PNG (the retail fallback below is
            # already sized to the asset alone, so it needs no cropping).
            left, top, width, height = _atlas_region(manifest_entry, crop, image.width, image.height)
            image = pngio.crop(image, left, top, width, height)
    else:
        image = self._asset_retail_image(asset)
    if image is None:
        QMessageBox.warning(self, "Export UI asset", "The retail texture cannot be decoded."); return
    out, _ = QFileDialog.getSaveFileName(self, "Export UI asset", asset["name"].rsplit("/", 1)[-1] + ".png", "PNG images (*.png)")
    if out: pngio.write(out, image)


def _remove_template(self):
    c = self.workspace_controls["UI"]; asset = c.get("selected")
    path, origin, manifest_entry = _entry_origin(self, asset)
    if path is None: return
    if origin == "pack" and manifest_entry is not None:
        crop = _legacy_crop(self, asset)
        if crop is not None and _asset_shares_entry(self, asset, manifest_entry):
            # A shared HD atlas another catalogued asset still needs: patch
            # this region back to its retail pixels instead of deleting the
            # file or un-declaring the manifest entry out from under it.
            base = _named_image(self, path)
            retail = self._asset_retail_image(asset)
            if base is not None and retail is not None:
                left, top, width, height = _atlas_region(manifest_entry, crop, base.width, base.height)
                patch = pngio.scale_to(retail, width, height)
                self.project.files[path] = pngio.encode(pngio.paste(base, patch, left, top))
                c.get("preview_image_cache", {}).pop(path, None)
            self._mark_dirty(); _refresh_template(self); return
        c.get("preview_image_cache", {}).pop(path, None)
        st = art.state(self.project)
        # Removing this first matching manifest entry restores the retail
        # texture read.  Only delete the backing PNG once no other manifest
        # entry -- catalogued or not -- still names that same file.
        if not _file_still_used(self.project, manifest_entry.get("file"), manifest_entry):
            _remember_asset_removal(self.project, path)
        st.entries = [entry for entry in st.entries or [] if entry is not manifest_entry]
        st.changed = True
        c.pop("legacy_pack_index", None)
        self._mark_dirty(); _refresh_template(self); return
    _remember_asset_removal(self.project, path)
    c.get("preview_image_cache", {}).pop(path, None)
    folder = self.project.other.get("assets")
    if not _asset_paths(self.project, folder):
        self.project.other.pop("assets", None)
    self._mark_dirty(); _refresh_template(self)


def _revert_template(self):
    folder = self.project.other.get("assets")
    for name in _asset_paths(self.project, folder):
        _remember_asset_removal(self.project, name)
    self.project.other.pop("assets", None)
    self._mark_dirty(); _refresh_template(self)


# --- the Build Deck tab: a texture-only view of the catalogue's build_deck/*
# entries. The game only reads positions and sizes for the duel HUD (ui_rules,
# ui_config.c); the Build Deck, Library and Password screens have no such
# per-element config on the C side, so this reuses the Assets catalogue's
# replace/export/revert machinery (same asset dicts, same preview rendering)
# with its own namespaced state -- not the generic multi-category browser --
# since build_deck/* has no subcategories to browse.

def _build_deck_catalog():
    return [asset for asset in _catalog() if asset["name"].startswith("build_deck/")]


def _build_build_deck_tab(self, page, controls):
    form = page

    def widget(kind, name):
        value = form.findChild(kind, name)
        if value is None: raise RuntimeError(f"Build Deck assets form is missing {name!r}")
        return value

    bd = controls.setdefault("build_deck", {})
    bd.clear()
    bd.update(
        form=form, catalog=_build_deck_catalog(), category="__all__", selected=None, filter_mode="all", preview_scale=2,
        table=widget(QTableWidget, "buildDeckTable"), search=widget(QLineEdit, "buildDeckSearchEdit"),
        all=widget(QPushButton, "buildDeckAllButton"), modified=widget(QPushButton, "buildDeckModifiedButton"),
        retail=widget(QPushButton, "buildDeckRetailButton"),
        name=widget(QLabel, "buildDeckSelectedName"), description=widget(QLabel, "buildDeckSelectedUse"),
        retail_preview=widget(QLabel, "buildDeckRetailPreview"), replacement_preview=widget(QLabel, "buildDeckReplacementPreview"),
        path=widget(QLabel, "buildDeckPathValue"), size=widget(QLabel, "buildDeckSizeValue"), uses=widget(QLabel, "buildDeckUsesValue"),
        replacement_info=widget(QLabel, "buildDeckStatusNote"), footer=widget(QLabel, "buildDeckFooterLabel"),
        import_=widget(QPushButton, "buildDeckReplaceButton"), export=widget(QPushButton, "buildDeckExportButton"),
        remove=widget(QPushButton, "buildDeckRevertButton"), remove_all=widget(QPushButton, "buildDeckRevertAllButton"),
    )
    table = bd["table"]
    table.setColumnCount(3)
    table.horizontalHeader().setStretchLastSection(False)
    table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
    table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
    bd["remove"].setEnabled(False)

    bd["import_"].clicked.connect(lambda: _import_build_deck(self))
    bd["export"].clicked.connect(lambda: _export_build_deck(self))
    bd["remove"].clicked.connect(lambda: _remove_build_deck(self))
    bd["remove_all"].clicked.connect(lambda: _revert_build_deck_all(self))
    for scale, name in ((1, "buildDeckPreview1xButton"), (2, "buildDeckPreview2xButton"), (4, "buildDeckPreview4xButton")):
        widget(QPushButton, name).clicked.connect(lambda _checked=False, value=scale: _set_build_deck_scale(self, value))
    for mode, button in (("all", bd["all"]), ("modified", bd["modified"]), ("retail", bd["retail"])):
        button.clicked.connect(lambda _checked=False, value=mode: _set_build_deck_filter(self, value))
    bd["search"].textChanged.connect(lambda value: _filter_build_deck(self, value))
    table.itemSelectionChanged.connect(lambda: _select_build_deck_row(self))
    _refresh_build_deck(self)


def _build_deck_values(self):
    c = self.workspace_controls.get("UI", {}); bd = c.get("build_deck", {})
    mode = bd.get("filter_mode", "all"); wanted = bd.get("search", "").strip().casefold() if isinstance(bd.get("search"), str) else ""
    values = []
    for asset in bd.get("catalog", []):
        entry = _entry_for(self, asset)
        if mode == "modified" and not entry: continue
        if mode == "retail" and entry: continue
        if wanted and wanted not in asset["name"].rsplit("/", 1)[-1].replace("_", " ").casefold(): continue
        values.append((asset, entry))
    return sorted(values, key=lambda value: value[0]["name"].casefold())


def _filter_build_deck(self, text):
    c = self.workspace_controls["UI"]; bd = c["build_deck"]
    bd["search"] = text
    _refresh_build_deck(self)


def _refresh_build_deck(self):
    c = self.workspace_controls.get("UI", {}); bd = c.get("build_deck", {})
    table = bd.get("table")
    if table is None: return
    previous = bd.get("selected")
    table.blockSignals(True); table.setRowCount(0)
    values = _build_deck_values(self)
    for row, (asset, entry) in enumerate(values):
        _path, origin, _manifest_entry = _entry_origin(self, asset)
        table.insertRow(row)
        name = asset["name"].rsplit("/", 1)[-1].replace("_", " ")
        method = "Texture pack" if origin == "pack" else "Named asset"
        for column, value in enumerate((name, method, "Modified" if entry else "Retail")):
            item = QTableWidgetItem(value)
            if column == 0: item.setData(Qt.ItemDataRole.UserRole, asset)
            if column == 2: item.setForeground(QColor("#6bdd9a" if entry else "#aebfd6"))
            table.setItem(row, column, item)
        if previous and previous.get("name") == asset["name"]: table.selectRow(row)
    table.blockSignals(False)
    if table.currentRow() < 0 and table.rowCount(): table.selectRow(0)
    if table.rowCount(): _select_build_deck_row(self)
    else: _select_build_deck(self, None)
    modified = sum(1 for asset in bd.get("catalog", []) if _entry_for(self, asset))
    bd["footer"].setText(f"{modified} modified asset{'s' if modified != 1 else ''}")


def _select_build_deck_row(self):
    bd = self.workspace_controls["UI"]["build_deck"]; table = bd["table"]
    item = table.item(table.currentRow(), 0) if table.currentRow() >= 0 else None
    _select_build_deck(self, item.data(Qt.ItemDataRole.UserRole) if item else None)


def _set_build_deck_filter(self, mode):
    bd = self.workspace_controls["UI"]["build_deck"]
    bd["filter_mode"] = mode
    for key in ("all", "modified", "retail"): bd[key].setChecked(key == mode)
    _refresh_build_deck(self)


def _set_build_deck_scale(self, scale):
    bd = self.workspace_controls["UI"]["build_deck"]
    bd["preview_scale"] = scale
    for value, name in ((1, "buildDeckPreview1xButton"), (2, "buildDeckPreview2xButton"), (4, "buildDeckPreview4xButton")):
        bd["form"].findChild(QPushButton, name).setChecked(value == scale)
    _select_build_deck(self, bd.get("selected"))


def _select_build_deck(self, asset):
    bd = self.workspace_controls["UI"]["build_deck"]; bd["selected"] = asset
    if asset is None:
        bd["name"].setText("No texture selected")
        bd["description"].setText("Choose a texture from the list.")
        _template_preview(bd["retail_preview"], None, "Retail preview", 1)
        _template_preview(bd["replacement_preview"], None, "Replacement preview", 1)
        bd["remove"].setEnabled(False); return
    entry, origin, _manifest_entry = _entry_origin(self, asset)
    cache = bd.setdefault("preview_image_cache", {}); pending = bd.setdefault("preview_image_loading", set())
    retail_cache = bd.setdefault("retail_preview_cache", {}); retail_pending = bd.setdefault("retail_preview_loading", set())
    retail_key = asset["name"]; retail_loading = retail_key not in retail_cache; retail = retail_cache.get(retail_key)
    loading = entry is not None and entry not in cache
    replacement = cache.get(entry) if entry is not None else None
    crop = _legacy_crop(self, asset) if origin == "pack" else None
    if replacement is not None and crop is not None:
        native_width, native_height = _native_size(asset)
        source_width, source_height = _native_size(_manifest_entry)
        source_width_px = replacement.width() if isinstance(replacement, QImage) else replacement.width
        source_height_px = replacement.height() if isinstance(replacement, QImage) else replacement.height
        scale_x = source_width_px / source_width; scale_y = source_height_px / source_height
        left, top = round(crop[0] * scale_x), round(crop[1] * scale_y)
        width, height = max(1, round(native_width * scale_x)), max(1, round(native_height * scale_y))
        replacement = (replacement.copy(left, top, width, height) if isinstance(replacement, QImage) else
                       pngio.crop(replacement, left, top, width, height))
    scale = bd.get("preview_scale", 2)
    bd["name"].setText(asset["name"].rsplit("/", 1)[-1])
    description = asset.get("what") or "Named UI texture."
    if origin == "pack": description += " Loaded from this mod's texture pack" + (" atlas." if crop else ".")
    bd["description"].setText(description)
    bd["path"].setText(entry or f"assets/{asset['name']}.png")
    bd["size"].setText(f"{asset.get('width', asset['words'] * (16 // asset['bpp']))} × {asset['rows']}")
    bd["uses"].setText(f"{asset['regions']} region{'s' if asset['regions'] != 1 else ''}")
    detail = "1×" if scale == 1 else f"up to {scale}×"
    bd["replacement_info"].setText(
        f"{replacement.width() if isinstance(replacement, QImage) else replacement.width} × "
        f"{replacement.height() if isinstance(replacement, QImage) else replacement.height} PNG · {detail} detail"
        if replacement else "Loading replacement…" if loading else "No replacement")
    bd["remove"].setEnabled(entry is not None)
    _template_preview(bd["retail_preview"], retail, "Loading retail preview…" if retail_loading else "Retail preview unavailable", 1, asset)
    _template_preview(bd["replacement_preview"], replacement, "Loading replacement…" if loading else "No replacement", scale, asset)
    if loading and entry not in pending: _load_build_deck_preview_image(self, entry, asset)
    if retail_loading and retail_key not in retail_pending: _load_build_deck_retail_preview_image(self, asset)


def _load_build_deck_preview_image(self, entry, asset):
    bd = self.workspace_controls.get("UI", {}).get("build_deck", {})
    pending = bd.setdefault("preview_image_loading", set())
    if entry in pending: return
    pending.add(entry); result = {}

    def read():
        try:
            if entry in self.project.files: result["image"] = QImage.fromData(self.project.files[entry])
            else:
                source = Path(self.project.source_dir) / entry if self.project.source_dir else None
                result["image"] = QImage(str(source)) if source else QImage()
            if result["image"].isNull(): result["image"] = None
        except (OSError, ValueError): result["image"] = None

    thread = threading.Thread(target=read, name="fm-editor-build-deck-preview", daemon=True); thread.start()

    def complete():
        if thread.is_alive(): QTimer.singleShot(15, complete); return
        current = self.workspace_controls.get("UI", {}).get("build_deck", {})
        cache = current.setdefault("preview_image_cache", {})
        current.setdefault("preview_image_loading", set()).discard(entry)
        cache[entry] = result.get("image")
        if len(cache) > 16: cache.pop(next(iter(cache)))
        selected = current.get("selected")
        if selected and selected.get("name") == asset.get("name"): _select_build_deck(self, selected)

    QTimer.singleShot(0, complete)


def _load_build_deck_retail_preview_image(self, asset):
    bd = self.workspace_controls.get("UI", {}).get("build_deck", {})
    key = asset["name"]; pending = bd.setdefault("retail_preview_loading", set())
    if key in pending: return
    pending.add(key); result = {}

    def read():
        try: result["image"] = self._asset_retail_image(asset)
        except (IndexError, KeyError, OSError, TypeError, ValueError, pngio.PngError): result["image"] = None

    thread = threading.Thread(target=read, name="fm-editor-build-deck-retail", daemon=True); thread.start()

    def complete():
        if thread.is_alive(): QTimer.singleShot(15, complete); return
        current = self.workspace_controls.get("UI", {}).get("build_deck", {})
        cache = current.setdefault("retail_preview_cache", {})
        current.setdefault("retail_preview_loading", set()).discard(key)
        cache[key] = result.get("image")
        if len(cache) > 32: cache.pop(next(iter(cache)))
        selected = current.get("selected")
        if selected and selected.get("name") == asset.get("name"): _select_build_deck(self, selected)

    QTimer.singleShot(0, complete)


def _import_build_deck(self):
    bd = self.workspace_controls["UI"]["build_deck"]; asset = bd.get("selected")
    if asset is None: return
    path, _ = QFileDialog.getOpenFileName(self, "Replace Build Deck texture", "", "PNG images (*.png)")
    if not path: return
    try: image = pngio.read(path)
    except (OSError, ValueError, pngio.PngError) as problem:
        QMessageBox.critical(self, "Could not import texture", str(problem)); return
    _path, origin, manifest_entry = _entry_origin(self, asset)
    if origin == "pack" and manifest_entry is not None:
        relative = f"{art.pack_dir(self.project).rstrip('/')}/{manifest_entry['file']}"
        crop = _legacy_crop(self, asset)
        if crop is not None:
            # This texture is only one region of a larger shared atlas PNG;
            # paste the replacement into its own corner rather than
            # overwriting every other texture that file also backs.
            base = _named_image(self, relative)
            if base is None:
                QMessageBox.critical(self, "Could not import texture",
                                      "This mod's shared texture atlas could not be read; nothing was changed.")
                return
            left, top, width, height = _atlas_region(manifest_entry, crop, base.width, base.height)
            if (image.width, image.height) != (width, height):
                image = pngio.scale_to(image, width, height)
            image = pngio.paste(base, image, left, top)
    else:
        folder = self.project.other.get("assets")
        if not isinstance(folder, str) or not folder: folder = "assets"; self.project.other["assets"] = folder
        relative = f"{folder.rstrip('/')}/{asset['name']}.png"
    self.project.files[relative] = pngio.encode(image)
    self.project.deleted_files.discard(relative)
    bd.get("preview_image_cache", {}).pop(relative, None)
    self._mark_dirty(); _refresh_build_deck(self)


def _export_build_deck(self):
    asset = self.workspace_controls["UI"]["build_deck"].get("selected")
    if asset is None: return
    path, origin, manifest_entry = _entry_origin(self, asset)
    image = _named_image(self, path)
    if image is not None:
        crop = _legacy_crop(self, asset) if origin == "pack" else None
        if crop is not None:
            left, top, width, height = _atlas_region(manifest_entry, crop, image.width, image.height)
            image = pngio.crop(image, left, top, width, height)
    else:
        image = self._asset_retail_image(asset)
    if image is None:
        QMessageBox.warning(self, "Export texture", "The retail texture cannot be decoded."); return
    out, _ = QFileDialog.getSaveFileName(self, "Export texture", asset["name"].rsplit("/", 1)[-1] + ".png", "PNG images (*.png)")
    if out: pngio.write(out, image)


def _remove_build_deck(self):
    bd = self.workspace_controls["UI"]["build_deck"]; asset = bd.get("selected")
    path, origin, manifest_entry = _entry_origin(self, asset)
    if path is None: return
    if origin == "pack" and manifest_entry is not None:
        crop = _legacy_crop(self, asset)
        if crop is not None and _asset_shares_entry(self, asset, manifest_entry):
            # A shared HD atlas another catalogued texture still needs:
            # patch this region back to retail instead of deleting the file
            # or un-declaring the manifest entry out from under it.
            base = _named_image(self, path)
            retail = self._asset_retail_image(asset)
            if base is not None and retail is not None:
                left, top, width, height = _atlas_region(manifest_entry, crop, base.width, base.height)
                patch = pngio.scale_to(retail, width, height)
                self.project.files[path] = pngio.encode(pngio.paste(base, patch, left, top))
                bd.get("preview_image_cache", {}).pop(path, None)
            self._mark_dirty(); _refresh_build_deck(self); return
        bd.get("preview_image_cache", {}).pop(path, None)
        st = art.state(self.project)
        if not _file_still_used(self.project, manifest_entry.get("file"), manifest_entry):
            _remember_asset_removal(self.project, path)
        st.entries = [entry for entry in st.entries or [] if entry is not manifest_entry]
        st.changed = True
        self.workspace_controls["UI"].pop("legacy_pack_index", None)
        self._mark_dirty(); _refresh_build_deck(self); return
    _remember_asset_removal(self.project, path)
    bd.get("preview_image_cache", {}).pop(path, None)
    folder = self.project.other.get("assets")
    if not _asset_paths(self.project, folder): self.project.other.pop("assets", None)
    self._mark_dirty(); _refresh_build_deck(self)


def _revert_build_deck_all(self):
    """Only the build_deck/* entries -- not every named asset in the mod."""
    bd = self.workspace_controls["UI"]["build_deck"]
    names_in_scope = {a["name"] for a in bd.get("catalog", [])}
    for asset in bd.get("catalog", []):
        path, origin, manifest_entry = _entry_origin(self, asset)
        if path is None: continue
        if origin == "pack" and manifest_entry is not None:
            crop = _legacy_crop(self, asset)
            if crop is not None and _asset_shares_entry_outside(self, manifest_entry, names_in_scope):
                # Shared with an asset outside this tab's own catalog (not
                # being reverted here): patch this region, leave the rest.
                base = _named_image(self, path)
                retail = self._asset_retail_image(asset)
                if base is not None and retail is not None:
                    left, top, width, height = _atlas_region(manifest_entry, crop, base.width, base.height)
                    patch = pngio.scale_to(retail, width, height)
                    self.project.files[path] = pngio.encode(pngio.paste(base, patch, left, top))
                continue
            # Every sibling this atlas has (if any) is also build_deck/* and
            # is being reverted in this same pass: safe to clear the entry
            # outright instead of leaving retail pixels under a live entry.
            st = art.state(self.project)
            if not _file_still_used(self.project, manifest_entry.get("file"), manifest_entry):
                _remember_asset_removal(self.project, path)
            st.entries = [entry for entry in st.entries or [] if entry is not manifest_entry]
            st.changed = True
            self.workspace_controls["UI"].pop("legacy_pack_index", None)
        else:
            _remember_asset_removal(self.project, path)
    bd.get("preview_image_cache", {}).clear()
    self.workspace_controls["UI"].pop("legacy_pack_index", None)
    folder = self.project.other.get("assets")
    if not _asset_paths(self.project, folder): self.project.other.pop("assets", None)
    self._mark_dirty(); _refresh_build_deck(self)
