"""Terrain-bonus workspace for the modern editor.

The field-art and duel-texture machinery remains here for the dedicated
field-art workspace, but it is deliberately not exposed by this page.  This
workspace is only for the terrain-bonus table written to ``mod.json``.
"""
from __future__ import annotations

from pathlib import Path

from .common import *  # noqa: F401,F403
from .common import _qimage
from .. import art, kit, pngio


FIELDS = tuple(enumerate(kit.TERRAIN_NAMES, start=1))
FIELD_CARDS = {1: 330, 2: 331, 3: 332, 4: 333, 5: 334, 6: 335}

# The seven arenas are texture sheets in WA_MRG.MRG, not the six field spell
# card illustrations.  Each arena has five floor palettes and ten palettes
# for its platform sides and trim.  These are the exact readings used by the
# HD texture pack, so saved replacements work in the port and alongside it.
_FIELD_TEXTURE_BASES = {
    "Forest": ("forest", 0xC3E000, 0xC45F00, 0xC46000, 0xC4D120),
    "Wasteland": ("wasteland", 0xCB3800, 0xCBB700, 0xCBB800, 0xCC2920),
    "Mountain": ("mountain", 0xD29000, 0xD30F00, 0xD31000, 0xD38120),
    # The game's field-card names differ from the HD pack's arena names.
    "Sogen": ("meadow", 0xD9E800, 0xDA6700, 0xDA6800, 0xDAD920),
    "Umi": ("sea", 0xE14000, 0xE1BF00, 0xE1C000, 0xE23120),
    "Yami": ("dark", 0xE89800, 0xE91700, 0xE91800, 0xE98920),
}
_TRIM_CLUT_DELTAS = (0x00, 0x20, 0x40, 0x60, 0x80, 0xE0, 0x100, 0x120, 0x140, 0x160)


def _field_textures(field_name):
    """The individual duel texture readings for one terrain."""
    slug, floor_offset, floor_clut, trim_offset, trim_clut = _FIELD_TEXTURE_BASES[field_name]
    common = {"archive": "WA_MRG.MRG", "words": 64, "rows": 256, "bpp": 4,
              "clut_entries": 16, "stride": 64, "row_offsets": None,
              "width": 256, "height": 256, "crop_left": 0, "setting": "duel"}
    textures = []
    for band in range(5):
        textures.append(dict(common, offset=floor_offset, clut_offset=floor_clut + band * 0x20,
            file=f"fields/{slug}-floor-{band + 1}.png",
            alias=f"Duel field: {slug} floor tiles, band {band + 1}",
            label=f"Floor tiles · band {band + 1}"))
    for palette, delta in enumerate(_TRIM_CLUT_DELTAS):
        textures.append(dict(common, offset=trim_offset, clut_offset=trim_clut + delta,
            file=f"fields/{slug}-trim-{palette + 1}.png",
            alias=f"Duel field: {slug} platform sides and trim, palette {palette + 1}",
            label=f"Platform trim · palette {palette + 1}"))
    return textures


def _same_texture(entry, texture):
    return isinstance(entry, dict) and all(entry.get(key) == texture[key] for key in
        ("archive", "offset", "words", "rows", "bpp", "clut_offset", "clut_entries"))


def _texture_replacement(editor, texture):
    return next((entry for entry in art.state(editor.project).entries or []
                 if _same_texture(entry, texture)), None)


def _retail_texture(editor, texture):
    try:
        palette = image_extract.read_palette(editor.preview_wa, texture["clut_offset"], texture["clut_entries"])
        width, height, rgba = image_extract.decode(editor.preview_wa, texture["offset"], texture["words"],
            texture["rows"], texture["bpp"], palette, texture["stride"], texture["row_offsets"])
        return pngio.Image(width, height, rgba)
    except (IndexError, KeyError, TypeError, ValueError, struct.error):
        return None


def _texture_image(editor, texture):
    entry = _texture_replacement(editor, texture)
    if entry is not None and isinstance(entry.get("file"), str):
        relative = f"{art.pack_dir(editor.project)}/{entry['file']}"
        try:
            if relative in editor.project.files:
                return pngio.decode(editor.project.files[relative])
            folder = art.state(editor.project).folder or editor.project.source_dir
            if folder is not None:
                return pngio.read(Path(folder) / relative)
        except (OSError, ValueError, pngio.PngError):
            pass
    return _retail_texture(editor, texture)


