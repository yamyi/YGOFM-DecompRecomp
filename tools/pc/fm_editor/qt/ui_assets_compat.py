"""Use the modern editor's Assets entry as PR #297's UI / Graphics page.

This compatibility module stays separate from master-tracked editor files.
"""
from __future__ import annotations

from .common import *  # noqa: F401,F403
from .common import _qimage
from PySide6.QtCore import QObject, QEvent
from .. import art, board_art, board_model, card_text, duel_screen, gamedata, pngio, ui_assets, ui_rules
import contextlib
import json
import re
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

        The scene-oriented tabs come from ``ui_page_all_tabs_compat.ui``.
        The catalogue editor remains a visible tab after Build Deck, rather
        than being replaced by a static mock-up.  This keeps the modern UI
        independent of the classic editor while preserving every existing
        replacement workflow.
        """
        layout = page.layout() or QVBoxLayout(page)
        _clear(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        shell = _all_tabs_form(page)
        layout.addWidget(shell)
        tabs = _asset_widget(shell, QTabWidget, "uiPageTabs")
        assets_tab = QWidget(tabs)
        assets_tab.setObjectName("assetsTab")
        assets_layout = QVBoxLayout(assets_tab)
        assets_layout.setContentsMargins(0, 0, 0, 0)
        tabs.addTab(assets_tab, "Assets")
        _build_template_framework(self, assets_tab, controls, assets_layout)
        build_deck_tab = QWidget(tabs)
        build_deck_tab.setObjectName("buildDeckTab")
        build_deck_layout = QVBoxLayout(build_deck_tab)
        build_deck_layout.setContentsMargins(0, 0, 0, 0)
        # Keep Build Deck with the screen-specific editors and leave the
        # catalogue visible directly after it.
        tabs.insertTab(tabs.indexOf(assets_tab), build_deck_tab, "Build Deck")
        _build_build_deck_tab(self, build_deck_tab, controls, build_deck_layout)
        controls.update(shell=shell, tabs=tabs, assets_tab=assets_tab)
        _apply_reference_skin(shell, tabs, assets_tab)
        _wire_ui_tabs(self, shell, controls)
        tabs.setCurrentIndex(0)
        return shell

    def duel(self): return _object(_object(self.project.other, "ui"), "duel")

    def _load(self):
        c = self.workspace_controls.get("Assets", {}); root = self.project.other
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
        c = self.workspace_controls.get("Assets", {})
        if not c: return
        element = self._ui_duel().get(c["element"].currentData(), {}); value = element.get(c["part"].currentData(), {}) if isinstance(element, dict) else {}; value = value if isinstance(value, dict) else {}
        for key in ("part_x", "part_y", "part_spacing", "part_tint", "part_hide"): c[key].blockSignals(True)
        c["part_x"].setValue(value.get("x", 0) if isinstance(value.get("x", 0), int) else 0); c["part_y"].setValue(value.get("y", 0) if isinstance(value.get("y", 0), int) else 0); c["part_spacing"].setValue(value.get("spacing", 0) if isinstance(value.get("spacing", 0), int) else 0); c["part_tint"].setText(str(value.get("tint", ""))); c["part_hide"].setChecked(bool(value.get("hide", False)))
        for key in ("part_x", "part_y", "part_spacing", "part_tint", "part_hide"): c[key].blockSignals(False)

    def _write(self):
        c = self.workspace_controls["Assets"]; root = self.project.other; title = _object(root, "title")
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

    def _reset(self): self._ui_duel().pop(self.workspace_controls["Assets"]["element"].currentData(), None); _load(self); self._mark_dirty()
    def _revert(self):
        for key in ("ui", "title", "menu"): self.project.other.pop(key, None)
        _load(self); self._mark_dirty()
    def refresh(self):
        _refresh_template(self)
        _refresh_ui_tabs(self)

    AssetsMixin._build_assets_page = build; AssetsMixin._refresh_assets = refresh; AssetsMixin._ui_duel = duel


def _apply_reference_skin(shell, tabs, assets_tab):
    """Apply the four-tab UI Assets presentation from the supplied reference."""
    title = shell.findChild(QLabel, "pageTitleLabel")
    summary = shell.findChild(QLabel, "pageSummaryLabel")
    title.setText("▣  UI Assets")
    summary.setText("Replace named interface graphics used by menus, icons, and duel screens.")
    title.setStyleSheet("font-size: 25px; font-weight: 700; color: #f3f8ff;")
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
    c = editor.workspace_controls.get("Assets", {})
    point, key = _preview_point(label, position), _preview_key(c.get(f"{kind}_boxes", {}), _preview_point(label, position))
    if key is None: return
    if kind == "title":
        c["title_selected"] = key; _refresh_title(editor)
    elif kind == "menu":
        c["menu_selected"] = key; _refresh_menu(editor)
    else:
        c["duel_selected"] = key; _refresh_duel(editor)
    c["preview_drag"] = {"kind": kind, "key": key, "point": point, "moved": False}


def _preview_drag(editor, kind, label, position):
    c, drag = editor.workspace_controls.get("Assets", {}), editor.workspace_controls.get("Assets", {}).get("preview_drag")
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
        _draw_title(editor)
    elif kind == "menu":
        # Not "if not target" -- a fresh item's target is a real but empty
        # {} (entries.setdefault), so that check always aborted the drag.
        if _menu_item(editor) is None: return
        target = _menu_target(editor, True)
        target["x"] = _as_int(drag.setdefault("x", target.get("x", 0))) + dx
        target["y"] = _as_int(drag.setdefault("y", target.get("y", 0))) + dy
        _draw_menu(editor)
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
        _draw_duel(editor)
    drag["moved"] = True


def _preview_nudge(editor, kind, key, amount):
    directions = {Qt.Key.Key_Left: (-amount, 0), Qt.Key.Key_Right: (amount, 0), Qt.Key.Key_Up: (0, -amount), Qt.Key.Key_Down: (0, amount)}
    if key not in directions: return False
    dx, dy = directions[key]; c = editor.workspace_controls.get("Assets", {})
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
    c = editor.workspace_controls.get("Assets", {}); name, part = _duel_path(c.get("duel_selected", ""))
    if part is not None or name not in ui_rules.SIZED or not delta: return
    target = _duel_target(editor, True); step = 10 if delta > 0 else -10
    target["scale"] = max(25, min(ui_rules.element_scale_max(name, target), _as_int(target.get("scale"), 100) + step))
    editor._mark_dirty(); _refresh_duel(editor)


def _preview_release(editor, kind):
    c, drag = editor.workspace_controls.get("Assets", {}), editor.workspace_controls.get("Assets", {}).pop("preview_drag", None)
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
    c = editor.workspace_controls.get("Assets", {})
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
    c = editor.workspace_controls["Assets"]
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


def _commit_ui(editor):
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
    c = editor.workspace_controls.get("Assets", {})
    if not c.get("shell") or c.get("ui_loading"):
        return
    c["ui_loading"] = True
    try:
        _refresh_title(editor); _refresh_menu(editor); _refresh_duel(editor); _board_refresh(editor)
    finally:
        c["ui_loading"] = False


def _title_target(editor, create=False):
    c, chosen = editor.workspace_controls["Assets"], editor.workspace_controls["Assets"].get("title_selected", "background")
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
    c, tree = editor.workspace_controls["Assets"], editor.workspace_controls["Assets"]["title_tree"]
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
    current = editor.workspace_controls["Assets"].get("title_selected")
    editor.workspace_controls["Assets"]["title_selected"] = chosen
    value = _title_target(editor, False)
    editor.workspace_controls["Assets"]["title_selected"] = current
    return value


def _title_select(editor, item):
    if editor.workspace_controls["Assets"].get("ui_loading") or item is None:
        return
    key = item.data(0, Qt.ItemDataRole.UserRole)
    if isinstance(key, str): editor.workspace_controls["Assets"]["title_selected"] = key; _refresh_title(editor)


def _fill_title_form(editor):
    c, selected = editor.workspace_controls["Assets"], editor.workspace_controls["Assets"].get("title_selected")
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
    c = editor.workspace_controls["Assets"]
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
    c = editor.workspace_controls["Assets"]
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
    c = editor.workspace_controls["Assets"]
    _render_title(editor, c.get("menu_number", 0) if c["title_menu_up"].isChecked() else None)


def _draw_menu(editor):
    c = editor.workspace_controls["Assets"]
    # The original menu page is the title screen with its first or second menu up.
    image = _render_title(editor, c.get("menu_number", 0))
    _png_preview(c["menu_preview"], image, "Load game files to preview the menu")
    # Rendering the menu shares the title compositor; restore the Title tab's own view.
    _draw_title(editor)


def _title_generic_changed(editor):
    c = editor.workspace_controls["Assets"]
    if c.get("ui_loading") or c.get("title_selected") == "background" or c.get("title_selected", "").startswith("text:"): return
    target = _title_target(editor, True)
    _put(target, "x", c["title_x"].value(), 160 if c["title_selected"].startswith("picture:") else 0); _put(target, "y", c["title_y"].value(), 120 if c["title_selected"].startswith("picture:") else 0)
    _put(target, "tint", _colour(c["title_tint"].text()), "#FFFFFF"); _put(target, "show", c["title_show"].currentData(), "always"); _put(target, "hide", c["title_hidden"].isChecked(), False); _commit_ui(editor)


def _title_background_changed(editor):
    c = editor.workspace_controls["Assets"]
    if c.get("ui_loading"): return
    target = _title_target(editor, True); _put(target, "color", _colour(c["title_bg_color"].text(), "#000000"), None); _put(target, "picture", c["title_bg_picture"].isChecked(), True); _commit_ui(editor)


def _title_text_changed(editor):
    c = editor.workspace_controls["Assets"]
    if c.get("ui_loading") or not c.get("title_selected", "").startswith("text:"): return
    target = _title_target(editor, True); _put(target, "text", c["title_text"].text().strip(), None); _put(target, "color", _colour(c["title_text_color"].text()), "#FFFFFF"); _put(target, "size", c["title_text_size"].value(), 1); _commit_ui(editor)


def _title_add_text(editor):
    title = _ui_section(editor, "title", True); values = title.setdefault("text", []); values.append({"text": "Words", "x": 160, "y": 220}); editor.workspace_controls["Assets"]["title_selected"] = f"text:{len(values) - 1}"; _commit_ui(editor)


def _title_add_picture(editor):
    image = _store_ui_png(editor, "title-picture")
    if image:
        title = _ui_section(editor, "title", True); values = title.setdefault("images", []); values.append({"image": image, "x": 160, "y": 120}); editor.workspace_controls["Assets"]["title_selected"] = f"picture:{len(values) - 1}"; _commit_ui(editor)


def _title_choose_image(editor):
    selected = editor.workspace_controls["Assets"].get("title_selected", "")
    if selected in ("background",) or selected.startswith("text:"): return
    image = _store_ui_png(editor, f"title-{selected.replace(':', '-')}")
    if image: _title_target(editor, True)["image"] = image; _commit_ui(editor)


def _title_clear_image(editor):
    target = _title_target(editor, True); target.pop("image", None); target.pop("width", None); target.pop("height", None); _commit_ui(editor)


def _title_background_image(editor):
    image = _store_ui_png(editor, "title-background")
    if image: _title_target(editor, True)["image"] = image; _commit_ui(editor)


def _title_export(editor):
    c, selected = editor.workspace_controls["Assets"], editor.workspace_controls["Assets"].get("title_selected", "background")
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
    c, selected = editor.workspace_controls["Assets"], editor.workspace_controls["Assets"].get("title_selected", "")
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
    c, selected = editor.workspace_controls["Assets"], editor.workspace_controls["Assets"].get("title_selected", "")
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
    editor.workspace_controls["Assets"]["title_selected"] = "background"; _commit_ui(editor)



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
    name = name or editor.workspace_controls["Assets"].get("menu_selected")
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
    c, current = editor.workspace_controls["Assets"], editor.workspace_controls["Assets"].get("menu_selected")
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
    c, tree = editor.workspace_controls["Assets"], editor.workspace_controls["Assets"]["menu_tree"]
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
    c = editor.workspace_controls["Assets"]
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
    c, item = editor.workspace_controls["Assets"], _menu_item(editor)
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
    c = editor.workspace_controls["Assets"]
    if c.get("ui_loading"): return
    c["menu_number"] = c["menu_mode"].currentData()
    scene = _menu_scene(editor)
    order = scene.order(c["menu_number"])
    if order and (_menu_item(editor) is None or _menu_item(editor).get("menu") != c["menu_number"]): c["menu_selected"] = order[0][0]["name"]
    _refresh_menu(editor)


def _menu_global_changed(editor):
    c = editor.workspace_controls["Assets"]
    if c.get("ui_loading"): return
    menu = _ui_section(editor, "menu", True); _put(menu, "spacing", c["menu_spacing"].value(), _MENU_SPACING); _put(menu, "scale", c["menu_all_scale"].value(), 100); _commit_ui(editor)


def _menu_item_changed(editor):
    c = editor.workspace_controls["Assets"]
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
    if editor.workspace_controls["Assets"].get("menu_number") == 1: row["menu"] = "second"
    buttons.append(row); editor.workspace_controls["Assets"]["menu_selected"] = f"{editor.project.info.id or 'mod'}:button{number}"; _commit_ui(editor)


def _menu_toggle_hidden(editor):
    item = _menu_item(editor)
    if item:
        target = _menu_target(editor, True); _put(target, "hide", not bool(item.get("hide")), False); _commit_ui(editor)


def _menu_move(editor, step):
    c, item = editor.workspace_controls["Assets"], _menu_item(editor)
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
    c, selected = editor.workspace_controls["Assets"], editor.workspace_controls["Assets"].get("menu_selected", "background")
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
    editor.workspace_controls["Assets"]["menu_selected"] = "new_game"; _commit_ui(editor)


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
    editor.workspace_controls["Assets"]["menu_selected"] = "new_game"; _commit_ui(editor)


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
    key = editor.workspace_controls["Assets"].get("duel_selected", "lp_player")
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
    c, current = editor.workspace_controls["Assets"], editor.workspace_controls["Assets"].get("duel_selected")
    c["duel_selected"] = key; value = _duel_target(editor); c["duel_selected"] = current
    return value


def _refresh_duel(editor):
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QHeaderView, QTreeWidgetItem
    c, tree = editor.workspace_controls["Assets"], editor.workspace_controls["Assets"]["duel_tree"]
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
    c = editor.workspace_controls["Assets"]
    if c.get("ui_loading") or item is None: return
    key = item.data(0, Qt.ItemDataRole.UserRole)
    if isinstance(key, str): c["duel_selected"] = key; _refresh_duel(editor)


def _fill_duel_form(editor):
    c, key = editor.workspace_controls["Assets"], editor.workspace_controls["Assets"].get("duel_selected", "lp_player")
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
    c = editor.workspace_controls["Assets"]
    key = id(getattr(editor, "files", None))
    if c.get("duel_art_key") != key:
        c["duel_art_key"] = key
        c["duel_art"] = ui_assets.DuelArt(getattr(getattr(editor, "files", None), "wa", None))
    return c["duel_art"]


def _duel_font(editor):
    """The same retail font and icons used by the classic duel preview."""
    c = editor.workspace_controls["Assets"]
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
    c = editor.workspace_controls["Assets"]
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
    c = editor.workspace_controls["Assets"]
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
    c = editor.workspace_controls["Assets"]
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
    key = editor.workspace_controls["Assets"].get("duel_selected", "duel")
    if "." in key: return
    image = _store_ui_png(editor, f"duel-{key.replace('_', '-')}")
    if image: _duel_target(editor, True)["image"] = image; _commit_ui(editor)


def _duel_export(editor):
    selected = editor.workspace_controls["Assets"].get("duel_selected", "lp_player")
    _export_ui_png(editor, _duel_asset_image(editor, selected), f"duel-{selected.replace('.', '-')}.png")


def _duel_revert_element(editor):
    key = editor.workspace_controls["Assets"].get("duel_selected", "lp_player"); name, part = _duel_path(key); root = _ui_section(editor, "ui")
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
    c = editor.workspace_controls["Assets"]
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
    c = editor.workspace_controls.get("Assets", {})
    if c.get("board_picture") is not None:
        _board_display(editor, c["board_picture"])


def _board_display(editor, picture, full_size=True):
    """The cached 3D render redrawn with the current part(s) outlined, no
    re-render needed (a part picked, or a selection made elsewhere)."""
    c = editor.workspace_controls.get("Assets", {})
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
    c = editor.workspace_controls.get("Assets", {})
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
        controls = editor.workspace_controls.get("Assets", {})
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
    c = editor.workspace_controls.get("Assets", {})
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
    c = editor.workspace_controls.get("Assets", {})
    point = _board_point(label, event.position())
    if event.button() == Qt.MouseButton.MiddleButton:
        kind = "pan" if event.modifiers() & (Qt.KeyboardModifier.ShiftModifier | Qt.KeyboardModifier.ControlModifier) else "turn"
        c["board_drag"] = {"kind": kind, "point": point, "camera": _board_camera(c)}
    else:
        c["board_click"] = point


def _board_motion(editor, label, event):
    c = editor.workspace_controls.get("Assets", {})
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
    c = editor.workspace_controls.get("Assets", {})
    if event.button() == Qt.MouseButton.MiddleButton:
        was_dragging = c.pop("board_drag", None) is not None
        if was_dragging: _board_request_render(editor, full_size=True)
    elif event.button() == Qt.MouseButton.LeftButton:
        point = c.pop("board_click", None)
        if point is not None: _board_pick(editor, point)


def _board_wheel(editor, delta):
    if not delta: return
    c = editor.workspace_controls.get("Assets", {})
    c["board_camera"] = board_model.zoom(_board_camera(c), 1 if delta > 0 else -1)
    _board_request_render(editor)


def _board_reset_view(editor):
    """The duel's own camera again (ui_board.py's reset_camera)."""
    c = editor.workspace_controls.get("Assets", {})
    c["board_camera"] = board_model.CAMERA
    _board_request_render(editor)


def _board_pick(editor, point):
    """A click on the 3D preview itself chooses the part under it."""
    c = editor.workspace_controls.get("Assets", {})
    picture = c.get("board_picture")
    if picture is None: return
    key = picture.part_at(int(point[0]), int(point[1]))
    if key is None or key not in board_art.BY_KEY: return
    if key != c.get("board_selected"):
        c["board_selected"] = key
        _board_refresh(editor)


def _board_select(editor, item):
    c = editor.workspace_controls["Assets"]
    if c.get("ui_loading") or item is None:
        return
    key = item.data(0, Qt.ItemDataRole.UserRole)
    if key == "floor" or key in board_art.BY_KEY:
        c["board_selected"] = key
        _board_refresh(editor)


def _board_filter(editor):
    query = editor.workspace_controls["Assets"]["board_search"].text().strip().casefold()
    tree = editor.workspace_controls["Assets"]["board_tree"]
    for index in range(tree.topLevelItemCount()):
        parent = tree.topLevelItem(index); visible = not query or query in parent.text(0).casefold()
        for child_index in range(parent.childCount()):
            child = parent.child(child_index)
            show = not query or query in child.text(0).casefold()
            child.setHidden(not show); visible = visible or show
        parent.setHidden(not visible)


def _board_tint(editor):
    c = editor.workspace_controls["Assets"]
    if c.get("ui_loading"):
        return
    value = _colour(c["board_tint"].text(), "")
    if not value:
        QMessageBox.warning(editor, "Duel board", "Use a six-digit colour, such as #C08040.")
        _board_refresh(editor); return
    board_art.set_tint(editor.project, _board_terrains(c), _board_parts(c), int(value[1:], 16))
    editor._mark_dirty(); _board_refresh(editor, force=True)


def _board_replace(editor):
    c = editor.workspace_controls["Assets"]
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
    c = editor.workspace_controls["Assets"]
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
    c = editor.workspace_controls["Assets"]
    board_art.revert(editor.project, _board_terrains(c), _board_parts(c))
    editor._mark_dirty(); _board_refresh(editor, force=True)


def _board_revert_all(editor):
    board_art.revert_all(editor.project)
    editor._mark_dirty(); _board_refresh(editor, force=True)


def _catalog():
    path = Path(__file__).resolve().parents[4] / "docs" / "asset-catalog.json"
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
    c = self.workspace_controls.get("Assets", {})
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
    if relative in _deleted_files(self.project):
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


def _build_framework(self, page, controls, layout):
    catalog = _catalog()
    categories = sorted({item["name"].split("/", 1)[0] for item in catalog}, key=str.casefold)
    controls.clear(); controls.update(page=page, catalog=catalog, category=categories[0] if categories else "", selected=None)
    self.workspace_controls["Assets"] = controls
    if hasattr(self, "nav_buttons") and "Assets" in self.nav_buttons: self.nav_buttons["Assets"].setText("Assets")
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
    self.workspace_controls["Assets"]["category"] = category; _refresh_framework(self)


def _preview(label, image, fallback):
    if image is None: label.setPixmap(QPixmap()); label.setText(fallback); return
    pixmap = QPixmap.fromImage(_qimage(image.width, image.height, image.rgba))
    label.setText(""); label.setPixmap(pixmap.scaled(label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))


def _refresh_framework(self):
    c = self.workspace_controls.get("Assets", {})
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
    c = self.workspace_controls.get("Assets", {})
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
    c = self.workspace_controls["Assets"]; c["selected"] = asset
    if asset is None:
        c["name"].setText("No asset selected"); c["description"].setText("No named assets match this category or search."); _preview(c["retail"], None, "Retail preview"); _preview(c["replacement"], None, "Replacement preview"); c["remove"].setEnabled(False); return
    entry = _entry_for(self, asset); retail = self._asset_retail_image(asset); replacement = _named_image(self, entry)
    c["name"].setText(asset["name"].rsplit("/", 1)[-1]); c["description"].setText(asset.get("what") or "Named UI texture."); c["path"].setText(asset["name"]); c["size"].setText(f"{asset.get('width', asset['words'] * (16 // asset['bpp']))} × {asset['rows']}"); c["uses"].setText(f"{_category(asset['name'])} · {asset['regions']} texture region{'s' if asset['regions'] != 1 else ''}"); c["state"].setText("Modified by this mod" if entry else "Retail"); c["remove"].setEnabled(entry is not None)
    _preview(c["retail"], retail, "Retail preview unavailable"); _preview(c["replacement"], replacement, "No replacement")


def _import_framework(self):
    c = self.workspace_controls["Assets"]; asset = c.get("selected")
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
    asset = self.workspace_controls["Assets"].get("selected")
    if asset is None: return
    image = _named_image(self, _entry_for(self, asset)) or self._asset_retail_image(asset)
    if image is None: QMessageBox.warning(self, "Export UI asset", "The retail texture cannot be decoded."); return
    path, _ = QFileDialog.getSaveFileName(self, "Export UI asset", asset["name"].rsplit("/", 1)[-1] + ".png", "PNG images (*.png)")
    if path: pngio.write(path, image)


def _remove_framework(self):
    c = self.workspace_controls["Assets"]; asset = c.get("selected"); path = _entry_for(self, asset) if asset else None
    if path is None: return
    self.project.files.pop(path, None)
    folder = self.project.other.get("assets")
    if isinstance(folder, str) and not any(name.startswith(folder.rstrip("/") + "/") for name in self.project.files): self.project.other.pop("assets", None)
    self._mark_dirty(); _select_framework(self, asset)


# A verbatim copy of the original Assets Designer form is kept beside this
# compatibility module.  Loading the copy lets the modern editor reuse that
# page without changing the master-tracked source form.
def _compat_form(parent):
    source = QFile(str(Path(__file__).with_name("original_assets_page_compat.ui")))
    if not source.open(QIODevice.OpenModeFlag.ReadOnly):
        raise RuntimeError(f"Could not load Assets form: {source.errorString()}")
    try:
        form = QUiLoader().load(source, parent)
    finally:
        source.close()
    if form is None:
        raise RuntimeError("Could not load the compatibility Assets form")
    return form


def _all_tabs_form(parent):
    """Load the user-provided UI Assets shell kept in the Qt compatibility layer."""
    source = QFile(str(Path(__file__).with_name("ui_page_all_tabs_compat.ui")))
    if not source.open(QIODevice.OpenModeFlag.ReadOnly):
        raise RuntimeError(f"Could not load UI Assets tabs form: {source.errorString()}")
    try:
        form = QUiLoader().load(source, parent)
    finally:
        source.close()
    if form is None:
        raise RuntimeError("Could not load the UI Assets tabs form")
    return form


def _asset_widget(form, kind, name):
    value = form.findChild(kind, name)
    if value is None:
        raise RuntimeError(f"Assets form is missing {name}")
    return value


def _build_template_framework(self, page, controls, layout):
    from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem
    _clear(layout)
    form = _compat_form(page)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(form)
    catalog = _catalog()
    categories = sorted({_category(item["name"]) for item in catalog}, key=str.casefold)
    controls.clear()
    controls.update(page=page, form=form, catalog=catalog, category="__all__",
                    selected=None, filter_mode="all", preview_scale=2)
    self.workspace_controls["Assets"] = controls

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
        # The original form has no catalogue footer.  Keep this bookkeeping
        # label out of the layout instead of changing the copied form.
        footer=QLabel(form),
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
    _asset_widget(form, QPushButton, "previewAssetsModButton").clicked.connect(self.preview_manifest)
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
    self.workspace_controls["Assets"]["category"] = category
    _refresh_template(self)


def _filter_template_categories(self, text):
    tree = self.workspace_controls["Assets"]["tree"]
    wanted = text.strip().casefold()
    def filter_item(item):
        own = wanted in item.text(0).casefold()
        child = any(filter_item(item.child(index)) for index in range(item.childCount()))
        item.setHidden(bool(wanted and not own and not child))
        return own or child
    for row in range(tree.topLevelItemCount()):
        filter_item(tree.topLevelItem(row))


def _set_template_filter(self, mode):
    c = self.workspace_controls["Assets"]
    c["filter_mode"] = mode
    for key in ("all", "modified", "retail"):
        c[key].setChecked(key == mode)
    _refresh_template(self)


def _set_template_scale(self, scale):
    c = self.workspace_controls["Assets"]
    c["preview_scale"] = scale
    form = c["form"]
    for value, name in ((1, "preview1xButton"), (2, "preview2xButton"), (4, "preview4xButton")):
        _asset_widget(form, QPushButton, name).setChecked(value == scale)
    _select_template(self, c.get("selected"))


def _template_values(self):
    c = self.workspace_controls.get("Assets", {})
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
    c = self.workspace_controls.get("Assets", {})
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
    modified = sum(1 for asset in c.get("catalog", []) if _entry_for(self, asset))
    c["footer"].setText(f"{modified} modified asset{'s' if modified != 1 else ''}")


def _select_template_row(self):
    table = self.workspace_controls["Assets"]["table"]
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
    c = self.workspace_controls["Assets"]; c["selected"] = asset
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
    c = self.workspace_controls.get("Assets", {})
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
        current = self.workspace_controls.get("Assets", {})
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
    c = self.workspace_controls.get("Assets", {})
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
        current = self.workspace_controls.get("Assets", {})
        cache = current.setdefault("retail_preview_cache", {})
        current.setdefault("retail_preview_loading", set()).discard(key)
        cache[key] = result.get("image")
        if len(cache) > 32:
            cache.pop(next(iter(cache)))
        selected = current.get("selected")
        if selected and selected.get("name") == asset.get("name"):
            _select_template(self, selected)

    QTimer.singleShot(0, complete)


def _deleted_files(project) -> set:
    """``project.deleted_files``: compat-only bookkeeping `Project` itself
    never declares, so create it on first use rather than assume it."""
    value = getattr(project, "deleted_files", None)
    if not isinstance(value, set):
        value = project.deleted_files = set()
    return value


def _asset_paths(project, folder):
    """All saved and pending named assets, minus queued removals."""
    if not isinstance(folder, str) or not folder:
        return set()
    prefix = folder.rstrip("/") + "/"
    removed = _deleted_files(project)
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
    _deleted_files(project).add(path)


def _import_template(self):
    c = self.workspace_controls["Assets"]; asset = c.get("selected")
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
    _deleted_files(self.project).discard(relative)
    c.get("preview_image_cache", {}).pop(relative, None)
    self._mark_dirty(); _refresh_template(self)


def _export_template(self):
    asset = self.workspace_controls["Assets"].get("selected")
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
    c = self.workspace_controls["Assets"]; asset = c.get("selected")
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
        _remember_asset_removal(self.project, path)
        c.get("preview_image_cache", {}).pop(path, None)
        st = art.state(self.project)
        # Removing this first matching manifest entry restores the retail
        # texture read.  Keep the old PNG on disk: it may be shared by an
        # unrelated entry and is harmless when no manifest entry names it.
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


def _build_build_deck_tab(self, page, controls, layout):
    _clear(layout)
    source = QFile(str(UI_DIR / "build_deck_assets_tab.ui"))
    if not source.open(QIODevice.OpenModeFlag.ReadOnly):
        raise RuntimeError(f"Could not open Build Deck assets form: {source.errorString()}")
    loader = QUiLoader(); form = loader.load(source, page); source.close()
    if form is None:
        raise RuntimeError(f"Could not load Build Deck assets form: {loader.errorString()}")
    layout.addWidget(form)

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
    c = self.workspace_controls.get("Assets", {}); bd = c.get("build_deck", {})
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
    c = self.workspace_controls["Assets"]; bd = c["build_deck"]
    bd["search"] = text
    _refresh_build_deck(self)


def _refresh_build_deck(self):
    c = self.workspace_controls.get("Assets", {}); bd = c.get("build_deck", {})
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
    bd = self.workspace_controls["Assets"]["build_deck"]; table = bd["table"]
    item = table.item(table.currentRow(), 0) if table.currentRow() >= 0 else None
    _select_build_deck(self, item.data(Qt.ItemDataRole.UserRole) if item else None)


def _set_build_deck_filter(self, mode):
    bd = self.workspace_controls["Assets"]["build_deck"]
    bd["filter_mode"] = mode
    for key in ("all", "modified", "retail"): bd[key].setChecked(key == mode)
    _refresh_build_deck(self)


def _set_build_deck_scale(self, scale):
    bd = self.workspace_controls["Assets"]["build_deck"]
    bd["preview_scale"] = scale
    for value, name in ((1, "buildDeckPreview1xButton"), (2, "buildDeckPreview2xButton"), (4, "buildDeckPreview4xButton")):
        bd["form"].findChild(QPushButton, name).setChecked(value == scale)
    _select_build_deck(self, bd.get("selected"))


def _select_build_deck(self, asset):
    bd = self.workspace_controls["Assets"]["build_deck"]; bd["selected"] = asset
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
    bd = self.workspace_controls.get("Assets", {}).get("build_deck", {})
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
        current = self.workspace_controls.get("Assets", {}).get("build_deck", {})
        cache = current.setdefault("preview_image_cache", {})
        current.setdefault("preview_image_loading", set()).discard(entry)
        cache[entry] = result.get("image")
        if len(cache) > 16: cache.pop(next(iter(cache)))
        selected = current.get("selected")
        if selected and selected.get("name") == asset.get("name"): _select_build_deck(self, selected)

    QTimer.singleShot(0, complete)


def _load_build_deck_retail_preview_image(self, asset):
    bd = self.workspace_controls.get("Assets", {}).get("build_deck", {})
    key = asset["name"]; pending = bd.setdefault("retail_preview_loading", set())
    if key in pending: return
    pending.add(key); result = {}

    def read():
        try: result["image"] = self._asset_retail_image(asset)
        except (IndexError, KeyError, OSError, TypeError, ValueError, pngio.PngError): result["image"] = None

    thread = threading.Thread(target=read, name="fm-editor-build-deck-retail", daemon=True); thread.start()

    def complete():
        if thread.is_alive(): QTimer.singleShot(15, complete); return
        current = self.workspace_controls.get("Assets", {}).get("build_deck", {})
        cache = current.setdefault("retail_preview_cache", {})
        current.setdefault("retail_preview_loading", set()).discard(key)
        cache[key] = result.get("image")
        if len(cache) > 32: cache.pop(next(iter(cache)))
        selected = current.get("selected")
        if selected and selected.get("name") == asset.get("name"): _select_build_deck(self, selected)

    QTimer.singleShot(0, complete)


def _import_build_deck(self):
    bd = self.workspace_controls["Assets"]["build_deck"]; asset = bd.get("selected")
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
    _deleted_files(self.project).discard(relative)
    bd.get("preview_image_cache", {}).pop(relative, None)
    self._mark_dirty(); _refresh_build_deck(self)


def _export_build_deck(self):
    asset = self.workspace_controls["Assets"]["build_deck"].get("selected")
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
    bd = self.workspace_controls["Assets"]["build_deck"]; asset = bd.get("selected")
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
        _remember_asset_removal(self.project, path)
        bd.get("preview_image_cache", {}).pop(path, None)
        st = art.state(self.project)
        st.entries = [entry for entry in st.entries or [] if entry is not manifest_entry]
        st.changed = True
        self.workspace_controls["Assets"].pop("legacy_pack_index", None)
        self._mark_dirty(); _refresh_build_deck(self); return
    _remember_asset_removal(self.project, path)
    bd.get("preview_image_cache", {}).pop(path, None)
    folder = self.project.other.get("assets")
    if not _asset_paths(self.project, folder): self.project.other.pop("assets", None)
    self._mark_dirty(); _refresh_build_deck(self)


def _revert_build_deck_all(self):
    """Only the build_deck/* entries -- not every named asset in the mod."""
    bd = self.workspace_controls["Assets"]["build_deck"]
    for asset in bd.get("catalog", []):
        path, origin, manifest_entry = _entry_origin(self, asset)
        if path is None: continue
        if origin == "pack" and manifest_entry is not None:
            crop = _legacy_crop(self, asset)
            if crop is not None and _asset_shares_entry(self, asset, manifest_entry):
                # Shared with an asset outside this tab's own catalog (not
                # being reverted here): patch this region, leave the rest.
                base = _named_image(self, path)
                retail = self._asset_retail_image(asset)
                if base is not None and retail is not None:
                    left, top, width, height = _atlas_region(manifest_entry, crop, base.width, base.height)
                    patch = pngio.scale_to(retail, width, height)
                    self.project.files[path] = pngio.encode(pngio.paste(base, patch, left, top))
                continue
            _remember_asset_removal(self.project, path)
            st = art.state(self.project)
            st.entries = [entry for entry in st.entries or [] if entry is not manifest_entry]
            st.changed = True
            self.workspace_controls["Assets"].pop("legacy_pack_index", None)
        else:
            _remember_asset_removal(self.project, path)
    bd.get("preview_image_cache", {}).clear()
    self.workspace_controls["Assets"].pop("legacy_pack_index", None)
    folder = self.project.other.get("assets")
    if not _asset_paths(self.project, folder): self.project.other.pop("assets", None)
    self._mark_dirty(); _refresh_build_deck(self)
