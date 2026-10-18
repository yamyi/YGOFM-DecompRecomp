"""The Limits page (a port of limits_tab.LimitsTab)."""
from __future__ import annotations

from .common import *      # noqa: F401,F403
from .common import (_qimage, _line_count, _pairs_text, _parse_pairs, _whole,
                     _card_image)      # noqa: F401


class LimitsMixin:
    def _build_limits_page(self, page, get, controls):
        # Static controls live in limits_page.ui.  This page only binds their
        # names to the limits model and connects behavior.
        fields = {}
        for key, _label, _retail, _low, _high, _hint, _storage in limits.ALL_FIELDS:
            spin = get(QSpinBox, f"limit_{key.replace('.', '_')}_spin")
            spin.valueChanged.connect(self._limits_edited)
            get(QPushButton, f"reset_{key.replace('.', '_')}_button").clicked.connect(
                lambda _checked=False, field=spin: field.setValue(field.minimum()))
            fields[key] = spin

        table = get(QTableWidget, "duelistLpTable")
        table.setColumnCount(4)
        scope = get(QComboBox, "lpScopeCombo")
        value = get(QSpinBox, "lpValueSpin")
        controls.update(limits=fields, table=table, scope=scope, value=value,
                        status=get(QLabel, "limitsStatusLabel"), rows={})
        for title in ("pageTitleLabel", "limitSettingsTitle", "startingLpTitle"):
            get(QLabel, title).setStyleSheet(
                "font-size:20px;font-weight:650;color:#f3f7fc" if title == "pageTitleLabel"
                else "font-size:16px;font-weight:650;color:#f3f7fc")
        for muted in ("pageSummaryLabel", "startingLpHint"):
            get(QLabel, muted).setStyleSheet("color:#9aacc4")
        for panel in ("limitSettingsPanel", "startingLpPanel"):
            get(QFrame, panel).setStyleSheet(
                f"QFrame#{panel} {{ background:#101b2b; border:1px solid #26374c; border-radius:10px; }}")
        # Without this the page's slack is shared out between the heading, the
        # summary and the status line, and the panels keep their bare hint.
        panels = get(QSplitter, "limitsSplitter")
        page_layout = page.layout()
        for index in range(page_layout.count()):
            page_layout.setStretch(index, 1 if page_layout.itemAt(index).widget() is panels else 0)
        panels.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        for label in ("pageTitleLabel", "pageSummaryLabel", "limitsStatusLabel", "startingLpHint"):
            get(QLabel, label).setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        for panel in ("limitSettingsPanel", "startingLpPanel"):
            get(QFrame, panel).setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        settings_scroll = get(QScrollArea, "limitSettingsScroll")
        settings_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        get(QFrame, "limitSettingsPanel").setMinimumWidth(430)
        get(QFrame, "startingLpPanel").setMinimumWidth(420)
        splitter = get(QSplitter, "limitsSplitter")
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 5)
        splitter.setSizes([520, 700])
        get(QPushButton, "applyLimitsButton").setStyleSheet(
            "background:#216cf1;border-color:#216cf1;color:white;font-weight:600")
        get(QPushButton, "setPlayerLpButton").clicked.connect(lambda: self._set_duelist_lp("player"))
        get(QPushButton, "setDuelistLpButton").clicked.connect(lambda: self._set_duelist_lp("opponent"))
        get(QPushButton, "resetDuelistLpButton").clicked.connect(self._reset_duelist_lp)
        get(QPushButton, "resetAllLimitsButton").clicked.connect(self._reset_all_limits)
        get(QPushButton, "revertLimitsButton").clicked.connect(self._revert_limits)
        get(QPushButton, "applyLimitsButton").clicked.connect(self._apply_limits)
        self.limits_filling = False
        self.limits_opened = None       # "limits" as the mod was opened with it
        self._limits_opened_captured = False
        self._limits_duelists = {}

    def _limit_names(self):
        """Every duelist a row is drawn for: the wildcard, the disc's forty, and
        any other name the mod's own "limits" already carries."""
        from .. import duelist_rules
        known = duelist_rules.references(self.project) if self.project else list(DUELIST_NAMES[1:])
        extra = [name for name in self._limits_duelists
                 if name != "all" and name not in known]
        return ["all"] + known + sorted(extra)

    def _fill_limit_duelists(self):
        """Populate the dynamic LP rows; their controls cannot be static UI."""
        c = self.workspace_controls["Limits"]
        table = c["table"]
        names = self._limit_names()
        table.blockSignals(True)
        wanted = 0
        try:
            table.clearContents()
            table.setRowCount(len(names))
            c["rows"] = {}
            for row, name in enumerate(names):
                number = "—" if name == "all" else str(DUELIST_NAMES.index(name)) if name in DUELIST_NAMES else "mod"
                id_item = QTableWidgetItem(number)
                name_item = QTableWidgetItem("All duelists" if name == "all" else name)
                table.setItem(row, 0, id_item)
                table.setItem(row, 1, name_item)
                values = self._limits_duelists.get(name, (None, None))
                spins = [id_item, name_item]
                for column, value in enumerate(values, start=2):
                    spin = QSpinBox(table)
                    spin.setRange(0, limits.LIFE_POINTS_MAX)
                    spin.setSpecialValueText("—")
                    spin.setValue(value if isinstance(value, int) and value > 0 else 0)
                    spin.valueChanged.connect(self._limits_edited)
                    table.setCellWidget(row, column, spin)
                    wanted = max(wanted, spin.sizeHint().height())
                    spins.append(spin)
                c["rows"][name] = spins
        finally:
            table.blockSignals(False)
        table.verticalHeader().setDefaultSectionSize(max(36, wanted + 4))
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for column in (2, 3):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)

    def _refresh_limits(self):
        c = self.workspace_controls.get("Limits")
        if not c:
            return
        stored = self.project.other.get("limits")
        if not self._limits_opened_captured:
            self.limits_opened = copy.deepcopy(stored)
            self._limits_opened_captured = True
        flat = limits.flatten(stored)
        self._limits_duelists = dict(flat.get("duelists", {}))
        self.limits_filling = True
        try:
            for key, spin in c["limits"].items():
                spin.setValue(flat[key] if key in flat else spin.minimum())
            self._fill_limit_duelists()
            scope = c["scope"]
            chosen = scope.currentData()
            scope.clear()
            scope.addItem("All duelists", "all")
            for name in self._limit_names()[1:]:
                scope.addItem(name, name)
            scope.setCurrentIndex(max(0, scope.findData(chosen)))
        finally:
            self.limits_filling = False
        self._limits_report()
    def _read_limits_form(self):
        c = self.workspace_controls["Limits"]
        flat = {}
        for key, spin in c["limits"].items():
            if spin.value() > spin.minimum():
                flat[key] = spin.value()
        duelists = {}
        for name, spins in c["rows"].items():
            player = spins[2].value() or None
            opponent = spins[3].value() or None
            if player is not None or opponent is not None:
                duelists[name] = (player, opponent)
        flat["duelists"] = duelists
        return flat
    def _limits_edited(self, *_):
        """Any field: store it at once, so nothing is lost by leaving the page."""
        if self.limits_filling or self.project is None:
            return
        flat = self._read_limits_form()
        self._limits_duelists = flat["duelists"]
        before = self.project.other.get("limits")
        after = limits.build(flat, before)
        # Do not rewrite imported malformed or unknown members merely because
        # the user visited this page.  ``values.build`` preserves them while
        # still applying the edits the form can represent.
        if after == limits.build(limits.flatten(before), before):
            after = before
        if after == before:
            return
        if after is None:
            self.project.other.pop("limits", None)
        else:
            self.project.other["limits"] = after
        self._mark_dirty()
        self._limits_report()
    def _limits_report(self):
        c = self.workspace_controls["Limits"]
        if self.project:
            from .. import roster
            problems = limits.check(self.project.other.get("limits"),
                                    lambda name: roster.named(self.project, name))
        else:
            problems = []
        c["status"].setText("\n".join(f"{level}: {where}: {message}"
                                      for level, where, message in problems[:8]))
        c["status"].setStyleSheet("color:#ff7777" if any(p[0] == "error" for p in problems)
                                  else "color:#f2c04c" if problems else "color:#9aacc4")
        return problems
    def _reset_all_limits(self):
        """Every limit back to the game's own number (LimitsTab.clear)."""
        c = self.workspace_controls["Limits"]
        self.limits_filling = True
        try:
            for spin in c["limits"].values():
                spin.setValue(spin.minimum())
            for spins in c["rows"].values():
                for spin in spins[2:]:
                    spin.setValue(spin.minimum())
        finally:
            self.limits_filling = False
        self._limits_edited()
        self._refresh_limits()

    def _set_duelist_lp(self, side):
        """Set one side's starting LP for the selected scope row."""
        c = self.workspace_controls["Limits"]
        name = c["scope"].currentData()
        row = c["rows"].get(name)
        if row is None:
            return
        row[2 if side == "player" else 3].setValue(c["value"].value())

    def _reset_duelist_lp(self):
        """Remove both per-duelist LP overrides for the selected scope row."""
        c = self.workspace_controls["Limits"]
        row = c["rows"].get(c["scope"].currentData())
        if row is None:
            return
        for spin in row[2:]:
            spin.setValue(spin.minimum())
    def _revert_limits(self):
        """Back to the "limits" the mod was opened with."""
        if self.limits_opened is None:
            self.project.other.pop("limits", None)
        else:
            self.project.other["limits"] = copy.deepcopy(self.limits_opened)
        self._mark_dirty()
        self._refresh_limits()
    def _apply_limits(self):
        self._limits_edited()
        problems = self._limits_report()
        errors = [p for p in problems if p[0] == "error"]
        c = self.workspace_controls["Limits"]
        if not problems:
            c["status"].setText("Limits applied; the loader would take all of them.")
            c["status"].setStyleSheet("color:#9aacc4")
        elif not errors:
            c["status"].setText(c["status"].text() + "\nApplied: the loader takes these with the notes above.")
        return not errors