def _duel_field_preview(editor, field_name):
    """Compose the top, centre, and lower board strips shown in a duel."""
    layers = _field_textures(field_name)
    source = [_texture_image(editor, layers[index]) for index in (0, 1, 2)]
    if any(image is None for image in source):
        return None
    board = QImage(256, 240, QImage.Format.Format_RGBA8888)
    board.fill(QColor("#0b1725"))
    painter = QPainter(board)
    # These are the screen strips from the three floor palettes: upper board,
    # the narrow centre band, and lower board.  Crop in source coordinates so
    # an HD replacement still displays at the console-sized field geometry.
    pieces = ((source[0], 0, 0, 104, 0, 104),
              (source[1], 0, 224, 32, 104, 32),
              (source[2], 0, 104, 104, 136, 104))
    for image, left, top, height, target_top, target_height in pieces:
        qimage = _qimage(image.width, image.height, image.rgba)
        scale_x, scale_y = qimage.width() / 256, qimage.height() / 256
        crop = qimage.copy(round(left * scale_x), round(top * scale_y),
                           max(1, round(256 * scale_x)), max(1, round(height * scale_y)))
        painter.drawImage(QRect(0, target_top, 256, target_height), crop)
    painter.end()
    return board


def _load_form(parent):
    source = QFile(str(Path(__file__).resolve().parents[1] / "ui" / "fields_page.ui"))
    if not source.open(QIODevice.OpenModeFlag.ReadOnly):
        raise RuntimeError(f"Could not load Fields form: {source.errorString()}")
    try:
        form = QUiLoader().load(source, parent)
    finally:
        source.close()
    if form is None:
        raise RuntimeError("Could not load the Fields compatibility form")
    return form


def _get(form, kind, name):
    value = form.findChild(kind, name)
    if value is None:
        raise RuntimeError(f"Fields form is missing {name!r}")
    return value


def _retail_bonus(editor, field_id, type_id):
    """The disc executable's signed-byte terrain table, in points."""
    try:
        value = kit.Memory(editor.files.slus).s8(
            kit.TERRAIN_BOOST + type_id * len(FIELDS) + field_id - 1)
        return int(value or 0) * 10
    except (AttributeError, IndexError, TypeError, ValueError):
        return 0


def _terrain_values(editor, field_name):
    raw = _terrain_table(editor)
    values = raw.get(field_name)
    return values if isinstance(values, dict) else {}


def _terrain_table(editor):
    raw = getattr(editor.project, "other", {}).get("terrain_bonus")
    return raw if isinstance(raw, dict) else {}


def _effective_bonus(editor, field_id, field_name, type_id):
    values = _terrain_values(editor, field_name)
    name = TYPE_NAMES[type_id]
    if name in values and isinstance(values[name], int):
        return values[name]
    replace = bool(_terrain_table(editor).get("replace"))
    return 0 if replace else _retail_bonus(editor, field_id, type_id)


def _field_changed(editor, field_name):
    table = _terrain_table(editor)
    return isinstance(table, dict) and (bool(table.get("replace")) or bool(table.get(field_name)))


def _render_preview(editor, field_id):
    c = editor.workspace_controls.get("Fields", {})
    label = c.get("preview")
    if label is None:
        return
    field_name = dict(FIELDS)[field_id]
    image = _duel_field_preview(editor, field_name)
    if image is None:
        label.setPixmap(QPixmap())
        label.setText("In-duel field texture unavailable")
        return
    pixmap = QPixmap.fromImage(image)
    label.setText("")
    label.setPixmap(pixmap.scaled(label.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                  Qt.TransformationMode.FastTransformation))


def _refresh_texture_controls(editor):
    c = editor.workspace_controls.get("Fields", {})
    combo = c.get("textures")
    field_id = c.get("field_id")
    if combo is None or not field_id:
        return
    current = combo.currentData()
    textures = _field_textures(dict(FIELDS)[field_id])
    combo.blockSignals(True)
    combo.clear()
    for index, texture in enumerate(textures):
        status = "Changed" if _texture_replacement(editor, texture) else "Retail"
        combo.addItem(f"{texture['label']} · {status}", index)
    if isinstance(current, int) and 0 <= current < len(textures):
        combo.setCurrentIndex(current)
    combo.blockSignals(False)


