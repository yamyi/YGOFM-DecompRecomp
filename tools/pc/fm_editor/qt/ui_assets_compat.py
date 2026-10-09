"""Use the modern editor's Assets entry as PR #297's UI / Graphics page.

This compatibility module stays separate from master-tracked editor files.
"""
from __future__ import annotations

from .common import *  # noqa: F401,F403
from .common import _qimage
from .. import art
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
        layout = page.layout() or QVBoxLayout(page)
        _clear(layout); layout.setContentsMargins(14, 12, 14, 12); layout.setSpacing(8)
        header = QHBoxLayout()
        text = QVBoxLayout(); text.setSpacing(1)
        _heading(text, "UI Asset Replacement", "Replace game interface graphics using the named asset framework.")
        header.addLayout(text, 1)
        open_folder = QPushButton("Open assets folder")
        documentation = QPushButton("View asset documentation")
        header.addWidget(open_folder); header.addWidget(documentation); layout.addLayout(header)
        open_folder.clicked.connect(lambda: _open_assets_folder(self))
        documentation.clicked.connect(lambda: _show_asset_help(self))
        return _build_template_framework(self, page, controls, layout)

        title = QWidget(); form = QFormLayout(title); form.setContentsMargins(18, 20, 18, 18)
        controls["title_background"] = _line("#RRGGBB"); controls["title_intro"] = _line("Intro scene or video"); controls["title_song"] = _line("Song identifier")
        form.addRow("Background tint", controls["title_background"]); form.addRow("Intro", controls["title_intro"]); form.addRow("Music", controls["title_song"])
        form.addRow(QLabel("Additional title pictures use title.images. Add PNG files with Art, then set their entries in mod.json until the PR #297 runtime is merged.")); tabs.addTab(title, "Title screen")

        menu = QWidget(); form = QFormLayout(menu); form.setContentsMargins(18, 20, 18, 18)
        controls["menu_scale"] = _spin(25, 400, "%"); controls["menu_tint"] = _line("#RRGGBB")
        form.addRow("All button size", controls["menu_scale"]); form.addRow("Background tint", controls["menu_tint"])
        form.addRow(QLabel("Individual menu-button settings remain under menu.entries and menu.buttons.")); tabs.addTab(menu, "Menus")

        duel = QWidget(); duel_layout = QVBoxLayout(duel); duel_layout.setContentsMargins(18, 16, 18, 16)
        _heading(duel_layout, "Duel HUD", "Move, scale, tint, hide or replace each element. LP panels and FIELD are vertical-only because the game slides them sideways.")
        pick = QHBoxLayout(); pick.addWidget(QLabel("Element")); controls["element"] = QComboBox()
        for key, label in ELEMENTS: controls["element"].addItem(label, key)
        pick.addWidget(controls["element"], 1); reset = QPushButton("Reset element"); pick.addWidget(reset); duel_layout.addLayout(pick)
        grid = QFormLayout(); controls["x"] = _spin(-400, 400); controls["y"] = _spin(-300, 300); controls["scale"] = _spin(25, 400, "%")
        controls["tint"] = _line("#RRGGBB"); controls["hide"] = QCheckBox("Hide this element"); controls["label"] = _line("LP label"); controls["digits"] = _line("Digits colour #RRGGBB"); controls["image"] = _line("ui/replacement.png"); controls["width"] = _spin(0, 320); controls["height"] = _spin(0, 240)
        for label, key in (("X", "x"), ("Y", "y"), ("Scale", "scale"), ("Tint", "tint"), ("Label", "label"), ("Digits", "digits"), ("PNG", "image"), ("PNG width", "width"), ("PNG height", "height")): grid.addRow(label, controls[key])
        grid.addRow("", controls["hide"]); duel_layout.addLayout(grid)
        group = QGroupBox("Card-bar parts"); parts = QFormLayout(group); controls["part"] = QComboBox()
        for key, label in PARTS: controls["part"].addItem(label, key)
        controls["part_x"] = _spin(-400, 400); controls["part_y"] = _spin(-300, 300); controls["part_tint"] = _line("#RRGGBB"); controls["part_hide"] = QCheckBox("Hide part"); controls["part_spacing"] = _spin(-3, 2)
        for label, key in (("Part", "part"), ("X", "part_x"), ("Y", "part_y"), ("Tint", "part_tint"), ("Name spacing", "part_spacing")): parts.addRow(label, controls[key])
        parts.addRow("", controls["part_hide"]); duel_layout.addWidget(group); duel_layout.addStretch(1); tabs.addTab(duel, "Duel HUD")

        board = QWidget(); board_layout = QVBoxLayout(board); board_layout.setContentsMargins(18, 16, 18, 16)
        _heading(board_layout, "Duel board", "PR #297 adds live 3D board previews and per-field floor, wall, trim and tint editing.")
        note = QLabel("Board replacements remain texture-pack entries. They are preserved in the mod and become interactive when the PR #297 game runtime is present."); note.setObjectName("muted"); note.setWordWrap(True); board_layout.addWidget(note); board_layout.addStretch(1); tabs.addTab(board, "Duel board")
        actions = QHBoxLayout(); actions.addStretch(1); revert = QPushButton("Revert UI to retail"); apply = QPushButton("Apply UI changes"); apply.setObjectName("primary"); actions.addWidget(revert); actions.addWidget(apply); layout.addLayout(actions)

        def changed(*_): _write(self); self._mark_dirty()
        for key in ("title_background", "title_intro", "title_song", "menu_tint", "tint", "label", "digits", "image", "part_tint"): controls[key].editingFinished.connect(changed)
        for key in ("menu_scale", "x", "y", "scale", "width", "height", "part_x", "part_y", "part_spacing"): controls[key].valueChanged.connect(changed)
        for key in ("hide", "part_hide"): controls[key].toggled.connect(changed)
        controls["element"].currentIndexChanged.connect(lambda *_: _load(self)); controls["part"].currentIndexChanged.connect(lambda *_: _load_part(self))
        reset.clicked.connect(lambda: _reset(self)); revert.clicked.connect(lambda: _revert(self)); apply.clicked.connect(self.save_mod); _load(self)

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
    def refresh(self): _refresh_template(self)

    AssetsMixin._build_assets_page = build; AssetsMixin._refresh_assets = refresh; AssetsMixin._ui_duel = duel


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


