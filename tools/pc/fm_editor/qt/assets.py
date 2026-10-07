"""The Assets page: generic texture-pack entries which are not card art."""
from __future__ import annotations

from .common import *      # noqa: F401,F403
from .common import _qimage


class AssetsMixin:
    """Browse and replace the UI texture readings a mod already declares.

    Card pictures remain in the Art page.  This page deliberately operates on
    the texture-pack's other entries unchanged, so its output is the same
    ``textures/manifest.json`` format the game reads.
    """

    def _build_assets_page(self, page, controls):
        c = controls
        # Keep compact keys in the controller, while using the designer's
        # descriptive object names.  This also makes a missing widget fail at
        # build time rather than later when its signal is connected.
        c.update({
            "table": page.findChild(QTableWidget, "assetTable"),
            "categories": page.findChild(QTreeWidget, "assetCategoryTree"),
            "search": page.findChild(QLineEdit, "assetCategorySearch"),
            "all": page.findChild(QPushButton, "allAssetsFilterButton"),
            "modified": page.findChild(QPushButton, "modifiedAssetsFilterButton"),
            "retail": page.findChild(QPushButton, "retailAssetsFilterButton"),
            "import": page.findChild(QPushButton, "importAssetButton"),
            "export": page.findChild(QPushButton, "exportAssetButton"),
            "revert": page.findChild(QPushButton, "revertAssetButton"),
            "replace": page.findChild(QPushButton, "replaceSelectedAssetButton"),
            "revert_selected": page.findChild(QPushButton, "revertSelectedAssetButton"),
            "revert_all": page.findChild(QPushButton, "revertAllUiButton"),
            "apply": page.findChild(QPushButton, "applyAssetsButton"),
            "preview": page.findChild(QPushButton, "previewAssetsModButton"),
            "guide": page.findChild(QPushButton, "uiModGuideButton"),
            "open": page.findChild(QPushButton, "openAssetFileButton"),
            "scale_1": page.findChild(QPushButton, "preview1xButton"),
            "scale_2": page.findChild(QPushButton, "preview2xButton"),
            "scale_4": page.findChild(QPushButton, "preview4xButton"),
        })
        c["mode"] = "all"
        c["scale"] = 2
        c["category"] = ""
        c["entries"] = []
        table = c["table"]
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        table.itemSelectionChanged.connect(self._select_asset)
        c["search"].textChanged.connect(lambda: self._refresh_assets())
        c["categories"].itemClicked.connect(self._asset_category_clicked)
        for mode, button in (("all", c["all"]), ("modified", c["modified"]), ("retail", c["retail"])):
            button.clicked.connect(lambda _=False, value=mode: self._set_asset_mode(value))
        for button in (c["import"], c["replace"]):
            button.clicked.connect(self._import_asset)
        c["export"].clicked.connect(self._export_asset)
        for button in (c["revert"], c["revert_selected"]):
            button.clicked.connect(self._revert_asset)
        c["revert_all"].clicked.connect(self._revert_all_assets)
        c["apply"].clicked.connect(self.save_mod)
        c["preview"].clicked.connect(self.preview_manifest)
        c["guide"].clicked.connect(self._show_assets_guide)
        c["open"].clicked.connect(self._asset_file_location)
        for scale, button in ((1, c["scale_1"]), (2, c["scale_2"]), (4, c["scale_4"])):
            button.clicked.connect(lambda _=False, value=scale: self._set_asset_scale(value))

    def _set_asset_scale(self, scale):
        c = self.workspace_controls["Assets"]
        c["scale"] = scale
        for value in (1, 2, 4):
            c[f"scale_{value}"].setChecked(value == scale)
        self._select_asset()

    @staticmethod
    def _asset_entry(entry):
        """A pack entry that is a stand-alone UI texture, not card artwork."""
        if not isinstance(entry, dict) or art.entry_card(entry) is not None:
            return False
        return (isinstance(entry.get("file"), str) and isinstance(entry.get("archive"), str)
                and all(isinstance(entry.get(key), int) for key in ("offset", "words", "rows", "bpp")))

    def _asset_entries(self):
        st = art.state(self.project)
        return [entry for entry in st.entries or [] if self._asset_entry(entry)]

    def _asset_category_clicked(self, item, _column):
        self.workspace_controls["Assets"]["category"] = item.text(0).lower()
        self._refresh_assets()

    def _set_asset_mode(self, mode):
        c = self.workspace_controls["Assets"]
        c["mode"] = mode
        for key in ("all", "modified", "retail"):
            c[key].setChecked(key == mode)
        self._refresh_assets()

    def _asset_matches_category(self, entry, category):
        if not category or category.startswith("screens"):
            return True
        alias = str(entry.get("alias", "")).lower()
        filename = str(entry.get("file", "")).lower()
        setting = str(entry.get("setting", "")).lower()
        text = " ".join((alias, filename, setting))
        # Portrait names can themselves contain “Guardian”; categories must
        # follow what the texture is, rather than a character's name.
        if category.startswith("portrait"):
            return "portrait" in alias or "portrait" in filename or "portrait" in setting
        if category.startswith("guardian"):
            return "guardian star" in alias or "guardian star" in filename or "guardian" in setting
        words = {
            "title": ("title", "menu"), "card ui": ("card", "frame", "star", "attribute", "atk", "def", "digit"),
            "story": ("story", "scene", "cutscene"), "map": ("map", "overworld"),
            "font": ("font", "text", "glyph"), "api": ("api", "overlay"),
        }
        return any(word in text for prefix, group in words.items() if category.startswith(prefix) for word in group)

    def _refresh_assets(self):
        if "Assets" not in self.workspace_controls:
            return
        c = self.workspace_controls["Assets"]
        table = c["table"]
        chosen = self._selected_asset()
        query = c["search"].text().strip().lower()
        entries = [entry for entry in self._asset_entries()
                   if self._asset_matches_category(entry, c["category"])
                   and (not query or query in " ".join(str(entry.get(k, "")) for k in ("alias", "file", "setting")).lower())]
        # Retail is meaningful for a stock catalog that has not yet been
        # authored; this first page manages declared texture readings, which
        # are all mod entries.
        if c["mode"] == "retail":
            entries = []
        c["entries"] = entries
        table.blockSignals(True)
        table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            label = str(entry.get("alias") or entry["file"])
            method = "Texture pack"
            values = (label, method, "Modified")
            for column, value in enumerate(values):
                cell = QTableWidgetItem(value)
                cell.setData(Qt.ItemDataRole.UserRole, row)
                table.setItem(row, column, cell)
        table.blockSignals(False)
        if chosen in entries:
            table.selectRow(entries.index(chosen))
        elif entries:
            table.selectRow(0)
        self._select_asset()

    def _selected_asset(self):
        c = self.workspace_controls.get("Assets", {})
        table = c.get("table")
        if table is None or not table.selectionModel().hasSelection():
            return None
        row = table.selectionModel().selectedRows()[0].row()
        entries = c.get("entries", [])
        return entries[row] if 0 <= row < len(entries) else None

    def _asset_retail_image(self, entry):
        if str(entry.get("archive", "")).upper() != "WA_MRG.MRG":
            return None
        bpp, clut = entry["bpp"], entry.get("clut_offset")
        if bpp not in (4, 8, 16):
            return None
        try:
            palette = None if bpp == 16 else image_extract.read_palette(
                self.preview_wa, int(clut), int(entry.get("clut_entries", 16 if bpp == 4 else 256)))
            width, height, rgba = image_extract.decode(
                self.preview_wa, entry["offset"], entry["words"], entry["rows"], bpp, palette,
                entry.get("stride"), entry.get("row_offsets"))
            return pngio.Image(width, height, rgba)
        except (IndexError, KeyError, TypeError, ValueError, struct.error):
            return None

    def _asset_mod_image(self, entry):
        st, filename = art.state(self.project), entry.get("file")
        if not isinstance(filename, str):
            return None
        relative = f"{art.pack_dir(self.project)}/{filename}"
        try:
            if relative in self.project.files:
                return pngio.decode(self.project.files[relative])
            folder = st.folder or self.project.source_dir
            return pngio.read(Path(folder) / art.pack_dir(self.project) / filename) if folder else None
        except (OSError, ValueError, pngio.PngError):
            return None

    @staticmethod
    def _asset_native_size(entry):
        """The console texture's dimensions, before an HD PNG is applied."""
        pixels_per_word = {4: 4, 8: 2, 16: 1}.get(entry.get("bpp"), 1)
        return entry["words"] * pixels_per_word, entry["rows"]

    @staticmethod
    def _asset_preview(label, image, empty, width, height):
        # All three columns use the console-sized canvas.  An HD replacement
        # is fitted into it, which makes the Retail/Mod/In game comparison
        # meaningful instead of making each PNG choose its own display size.
        label.setFixedSize(width, height)
        if image is None:
            label.setPixmap(QPixmap())
            label.setText(empty)
            return
        label.setText("")
        pixmap = QPixmap.fromImage(_qimage(image.width, image.height, image.rgba))
        label.setPixmap(pixmap.scaled(width, height, Qt.AspectRatioMode.KeepAspectRatio,
                                      Qt.TransformationMode.FastTransformation))

    def _select_asset(self):
        c = self.workspace_controls.get("Assets", {})
        page, entry = c.get("page"), self._selected_asset()
        if page is None:
            return
        name = page.findChild(QLabel, "selectedAssetName")
        status = page.findChild(QLabel, "assetStatus")
        if entry is None:
            name.setText("No UI asset selected")
            status.setText("No texture-pack UI assets in this mod")
            for label, text in (("retailPreview", "Retail preview"), ("modPreview", "Mod preview"),
                                ("gamePreview", "In-game preview")):
                self._asset_preview(page.findChild(QLabel, label), None, text, 150, 200)
            return
        name.setText(str(entry.get("alias") or entry.get("file")))
        status.setText("Modified by this mod")
        page.findChild(QLabel, "assetMethodValue").setText("Texture pack")
        page.findChild(QLabel, "assetKeyValue").setText('textures: "textures"')
        page.findChild(QLabel, "assetFilenameValue").setText(str(entry.get("file")))
        page.findChild(QLabel, "assetSizeValue").setText(f"{entry['words'] * (4 if entry['bpp'] == 4 else 2)} x {entry['rows']} sheet")
        page.findChild(QLabel, "assetScaleValue").setText("Internal 2x / 4x")
        retail, mod = self._asset_retail_image(entry), self._asset_mod_image(entry)
        scale = c.get("scale", 2)
        native_width, native_height = self._asset_native_size(entry)
        # The comparison slots deliberately never change size.  Retail stays
        # at its disc resolution, Mod uses the source HD PNG, and In game is
        # first reduced to the port's selected internal resolution before it
        # is fitted into the same retail-sized slot.
        game = mod or retail
        if game is not None:
            game = pngio.resample(game, native_width * scale, native_height * scale)
        self._asset_preview(page.findChild(QLabel, "retailPreview"), retail, "Retail preview unavailable", native_width, native_height)
        self._asset_preview(page.findChild(QLabel, "modPreview"), mod, "Mod file unavailable", native_width, native_height)
        self._asset_preview(page.findChild(QLabel, "gamePreview"), game, "In-game preview unavailable", native_width, native_height)

    def _import_asset(self):
        entry = self._selected_asset()
        if entry is None:
            return
        path, _ = QFileDialog.getOpenFileName(self, "Replace UI asset", "", "PNG images (*.png)")
        if not path:
            return
        try:
            image = pngio.read(path)
        except (OSError, ValueError, pngio.PngError) as problem:
            QMessageBox.critical(self, "Could not import UI asset", str(problem))
            return
        original = str(entry.get("file", "asset.png"))
        stem = re.sub(r"[^a-z0-9]+", "-", Path(original).stem.lower()).strip("-") or "asset"
        # Several sheets deliberately use the same source filename.  The
        # texture identity is its image offset and palette, so include both
        # in the replacement name rather than letting one import replace a
        # different sheet's PNG.
        offset = int(entry.get("offset", 0))
        palette = int(entry.get("clut_offset", 0))
        filename = f"ui-assets/{stem}-{offset:x}-{palette:x}.png"
        entry["file"] = filename
        self.project.files[f"{art.pack_dir(self.project)}/{filename}"] = pngio.encode(image)
        art.state(self.project).changed = True
        self._mark_dirty()
        self._refresh_assets()

    def _export_asset(self):
        entry = self._selected_asset()
        if entry is None:
            return
        image = self._asset_mod_image(entry) or self._asset_retail_image(entry)
        if image is None:
            QMessageBox.warning(self, "Export UI asset", "This entry has no readable preview image.")
            return
        default = Path(str(entry.get("file", "asset.png"))).name
        path, _ = QFileDialog.getSaveFileName(self, "Export UI asset", default, "PNG images (*.png)")
        if path:
            pngio.write(path, image)

    def _revert_asset(self):
        entry = self._selected_asset()
        if entry is None:
            return
        state = art.state(self.project)
        filename = entry.get("file")
        if isinstance(filename, str):
            relative = f"{art.pack_dir(self.project)}/{filename}"
            shared = any(other is not entry and other.get("file") == filename
                         for other in state.entries or [] if isinstance(other, dict))
            if not shared:
                self.project.files.pop(relative, None)
                self.project.removed_files.add(relative)
        state.entries.remove(entry)
        state.changed = True
        self._mark_dirty()
        self._refresh_assets()

    def _revert_all_assets(self):
        entries = self._asset_entries()
        if not entries:
            return
        if QMessageBox.question(self, "Revert all UI assets", f"Remove {len(entries)} UI texture replacement(s)?") != QMessageBox.StandardButton.Yes:
            return
        state = art.state(self.project)
        removed_files = getattr(self.project, "removed_files", None)
        if removed_files is None:
            removed_files = self.project.removed_files = set()
        for entry in entries:
            filename = entry.get("file")
            if isinstance(filename, str):
                relative = f"{art.pack_dir(self.project)}/{filename}"
                self.project.files.pop(relative, None)
                removed_files.add(relative)
            state.entries.remove(entry)
        state.changed = True
        self._mark_dirty()
        self._refresh_assets()

    def _asset_file_location(self):
        entry = self._selected_asset()
        if entry is not None:
            QMessageBox.information(self, "UI asset file", f"textures/{entry.get('file', '')}")

    def _show_assets_guide(self):
        QMessageBox.information(self, "UI mod guide",
            "UI assets are texture-pack readings. Import a PNG to replace the selected reading; save writes it under textures/ and updates textures/manifest.json.")