def _selected_texture(editor):
    c = editor.workspace_controls.get("Fields", {})
    field_id, combo = c.get("field_id"), c.get("textures")
    if not field_id or combo is None:
        return None
    index = combo.currentData()
    textures = _field_textures(dict(FIELDS)[field_id])
    return textures[index] if isinstance(index, int) and 0 <= index < len(textures) else None


def _import_texture(editor):
    texture = _selected_texture(editor)
    if texture is None:
        return
    path, _ = QFileDialog.getOpenFileName(editor, "Replace duel field texture", "", "PNG images (*.png)")
    if not path:
        return
    try:
        image = pngio.read(path)
    except (OSError, ValueError, pngio.PngError) as problem:
        QMessageBox.critical(editor, "Could not replace duel field texture", str(problem)); return
    state = art.state(editor.project)
    entry = _texture_replacement(editor, texture)
    file = texture["file"]
    if entry is None:
        entry = dict(texture)
        state.entries = list(state.entries or [])
        # The game chooses the first matching texture reading.  Put a new
        # editor override before an existing gated entry, if any.
        state.entries.insert(0, entry)
    else:
        entry["file"] = file
        entry.pop("label", None)
    editor.project.files[f"{art.pack_dir(editor.project)}/{file}"] = pngio.encode(image)
    state.changed = True
    editor._mark_dirty()
    _select_field(editor, editor.workspace_controls["Fields"]["field_id"])


def _export_texture(editor):
    texture = _selected_texture(editor)
    if texture is None:
        return
    image = _texture_image(editor, texture)
    if image is None:
        QMessageBox.warning(editor, "Export duel field texture", "This texture cannot be decoded."); return
    path, _ = QFileDialog.getSaveFileName(editor, "Export duel field texture", Path(texture["file"]).name,
                                          "PNG images (*.png)")
    if path:
        pngio.write(path, image)


def _revert_texture(editor):
    texture = _selected_texture(editor)
    if texture is None:
        return
    state = art.state(editor.project)
    entry = _texture_replacement(editor, texture)
    if entry is None:
        return
    file = entry.get("file")
    state.entries.remove(entry)
    if isinstance(file, str):
        editor.project.files.pop(f"{art.pack_dir(editor.project)}/{file}", None)
    state.changed = True
    editor._mark_dirty()
    _select_field(editor, editor.workspace_controls["Fields"]["field_id"])


def _select_field(editor, field_id):
    c = editor.workspace_controls.get("Fields", {})
    if not c:
        return
    field_name = dict(FIELDS)[field_id]
    c["field_id"] = field_id
    changed = _field_changed(editor, field_name)
    c["field_summary"].setText(f"Selected field: <b>{field_name}</b>")
    c["field_state"].setText("State: Changed" if changed else "State: Stock")
    c["field_state"].setStyleSheet("color:#6bdd9a" if changed else "color:#aebfd6")
    _refresh_field_table(editor)
    _refresh_bonus_table(editor)


def _refresh_field_table(editor):
    c = editor.workspace_controls.get("Fields", {})
    table = c.get("fields")
    if table is None:
        return
    selected = c.get("field_id", 1)
    held = sort_paused(table)
    previous = table.blockSignals(True)
    table.setRowCount(len(FIELDS))
    for row, (field_id, field_name) in enumerate(FIELDS):
        changed = _field_changed(editor, field_name)
        values = (str(field_id), field_name, "Changed" if changed else "Stock")
        for column, value in enumerate(values):
            item = QTableWidgetItem(value)
            if column == 0:
                item.setData(Qt.ItemDataRole.UserRole, field_id)
            if column == 2:
                item.setForeground(QColor("#6bdd9a") if changed else QColor("#aebfd6"))
            table.setItem(row, column, item)
    sort_resumed(table, held)
    for row in range(table.rowCount()):
        item = table.item(row, 0)
        if item is not None and item.data(Qt.ItemDataRole.UserRole) == selected:
            table.selectRow(row)
            break
    table.blockSignals(previous)


