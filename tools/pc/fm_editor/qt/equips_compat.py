"""Multi-type targeting and card-style filters for the Equips workspace."""
from __future__ import annotations

from pathlib import Path


def install() -> None:
    from .common import (ATTRIBUTE_NAMES, QFile, QIODevice, QLineEdit,
                         QListWidget, QListWidgetItem, QMessageBox, QPushButton, QCheckBox, QToolButton,
                         QUiLoader, Qt, TYPE_NAMES, declared_type_choices,
                         decorate_attribute_items, decorate_type_items)
    from .window import ModernEditor
    from .. import bulk_fusions

    if getattr(ModernEditor, "_equips_compat_installed", False):
        return
    ModernEditor._equips_compat_installed = True

    original_build = ModernEditor._build_workspace_page
    original_fill_monsters = ModernEditor._fill_equip_monsters

    def build(self, name, parent):
        result = original_build(self, name, parent)
        if name != "Equips":
            return result
        controls = self.workspace_controls["Equips"]
        page = controls["page"]
        advanced = page.findChild(QPushButton, "equipAdvancedFilterButton")
        clear = page.findChild(QPushButton, "equipClearFilterButton")
        if advanced is None or clear is None:
            raise RuntimeError("Equips form is missing filter controls")
        self.equip_advanced_filters = {"types": set(), "attributes": set(), "bounds": {}}
        self.equip_type_filter = None
        controls["type_toggles"] = [page.findChild(QCheckBox, f"equipTypeToggle{typ}")
                                    for typ in range(20)]
        controls["type_counts"] = [page.findChild(QToolButton, f"equipTypeCount{typ}")
                                   for typ in range(20)]
        if any(widget is None for widget in (*controls["type_toggles"], *controls["type_counts"])):
            raise RuntimeError("Equips form is missing type-targeting controls")
        advanced.clicked.connect(self._open_equip_advanced_filter)
        clear.clicked.connect(self._clear_equip_advanced_filters)
        controls["monsters"].itemSelectionChanged.connect(self._sync_selected_equip_action)
        for typ, toggle in enumerate(controls["type_toggles"]):
            toggle.stateChanged.connect(lambda state, typ=typ: self._toggle_equip_type(typ, state))
            controls["type_counts"][typ].clicked.connect(lambda _checked=False, typ=typ: self._show_equip_type(typ))
        self._sync_selected_equip_action()
        return result

    def sync_selected(self):
        controls = self.workspace_controls.get("Equips", {})
        equip = getattr(self, "equip_current", None)
        button = controls.get("add_selected")
        if button is None:
            return
        selected = set()
        for row in {item.row() for item in controls["monsters"].selectedItems()}:
            item = controls["monsters"].item(row, 0)
            if item is not None:
                selected.add(item.data(Qt.ItemDataRole.UserRole))
        button.setEnabled(bool(selected) and equip in self.project.cards)
        if not selected or equip not in self.project.cards:
            button.setText("Add selected")
            return
        targets = self.project.equip_targets(equip)
        button.setText("Remove selected" if selected.issubset(targets) else "Add selected")

    def toggle_selected(self):
        controls = self.workspace_controls.get("Equips", {})
        equip = getattr(self, "equip_current", None)
        if equip not in self.project.cards:
            return
        selected = set()
        for row in {item.row() for item in controls["monsters"].selectedItems()}:
            item = controls["monsters"].item(row, 0)
            if item is not None:
                selected.add(item.data(Qt.ItemDataRole.UserRole))
        if not selected:
            return
        targets = self.project.equips.setdefault(equip, self.project.equip_targets(equip))
        if selected.issubset(targets):
            targets.difference_update(selected)
        else:
            targets.update(selected)
        self._mark_dirty()
        self._refresh_equips()

    def clear_filters(self):
        self.equip_advanced_filters = {"types": set(), "attributes": set(), "bounds": {}}
        controls = self.workspace_controls.get("Equips", {})
        search = controls.get("monster_search")
        if search is not None:
            self._filter_equip_monsters(search.text())

    def wanted(self, cid, text):
        if not self._card_matches(cid, text):
            return False
        card = self.project.cards[cid]
        filters = getattr(self, "equip_advanced_filters", {})
        if filters.get("types") and card.type not in filters["types"]:
            return False
        if filters.get("attributes") and card.attribute not in filters["attributes"]:
            return False
        bounds = filters.get("bounds", {})
        return (bulk_fusions._within(card.attack, bounds.get("atk_min"), bounds.get("atk_max"))
                and bulk_fusions._within(card.defense, bounds.get("def_min"), bounds.get("def_max"))
                and bulk_fusions._within(card.level, bounds.get("level_min"), bounds.get("level_max")))

    def filter_monsters(self, text):
        controls = self.workspace_controls.get("Equips")
        if not controls:
            return
        table = controls["monsters"]
        only_type = getattr(self, "equip_type_filter", None)
        for row in range(table.rowCount()):
            item = table.item(row, 0)
            cid = item.data(Qt.ItemDataRole.UserRole) if item else None
            wanted = cid is not None and self._equip_filter_wanted(cid, text)
            if wanted and only_type is not None:
                wanted = self.project.cards[cid].type == only_type
            table.setRowHidden(row, not wanted)
        self._sync_selected_equip_action()

    def fill_monsters(self):
        original_fill_monsters(self)
        controls = self.workspace_controls.get("Equips", {})
        toggles = controls.get("type_toggles", ())
        counts = controls.get("type_counts", ())
        equip = getattr(self, "equip_current", None)
        editable = equip in self.project.cards and self.project.cards[equip].type == 23
        targets = self.project.equip_targets(equip) if editable else set()
        monsters = self.project.monsters() if editable else []
        for typ, (toggle, count) in enumerate(zip(toggles, counts)):
            members = {cid for cid in monsters if self.project.cards[cid].type == typ}
            have = len(targets & members)
            toggle.blockSignals(True)
            toggle.setEnabled(editable and bool(members))
            toggle.setCheckState(Qt.CheckState.Checked if members and have == len(members)
                                 else Qt.CheckState.PartiallyChecked if have else Qt.CheckState.Unchecked)
            toggle.blockSignals(False)
            count.setEnabled(editable and bool(members))
            count.setText(f"{have}/{len(members)}" if editable else "")
            count.setDown(getattr(self, "equip_type_filter", None) == typ)

    def toggle_type(self, typ, state):
        if self._loading_workspace or getattr(self, "_restoring", False):
            return
        self._equip_by_type(state != Qt.CheckState.Unchecked.value, typ)

    def show_type(self, typ):
        self.equip_type_filter = None if getattr(self, "equip_type_filter", None) == typ else typ
        controls = self.workspace_controls.get("Equips", {})
        search = controls.get("monster_search")
        if search is not None:
            self._filter_equip_monsters(search.text())
        self._sync_equip_type_controls()

    def sync_type_controls(self):
        self._fill_equip_monsters()

    def equip_by_type(self, allow, typ=None):
        equip = getattr(self, "equip_current", None)
        if equip not in self.project.cards or self.project.cards[equip].type != 23:
            return
        typ = 0 if typ is None else typ
        members = {cid for cid in self.project.monsters() if self.project.cards[cid].type == typ}
        targets = self.project.equips.setdefault(equip, self.project.equip_targets(equip))
        before = set(targets)
        if allow:
            targets.update(members)
        else:
            targets.difference_update(members)
        if targets == before:
            return
        self._mark_dirty()
        self._refresh_equips()

    def load_filter_form(parent):
        source = QFile(str(Path(__file__).resolve().parents[1] / "ui" / "equip_filter_dialog.ui"))
        if not source.open(QIODevice.OpenModeFlag.ReadOnly):
            raise RuntimeError(f"Could not open Equip filter form: {source.errorString()}")
        try:
            dialog = QUiLoader().load(source, parent)
        finally:
            source.close()
        if dialog is None:
            raise RuntimeError("Could not load Equip filter form")
        return dialog

    def open_advanced(self):
        dialog = load_filter_form(self)
        dialog.setModal(True)
        types = dialog.findChild(QListWidget, "equipFilterTypes")
        attributes = dialog.findChild(QListWidget, "equipFilterAttributes")
        edits = {
            "atk_min": dialog.findChild(QLineEdit, "equipFilterAtkMin"),
            "atk_max": dialog.findChild(QLineEdit, "equipFilterAtkMax"),
            "def_min": dialog.findChild(QLineEdit, "equipFilterDefMin"),
            "def_max": dialog.findChild(QLineEdit, "equipFilterDefMax"),
            "level_min": dialog.findChild(QLineEdit, "equipFilterLevelMin"),
            "level_max": dialog.findChild(QLineEdit, "equipFilterLevelMax"),
        }
        filters = getattr(self, "equip_advanced_filters", {})
        for listing, labels, selected in ((types, declared_type_choices(self.project, monster_only=True), filters.get("types", set())),
                                          (attributes, ATTRIBUTE_NAMES, filters.get("attributes", set()))):
            for index, entry in enumerate(labels):
                type_id, label = entry if isinstance(entry, tuple) else (index, entry)
                item = QListWidgetItem(label)
                item.setData(Qt.ItemDataRole.UserRole, type_id)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked if type_id in selected else Qt.CheckState.Unchecked)
                listing.addItem(item)
        decorate_type_items(self, types)
        decorate_attribute_items(self, attributes)
        for key, edit in edits.items():
            value = filters.get("bounds", {}).get(key)
            edit.setText("" if value is None else str(value))
        clear = dialog.findChild(QPushButton, "clearButton")
        cancel = dialog.findChild(QPushButton, "cancelButton")
        apply = dialog.findChild(QPushButton, "applyButton")
        clear.clicked.connect(lambda: ([types.item(i).setCheckState(Qt.CheckState.Unchecked)
                                        for i in range(types.count())],
                                       [attributes.item(i).setCheckState(Qt.CheckState.Unchecked)
                                        for i in range(attributes.count())],
                                       [edit.clear() for edit in edits.values()]))
        cancel.clicked.connect(dialog.reject)
        apply.clicked.connect(dialog.accept)
        if not dialog.exec():
            return
        try:
            bounds = {key: int(edit.text()) if edit.text().strip() else None
                      for key, edit in edits.items()}
            for label, low, high in (("ATK", "atk_min", "atk_max"),
                                     ("DEF", "def_min", "def_max"),
                                     ("Level", "level_min", "level_max")):
                if bounds[low] is not None and bounds[high] is not None and bounds[low] > bounds[high]:
                    raise ValueError(f"{label} minimum exceeds maximum")
        except ValueError as problem:
            QMessageBox.warning(self, "Advanced filters", str(problem))
            return
        self.equip_advanced_filters = {
            "types": {types.item(index).data(Qt.ItemDataRole.UserRole) for index in range(types.count())
                      if types.item(index).checkState() == Qt.CheckState.Checked},
            "attributes": {index for index in range(attributes.count())
                           if attributes.item(index).checkState() == Qt.CheckState.Checked},
            "bounds": bounds,
        }
        self._filter_equip_monsters(self.workspace_controls["Equips"]["monster_search"].text())

    ModernEditor._build_workspace_page = build
    ModernEditor._sync_selected_equip_action = sync_selected
    ModernEditor._toggle_selected_equip_monsters = toggle_selected
    ModernEditor._clear_equip_advanced_filters = clear_filters
    ModernEditor._equip_filter_wanted = wanted
    ModernEditor._filter_equip_monsters = filter_monsters
    ModernEditor._fill_equip_monsters = fill_monsters
    ModernEditor._toggle_equip_type = toggle_type
    ModernEditor._show_equip_type = show_type
    ModernEditor._sync_equip_type_controls = sync_type_controls
    ModernEditor._equip_by_type = equip_by_type
    ModernEditor._open_equip_advanced_filter = open_advanced
