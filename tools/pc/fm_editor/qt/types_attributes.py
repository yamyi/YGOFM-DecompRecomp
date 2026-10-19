"""The Types & Attributes page: add, rename, remove and give a custom icon
to card types and attributes (cards.c add_card_types_section, attributes.c
Attributes_Add -- both accept an optional per-declaration "icon", a PNG path
inside the mod, and both treat a declaration without one as clearing an
earlier mod's icon rather than keeping it under a new name).

Types live in project.type_names/project.type_icons (model.Project);
attributes have no project-level cache, so they are read and written straight
from project.other["attributes"], the same raw section manifest.py's
_attribute_registry() already resolves everywhere else."""
from __future__ import annotations

from pathlib import Path

from .common import *      # noqa: F401,F403
from .common import _qimage
from .. import pngio
from ..gamedata import TYPE_LIMIT

_KEEP = object()           # _apply_type/_apply_attribute: leave the icon as it is


class TypesAttributesMixin:
    def _build_types_attributes_page(self, page, get, controls):
        controls.update(types_tree=get(QTreeWidget, "typesTree"),
                        attributes_tree=get(QTreeWidget, "attributesTree"),
                        types_icon_preview=get(QLabel, "typesIconPreview"),
                        types_icon_path=get(QLabel, "typesIconPathLabel"),
                        attributes_icon_preview=get(QLabel, "attributesIconPreview"),
                        attributes_icon_path=get(QLabel, "attributesIconPathLabel"))
        self.type_icon_cache = {}
        self.attribute_icon_cache = {}
        for tree in (controls["types_tree"], controls["attributes_tree"]):
            tree.setRootIsDecorated(False)
            header = tree.header()
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
            header.resizeSection(0, 60)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
            header.resizeSection(2, 80)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
            header.resizeSection(3, 140)
        controls["types_tree"].itemDoubleClicked.connect(lambda *_: self._edit_type())
        controls["attributes_tree"].itemDoubleClicked.connect(lambda *_: self._edit_attribute())
        controls["types_tree"].itemSelectionChanged.connect(self._show_type_icon)
        controls["attributes_tree"].itemSelectionChanged.connect(self._show_attribute_icon)
        get(QPushButton, "typesAddButton").clicked.connect(self._add_type)
        get(QPushButton, "typesEditButton").clicked.connect(self._edit_type)
        get(QPushButton, "typesRemoveButton").clicked.connect(self._remove_type)
        get(QPushButton, "typesImportIconButton").clicked.connect(self._import_type_icon)
        get(QPushButton, "typesExportIconButton").clicked.connect(self._export_type_icon)
        get(QPushButton, "typesRemoveIconButton").clicked.connect(self._remove_type_icon)
        get(QPushButton, "attributesAddButton").clicked.connect(self._add_attribute)
        get(QPushButton, "attributesEditButton").clicked.connect(self._edit_attribute)
        get(QPushButton, "attributesRemoveButton").clicked.connect(self._remove_attribute)
        get(QPushButton, "attributesImportIconButton").clicked.connect(self._import_attribute_icon)
        get(QPushButton, "attributesExportIconButton").clicked.connect(self._export_attribute_icon)
        get(QPushButton, "attributesRemoveIconButton").clicked.connect(self._remove_attribute_icon)

    def _refresh_types_attributes(self):
        c = self.workspace_controls.get("Types & Attributes")
        if c is None:
            return
        # Every other list that shows a type/attribute icon (Cards, its
        # filters, Equips, Starter decks, Packs, ...) caches it by id through
        # common.type_icon/attribute_icon; an edit here can change what that
        # id resolves to, so those caches -- and this page's own preview
        # cache -- must not keep answering with what it used to be.
        self.type_icon_cache.clear()
        self.attribute_icon_cache.clear()
        forget_icon_caches(self)
        c["types_tree"].clear()
        for id_, name, origin in self._type_rows():
            item = QTreeWidgetItem([str(id_), name, "", origin])
            item.setIcon(2, self._type_display_icon(id_))
            item.setData(0, Qt.ItemDataRole.UserRole, id_)
            c["types_tree"].addTopLevelItem(item)
        c["attributes_tree"].clear()
        for id_, name, origin in self._attribute_rows():
            item = QTreeWidgetItem([str(id_), name, "", origin])
            item.setIcon(2, self._attribute_display_icon(id_))
            item.setData(0, Qt.ItemDataRole.UserRole, id_)
            c["attributes_tree"].addTopLevelItem(item)
        self._show_type_icon()
        self._show_attribute_icon()

    def _type_display_icon(self, id_):
        """The custom icon where one is declared, else the retail symbol
        (common.type_icon) -- the same fallback guardian_star_icon uses."""
        custom = self.project.type_icons.get(id_)
        if custom:
            pixmap = self._icon_pixmap(self.type_icon_cache, custom)
            if pixmap is not None:
                return QIcon(pixmap)
        return type_icon(self, id_)

    def _attribute_display_icon(self, id_):
        custom = self._attribute_icon(id_)
        if custom:
            pixmap = self._icon_pixmap(self.attribute_icon_cache, custom)
            if pixmap is not None:
                return QIcon(pixmap)
        return attribute_icon(self, id_)

    def _selected_id(self, tree):
        item = tree.currentItem()
        return item.data(0, Qt.ItemDataRole.UserRole) if item is not None else None

    def _icon_pixmap(self, cache, path, side=36):
        if not path:
            return None
        if path not in cache:
            try:
                if path in self.project.files:
                    image = pngio.decode(self.project.files[path])
                elif self.project.source_dir:
                    image = pngio.read(Path(self.project.source_dir) / path)
                else:
                    image = None
            except (OSError, pngio.PngError, ValueError):
                image = None
            cache[path] = image
        image = cache[path]
        if image is None:
            return None
        image = pngio.resample(image, side, side)
        return QPixmap.fromImage(_qimage(image.width, image.height, image.rgba))

    def _show_icon(self, path, cache, fallback, preview, path_label):
        """path is the declaration's own custom icon, if any; fallback is the
        retail symbol (type_icon/attribute_icon) to show otherwise -- the
        page would read as broken next to Cards, which always shows that
        symbol, if a retail row showed nothing just for lacking an override."""
        pixmap = self._icon_pixmap(cache, path)
        if pixmap is not None:
            preview.setPixmap(pixmap)
            preview.setText("")
            path_label.setText(path)
        elif fallback is not None and not fallback.isNull():
            preview.setPixmap(fallback.pixmap(36, 36))
            preview.setText("")
            path_label.setText("Retail icon (no custom override)")
        else:
            preview.setPixmap(QPixmap())
            preview.setText("—")
            path_label.setText("No icon")

    # --- types ------------------------------------------------------------

    def _type_rows(self):
        names = self.project.type_names
        rows = []
        for id_ in range(TYPE_LIMIT):
            name = names[id_] if id_ < len(names) else None
            if id_ < len(TYPE_NAMES):
                origin = "Retail" if name == TYPE_NAMES[id_] else "Renamed retail"
                name = name or TYPE_NAMES[id_]
            else:
                if not name:
                    continue
                origin = "Custom"
            rows.append((id_, name, origin))
        return rows

    def _show_type_icon(self):
        c = self.workspace_controls["Types & Attributes"]
        id_ = self._selected_id(c["types_tree"])
        path = self.project.type_icons.get(id_) if id_ is not None else None
        fallback = type_icon(self, id_) if id_ is not None else None
        self._show_icon(path, self.type_icon_cache, fallback, c["types_icon_preview"], c["types_icon_path"])

    def _next_free_type_id(self):
        names = self.project.type_names
        for id_ in range(len(TYPE_NAMES), TYPE_LIMIT):
            if id_ >= len(names) or not names[id_]:
                return id_
        return len(TYPE_NAMES)

    def _add_type(self):
        id_, ok = QInputDialog.getInt(self, "Add type", "Numeric ID (24-255):",
                                       self._next_free_type_id(), len(TYPE_NAMES), TYPE_LIMIT - 1)
        if not ok:
            return
        name, ok = QInputDialog.getText(self, "Add type", "Display name:")
        if not ok or not name.strip():
            return
        self._apply_type(id_, name.strip(), icon=None)

    def _edit_type(self):
        id_ = self._selected_id(self.workspace_controls["Types & Attributes"]["types_tree"])
        if id_ is None:
            return
        current = self.project.type_names[id_] or (TYPE_NAMES[id_] if id_ < len(TYPE_NAMES) else "")
        name, ok = QInputDialog.getText(self, "Rename type", "Display name:", text=current)
        if not ok or not name.strip():
            return
        self._apply_type(id_, name.strip())

    def _apply_type(self, id_, name, icon=_KEEP):
        if icon is _KEEP:
            icon = self.project.type_icons.get(id_)
        entry = {"id": id_, "name": name}
        if icon:
            entry["icon"] = icon
        messages = []
        manifest.read_card_types(self.project, {"types": [entry]}, messages)
        if messages:
            QMessageBox.critical(self, "Type", "\n".join(messages))
            return False
        self._mark_dirty()
        self._refresh_types_attributes()
        return True

    def _remove_type(self):
        c = self.workspace_controls["Types & Attributes"]
        id_ = self._selected_id(c["types_tree"])
        if id_ is None:
            return
        self._discard_type_icon_file(self.project.type_icons.get(id_), except_id=id_)
        self.project.type_icons.pop(id_, None)
        if id_ < len(TYPE_NAMES):
            self.project.type_names[id_] = TYPE_NAMES[id_]
        else:
            self.project.type_names[id_] = None
        self.type_icon_cache.clear()
        self._mark_dirty()
        self._refresh_types_attributes()

    def _discard_type_icon_file(self, icon, except_id=None):
        """Drop a mod file only after the last type stops using it."""
        if not icon:
            return
        if any(id_ != except_id and path == icon for id_, path in self.project.type_icons.items()):
            return
        self.project.files.pop(icon, None)

    def _import_type_icon(self):
        c = self.workspace_controls["Types & Attributes"]
        id_ = self._selected_id(c["types_tree"])
        if id_ is None:
            return
        path, _ = QFileDialog.getOpenFileName(self, "A type's icon", "", "PNG images (*.png);;All files (*)")
        if not path:
            return
        try:
            data = Path(path).read_bytes()
            pngio.decode(data)
        except (OSError, pngio.PngError, ValueError) as problem:
            QMessageBox.critical(self, "Type", f"Could not read {path}: {problem}")
            return
        old = self.project.type_icons.get(id_)
        icon = f"icons/type-{id_}.png"
        name = self.project.type_names[id_] or (TYPE_NAMES[id_] if id_ < len(TYPE_NAMES) else "")
        self.project.files[icon] = data
        if self._apply_type(id_, name, icon):
            if old and old != icon:
                self._discard_type_icon_file(old, except_id=id_)
            self.type_icon_cache.pop(icon, None)
        else:
            self.project.files.pop(icon, None)

    def _remove_type_icon(self):
        c = self.workspace_controls["Types & Attributes"]
        id_ = self._selected_id(c["types_tree"])
        if id_ is None or not self.project.type_icons.get(id_):
            return
        name = self.project.type_names[id_] or (TYPE_NAMES[id_] if id_ < len(TYPE_NAMES) else "")
        old = self.project.type_icons.get(id_)
        if self._apply_type(id_, name, icon=None):
            self._discard_type_icon_file(old, except_id=id_)
            self.type_icon_cache.pop(old, None)

    def _export_type_icon(self):
        c = self.workspace_controls["Types & Attributes"]
        id_ = self._selected_id(c["types_tree"])
        icon = self.project.type_icons.get(id_) if id_ is not None else None
        if not icon:
            return
        data = self.project.files.get(icon)
        if data is None and self.project.source_dir:
            try:
                data = (Path(self.project.source_dir) / icon).read_bytes()
            except OSError:
                data = None
        if data is None:
            QMessageBox.critical(self, "Type", f"{icon} could not be read.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export the type's icon", Path(icon).name,
                                              "PNG images (*.png)")
        if not path:
            return
        Path(path).write_bytes(data)

    # --- attributes -------------------------------------------------------

    def _attribute_section(self):
        section = self.project.other.get("attributes")
        return section if isinstance(section, dict) else {}

    def _attribute_entry(self, id_):
        entries = self._attribute_section().get("attributes")
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, dict) and entry.get("id") == id_:
                    return entry
        return None

    def _attribute_icon(self, id_):
        entry = self._attribute_entry(id_)
        icon = entry.get("icon") if entry else None
        return icon if isinstance(icon, str) and icon else None

    def _attribute_rows(self):
        names, declared = manifest._attribute_registry(self._attribute_section())
        rows = []
        for id_ in range(256):
            if id_ in (6, 7):
                continue
            if id_ < len(ATTRIBUTE_NAMES):
                rows.append((id_, names[id_] or ATTRIBUTE_NAMES[id_],
                            "Renamed retail" if id_ in declared else "Retail"))
            elif id_ in declared:
                rows.append((id_, names[id_], "Custom"))
        return rows

    def _show_attribute_icon(self):
        c = self.workspace_controls["Types & Attributes"]
        id_ = self._selected_id(c["attributes_tree"])
        path = self._attribute_icon(id_) if id_ is not None else None
        fallback = attribute_icon(self, id_) if id_ is not None else None
        self._show_icon(path, self.attribute_icon_cache, fallback, c["attributes_icon_preview"], c["attributes_icon_path"])

    def _next_free_attribute_id(self):
        names, declared = manifest._attribute_registry(self._attribute_section())
        for id_ in range(len(ATTRIBUTE_NAMES), 256):
            if id_ in (6, 7) or id_ in declared:
                continue
            return id_
        return len(ATTRIBUTE_NAMES)

    def _add_attribute(self):
        id_, ok = QInputDialog.getInt(self, "Add attribute", "Numeric ID (8-255):",
                                       self._next_free_attribute_id(), len(ATTRIBUTE_NAMES), 255)
        if not ok:
            return
        if id_ in (6, 7):
            QMessageBox.critical(self, "Attribute", "IDs 6 and 7 are reserved and cannot be used.")
            return
        name, ok = QInputDialog.getText(self, "Add attribute", "Display name:")
        if not ok or not name.strip():
            return
        self._apply_attribute(id_, name.strip(), icon=None)

    def _edit_attribute(self):
        id_ = self._selected_id(self.workspace_controls["Types & Attributes"]["attributes_tree"])
        if id_ is None:
            return
        names, _ = manifest._attribute_registry(self._attribute_section())
        name, ok = QInputDialog.getText(self, "Rename attribute", "Display name:", text=names[id_])
        if not ok or not name.strip():
            return
        self._apply_attribute(id_, name.strip())

    def _apply_attribute(self, id_, name, icon=_KEEP):
        if icon is _KEEP:
            icon = self._attribute_icon(id_)
        section = self.project.other.setdefault("attributes", {})
        if not isinstance(section, dict):
            section = {}
            self.project.other["attributes"] = section
        entries = section.setdefault("attributes", [])
        if not isinstance(entries, list):
            entries = []
        entries = [e for e in entries if not (isinstance(e, dict) and e.get("id") == id_)]
        new_entry = {"id": id_, "name": name}
        if icon:
            new_entry["icon"] = icon
        entries.append(new_entry)
        section["attributes"] = entries
        _, declared = manifest._attribute_registry(section)
        if id_ not in declared:
            QMessageBox.critical(self, "Attribute",
                                  f'"{name}" cannot be used: it may be empty, purely numeric, '
                                  "or already another attribute's name.")
            entries.remove(new_entry)
            if entries:
                section["attributes"] = entries
            else:
                del self.project.other["attributes"]
            return False
        self._mark_dirty()
        self._refresh_types_attributes()
        return True

    def _remove_attribute(self):
        c = self.workspace_controls["Types & Attributes"]
        id_ = self._selected_id(c["attributes_tree"])
        if id_ is None:
            return
        section = self.project.other.get("attributes")
        entries = section.get("attributes") if isinstance(section, dict) else None
        if not isinstance(entries, list):
            return
        icon = self._attribute_icon(id_)
        kept = [e for e in entries if not (isinstance(e, dict) and e.get("id") == id_)]
        if len(kept) == len(entries):
            return
        if kept:
            section["attributes"] = kept
        else:
            del self.project.other["attributes"]
        self._discard_attribute_icon_file(icon, except_id=id_)
        self.attribute_icon_cache.clear()
        self._mark_dirty()
        self._refresh_types_attributes()

    def _discard_attribute_icon_file(self, icon, except_id=None):
        """Drop a mod file only after the last attribute stops using it."""
        if not icon:
            return
        entries = self._attribute_section().get("attributes")
        if isinstance(entries, list) and any(
                isinstance(e, dict) and e.get("id") != except_id and e.get("icon") == icon for e in entries):
            return
        self.project.files.pop(icon, None)

    def _import_attribute_icon(self):
        c = self.workspace_controls["Types & Attributes"]
        id_ = self._selected_id(c["attributes_tree"])
        if id_ is None:
            return
        path, _ = QFileDialog.getOpenFileName(self, "An attribute's icon", "", "PNG images (*.png);;All files (*)")
        if not path:
            return
        try:
            data = Path(path).read_bytes()
            pngio.decode(data)
        except (OSError, pngio.PngError, ValueError) as problem:
            QMessageBox.critical(self, "Attribute", f"Could not read {path}: {problem}")
            return
        old = self._attribute_icon(id_)
        icon = f"icons/attribute-{id_}.png"
        names, _ = manifest._attribute_registry(self._attribute_section())
        self.project.files[icon] = data
        if self._apply_attribute(id_, names[id_], icon):
            if old and old != icon:
                self._discard_attribute_icon_file(old, except_id=id_)
            self.attribute_icon_cache.pop(icon, None)
        else:
            self.project.files.pop(icon, None)

    def _remove_attribute_icon(self):
        c = self.workspace_controls["Types & Attributes"]
        id_ = self._selected_id(c["attributes_tree"])
        if id_ is None:
            return
        old = self._attribute_icon(id_)
        if not old:
            return
        names, _ = manifest._attribute_registry(self._attribute_section())
        if self._apply_attribute(id_, names[id_], icon=None):
            self._discard_attribute_icon_file(old, except_id=id_)
            self.attribute_icon_cache.pop(old, None)

    def _export_attribute_icon(self):
        c = self.workspace_controls["Types & Attributes"]
        id_ = self._selected_id(c["attributes_tree"])
        icon = self._attribute_icon(id_) if id_ is not None else None
        if not icon:
            return
        data = self.project.files.get(icon)
        if data is None and self.project.source_dir:
            try:
                data = (Path(self.project.source_dir) / icon).read_bytes()
            except OSError:
                data = None
        if data is None:
            QMessageBox.critical(self, "Attribute", f"{icon} could not be read.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export the attribute's icon", Path(icon).name,
                                              "PNG images (*.png)")
        if not path:
            return
        Path(path).write_bytes(data)