def _refresh_bonus_table(editor):
    c = editor.workspace_controls.get("Fields", {})
    if not c or not c.get("field_id"):
        return
    field_id = c["field_id"]
    field_name = dict(FIELDS)[field_id]
    values = _terrain_values(editor, field_name)
    table = c["bonuses"]
    selected_types = set(c.get("type_ids", (c.get("type_id", 0),)))
    for row in {item.row() for item in table.selectedItems()}:
        current_type = table.item(row, 0)
        if current_type is not None:
            selected_types.add(current_type.data(Qt.ItemDataRole.UserRole))
    held = sort_paused(table)
    table.blockSignals(True)
    table.setRowCount(20)
    for type_id, type_name in enumerate(TYPE_NAMES[:20]):
        retail = _retail_bonus(editor, field_id, type_id)
        overridden = values.get(type_name)
        effective = _effective_bonus(editor, field_id, field_name, type_id)
        columns = (type_name, f"{retail:+d}", "—" if overridden is None else f"{overridden:+d}",
                   f"{effective:+d}")
        for column, value in enumerate(columns):
            item = QTableWidgetItem(value)
            if column == 0:
                item.setData(Qt.ItemDataRole.UserRole, type_id)
                item.setIcon(type_icon(editor, type_id))
            if column == 2 and overridden is not None:
                item.setForeground(QColor("#6bdd9a"))
            if column == 3:
                item.setForeground(QColor("#f2cd58") if effective > 0 else
                                   QColor("#ff8998") if effective < 0 else QColor("#aebfd6"))
            table.setItem(type_id, column, item)
    table.blockSignals(False)
    sort_resumed(table, held)
    table.clearSelection()
    for row in range(table.rowCount()):
        item = table.item(row, 0)
        if item is not None and item.data(Qt.ItemDataRole.UserRole) in selected_types:
            for column in range(table.columnCount()):
                cell = table.item(row, column)
                if cell is not None:
                    cell.setSelected(True)
    _select_bonus(editor)


def _select_bonus(editor):
    c = editor.workspace_controls.get("Fields", {})
    row = c.get("bonuses").currentRow() if c.get("bonuses") else -1
    if row < 0 or not c.get("field_id"):
        return
    field_id, field_name = c["field_id"], dict(FIELDS)[c["field_id"]]
    selected = {int(c["bonuses"].item(selected_row, 0).data(Qt.ItemDataRole.UserRole))
                for selected_row in {item.row() for item in c["bonuses"].selectedItems()}
                if c["bonuses"].item(selected_row, 0) is not None}
    type_id = int(c["bonuses"].item(row, 0).data(Qt.ItemDataRole.UserRole))
    c["type_ids"] = selected or {type_id}
    c["type_id"] = type_id
    if len(c["type_ids"]) == 1:
        c["type"].setText(TYPE_NAMES[type_id])
        c["type_icon"].setPixmap(type_icon(editor, type_id).pixmap(QSize(52, 52)))
    else:
        c["type"].setText(f"{len(c['type_ids'])} types selected")
        c["type_icon"].setPixmap(QPixmap())
    c["spin"].blockSignals(True)
    c["spin"].setValue(_effective_bonus(editor, field_id, field_name, type_id))
    c["spin"].blockSignals(False)


def _set_bonus(editor, value=None, retail=False, clear=False):
    c = editor.workspace_controls["Fields"]
    if not c.get("field_id") or c.get("type_id") is None:
        return
    field_id = c["field_id"]
    field_name = dict(FIELDS)[field_id]
    table = editor.project.other.setdefault("terrain_bonus", {})
    if not isinstance(table, dict):
        editor.project.other["terrain_bonus"] = table = {}
    values = table.setdefault(field_name, {})
    for type_id in c.get("type_ids", {c["type_id"]}):
        type_name = TYPE_NAMES[type_id]
        if clear:
            values.pop(type_name, None)
        else:
            values[type_name] = _retail_bonus(editor, field_id, type_id) if retail else int(value)
    if not values:
        table.pop(field_name, None)
    if not table:
        editor.project.other.pop("terrain_bonus", None)
    editor._mark_dirty()
    _select_field(editor, field_id)


def _revert_field(editor):
    c = editor.workspace_controls["Fields"]
    field_id = c.get("field_id")
    if not field_id:
        return
    table = editor.project.other.get("terrain_bonus")
    if isinstance(table, dict):
        table.pop(dict(FIELDS)[field_id], None)
        if not table:
            editor.project.other.pop("terrain_bonus", None)
    editor._mark_dirty()
    _select_field(editor, field_id)


def _revert_all(editor):
    editor.project.other.pop("terrain_bonus", None)
    editor._mark_dirty()
    _select_field(editor, editor.workspace_controls["Fields"].get("field_id", 1))