# The supplied Designer form is kept next to this compatibility module.  It
# is intentionally separate from tools/pc/fm_editor/ui/assets_page.ui, which
# belongs to origin/master.
def _compat_form(parent):
    source = QFile(str(Path(__file__).with_name("assets_page_compat.ui")))
    if not source.open(QIODevice.OpenModeFlag.ReadOnly):
        raise RuntimeError(f"Could not load Assets form: {source.errorString()}")
    try:
        form = QUiLoader().load(source, parent)
    finally:
        source.close()
    if form is None:
        raise RuntimeError("Could not load the compatibility Assets form")
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

    controls.update(
        tree=tree, category_search=_asset_widget(form, QLineEdit, "assetCategorySearch"), table=table,
        all=_asset_widget(form, QPushButton, "allAssetsFilterButton"),
        modified=_asset_widget(form, QPushButton, "modifiedAssetsFilterButton"),
        retail=_asset_widget(form, QPushButton, "retailAssetsFilterButton"),
        name=_asset_widget(form, QLabel, "selectedAssetName"),
        description=_asset_widget(form, QLabel, "assetStatus"),
        retail_preview=_asset_widget(form, QLabel, "retailPreview"),
        replacement_preview=_asset_widget(form, QLabel, "modPreview"),
        import_=_asset_widget(form, QPushButton, "replaceSelectedAssetButton"),
        export=_asset_widget(form, QPushButton, "exportAssetButton"),
        remove=_asset_widget(form, QPushButton, "removeReplacementButton"),
        path=_asset_widget(form, QLabel, "assetFilenameValue"),
        size=_asset_widget(form, QLabel, "assetSizeValue"),
        uses=_asset_widget(form, QLabel, "assetMethodValue"),
        state=_asset_widget(form, QLabel, "assetStatus"),
        footer=_asset_widget(form, QLabel, "assetFooterStatus"),
        replacement_info=_asset_widget(form, QLabel, "replacementImageInfoValue"),
    )
    controls["remove"].setEnabled(False)
    _asset_widget(form, QPushButton, "importAssetButton").clicked.connect(lambda: _import_template(self))
    controls["import_"].clicked.connect(lambda: _import_template(self))
    controls["export"].clicked.connect(lambda: _export_template(self))
    _asset_widget(form, QPushButton, "revertAssetButton").clicked.connect(lambda: _remove_template(self))
    controls["remove"].clicked.connect(lambda: _remove_template(self))
    _asset_widget(form, QPushButton, "revertSelectedAssetButton").clicked.connect(lambda: _remove_template(self))
    _asset_widget(form, QPushButton, "openAssetFileButton").clicked.connect(lambda: _open_assets_folder(self))
    _asset_widget(form, QPushButton, "uiModGuideButton").clicked.connect(lambda: _show_asset_help(self))
    _asset_widget(form, QPushButton, "revertAllUiButton").clicked.connect(lambda: _revert_template(self))
    _asset_widget(form, QPushButton, "applyAssetsButton").clicked.connect(self.save_mod)
    _asset_widget(form, QPushButton, "previewAssetsModButton").clicked.connect(lambda: _show_asset_help(self))
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
    else:
        folder = self.project.other.get("assets")
        if not isinstance(folder, str) or not folder:
            folder = "assets"; self.project.other["assets"] = folder
        relative = f"{folder.rstrip('/')}/{asset['name']}.png"
    self.project.files[relative] = pngio.encode(image)
    c.get("preview_image_cache", {}).pop(relative, None)
    self._mark_dirty(); _refresh_template(self)


