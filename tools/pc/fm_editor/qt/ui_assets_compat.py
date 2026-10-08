"""Use the modern editor's Assets entry as PR #297's UI / Graphics page.

This compatibility module stays separate from master-tracked editor files.
"""
from __future__ import annotations

from .common import *  # noqa: F401,F403
from .common import _qimage
import json
import re

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
        _clear(layout); layout.setContentsMargins(18, 14, 18, 14); layout.setSpacing(10)
        _heading(layout, "UI / Graphics", "Title, menus and duel graphics. This replaces the former texture-pack browser in the Assets workspace.")
        return _build_framework(self, page, controls, layout)

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
    def refresh(self): _refresh_framework(self)

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
    """The catalog folder is the category; do not invent editor-only groups."""
    return name.split("/", 1)[0]


def _entry_for(self, asset):
    folder = self.project.other.get("assets")
    if not isinstance(folder, str) or not folder: return None
    relative = f"{folder.rstrip('/')}/{asset['name']}.png"
    if relative in self.project.files: return relative
    source = self.project.source_dir
    return relative if source and (Path(source) / relative).is_file() else None


def _named_image(self, relative):
    if not relative: return None
    try:
        if relative in self.project.files: return pngio.decode(self.project.files[relative])
        return pngio.read(Path(self.project.source_dir) / relative) if self.project.source_dir else None
    except (OSError, ValueError, pngio.PngError):
        return None


def _build_framework(self, page, controls, layout):
    catalog = _catalog()
    categories = sorted({item["name"].split("/", 1)[0] for item in catalog}, key=str.casefold)
    controls.clear(); controls.update(page=page, catalog=catalog, category=categories[0] if categories else "", selected=None)
    self.workspace_controls["Assets"] = controls
    if hasattr(self, "nav_buttons") and "Assets" in self.nav_buttons: self.nav_buttons["Assets"].setText("UI / Graphics")
    root = QSplitter(Qt.Orientation.Horizontal); root.setChildrenCollapsible(False); layout.addWidget(root, 1)
    category_box = QGroupBox("Asset categories")
    category_layout = QVBoxLayout(category_box); categories_view = QListWidget(); categories_view.setMinimumWidth(170); categories_view.setSpacing(3)
    controls["categories"] = categories_view
    for name in categories: categories_view.addItem(name)
    categories_view.setCurrentRow(0); category_layout.addWidget(categories_view); root.addWidget(category_box)
    centre = QWidget(); centre_layout = QVBoxLayout(centre); centre_layout.setContentsMargins(10, 0, 10, 0)
    controls["grid_heading"] = QLabel(); controls["grid_heading"].setObjectName("heading"); centre_layout.addWidget(controls["grid_heading"])
    search = _line("Search assets…"); controls["search"] = search; centre_layout.addWidget(search)
    grid = QListWidget(); grid.setViewMode(QListView.ViewMode.IconMode); grid.setResizeMode(QListView.ResizeMode.Adjust); grid.setMovement(QListView.Movement.Static); grid.setIconSize(QSize(112, 112)); grid.setGridSize(QSize(142, 154)); grid.setSpacing(8)
    controls["grid"] = grid; centre_layout.addWidget(grid, 1); root.addWidget(centre)
    detail = QWidget(); detail.setMinimumWidth(520); detail_layout = QVBoxLayout(detail); detail_layout.setContentsMargins(0, 0, 0, 0)
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
    detail_layout.addWidget(info); detail_layout.addStretch(1); root.addWidget(detail); root.setSizes([205, 470, 665])
    categories_view.currentTextChanged.connect(lambda value: _set_category(self, value)); search.textChanged.connect(lambda *_: _refresh_framework(self)); grid.currentItemChanged.connect(lambda item, _: _select_framework(self, item.data(Qt.ItemDataRole.UserRole) if item else None))
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
    c["grid_heading"].setText(f"Assets in {category}")
    grid = c["grid"]; previous = c.get("selected"); grid.blockSignals(True); grid.clear()
    for asset in values:
        item = QListWidgetItem(asset["name"].rsplit("/", 1)[-1].replace("_", " "))
        item.setData(Qt.ItemDataRole.UserRole, asset)
        retail = self._asset_retail_image(asset)
        if retail is not None: item.setIcon(QIcon(QPixmap.fromImage(_qimage(retail.width, retail.height, retail.rgba)).scaled(112, 112, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation)))
        grid.addItem(item)
        if previous and previous.get("name") == asset["name"]: grid.setCurrentItem(item)
    grid.blockSignals(False)
    if grid.currentItem() is None and grid.count(): grid.setCurrentRow(0)
    if not grid.count(): _select_framework(self, None)


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