def _set_replace(editor, checked):
    table = editor.project.other.setdefault("terrain_bonus", {})
    if not isinstance(table, dict):
        editor.project.other["terrain_bonus"] = table = {}
    if checked:
        table["replace"] = True
    else:
        table.pop("replace", None)
    if not table:
        editor.project.other.pop("terrain_bonus", None)
    editor._mark_dirty()
    _select_field(editor, editor.workspace_controls["Fields"].get("field_id", 1))


def _refresh_fields(editor):
    c = editor.workspace_controls.get("Fields", {})
    if not c:
        return
    replace = bool(_terrain_table(editor).get("replace"))
    c["replace"].blockSignals(True)
    c["replace"].setChecked(replace)
    c["replace"].blockSignals(False)
    _select_field(editor, c.get("field_id", 1))


def _build_fields(editor, parent):
    layout = parent.layout() or QVBoxLayout(parent)
    layout.setContentsMargins(0, 0, 0, 0)
    form = _load_form(parent)
    layout.addWidget(form)
    fields = _get(form, QTableWidget, "fieldTable")
    c = {
        "page": form, "form": form, "fields": fields,
        "field_summary": _get(form, QLabel, "selectedFieldSummaryLabel"),
        "field_state": _get(form, QLabel, "fieldStateLabel"),
        "bonuses": _get(form, QTableWidget, "terrainBonusTable"),
        "type": _get(form, QLabel, "selectedMonsterTypeLabel"),
        "type_icon": _get(form, QLabel, "selectedMonsterTypeIcon"),
        "spin": _get(form, QSpinBox, "terrainBonusSpinBox"),
        "replace": _get(form, QCheckBox, "replaceTerrainBonusesCheckBox"),
        "field_id": 1, "type_id": 0,
    }
    editor.workspace_forms["Fields"] = form
    editor.workspace_controls["Fields"] = c
    fields.setColumnCount(3)
    fields.setHorizontalHeaderLabels(["ID", "Field", "State"])
    fields.verticalHeader().setVisible(False)
    fields.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
    fields.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
    fields.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
    table = c["bonuses"]
    table.setColumnCount(4)
    table.setHorizontalHeaderLabels(["Monster type", "Retail", "Mod", "In-game"])
    table.verticalHeader().setVisible(False)
    table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    for column in (1, 2, 3):
        table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
    fields.itemSelectionChanged.connect(
        lambda: _select_field(editor, int(fields.item(fields.currentRow(), 0).data(Qt.ItemDataRole.UserRole)))
        if fields.currentRow() >= 0 and fields.item(fields.currentRow(), 0) is not None else None)
    table.itemSelectionChanged.connect(lambda: _select_bonus(editor))
    _get(form, QPushButton, "setTerrainBonusButton").clicked.connect(
        lambda: _set_bonus(editor, c["spin"].value()))
    _get(form, QPushButton, "useRetailTerrainBonusButton").clicked.connect(
        lambda: _set_bonus(editor, retail=True))
    _get(form, QPushButton, "clearTerrainBonusButton").clicked.connect(
        lambda: _set_bonus(editor, clear=True))
    _get(form, QPushButton, "revertFieldButton").clicked.connect(lambda: _revert_field(editor))
    _get(form, QPushButton, "revertAllFieldsButton").clicked.connect(lambda: _revert_all(editor))
    _get(form, QPushButton, "applyFieldsButton").clicked.connect(lambda: _set_bonus(editor, c["spin"].value()))
    c["replace"].toggled.connect(lambda checked: _set_replace(editor, checked))
    _refresh_fields(editor)


def install():
    """Add the branch-only Fields workspace without modifying classic files."""
    from .window import ModernEditor
    if getattr(ModernEditor, "_fields_compat_installed", False):
        return
    ModernEditor._fields_compat_installed = True
    ModernEditor.NAV = [*ModernEditor.NAV[:4], "Fields", *ModernEditor.NAV[4:]]
    original_build = ModernEditor._build_workspace_page
    original_refresh = ModernEditor._refresh_workspace

    def build(self, name, parent):
        if name == "Fields":
            _build_fields(self, parent)
            return
        return original_build(self, name, parent)

    def refresh(self, name):
        if name == "Fields":
            _refresh_fields(self)
            return
        return original_refresh(self, name)

    ModernEditor._build_workspace_page = build
    ModernEditor._refresh_workspace = refresh
