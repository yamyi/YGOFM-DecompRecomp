"""Inline condition controls for the modern Rituals page."""
from __future__ import annotations


def install() -> None:
    """Put the condition recipe editor into each tribute panel.

    The compiled UI is left untouched: the extra controls are attached to the
    existing three tribute panels when the workspace is first shown.
    """
    from .common import (
        FUSION_GROUPS, TYPE_NAMES, QComboBox, QFrame, QHBoxLayout, QLabel,
        QMenu, QPushButton, QSpinBox, QTabWidget, QVBoxLayout, QWidget, QGridLayout, Qt,
    )
    from .rituals import RitualsMixin

    if getattr(RitualsMixin, "_rituals_compat_installed", False):
        return
    RitualsMixin._rituals_compat_installed = True
    original_refresh = RitualsMixin._refresh_rituals
    original_detail = RitualsMixin._refresh_ritual_detail
    original_stage = RitualsMixin._stage_ritual_selector_recipe
    original_apply = RitualsMixin._apply_ritual_selector_recipe

    def recipe_for(self, ritual):
        return tuple(self.ritual_pending.get(ritual)
                     or self.project.rituals.get(ritual)
                     or self.project.retail.rituals.get(ritual)
                     or self.project.rituals.get(self.project.base_of(ritual))
                     or (0, 0, 0, 0))

    def pending_requirements(self, ritual):
        if not hasattr(self, "ritual_condition_pending"):
            self.ritual_condition_pending = {}
        if ritual not in self.ritual_condition_pending:
            saved = self.project.ritual_requirements.get(ritual)
            recipe = recipe_for(self, ritual)
            rows = ([dict(row) for row in saved] if saved else
                    [{"card": recipe[i]} if recipe[i] else {} for i in range(3)])
            rows.extend({} for _ in range(3 - len(rows)))
            self.ritual_condition_pending[ritual] = rows[:3]
        return self.ritual_condition_pending[ritual]

    def modes_for(self, ritual):
        if not hasattr(self, "ritual_tribute_modes"):
            self.ritual_tribute_modes = {}
        if ritual not in self.ritual_tribute_modes:
            saved = self.project.ritual_requirements.get(ritual)
            self.ritual_tribute_modes[ritual] = [
                "condition" if saved and i < len(saved) and set(saved[i]) != {"card"}
                else "card" for i in range(3)
            ]
        return self.ritual_tribute_modes[ritual]

    def condition_label(self, key):
        return next(label for label, item_key, _ in self.RITUAL_CONDITIONS if item_key == key)

    def default_for(self, key):
        if key == "type":
            return TYPE_NAMES[0]
        if key == "fusion_group":
            return FUSION_GROUPS[0]
        if key == "defense_gt_attack":
            return True
        return next(number[2] for _label, item_key, number in self.RITUAL_CONDITIONS
                    if item_key == key and number is not None)

    def clear_layout(layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
            elif item.layout() is not None:
                clear_layout(item.layout())

    def take_widget(layout, widget):
        index = layout.indexOf(widget)
        if index >= 0:
            layout.takeAt(index)

    def take_layout(layout, child):
        for index in range(layout.count()):
            if layout.itemAt(index).layout() is child:
                layout.takeAt(index)
                return

    def ensure_panels(self):
        if len(getattr(self, "ritual_condition_panels", [])) == 3:
            return
        controls = self.workspace_controls.get("Rituals")
        if not controls:
            return
        panels = [image.parentWidget() for image in controls["tribute_images"]]
        if len(panels) != 3 or any(panel is None or panel.layout() is None for panel in panels):
            return
        created = []
        for index, panel in enumerate(panels):
            outer = panel.layout()
            image = controls["tribute_images"][index]
            combo = controls["tribute_combos"][index]
            prefix = f"ritualTribute{index + 1}"
            grid = panel.findChild(QGridLayout, prefix + "DetailsGrid")
            if grid is None:
                return

            # Move the stock widgets into a genuine Card tab instead of
            # merely hiding them behind a separate condition control.
            take_widget(outer, image)
            take_widget(outer, combo)
            take_layout(outer, grid)
            tabs = QTabWidget(panel)
            tabs.setObjectName(f"ritualTributeTabs{index + 1}")
            tabs.setStyleSheet(
                "QTabWidget::pane { border:1px solid #2b425c; border-radius:5px; top:-1px; }"
                "QTabBar::tab { background:#101d2b; border:1px solid #304861; color:#d7e2ee;"
                " padding:5px 14px; }"
                "QTabBar::tab:selected { background:#1b2d43; border-color:#4784c4; color:#fff;"
                " border-bottom-color:#1b2d43; }"
            )
            card_page = QWidget(tabs)
            card_layout = QVBoxLayout(card_page)
            card_layout.setContentsMargins(12, 10, 12, 10)
            card_layout.setSpacing(6)
            image.setFixedSize(112, 157)
            card_layout.addWidget(image, 0, Qt.AlignmentFlag.AlignHCenter)
            card_layout.addWidget(combo)
            card_layout.addLayout(grid)
            card_layout.addStretch(1)

            condition_page = QWidget(tabs)
            layout = QVBoxLayout(condition_page)
            layout.setContentsMargins(12, 10, 12, 10)
            layout.setSpacing(6)
            layout.setAlignment(Qt.AlignmentFlag.AlignTop)
            summary = QLabel()
            summary.setWordWrap(True)
            summary.setStyleSheet("color:#9eb2c9;")
            layout.addWidget(summary)
            rules_holder = QWidget(condition_page)
            rules = QVBoxLayout(rules_holder)
            rules.setContentsMargins(0, 0, 0, 0)
            rules.setSpacing(4)
            layout.addWidget(rules_holder)
            layout.addStretch(1)
            actions = QHBoxLayout()
            add = QPushButton("+ Add condition")
            clear = QPushButton("Clear all")
            add.clicked.connect(lambda _checked=False, n=index, b=add: offer(self, n, b))
            clear.clicked.connect(lambda _checked=False, n=index: clear_conditions(self, n))
            actions.addWidget(add)
            actions.addStretch(1)
            actions.addWidget(clear)
            layout.addLayout(actions)

            tabs.addTab(card_page, "Card")
            tabs.addTab(condition_page, "Condition")
            tabs.currentChanged.connect(
                lambda tab, n=index: set_mode(self, n, "condition" if tab else "card"))
            outer.insertWidget(1, tabs)
            created.append({"tabs": tabs, "summary": summary, "rules": rules,
                            "add": add, "clear": clear})
        self.ritual_condition_panels = created

    def set_mode(self, index, mode):
        ritual = getattr(self, "ritual_current", None)
        if ritual not in self.project.cards:
            return
        modes_for(self, ritual)[index] = mode
        requirement = pending_requirements(self, ritual)[index]
        combo = self.workspace_controls["Rituals"]["tribute_combos"][index]
        if mode == "condition":
            selected = combo.currentData()
            if not requirement and selected:
                requirement["card"] = selected
        elif "card" not in requirement:
            combo.blockSignals(True)
            combo.setCurrentIndex(0)
            combo.blockSignals(False)
            recipe = list(self.ritual_pending.get(ritual, recipe_for(self, ritual)))
            recipe[index] = None
            self.ritual_pending[ritual] = tuple(recipe)
        self._refresh_ritual_detail()

    def change_rule(self, index, key, value):
        ritual = getattr(self, "ritual_current", None)
        if ritual not in self.project.cards:
            return
        pending_requirements(self, ritual)[index][key] = value
        refresh_inline(self)

    def add_row(self, index, key, requirement, layout):
        row = QHBoxLayout()
        title = QLabel(condition_label(self, key))
        title.setMinimumWidth(90)
        row.addWidget(title)
        if key == "card":
            field = self._card_combo(None, requirement.get(key) or None, ids=self.project.monsters())
            field.currentIndexChanged.connect(
                lambda _value, n=index, widget=field: change_rule(self, n, "card", self._combo_card_id(widget) or 0))
            row.addWidget(field, 1)
        elif key in ("type", "fusion_group"):
            field = QComboBox()
            field.addItems(list(TYPE_NAMES[:20] if key == "type" else FUSION_GROUPS))
            found = field.findText(str(requirement.get(key, "")))
            field.setCurrentIndex(found if found >= 0 else 0)
            field.currentTextChanged.connect(lambda text, n=index, k=key: change_rule(self, n, k, text))
            row.addWidget(field, 1)
        elif key == "defense_gt_attack":
            row.addWidget(QLabel("Required"), 1)
        else:
            low, high, _start = next(number for _label, item_key, number in self.RITUAL_CONDITIONS
                                     if item_key == key)
            field = QSpinBox()
            field.setRange(low, high)
            field.setValue(int(requirement.get(key, low)))
            field.valueChanged.connect(lambda value, n=index, k=key: change_rule(self, n, k, value))
            row.addWidget(field, 1)
        remove = QPushButton("X")
        remove.setToolTip("Remove this condition")
        remove.setFixedWidth(28)
        remove.clicked.connect(lambda _checked=False, n=index, k=key: remove_condition(self, n, k))
        row.addWidget(remove)
        layout.addLayout(row)

    def remove_condition(self, index, key):
        ritual = getattr(self, "ritual_current", None)
        if ritual not in self.project.cards:
            return
        pending_requirements(self, ritual)[index].pop(key, None)
        refresh_inline(self)

    def clear_conditions(self, index):
        ritual = getattr(self, "ritual_current", None)
        if ritual not in self.project.cards:
            return
        pending_requirements(self, ritual)[index].clear()
        refresh_inline(self)

    def offer(self, index, button):
        ritual = getattr(self, "ritual_current", None)
        if ritual not in self.project.cards:
            return
        requirement = pending_requirements(self, ritual)[index]
        menu = QMenu(button)
        for label, key, _number in self.RITUAL_CONDITIONS:
            action = menu.addAction(label)
            action.setEnabled(key not in requirement)
            action.triggered.connect(lambda _checked=False, n=index, k=key: add_condition(self, n, k))
        menu.exec(button.mapToGlobal(button.rect().bottomLeft()))

    def add_condition(self, index, key):
        ritual = getattr(self, "ritual_current", None)
        if ritual not in self.project.cards:
            return
        requirement = pending_requirements(self, ritual)[index]
        if key == "card":
            card = self._choose_one_card("Specific ritual tribute", ids=self.project.monsters())
            if not card:
                return
            requirement[key] = card
        else:
            requirement[key] = default_for(self, key)
        refresh_inline(self)

    def refresh_inline(self):
        ensure_panels(self)
        ritual = getattr(self, "ritual_current", None)
        if ritual not in self.project.cards:
            for item in getattr(self, "ritual_condition_panels", []):
                item["tabs"].hide()
            return
        requirements = pending_requirements(self, ritual)
        modes = modes_for(self, ritual)
        for index, item in enumerate(self.ritual_condition_panels):
            condition_mode = modes[index] == "condition"
            item["tabs"].show()
            item["tabs"].blockSignals(True)
            item["tabs"].setCurrentIndex(1 if condition_mode else 0)
            item["tabs"].blockSignals(False)
            clear_layout(item["rules"])
            if condition_mode:
                requirement = requirements[index]
                item["summary"].setText(
                    f"{len(requirement)} condition{'s' if len(requirement) != 1 else ''} (all must match)\n"
                    + self._ritual_tribute_text(requirement))
                for key in list(requirement):
                    add_row(self, index, key, requirement, item["rules"])

    def refresh_rituals(self, *args, **kwargs):
        result = original_refresh(self, *args, **kwargs)
        # Recipes belong in the detail editor; retaining the column makes the
        # list cramped without adding useful selection information.
        table = self.workspace_controls["Rituals"]["cards"]
        table.setColumnHidden(3, True)
        header = table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, header.ResizeMode.Fixed)
        header.resizeSection(0, 52)
        header.setSectionResizeMode(1, header.ResizeMode.Stretch)
        header.setSectionResizeMode(2, header.ResizeMode.Fixed)
        header.resizeSection(2, 86)
        return result

    def refresh_detail(self, *args, **kwargs):
        result = original_detail(self, *args, **kwargs)
        refresh_inline(self)
        return result

    def stage_recipe(self, *args, **kwargs):
        result = original_stage(self, *args, **kwargs)
        refresh_inline(self)
        return result

    def apply_recipe(self, *_args):
        ritual = getattr(self, "ritual_current", None)
        if ritual not in self.project.cards:
            return
        if not any(mode == "condition" for mode in modes_for(self, ritual)):
            return original_apply(self)
        requirements = [dict(row) for row in pending_requirements(self, ritual)]
        for index, requirement in enumerate(requirements):
            if not requirement:
                self.statusBar().showMessage(f"Tribute {index + 1} needs at least one condition", 5000)
                return
            if "card" in requirement and not requirement["card"]:
                self.statusBar().showMessage(f"Tribute {index + 1}: choose a card or remove Specific card", 5000)
                return
            for low, high, name in (("min_attack", "max_attack", "ATK"),
                                    ("min_defense", "max_defense", "DEF"),
                                    ("min_level", "max_level", "level")):
                if (requirement.get(low) is not None and requirement.get(high) is not None
                        and requirement[low] > requirement[high]):
                    self.statusBar().showMessage(
                        f"Tribute {index + 1}: minimum {name} is above maximum", 5000)
                    return
        summoned = self.workspace_controls["Rituals"]["summon_combo"].currentData()
        if not summoned:
            self.statusBar().showMessage("Choose a monster for Summons before applying the recipe", 5000)
            return
        self.project.rituals[ritual] = tuple(row.get("card", 0) for row in requirements) + (summoned,)
        if all(set(row) == {"card"} for row in requirements):
            self.project.ritual_requirements.pop(ritual, None)
        else:
            self.project.ritual_requirements[ritual] = requirements
        self.ritual_pending.pop(ritual, None)
        self.ritual_condition_pending.pop(ritual, None)
        self._mark_dirty()
        self._refresh_rituals()

    RitualsMixin._refresh_rituals = refresh_rituals
    RitualsMixin._refresh_ritual_detail = refresh_detail
    RitualsMixin._stage_ritual_selector_recipe = stage_recipe
    RitualsMixin._apply_ritual_selector_recipe = apply_recipe