def _export_template(self):
    asset = self.workspace_controls["Assets"].get("selected")
    if asset is None: return
    image = _named_image(self, _entry_for(self, asset)) or self._asset_retail_image(asset)
    if image is None:
        QMessageBox.warning(self, "Export UI asset", "The retail texture cannot be decoded."); return
    path, _ = QFileDialog.getSaveFileName(self, "Export UI asset", asset["name"].rsplit("/", 1)[-1] + ".png", "PNG images (*.png)")
    if path: pngio.write(path, image)


def _remove_template(self):
    c = self.workspace_controls["Assets"]; asset = c.get("selected")
    path, origin, manifest_entry = _entry_origin(self, asset)
    if path is None: return
    self.project.files.pop(path, None)
    c.get("preview_image_cache", {}).pop(path, None)
    if origin == "pack" and manifest_entry is not None:
        st = art.state(self.project)
        # Removing this first matching manifest entry restores the retail
        # texture read.  Keep the old PNG on disk: it may be shared by an
        # unrelated entry and is harmless when no manifest entry names it.
        st.entries = [entry for entry in st.entries or [] if entry is not manifest_entry]
        st.changed = True
        c.pop("legacy_pack_index", None)
        self._mark_dirty(); _refresh_template(self); return
    folder = self.project.other.get("assets")
    if isinstance(folder, str) and not any(name.startswith(folder.rstrip("/") + "/") for name in self.project.files):
        self.project.other.pop("assets", None)
    self._mark_dirty(); _refresh_template(self)


def _revert_template(self):
    self.project.other.pop("assets", None)
    for name in list(self.project.files):
        if name.startswith("assets/"):
            self.project.files.pop(name)
    self._mark_dirty(); _refresh_template(self)
