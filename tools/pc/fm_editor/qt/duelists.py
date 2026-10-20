"""The Duelists page, its pools and its fixed decks (fixed_deck_view)."""
from __future__ import annotations

from .common import *      # noqa: F401,F403
from .common import (_qimage, _line_count, _pairs_text, _parse_pairs, _whole,
                     _card_image)      # noqa: F401
from .. import roster, duelist_rules, bust as bustm
from ..gamedata import AI_FIELD_LABELS, RANK_RULES, RANK_STEPS, RANK_ABOVE


# duel_init_scene.c branches at this final retail opponent ID and deals the
# player's deck to the opponent instead of reading a weighted opponent deck.
DUEL_MASTER_K_OPPONENT_ID = len(DUELIST_NAMES) - 1


class DuelistsMixin:
    def _load_duelist_dialog(self, filename):
        """Load a Designer-defined dialog; Python only binds roster data
        and actions to its existing widgets."""
        source = QFile(str(Path(__file__).resolve().parents[1] / "ui" / filename))
        if not source.open(QIODevice.OpenModeFlag.ReadOnly):
            raise RuntimeError(f"Could not open {filename}: {source.errorString()}")
        dialog = QUiLoader().load(source, self)
        source.close()
        if not isinstance(dialog, QDialog):
            raise RuntimeError(f"Could not load {filename}")
        return dialog

    ADDED_DUELISTS_DESCRIPTION = re.compile(r"^Adds \d+ duelists to the free duel$")

    def _sync_added_duelists_description(self):
        """Add the editor's Free Duel note only to an otherwise blank
        description, then keep that generated note's count current."""
        count = len(roster.copies(self.project))
        previous = self.project.info.description
        lines = previous.splitlines()
        line = f"Adds {count} duelists to the free duel"
        managed = [index for index, text in enumerate(lines)
                   if self.ADDED_DUELISTS_DESCRIPTION.fullmatch(text.strip())]
        generated_only = len(lines) == 1 and bool(managed)
        if count and not previous.strip():
            lines = [line]
        elif count and generated_only:
            lines = [line]
        elif not count and generated_only:
            lines = []
        else:
            return False
        updated = "\n".join(lines)
        if updated == previous:
            return False
        self.project.info.description = updated
        controls = self.workspace_controls.get("Mod info")
        if controls is not None and controls["description"].toPlainText() == previous:
            controls["description"].setPlainText(updated)
        return True

    @staticmethod
    def _put_rows(table, rows):
        held = sort_paused(table)
        table.setRowCount(0)
        table.setRowCount(len(rows))
        for row, values in enumerate(rows):
            for col, value in enumerate(values):
                table.setItem(row, col, TableItem(str(value)))
        sort_resumed(table, held)
    def _duelist_roster_source(self):
        """Compatibility view of the roster; editing uses roster.py directly."""
        entries = [roster.entry(entry, True) for entry in roster.entries(self.project)]
        sources = {entry.key: f"duelists/{entry.key}.json" for entry in roster.entries(self.project)
                   if entry.origin == "folder"}
        mode = "file" if self.project.roster_file is not None else (
            "inline" if any(entry.origin == "manifest" for entry in roster.entries(self.project)) else "folder")
        return entries, mode, self.project.roster_file, sources
    @staticmethod
    def _replaces_slot(entry, slot) -> bool:
        """Whether this entry replaces that duelist, however it names one: by
        number or by name in any case, as the port reads it (duelist_named).
        Matching the name alone added a second entry for the same duelist."""
        from ..model import duelist_named
        value=entry.get("replace")
        if value is None or isinstance(value,bool):
            return False
        if isinstance(value,int):
            return value==slot
        return duelist_named(value)==slot

    @staticmethod
    def _duelist_slug(text):
        import re
        slug=re.sub(r"[^a-z0-9]+","-",str(text).lower()).strip("-")
        return slug or "new-duelist"
    def _duelist_layout(self):
        """The game roster laid out by its shared model, not a second raw
        manifest view.  In particular, an added copy keeps its own roster
        subject so its pools and fixed deck cannot fall through to its base."""
        slots = {i: {"slot": i, "name": roster.shown_name(self.project, i),
                     "base": i, "kind": "stock", "entry": None, "subject": i}
                 for i in range(1, min(40, len(DUELIST_NAMES)))}
        for entry in roster.entries(self.project):
            if entry.replace and 0 < entry.base < 40:
                slots[entry.base] = {
                    "slot": entry.base, "name": roster.shown_name(self.project, entry.base),
                    "base": entry.base, "kind": "replacement",
                    "entry": roster.entry(entry, True), "subject": entry.base,
                }
        for entry, slot in roster.placement(self.project).items():
            if slot is None or not 40 <= slot < 128:
                continue
            slots[slot] = {
                "slot": slot, "name": roster.shown_name(self.project, entry),
                "base": entry.base, "kind": "added",
                "entry": roster.entry(entry, True), "subject": entry,
            }
        return slots
    @staticmethod
    def _duelist_base_name(base) -> str:
        """The stock duelist a copy is of, as the port names them."""
        base = int(base)
        return DUELIST_NAMES[base] if 0 < base < len(DUELIST_NAMES) else str(base)
    @staticmethod
    def _duelist_base_index(value):
        from ..model import duelist_named
        if value is None:return 1
        if isinstance(value,int) and 1<=value<len(DUELIST_NAMES):return value
        found=duelist_named(value)
        return found if found>0 else 1
    def _duelist_portrait_pixmap(self, record):
        subject = record.get("subject")
        if subject is not None and not isinstance(subject, int) and subject.portrait is not None:
            pix = QPixmap()
            if pix.loadFromData(subject.portrait):
                return pix
        entry=record.get("entry") or {}
        portrait=entry.get("portrait")
        if portrait:
            blob=self.project.files.get(portrait)
            if blob is None and self.project.source_dir:
                try:blob=(Path(self.project.source_dir)/portrait).read_bytes()
                except OSError:blob=None
            if blob:
                pix=QPixmap()
                if pix.loadFromData(blob):return pix
        base=int(record.get("base",1))
        if not 0<=base<40:return QPixmap()
        # Free Duel portraits can also be replaced by texture-pack entries
        # targeting their WA_MRG.MRG records.
        try:
            texture_state=art.state(self.project)
            pack_entries=texture_state.entries
            if pack_entries is None:
                manifest_path=f"{art.pack_dir(self.project)}/manifest.json"
                manifest_blob=self.project.files.get(manifest_path)
                if manifest_blob:
                    pack_entries=json.loads(manifest_blob.decode("utf-8-sig"))
            portrait_offset=0xF55000+base*0x980
            for texture in pack_entries or ():
                if (not isinstance(texture,dict) or
                        str(texture.get("archive","")).upper()!="WA_MRG.MRG" or
                        not art.contained(texture.get("file"))):
                    continue
                try:offset=int(str(texture.get("offset","-1")),0)
                except ValueError:continue
                if offset!=portrait_offset:continue
                relative=f"{art.pack_dir(self.project)}/{texture['file']}"
                blob=self.project.files.get(relative)
                if blob is None:
                    folder=texture_state.folder or self.project.source_dir
                    if folder is not None:
                        blob=(Path(folder)/relative).read_bytes()
                if blob:
                    pix=QPixmap()
                    if pix.loadFromData(blob):return pix
                break
        except (OSError,ValueError,TypeError,json.JSONDecodeError):
            pass
        try:
            wa=self.preview_wa;offset=0xF55000+base*0x980
            palette=image_extract.read_palette(wa,offset+0x900,64)
            palette.extend([0]*(256-len(palette)))
            width,height,rgba=image_extract.decode(wa,offset,24,48,8,palette)
            return QPixmap.fromImage(_qimage(width,height,rgba))
        except (IndexError,ValueError,struct.error):
            return QPixmap()
    def _refresh_duelists(self,*_):
        c=self.workspace_controls["Duelists"];grid=c["duelists"]
        self.duelist_slots=self._duelist_layout()
        if not hasattr(self,"duelist_selected_slot"):self.duelist_selected_slot=1
        page=c["page"].currentIndex();query=c["search"].text().strip().casefold()
        # A page holds up to forty positions (five rows of eight).  The
        # 128-slot format leaves Page 4 with positions 120–127 only, so do
        # not render four extra rows of non-existent duelists there.
        first_slot = page * 40
        page_slots = max(0, min(40, 128 - first_slot))
        page_rows = max(1, (page_slots + 7) // 8)
        grid.clearContents();grid.setRowCount(page_rows);grid.setColumnCount(8)
        # Eight portrait tiles are always visible.  Fixed cells prevent Qt
        # from squeezing labels underneath neighbouring portraits when the
        # left pane is resized.
        grid.horizontalHeader().setVisible(False)
        grid.verticalHeader().setVisible(False)
        grid.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        grid.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        tile_width = max(70, grid.viewport().width() // 8)
        for column in range(8):
            grid.setColumnWidth(column, tile_width)
        for row_index in range(page_rows):
            grid.setRowHeight(row_index, 96)
        # Keep the browser's height to its real rows.  This also brings the
        # editor panel directly below the eight final slots on Page 4.
        chrome = grid.frameWidth() * 2 + grid.horizontalScrollBar().sizeHint().height()
        grid.setMinimumHeight(page_rows * 96 + chrome)
        grid.setMaximumHeight(page_rows * 96 + chrome)
        for cell in range(page_slots):
            slot=first_slot+cell;row,col=divmod(cell,8);record=self.duelist_slots.get(slot)
            item=TableItem("");item.setData(Qt.ItemDataRole.UserRole,slot)
            if slot==0:item.setFlags(Qt.ItemFlag.NoItemFlags)
            grid.setItem(row,col,item)
            if record is None:
                continue
            if query and query not in record["name"].casefold() and query not in str(slot) and query not in f"{slot:03d}":
                continue
            tile=QWidget();tile.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents,True)
            tile_layout=QVBoxLayout(tile);tile_layout.setContentsMargins(2,2,2,2);tile_layout.setSpacing(1)
            portrait=QLabel();portrait.setFixedSize(48,48);portrait.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pix=self._duelist_portrait_pixmap(record)
            if not pix.isNull():portrait.setPixmap(pix.scaled(portrait.size(),Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.FastTransformation))
            else:portrait.setText("—")
            # One line, cut with an ellipsis rather than wrapped: wrapped, a
            # name of two or three words was taller than the cell and only
            # its middle line showed -- "001 · Simon Muran" read as "Simon".
            label=QLabel();label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            # The cell's width, taken off the grid rather than off a column
            # that has not been laid out yet. The number is in the tooltip:
            # on a tile this wide it ate the name it was labelling.
            room=max(48,grid.viewport().width()//max(1,grid.columnCount())-8)
            label.setText(QFontMetrics(label.font()).elidedText(
                record["name"],Qt.TextElideMode.ElideRight,room))
            # A duelist the mod has touched reads as touched, as the Tk list's
            # "changed"/"fixed" column says.
            base=int(record.get("base",0) or 0)
            subject = record.get("subject", base)
            state=""
            if fixed_decks.deck_of(self.project, subject) is not None:
                state="fixed"
            elif any({c:w for c,w in roster.pools_of(self.project, subject)[pool].items() if w}
                     !=roster.retail_pool(self.project, subject, pool) for pool in POOLS):
                state="changed"
            if record["kind"]=="added" and not state:
                state="added"
            if state:
                ink=self._state_colour("added" if state in ("added","fixed") else state)
                if ink is not None:label.setStyleSheet(f"color:{ink.name()}")
            label.setToolTip(f"{slot:03d} · {record['name']}"+(f"  ({state})" if state else ""))
            tile_layout.addWidget(portrait,0,Qt.AlignmentFlag.AlignHCenter);tile_layout.addWidget(label)
            grid.setCellWidget(row,col,tile)
        current=getattr(self,"duelist_selected_slot",1)
        cell=current-first_slot
        if not 0<=cell<page_slots or current==0:
            cell=1 if page==0 else 0
            self.duelist_selected_slot=first_slot+cell
        grid.setCurrentCell(cell//8,cell%8)
        self._select_duelist(grid.currentRow(),grid.currentColumn(),refresh_grid=False)
    def _selected_duelist(self):
        slot=getattr(self,"duelist_selected_slot",0)
        record=getattr(self,"duelist_slots",{}).get(slot)
        return (record or {}).get("base",1)
    def _selected_duelist_subject(self):
        """The roster subject currently being edited: a retail ID or a copy."""
        slot = getattr(self, "duelist_selected_slot", 0)
        record = getattr(self, "duelist_slots", {}).get(slot)
        return (record or {}).get("subject", (record or {}).get("base", 1))

    def _selected_duelist_stash_key(self):
        subject = self._selected_duelist_subject()
        return subject if isinstance(subject, int) else ("copy", subject.key)
    def _select_duelist(self,row=None,column=None,refresh_grid=True):
        c=self.workspace_controls["Duelists"]
        if row is None or row<0:row=c["duelists"].currentRow()
        if column is None or column<0:column=c["duelists"].currentColumn()
        if row<0 or column<0:return
        slot=c["page"].currentIndex()*40+row*8+column
        if slot==0:return
        if slot != getattr(self,"duelist_selected_slot",None):
            self._duelist_portrait_pending=None
        self.duelist_selected_slot=slot
        self.duelist_current=self._selected_duelist()
        record=self.duelist_slots.get(slot)
        c["remove"].setEnabled(bool(record and record["kind"]=="added"))
        c["base"].setEnabled(record is None or record["kind"]=="added")
        if record:
            c["name"].setText(record["name"])
            entry=record.get("entry") or {}
            c["id"].setText(str(entry.get("id") or ""))
            c["id"].setReadOnly(record["kind"] in ("added","replacement"))
            base_index=max(1,int(record.get("base",1)))
            c["base"].setCurrentIndex(max(0,c["base"].findData(base_index)))
            wanted=entry.get("slot") if record["kind"]=="added" else None
            c["position"].setCurrentIndex(max(0,c["position"].findData(wanted)))
            pix=self._duelist_portrait_pixmap(record)
            c["portrait"].setPixmap(pix.scaled(c["portrait"].size(),Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation) if not pix.isNull() else QPixmap())
            c["portrait"].setText("" if not pix.isNull() else "Portrait")
        else:
            c["name"].clear();c["id"].clear();c["id"].setReadOnly(False)
            c["portrait"].setPixmap(QPixmap());c["portrait"].setText("Portrait")
            c["base"].setCurrentIndex(0);c["position"].setCurrentIndex(max(0,c["position"].findData(slot if slot>=40 else None)))
        self._refresh_duelist_pool()
    def _choose_duelist_portrait(self):
        path,_=QFileDialog.getOpenFileName(self,"Choose duelist portrait","","PNG images (*.png)")
        if not path:return
        image=QImage(path)
        if image.isNull():
            QMessageBox.warning(self,"Invalid portrait","Choose a readable PNG image.");return
        self._duelist_portrait_pending=Path(path).read_bytes()
        pix=QPixmap.fromImage(image)
        label=self.workspace_controls["Duelists"]["portrait"]
        label.setPixmap(pix.scaled(label.size(),Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation));label.setText("")
    def _roster_origin(self):
        """Where a newly created roster entry belongs in the current mod."""
        if self.project.roster_file is not None:
            return "file"
        if any(entry.origin == "manifest" for entry in roster.entries(self.project)):
            return "manifest"
        return "folder"

    def _save_duelist(self, adding=False):
        """Apply the form through roster.py so every custom duelist remains
        its own pool and fixed-deck subject after save/reopen."""
        c = self.workspace_controls["Duelists"]
        name = c["name"].text().strip()
        if not name:
            QMessageBox.warning(self, "Duelist name required", "Enter a name for this duelist.")
            return
        slot = getattr(self, "duelist_selected_slot", None)
        record = self.duelist_slots.get(slot) if slot is not None else None
        mine = record.get("subject") if record else None
        taken = next((other for other in self.duelist_slots.values()
                      if other.get("subject") is not mine and
                      other.get("name", "").casefold() == name.casefold()), None)
        if taken is not None:
            QMessageBox.warning(
                self, "Name already used",
                f"{taken['name']} is at grid position {taken['slot']} already. "
                "Two duelists with one name cannot be told apart by \"beat\", \"drops\" or \"decks\".")
            return

        requested_key = c["id"].text().strip()
        if adding:
            base = c["base"].currentData()
            if base is None:
                QMessageBox.warning(self, "Choose a base", "Choose a stock duelist to copy.")
                return
            chosen_slot = c["position"].currentData()
            if chosen_slot is not None and chosen_slot in self.duelist_slots:
                QMessageBox.warning(self, "Position occupied",
                                    f"Grid position {chosen_slot} is occupied. Choose another position or Automatic.")
                return
            key = self._duelist_slug(requested_key or name)
            if roster.find(self.project, key) is not None:
                QMessageBox.warning(self, "ID already used", f"The ID {key!r} is already in use.")
                return
            subject = roster.add_copy(self.project, base, name, chosen_slot, key)
            subject.origin = self._roster_origin()
        else:
            if record is None:
                QMessageBox.warning(self, "Choose a duelist",
                                    "Select a duelist to edit, or use Add duelist for an empty position.")
                return
            subject = record.get("subject", record["base"])
            if isinstance(subject, int):
                subject = roster.take_over(self.project, subject)
                subject.origin = self._roster_origin()
            if record["kind"] == "added":
                base = c["base"].currentData()
                if base is None:
                    QMessageBox.warning(self, "Choose a base", "Choose a stock duelist to copy.")
                    return
                chosen_slot = c["position"].currentData()
                if chosen_slot is not None and chosen_slot in self.duelist_slots and chosen_slot != slot:
                    QMessageBox.warning(self, "Position occupied", f"Grid position {chosen_slot} is occupied.")
                    return
                subject.base = int(base)
                subject.slot = chosen_slot
            if requested_key and requested_key != subject.key:
                key = self._duelist_slug(requested_key)
                other = roster.find(self.project, key)
                if other is not None and other is not subject:
                    QMessageBox.warning(self, "ID already used", f"The ID {key!r} is already in use.")
                    return
                subject.key = key
            roster.set_name(self.project, subject, name)
            subject.written = None

        portrait = getattr(self, "_duelist_portrait_pending", None)
        if portrait:
            try:
                roster.set_portrait(self.project, subject, portrait)
            except pngio.PngError as problem:
                QMessageBox.warning(self, "Invalid portrait", str(problem))
                return
            self._duelist_portrait_pending = None
        self._mark_dirty()
        self.duelist_slots = self._duelist_layout()
        self._sync_added_duelists_description()
        selected = roster.slot_of(self.project, subject)
        if selected is not None:
            self.duelist_selected_slot = selected
            if c["search"].text() and c["search"].text().casefold() not in name.casefold():
                c["search"].clear()
            c["page"].setCurrentIndex(selected // 40)
        self._refresh_duelists()
        self.statusBar().showMessage(f"Applied edits to {name}. Use Save to write them to the mod.", 8000)

    # The unlock a duelist entry may carry (free_duel/duelists.c read_one_duelist):
    # beaten duelist, card owned, wins, campaign flag. The pack's own Unlock
    # tab has the same four and three more a pack alone can ask for.
    DUELIST_UNLOCK_NUMBERS = (("wins", "Wins", "against Beat, or in all without it", 0, 9999),
                              ("copies", "Copies", "of the card below (1 by default)", 0, 250))
    # The save's flag array is 2048 bits, and the ranges the game gives them
    # are known (notes/research/the-game.md, the flag array). A number is a
    # poor thing to ask a modder for when the useful ones all read as a
    # sentence, so the flag is picked as what it means, with the number itself
    # left for the story's own flags (0x47-0x6F) and anything unmapped.
    STORY_SUBJECTS = {"duelist": 0, "card": 1, "number": 2}
    STORY_FLAG_KINDS = (("Duelist unlocked in Free Duel", "duelist", 0x6E0, 1, 38),
                        ("Duelist beaten in the campaign", "duelist", 0x1F, 1, 38),
                        ("Card seen in the Library", "card", 0x120, 1, CARD_COUNT),
                        ("Card's password used", "card", 0x400, 1, CARD_COUNT),
                        ("Flag number", "number", 0, 0, 0xFFFF))

    def _story_flag_value(self, kind_box, subject):
        """The flag number the two boxes name, or None for (none)."""
        chosen = kind_box.currentData()
        if chosen is None or chosen < 0:
            return None
        _title, kind, base, low, high = self.STORY_FLAG_KINDS[chosen]
        # The stack holds them in the order STORY_SUBJECTS names.
        if kind == "number":
            return subject.widget(self.STORY_SUBJECTS["number"]).value()
        if kind == "duelist":
            return base + int(subject.widget(self.STORY_SUBJECTS["duelist"]).currentData() or 0)
        return base + int(self._combo_card_id(subject.widget(self.STORY_SUBJECTS["card"])) or 0)

    def _roster_names(self) -> list:
        """Every duelist by name, in grid order: the disc's, the ones a mod
        replaced (under the name it gave them) and the ones it added."""
        seen, out = set(), []
        for slot, record in sorted(getattr(self, "duelist_slots", {}).items()):
            name = record.get("name")
            if slot and name and name not in seen:
                seen.add(name)
                out.append(name)
        for name in DUELIST_NAMES[1:]:
            if name not in seen:
                seen.add(name)
                out.append(name)
        return out

    @staticmethod
    def _unlock_number(value, fallback):
        """A whole number an entry wrote, or the fallback for anything else."""
        return value if isinstance(value, int) and not isinstance(value, bool) else fallback

    @classmethod
    def _story_flag_parts(cls, value):
        """(which kind, the subject) for a flag, or (the number kind, it)."""
        if isinstance(value, int) and not isinstance(value, bool):
            for index, (_title, kind, base, low, high) in enumerate(cls.STORY_FLAG_KINDS):
                if kind != "number" and low <= value - base <= high:
                    return index, value - base
        return len(cls.STORY_FLAG_KINDS) - 1, value

    UNLOCK_CARD_STYLE = """
QFrame#conditionCard { background: #101b2b; border: 1px solid #26374c; border-radius: 10px; }
QFrame#conditionCard[on="true"] { border: 1px solid #2f6fd0; }
QLabel#conditionTitle { font-size: 15px; font-weight: 600; color: #e5edf8; }
QLabel#conditionWhat { color: #8aa0bd; }
QLabel#fieldCaption { color: #9aacc4; font-size: 11px; }
QFrame#sidePanel { background: #101b2b; border: 1px solid #26374c; border-radius: 10px; }
QFrame#ruleRow { background: #152439; border: 1px solid #26374c; border-radius: 8px; }
QLabel#ruleTitle { font-weight: 600; color: #e5edf8; }
QLabel#ruleValue { color: #8aa0bd; font-size: 11px; }
QFrame#noteBox { background: #112542; border: 1px solid #2f6fd0; border-radius: 8px; }
QLabel#noteTitle { font-weight: 600; color: #cfe0f7; }
QLabel#noteBody { color: #9fb6d6; }
QLabel#sideHeading { font-size: 14px; font-weight: 600; color: #e5edf8; }
QPushButton#ruleDrop { background: transparent; border: 0; color: #8aa0bd; padding: 0 6px; font-size: 15px; }
QPushButton#ruleDrop:hover { color: #ffffff; }
"""

    def _open_duelist_unlock(self):
        """When the duelist shows up in Free Duel: any of the four conditions
        the port reads (free_duel/duelists.c read_one_duelist), each on its own
        and all of them together."""
        c = self.workspace_controls["Duelists"]
        slot = getattr(self, "duelist_selected_slot", None)
        record = self.duelist_slots.get(slot) if slot is not None else None
        if not record or slot == 0:
            QMessageBox.information(self, "Unlock conditions", "Choose a duelist first.")
            return
        entry = record.get("entry") or {}
        unlock = entry.get("unlock") if isinstance(entry.get("unlock"), dict) else {}

        dialog = QDialog(self)
        dialog.setWindowTitle("Unlock conditions")
        dialog.setStyleSheet(self.UNLOCK_CARD_STYLE)
        dialog.resize(1060, 700)
        outer = QVBoxLayout(dialog)
        outer.setContentsMargins(18, 16, 18, 16)
        outer.setSpacing(14)

        heading = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(2)
        title = QLabel("Unlock conditions")
        title.setStyleSheet("font-size:18px;font-weight:600;")
        what = QLabel(f"When {record['name']} becomes available in Free Duel.")
        what.setObjectName("conditionWhat")
        titles.addWidget(title)
        titles.addWidget(what)
        heading.addLayout(titles)
        heading.addStretch(1)
        outer.addLayout(heading)

        body = QHBoxLayout()
        body.setSpacing(14)
        outer.addLayout(body, 1)
        column = QVBoxLayout()
        column.setSpacing(10)
        body.addLayout(column, 3)

        boxes, cards = {}, {}

        def card(key_name, title_text, what_text):
            frame = QFrame()
            frame.setObjectName("conditionCard")
            inner = QVBoxLayout(frame)
            inner.setContentsMargins(14, 12, 14, 12)
            inner.setSpacing(6)
            top = QHBoxLayout()
            box = QCheckBox()
            boxes[key_name] = box
            top.addWidget(box)
            name = QLabel(title_text)
            name.setObjectName("conditionTitle")
            top.addWidget(name)
            top.addStretch(1)
            inner.addLayout(top)
            line = QLabel(what_text)
            line.setObjectName("conditionWhat")
            line.setWordWrap(True)
            inner.addWidget(line)
            fields = QGridLayout()
            fields.setHorizontalSpacing(14)
            fields.setVerticalSpacing(4)
            inner.addLayout(fields)
            cards[key_name] = frame
            column.addWidget(frame)
            return fields

        def caption(grid, text, row, col):
            label = QLabel(text)
            label.setObjectName("fieldCaption")
            grid.addWidget(label, row, col)

        # Beat a duelist -------------------------------------------------
        grid = card("beat", "Beat duelist",
                    "Require that a duelist has been defeated -- that many times, with a number of wins. "
                    "Without a duelist named, the wins are counted in all.")
        caption(grid, "Duelist", 0, 0)
        caption(grid, "Required wins", 0, 1)
        beat = short_popup(QComboBox())
        beat.setEditable(True)
        # Every duelist the roster has, the mod's own among them: the port
        # asks Duelists_Named for the name, which finds an added duelist as
        # readily as one of the disc's.
        beat.addItems([""] + [name for name in self._roster_names() if name != record["name"]])
        wins = QSpinBox()
        wins.setRange(1, 9999)
        wins.setValue(1)
        wins.setMaximumWidth(140)
        grid.addWidget(beat, 1, 0)
        grid.addWidget(wins, 1, 1)
        grid.setColumnStretch(0, 1)

        # Own a card -----------------------------------------------------
        grid = card("card", "Own card", "Require that the player owns a specific card.")
        caption(grid, "Card", 0, 0)
        caption(grid, "Copies", 0, 1)
        card_box = self._card_combo(dialog)
        copies = QSpinBox()
        copies.setRange(1, 250)
        copies.setValue(1)
        copies.setMaximumWidth(120)
        grid.addWidget(card_box, 1, 0)
        grid.addWidget(copies, 1, 1)
        grid.setColumnStretch(0, 1)

        # A story flag ---------------------------------------------------
        grid = card("story", "Story flag", "Require something the save has already recorded.")
        caption(grid, "What", 0, 0)
        caption(grid, "Which", 0, 1)
        story_kind = short_popup(QComboBox())
        for index, (text, _kind, _base, _low, _high) in enumerate(self.STORY_FLAG_KINDS):
            story_kind.addItem(text, index)
        story_subject = QStackedWidget()
        story_duelist = short_popup(QComboBox())
        for number in range(1, len(DUELIST_NAMES)):
            story_duelist.addItem(f"{number:02d} {DUELIST_NAMES[number]}", number)
        story_card = self._card_combo(dialog)
        story_number = QSpinBox()
        story_number.setRange(0, 0xFFFF)
        for widget in (story_duelist, story_card, story_number):
            story_subject.addWidget(widget)
        grid.addWidget(story_kind, 1, 0)
        grid.addWidget(story_subject, 1, 1)
        flag_note = QLabel("")
        flag_note.setObjectName("fieldCaption")
        grid.addWidget(flag_note, 2, 0, 1, 2)
        grid.setColumnStretch(1, 1)
        column.addStretch(1)

        # The side: who it is, what is on, and what that means ------------
        side = QFrame()
        side.setObjectName("sidePanel")
        side.setMinimumWidth(320)
        side_column = QVBoxLayout(side)
        side_column.setContentsMargins(14, 14, 14, 14)
        side_column.setSpacing(10)
        body.addWidget(side, 2)
        chosen_heading = QLabel("Selected duelist")
        chosen_heading.setObjectName("sideHeading")
        side_column.addWidget(chosen_heading)
        who = QHBoxLayout()
        portrait = QLabel()
        portrait.setFixedSize(72, 72)
        portrait.setAlignment(Qt.AlignmentFlag.AlignCenter)
        picture = self._duelist_portrait_pixmap(record)
        if not picture.isNull():
            portrait.setPixmap(picture.scaled(portrait.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                              Qt.TransformationMode.FastTransformation))
        who.addWidget(portrait)
        about = QVBoxLayout()
        about.setSpacing(2)
        who_name = QLabel(record["name"])
        who_name.setObjectName("conditionTitle")
        about.addWidget(who_name)
        for text in (f"Grid position {slot}",
                     f"{'Added' if record['kind'] == 'added' else 'Replaces' if record['kind'] == 'replacement' else 'Stock'}"
                     f" · plays as {DUELIST_NAMES[record['base']]}"):
            line = QLabel(text)
            line.setObjectName("ruleValue")
            about.addWidget(line)
        about.addStretch(1)
        who.addLayout(about, 1)
        side_column.addLayout(who)
        rules_heading = QLabel("Active conditions")
        rules_heading.setObjectName("sideHeading")
        side_column.addWidget(rules_heading)
        rules_column = QVBoxLayout()
        rules_column.setSpacing(6)
        side_column.addLayout(rules_column)
        note = QFrame()
        note.setObjectName("noteBox")
        note_column = QVBoxLayout(note)
        note_column.setContentsMargins(12, 10, 12, 10)
        note_column.setSpacing(4)
        note_title = QLabel("All of them")
        note_title.setObjectName("noteTitle")
        note_body = QLabel("Every condition that is on must hold. With none on, the duelist is there "
                           "from the start.")
        note_body.setObjectName("noteBody")
        note_body.setWordWrap(True)
        note_column.addWidget(note_title)
        note_column.addWidget(note_body)
        side_column.addWidget(note)
        counted = QLabel("")
        counted.setObjectName("ruleValue")
        side_column.addWidget(counted)
        side_column.addStretch(1)

        # A coloured dot rather than a picture: the window's font carries no
        # emoji, and a missing glyph draws as an empty box.
        ICONS = {"beat": "#4f9cf5", "card": "#7fd49b", "story": "#c79bf0"}
        TITLES = {"beat": "Beat duelist", "card": "Own card", "story": "Story flag"}

        def worth(key_name):
            """What the rule reads as in the list, or None when it is off."""
            if not boxes[key_name].isChecked():
                return None
            if key_name == "beat":
                who = beat.currentText().strip()
                if wins.value() > 1:
                    return f"{who}, {wins.value()} wins" if who else f"{wins.value()} wins in all"
                return who or "any win"
            if key_name == "card":
                return f"{card_box.currentText().strip() or '(no card)'} ×{copies.value()}"
            flag = self._story_flag_value(story_kind, story_subject)
            return f"{self.STORY_FLAG_KINDS[story_kind.currentData()][0]} ({flag:#x})" if flag is not None else "-"

        def redraw(*_):
            while rules_column.count():
                gone = rules_column.takeAt(0).widget()
                if gone is not None:
                    # Taken out of the layout is not taken off the panel:
                    # deleteLater runs a turn later, and until it does the old
                    # row is still a child, drawn where it last sat -- over the
                    # headings. setParent(None) is what takes it away now.
                    gone.setParent(None)
                    gone.deleteLater()
            on = 0
            for key_name in ("beat", "card", "story"):
                cards[key_name].setProperty("on", "true" if boxes[key_name].isChecked() else "false")
                cards[key_name].style().unpolish(cards[key_name])
                cards[key_name].style().polish(cards[key_name])
                text = worth(key_name)
                if text is None:
                    continue
                on += 1
                row = QFrame()
                row.setObjectName("ruleRow")
                line = QHBoxLayout(row)
                line.setContentsMargins(10, 7, 6, 7)
                mark = QLabel("●")
                mark.setStyleSheet(f"color:{ICONS[key_name]};font-size:13px;")
                line.addWidget(mark)
                stack = QVBoxLayout()
                stack.setSpacing(0)
                name = QLabel(TITLES[key_name])
                name.setObjectName("ruleTitle")
                value = QLabel(text)
                value.setObjectName("ruleValue")
                stack.addWidget(name)
                stack.addWidget(value)
                line.addLayout(stack, 1)
                drop = QPushButton("✕")
                drop.setObjectName("ruleDrop")
                drop.setToolTip(f"Turn {TITLES[key_name]} off")
                drop.clicked.connect(lambda _checked=False, which=key_name: boxes[which].setChecked(False))
                line.addWidget(drop)
                rules_column.addWidget(row)
            counted.setText(f"{on} on · {len(boxes) - on} off" if on else "none on: there from the start")
            kind = self.STORY_FLAG_KINDS[story_kind.currentData() or 0][1]
            story_subject.setCurrentIndex(self.STORY_SUBJECTS.get(kind, 0))
            flag = self._story_flag_value(story_kind, story_subject)
            flag_note.setText(f"flag {flag:#x} in the save" if flag is not None else "")

        for box in boxes.values():
            box.toggled.connect(redraw)
        for widget in (beat, card_box, story_kind, story_duelist, story_card):
            widget.currentIndexChanged.connect(redraw)
        for widget in (beat, card_box, story_card):
            widget.editTextChanged.connect(redraw)
        for widget in (copies, wins, story_number):
            widget.valueChanged.connect(redraw)
        for key_name, box in boxes.items():
            box.toggled.connect(lambda on, which=key_name: self._unlock_card_enabled(cards[which], on))

        # What the duelist already asks for ------------------------------
        if unlock.get("beat") or self._unlock_number(unlock.get("wins"), 0) > 0:
            boxes["beat"].setChecked(True)
            beat.setCurrentText(str(unlock.get("beat", "")))
            wins.setValue(max(1, min(9999, self._unlock_number(unlock.get("wins"), 1))))
        if "card" in unlock:
            boxes["card"].setChecked(True)
            known = self.project.resolve(unlock["card"])
            if known > 0:
                self._set_combo_card(card_box, known)
            else:
                card_box.setCurrentText(str(unlock["card"]))
            copies.setValue(max(1, min(250, self._unlock_number(unlock.get("copies"), 1))))
        if self._unlock_number(unlock.get("story"), -1) >= 0:
            boxes["story"].setChecked(True)
            index, subject = self._story_flag_parts(unlock["story"])
            story_kind.setCurrentIndex(story_kind.findData(index))
            kind = self.STORY_FLAG_KINDS[index][1]
            if kind == "duelist":
                story_duelist.setCurrentIndex(max(0, story_duelist.findData(subject)))
            elif kind == "card":
                self._set_combo_card(story_card, subject)
            elif isinstance(subject, int):
                story_number.setValue(max(0, min(0xFFFF, subject)))
        for key_name, box in boxes.items():
            self._unlock_card_enabled(cards[key_name], box.isChecked())
        redraw()

        footer = QHBoxLayout()
        clear = QPushButton("Clear all")
        clear.clicked.connect(lambda: [box.setChecked(False) for box in boxes.values()])
        footer.addWidget(clear)
        footer.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(dialog.reject)
        save = QPushButton("Save conditions")
        save.setObjectName("primary")
        save.clicked.connect(dialog.accept)
        footer.addWidget(cancel)
        footer.addWidget(save)
        outer.addLayout(footer)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        written = {}
        if boxes["beat"].isChecked():
            if beat.currentText().strip():
                written["beat"] = beat.currentText().strip()
            if wins.value() > 1 or not written.get("beat"):
                written["wins"] = wins.value()
        if boxes["card"].isChecked():
            chosen, typed = self._combo_card_id(card_box), card_box.currentText().strip()
            if chosen:
                written["card"] = (unlock["card"] if "card" in unlock
                                   and self.project.resolve(unlock["card"]) == chosen
                                   else self.project.ref(chosen))
            elif typed:
                written["card"] = typed
            if written.get("card") is not None and copies.value() > 1:
                written["copies"] = copies.value()
        if boxes["story"].isChecked():
            flag = self._story_flag_value(story_kind, story_subject)
            if flag is not None:
                written["story"] = flag
        self._set_duelist_unlock(record, written)

    @staticmethod
    def _unlock_card_enabled(frame, on):
        """A condition that is off keeps its fields, greyed."""
        for child in frame.findChildren(QWidget):
            if not isinstance(child, QCheckBox):
                child.setEnabled(on)

    def _set_duelist_unlock(self, record, unlock):
        """Store unlock data on the selected roster entry, creating a retail
        replacement only when the stock duelist actually needs one."""
        subject = record.get("subject", record.get("base"))
        if isinstance(subject, int):
            subject = roster.take_over(self.project, subject)
            subject.origin = self._roster_origin()
        if unlock:
            subject.extra["unlock"] = unlock
        else:
            subject.extra.pop("unlock", None)
        subject.written = None
        roster.prune(self.project, subject)
        self._mark_dirty()
        self._refresh_duelists()
        self.statusBar().showMessage(
            f"{record['name']} is unlocked by {', '.join(sorted(unlock))}." if unlock
            else f"{record['name']} is there from the start.", 8000)

    def _duelist_record_or_notice(self, title):
        slot = getattr(self, "duelist_selected_slot", None)
        record = self.duelist_slots.get(slot) if slot is not None else None
        if not record or slot == 0:
            QMessageBox.information(self, title, "Choose a duelist first.")
            return None
        return record

    def _duplicate_duelist(self):
        """Duplicate an added duelist with its independent pools, bust,
        portrait and fixed deck through the shared roster model."""
        record = self._duelist_record_or_notice("Duplicate duelist")
        if record is None:
            return
        subject = record.get("subject")
        if isinstance(subject, int):
            QMessageBox.information(
                self, "Duplicate duelist",
                "Apply edits to this retail duelist first, then duplicate its custom entry. "
                "Retail duelists themselves stay part of the game.")
            return
        copy = roster.duplicate(self.project, subject)
        copy.origin = self._roster_origin()
        self._mark_dirty()
        self._sync_added_duelists_description()
        slot = roster.slot_of(self.project, copy)
        if slot is not None:
            self.duelist_selected_slot = slot
            self.workspace_controls["Duelists"]["page"].setCurrentIndex(slot // 40)
        self._refresh_duelists()
        self.statusBar().showMessage(f"Duplicated {record['name']} as {roster.shown_name(self.project, copy)}.", 8000)

    def _revert_duelist_portrait(self):
        record = self._duelist_record_or_notice("Revert portrait")
        if record is None:
            return
        subject = record.get("subject", record["base"])
        if not roster.has_portrait(self.project, subject):
            self.statusBar().showMessage("This duelist already uses its inherited portrait.", 5000)
            return
        roster.revert_portrait(self.project, subject)
        self._duelist_portrait_pending = None
        self._mark_dirty()
        self._refresh_duelists()
        self.statusBar().showMessage(f"Restored {record['name']}'s inherited portrait.", 8000)

    def _open_duelist_rules(self):
        """Edit the game's existing AI and rank-rule records.  The controls
        are intentionally a dialog: all fields belong to the selected roster
        subject and write through duelist_rules rather than a Qt-only format."""
        record = self._duelist_record_or_notice("AI and rank scoring")
        if record is None:
            return
        subject = record.get("subject", record["base"])
        existing = roster.replacement(self.project, subject) if isinstance(subject, int) else subject
        view = existing or SimpleNamespace(extra={})
        ai = duelist_rules.ai_of(view)
        ranks = duelist_rules.ranks_of(view)

        dialog = self._load_duelist_dialog("duelist_rules_dialog.ui")
        dialog.setWindowTitle(f"AI and rank scoring — {record['name']}")
        dialog.findChild(QLabel, "rulesDescription").setText(
            "Configure this duelist's behaviour and scoring overrides. Unticked values inherit from "
            "the selected AI source or the retail base.")
        ai_copy = dialog.findChild(QComboBox, "duelistAiCopy")
        ai_copy.clear()
        ai_copy.addItem("Retail base", "")
        for name in self._roster_names():
            if name != record["name"]:
                ai_copy.addItem(name, name)
        ai_copy.setCurrentIndex(max(0, ai_copy.findData(ai["copy"])))

        sight = dialog.findChild(QComboBox, "duelistAiSight")
        # QUiLoader does not reliably retain Designer item data.  The choices
        # themselves are Designer widgets; bind only their stored game values.
        for index, value in enumerate((None, True, False)):
            sight.setItemData(index, value)
        sight.setCurrentIndex(max(0, sight.findData(ai["sight"])))

        ai_widgets = []
        inherited_row = duelist_rules.under_row(self.project, subject, ai["copy"])
        for row in range(len(AI_FIELD_LABELS)):
            enabled = dialog.findChild(QCheckBox, f"duelistAiOverride{row}")
            number = dialog.findChild(QSpinBox, f"duelistAiValue{row}")
            current = ai["values"][row]
            number.setValue(inherited_row[row] if current is None else current)
            number.setEnabled(current is not None)
            enabled.setChecked(current is not None)
            enabled.toggled.connect(number.setEnabled)
            ai_widgets.append((enabled, number))

        rank_groups = {}
        for rule in range(len(RANK_RULES)):
            group = dialog.findChild(QGroupBox, f"duelistRankGroup{rule}")
            group.setChecked(rule in ranks)
            current = ranks.get(rule, duelist_rules.retail_rank(rule))
            pairs = []
            for step in range(RANK_STEPS):
                threshold = dialog.findChild(QSpinBox, f"duelistRankThreshold{rule}_{step}")
                change = dialog.findChild(QSpinBox, f"duelistRankChange{rule}_{step}")
                threshold.setValue(current[step][0])
                change.setValue(current[step][1])
                pairs.append((threshold, change))
            rank_groups[rule] = (group, pairs)

        restore = dialog.findChild(QPushButton, "rulesRestoreButton")
        def restore_defaults():
            ai_copy.setCurrentIndex(0); sight.setCurrentIndex(0)
            for enabled, number in ai_widgets:
                enabled.setChecked(False)
            for rule, (group, pairs) in rank_groups.items():
                group.setChecked(False)
                retail = duelist_rules.retail_rank(rule)
                for step, (threshold, change) in enumerate(pairs):
                    threshold.setValue(retail[step][0])
                    change.setValue(retail[step][1])
        restore.clicked.connect(restore_defaults)
        cancel = dialog.findChild(QPushButton, "rulesCancelButton")
        save = dialog.findChild(QPushButton, "rulesSaveButton")
        save.setObjectName("primary")
        cancel.clicked.connect(dialog.reject)
        save.clicked.connect(dialog.accept)
        accepted = dialog.exec() == QDialog.DialogCode.Accepted
        if not accepted:
            dialog.deleteLater()
            QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            return

        copy_name = ai_copy.currentData() or ""
        values = [number.value() if enabled.isChecked() else None for enabled, number in ai_widgets]
        written_ai = duelist_rules.ai_value(view, copy=copy_name, values=values,
                                            sight=sight.currentData(),
                                            under=duelist_rules.under_row(self.project, subject, copy_name))
        written_ranks = {}
        for rule, (group, pairs) in rank_groups.items():
            if group.isChecked():
                written_ranks[rule] = tuple((RANK_ABOVE if step == RANK_STEPS - 1 else threshold.value(), change.value())
                                            for step, (threshold, change) in enumerate(pairs))
        written_ranks = duelist_rules.ranks_value(view, written_ranks)
        old_unlock = view.extra.get("unlock")
        duelist_rules.set_rules(self.project, subject, unlock=old_unlock, ai=written_ai, ranks=written_ranks)
        self._mark_dirty()
        self._refresh_duelists()
        dialog.deleteLater()
        QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.statusBar().showMessage(f"Saved AI and rank rules for {record['name']}.", 8000)

    def _open_duelist_bust(self):
        """A compact PySide editor for the existing bust model.  It supports
        all expression pictures, talking/blink frames, ordering and campaign
        replacement without inventing a second serialization layer."""
        record = self._duelist_record_or_notice("Bust editor")
        if record is None:
            return
        subject = record.get("subject", record["base"])
        dialog = self._load_duelist_dialog("duelist_bust_dialog.ui")
        dialog.setWindowTitle(f"Bust editor — {record['name']}")
        listing = dialog.findChild(QListWidget, "bustExpressionList")
        preview = dialog.findChild(QLabel, "bustPreview")
        mode = dialog.findChild(QComboBox, "bustFrameMode")
        side = dialog.findChild(QComboBox, "bustSide")
        # QUiLoader has discarded combo item userData on some supported
        # builds.  Bind the game values explicitly instead of relying on
        # Designer's XML representation.
        for index, value in enumerate(("image", "talk0", "talk1", "blink")):
            mode.setItemData(index, value)
        for index, value in enumerate(("left", "right")):
            side.setItemData(index, value)
        button_names = {"add": "bustAddButton", "rename": "bustRenameButton", "remove": "bustRemoveButton",
                        "default": "bustDefaultButton", "up": "bustUpButton", "down": "bustDownButton",
                        "picture": "bustPictureButton", "talk": "bustTalkButton", "untalk": "bustUntalkButton",
                        "blink": "bustBlinkButton", "unblink": "bustUnblinkButton", "drop": "bustDropButton"}
        buttons = {key: dialog.findChild(QPushButton, name) for key, name in button_names.items()}
        replace = dialog.findChild(QCheckBox, "bustReplaceCheck")
        note = dialog.findChild(QLabel, "bustNote")

        def bust(): return roster.bust_of(self.project, subject)
        def selected():
            b = bust(); item = listing.currentItem()
            return next((e for e in (b.expressions if b else []) if item and item.data(Qt.ItemDataRole.UserRole) is e), None)
        def png_from_dialog(title):
            path, _ = QFileDialog.getOpenFileName(dialog, title, "", "PNG images (*.png)")
            if not path: return None
            try: return Path(path).read_bytes() if pngio.decode(Path(path).read_bytes()) else None
            except (OSError, pngio.PngError) as problem:
                QMessageBox.warning(dialog, "Invalid PNG", str(problem)); return None
        def changed():
            self._mark_dirty(); self._refresh_duelists(); refresh()
        def refresh(*_):
            b, keep = bust(), selected()
            listing.blockSignals(True)
            listing.clear()
            if b is not None:
                for number, expr in enumerate(bustm.order(b)):
                    frames = f" · talk {len(expr.talk)}" if expr.talk else ""
                    if expr.blink is not None: frames += " · blink"
                    item = QListWidgetItem(f"{number}. {expr.name}{frames}")
                    item.setData(Qt.ItemDataRole.UserRole, expr); listing.addItem(item)
                    if expr is keep: listing.setCurrentItem(item)
                if listing.currentRow() < 0 and listing.count(): listing.setCurrentRow(0)
            listing.blockSignals(False)
            expr = selected()
            selected_mode = mode.currentData()
            selected_mode = (("talk", int(selected_mode[-1])) if isinstance(selected_mode, str) and selected_mode.startswith("talk") else selected_mode)
            image = bustm.frame(expr, selected_mode) if expr is not None else None
            stage = bustm.preview(image, side.currentData())
            preview.setPixmap(QPixmap.fromImage(_qimage(stage.width, stage.height, stage.rgba)))
            can_edit = b is not None and not b.unread and expr is not None
            for key in ("rename", "remove", "default", "up", "down", "picture", "talk", "blink"):
                buttons[key].setEnabled(can_edit)
            buttons["untalk"].setEnabled(can_edit and bool(expr.talk))
            buttons["unblink"].setEnabled(can_edit and expr.blink is not None)
            buttons["drop"].setEnabled(b is not None)
            buttons["add"].setEnabled(subject != 0 and not (b and b.unread))
            replace.setVisible(isinstance(subject, int)); replace.setEnabled(isinstance(subject, int) and b is not None)
            entry = roster.replacement(self.project, subject) if isinstance(subject, int) else subject
            replace.blockSignals(True); replace.setChecked(bool(entry and entry.replace_bust)); replace.blockSignals(False)
            note.setText("Use a bust replacement only when the campaign should show it too." if isinstance(subject, int) else
                         "An added duelist's bust is used whenever a story names it.")
        def edit_expr(action):
            expr = selected(); b = bust()
            if action == "add":
                data = png_from_dialog("Choose expression picture")
                if not data: return
                name, ok = QInputDialog.getText(dialog, "Expression name", "Name:", text="default" if b is None else "expression")
                if ok:
                    try:
                        target = roster.give_bust(self.project, subject, data, name) if b is None else b
                        if b is not None: bustm.add(target, name, data)
                    except ValueError as problem: QMessageBox.warning(dialog, "Expression", str(problem)); return
                    changed()
            elif expr is None: return
            elif action == "rename":
                name, ok = QInputDialog.getText(dialog, "Rename expression", "Name:", text=expr.name)
                if ok:
                    try: bustm.rename(b, expr, name)
                    except ValueError as problem: QMessageBox.warning(dialog, "Expression", str(problem)); return
                    changed()
            elif action == "remove": bustm.remove(b, expr); changed()
            elif action == "default": b.default = expr.name; changed()
            elif action in ("up", "down"): bustm.move(b, expr, -1 if action == "up" else 1); changed()
            elif action in ("picture", "talk", "blink"):
                data = png_from_dialog("Choose bust frame")
                if not data: return
                if action == "picture": expr.image, expr.image_path = data, None
                elif action == "talk": expr.talk.append(data); expr.talk_paths.append(None)
                else: expr.blink, expr.blink_path = data, None
                changed()
            elif action == "untalk": expr.talk, expr.talk_paths = [], []; changed()
            elif action == "unblink": expr.blink, expr.blink_path = None, None; changed()
            elif action == "drop": roster.drop_bust(self.project, subject); changed()
        for key, button in buttons.items(): button.clicked.connect(lambda _=False, key=key: edit_expr(key))
        listing.currentItemChanged.connect(refresh); mode.currentIndexChanged.connect(refresh); side.currentIndexChanged.connect(refresh)
        replace.toggled.connect(lambda on: (roster.set_replace_bust(self.project, subject, on), changed()) if isinstance(subject, int) and bust() is not None else None)
        dialog.findChild(QPushButton, "bustCloseButton").clicked.connect(dialog.accept)
        refresh(); dialog.exec()
        dialog.deleteLater()
        QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    def _remove_duelist(self):
        slot = getattr(self, "duelist_selected_slot", None)
        record = self.duelist_slots.get(slot) if slot is not None else None
        subject = (record or {}).get("subject")
        if not record or record.get("kind") != "added" or isinstance(subject, int):
            QMessageBox.information(self, "Remove duelist",
                                    "Select a custom-added duelist to remove. Retail duelists and replacements cannot be removed.")
            return
        answer = QMessageBox.question(
            self, "Remove duelist",
            f"Remove {record['name']} from the roster? Its duelist, deck, drop, and portrait files will be removed when you save the mod.")
        if answer != QMessageBox.StandardButton.Yes:
            return
        roster.remove(self.project, subject)
        self._duelist_portrait_pending = None
        self._mark_dirty()
        self.duelist_slots = self._duelist_layout()
        self._sync_added_duelists_description()
        self._refresh_duelists()

    def _selected_pool_name(self):
        index = self.workspace_controls["Duelists"]["pool"].currentIndex()
        return POOLS[index] if 0 <= index < len(POOLS) else None
    STAT_STYLE = """
QFrame#statsPanel { background: #101b2b; border: 1px solid #26374c; border-radius: 10px; }
QLabel#statsTitle { font-weight: 600; color: #e5edf8; }
QLabel#statsWhat { color: #8aa0bd; font-size: 11px; }
QLabel#statsCaption { color: #9aacc4; }
QLabel#statsValue { color: #e5edf8; font-weight: 600; }
QLabel#statsRank { color: #8aa0bd; }
"""
    # What a card counts as in the type bar, and the colour it is drawn in.
    STAT_KINDS = (("Monsters", "#e8833a"), ("Equips", "#49a7e8"), ("Magic", "#2bc48a"),
                  ("Traps", "#c062d6"), ("Rituals", "#e8c54a"))

    def _build_pool_statistics(self, controls, parent_layout):
        """The panel under a pool's list: what the weights add up to, what the
        deal is made of, and the cards most likely to come out of it."""
        panel = QFrame()
        panel.setObjectName("statsPanel")
        panel.setStyleSheet(self.STAT_STYLE)
        # As tall as its own rows: stretched, it spread the numbers out and
        # took the list's room with it.
        panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        column = QVBoxLayout(panel)
        column.setContentsMargins(12, 8, 12, 8)
        column.setSpacing(4)
        top = QHBoxLayout()
        title = QLabel("Statistics")
        title.setObjectName("statsTitle")
        top.addWidget(title)
        said = QLabel("(calculated)")
        said.setObjectName("statsWhat")
        top.addWidget(said)
        top.addStretch(1)
        column.addLayout(top)

        body = QHBoxLayout()
        body.setSpacing(16)
        column.addLayout(body)
        numbers = QGridLayout()
        numbers.setHorizontalSpacing(16)
        numbers.setVerticalSpacing(3)
        body.addLayout(numbers, 1)
        values = {}
        for row, (key, text) in enumerate((("total", "Total weight"), ("average", "Average weight"),
                                           ("unique", "Unique cards"))):
            caption = QLabel(text)
            caption.setObjectName("statsCaption")
            value = QLabel("0")
            value.setObjectName("statsValue")
            numbers.addWidget(caption, row, 0)
            numbers.addWidget(value, row, 1)
            values[key] = value
        kinds_caption = QLabel("Card types")
        kinds_caption.setObjectName("statsCaption")
        numbers.addWidget(kinds_caption, 3, 0, Qt.AlignmentFlag.AlignTop)
        kinds = QVBoxLayout()
        kinds.setSpacing(3)
        bar = PoolTypeBar()
        kinds.addWidget(bar)
        legend = {}
        legend_grid = QGridLayout()
        legend_grid.setHorizontalSpacing(10)
        legend_grid.setVerticalSpacing(1)
        for index, (name, colour) in enumerate(self.STAT_KINDS):
            line = QHBoxLayout()
            line.setSpacing(4)
            dot = QLabel("●")
            dot.setStyleSheet(f"color:{colour};")
            text = QLabel(name)
            text.setObjectName("statsCaption")
            count = QLabel("0")
            count.setObjectName("statsCaption")
            line.addWidget(dot)
            line.addWidget(text)
            line.addStretch(1)
            line.addWidget(count)
            legend_grid.addLayout(line, index // 2, index % 2)
            legend[name] = count
        kinds.addLayout(legend_grid)
        numbers.addLayout(kinds, 3, 1)
        numbers.setColumnStretch(1, 1)
        numbers.setRowStretch(4, 1)

        best_column = QVBoxLayout()
        best_column.setSpacing(2)
        body.addLayout(best_column, 1)
        best_caption = QLabel("Highest weights")
        best_caption.setObjectName("statsTitle")
        best_column.addWidget(best_caption)
        best_rows = []
        for place in range(5):
            line = QHBoxLayout()
            line.setSpacing(8)
            rank = QLabel(str(place + 1))
            rank.setObjectName("statsRank")
            rank.setFixedWidth(12)
            icon = QLabel()
            icon.setFixedSize(18, 18)
            icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name = QLabel("")
            name.setObjectName("statsCaption")
            weight = QLabel("")
            weight.setObjectName("statsCaption")
            line.addWidget(rank)
            line.addWidget(icon)
            line.addWidget(name, 1)
            line.addWidget(weight)
            best_column.addLayout(line)
            best_rows.append((rank, icon, name, weight))
        controls["stats"] = {"panel": panel, "values": values, "bar": bar, "legend": legend, "best": best_rows}
        parent_layout.addWidget(panel)

    POOL_CARD_KINDS = {gamedata.TYPE_MAGIC: "Magic", gamedata.TYPE_TRAP: "Traps",
                       gamedata.TYPE_RITUAL: "Rituals", gamedata.TYPE_EQUIP: "Equips"}

    def _pool_card_kind(self, cid) -> str:
        """What the card counts as: one of the twenty monster types, or the
        four the game keeps past them (card_constants.h)."""
        card = self.project.cards.get(cid)
        if card is None:
            return "Monsters"
        return self.POOL_CARD_KINDS.get(card.type, "Monsters")

    def _show_pool_statistics(self, weights):
        """Fill the panel from {card id: weight}; a card weighted 0 is not in
        the deal and is left out of all of it."""
        stats = self.workspace_controls["Duelists"].get("stats")
        if not stats:
            return
        held = {cid: weight for cid, weight in weights.items() if weight}
        total = sum(held.values())
        unique = len(held)
        stats["values"]["total"].setText(f"{total:,}")
        stats["values"]["average"].setText(f"{total / unique:.2f}" if unique else "0")
        stats["values"]["unique"].setText(str(unique))
        counts = {name: 0 for name, _colour in self.STAT_KINDS}
        for cid in held:
            counts[self._pool_card_kind(cid)] += 1
        for name, box in stats["legend"].items():
            share = counts[name] * 100 / unique if unique else 0
            box.setText(f"{counts[name]} ({share:.1f}%)")
        stats["bar"].show_counts([(counts[name], colour) for name, colour in self.STAT_KINDS])
        best = sorted(held.items(), key=lambda pair: (-pair[1], pair[0]))[:5]
        for place, (rank, icon, name, weight) in enumerate(stats["best"]):
            if place >= len(best):
                for widget in (rank, name, weight):
                    widget.setText("")
                icon.setPixmap(QPixmap())
                continue
            cid, value = best[place]
            rank.setText(str(place + 1))
            name.setText(self.project.cards[cid].name if cid in self.project.cards else str(cid))
            weight.setText(f"{value} ({value * 100 / total:.2f}%)" if total else str(value))
            picture = self._pool_card_icon(cid)
            icon.setPixmap(picture if picture is not None else QPixmap())

    def _pool_card_icon(self, cid):
        """A card's thumbnail for the statistics panel, kept between draws.
        A pool may name a card the mod does not have (the Problems page says
        so); there is no picture to draw for one."""
        cache = getattr(self, "_pool_icons", None)
        if cache is None:
            cache = self._pool_icons = {}
        if cid not in self.project.cards:
            return None
        if cid not in cache:
            try:
                picture = _card_image(self.project, self.preview_wa, cid, self.frame_cache)
                cache[cid] = picture.scaled(18, 18, Qt.AspectRatioMode.KeepAspectRatio,
                                            Qt.TransformationMode.SmoothTransformation)
            except (OSError, ValueError, IndexError, struct.error):
                cache[cid] = QPixmap()
        return cache[cid]

    def _refresh_duelist_pool(self,*_):
        if "Duelists" not in self.workspace_controls:return
        c=self.workspace_controls["Duelists"];d=self._selected_duelist();subject=self._selected_duelist_subject();name=self._selected_pool_name()
        if name is None:
            self._set_duelist_pool_editor_visible(False)
            c["master_k_notice"].setVisible(False)
            c["randomizer_page"].setVisible(True)
            self._refresh_drop_randomizer()
            return
        c["randomizer_page"].setVisible(False)
        player_deck = self._copies_player_deck()
        c["master_k_notice"].setVisible(player_deck)
        self._set_duelist_pool_editor_visible(not player_deck)
        if player_deck:
            return
        record=getattr(self,"duelist_slots",{}).get(getattr(self,"duelist_selected_slot",d))
        pool=roster.pools_of(self.project, subject)[name];retail=roster.retail_pool(self.project, subject, name)
        title=record["name"] if record else DUELIST_NAMES[d]
        if self._refresh_fixed_deck():
            return                      # the forty written down are what shows
        total=sum(pool.values())
        # The tab names and selected duelist already identify this pool. Keep
        # its header to the one useful figure: its current total weight.
        c["summary"].setText(f"{total:,}/{POOL_TOTAL:,} weight")
        c["summary"].setStyleSheet("color:#7fd49b" if total==POOL_TOTAL else "color:#ff7777")
        for button_name in ("addPoolCardButton","setPoolWeightButton","removePoolCardButton","normalizePoolButton","revertPoolButton"):
            button=c["page"].findChild(QPushButton,button_name)
            if button:button.setEnabled(True)
        rows=[]
        for cid in sorted(set(pool)|set(retail),key=lambda i:(-pool.get(i,0),i)):
            weight,before=pool.get(cid,0),retail.get(cid,0)
            if not weight and not before:continue
            card=self.project.cards.get(cid)
            state="" if weight==before else "added" if not before else "removed" if not weight else "changed"
            rows.append((cid,card.name if card else "?",type_name(self.project, card.type) if card else "",weight,
                         f"{weight*100/POOL_TOTAL:.2f}%",before,state.title()))
        self._show_pool_statistics(pool)
        table=c["table"];held=sort_paused(table);table.setRowCount(len(rows))
        for i,row in enumerate(rows):
            for col,value in enumerate(row):
                item=TableItem(str(value))
                if col==0:item.setData(Qt.ItemDataRole.UserRole,row[0])
                elif col==2:
                    row_card = self.project.cards.get(row[0])
                    if row_card is not None:
                        item.setIcon(type_icon(self, row_card.type))
                self._tint_state(item,row[6].lower())
                table.setItem(i,col,item)
        sort_resumed(table,held)

    def _copies_player_deck(self):
        """Whether the selected Deck tab is dealt from the player's cards.

        Custom roster entries keep their base opponent ID, so a copy of Duel
        Master K follows the same retail game branch and must be read-only too.
        """
        return (self._selected_pool_name() == "deck"
                and self._selected_duelist() == DUEL_MASTER_K_OPPONENT_ID)

    def _set_duelist_pool_editor_visible(self, visible):
        """Show the normal pool editor, or leave room for Randomizer.

        The two views share the duelist selection and the tab bar.  Keeping
        their widgets in the Designer form and only changing visibility keeps
        layout ownership with the UI file.
        """
        c = self.workspace_controls["Duelists"]
        c["summary"].setVisible(visible)
        self._show_fixed_widgets(c["mode_row"], visible)
        c["table"].setVisible(visible)
        self._show_fixed_widgets(c["pool_actions"], visible)
        c["fixed_table"].setVisible(visible)
        c["fixed_hint"].setVisible(visible)
        self._show_fixed_widgets(c["fixed_actions"], visible)
        stats = c.get("stats")
        if stats:
            stats["panel"].setVisible(visible)

    def _drop_randomizer_filter_wanted(self, cid, text):
        if not self._card_matches(cid, text):
            return False
        card = self.project.cards[cid]
        filters = getattr(self, "drop_randomizer_advanced_filters", {})
        if filters.get("types") and card.type not in filters["types"]:
            return False
        if filters.get("attributes") and card.attribute not in filters["attributes"]:
            return False
        bounds = filters.get("bounds", {})
        return (bulk_fusions._within(card.attack, bounds.get("atk_min"), bounds.get("atk_max"))
                and bulk_fusions._within(card.defense, bounds.get("def_min"), bounds.get("def_max"))
                and bulk_fusions._within(card.level, bounds.get("level_min"), bounds.get("level_max")))

    def _refresh_drop_randomizer(self):
        """Fill the checked-card catalogue from the active mod, not retail."""
        c = self.workspace_controls["Duelists"]
        table = c["randomizer_table"]
        selected = getattr(self, "drop_randomizer_selected", set())
        selected.intersection_update(self.project.cards)
        self._loading_drop_randomizer = True
        held = sort_paused(table)
        table.blockSignals(True)
        table.setRowCount(0)
        for row, cid in enumerate(sorted(self.project.cards)):
            card = self.project.cards[cid]
            table.insertRow(row)
            check = TableItem("")
            check.setData(Qt.ItemDataRole.UserRole, cid)
            check.setFlags(check.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            check.setCheckState(Qt.CheckState.Checked if cid in selected else Qt.CheckState.Unchecked)
            table.setItem(row, 0, check)
            values = (cid, card.name, type_name(self.project, card.type),
                      attribute_name(self.project, card.attribute), card.attack,
                      card.defense, card.level)
            for column, value in enumerate(values, 1):
                item = TableItem(str(value))
                if column == 3:
                    item.setIcon(type_icon(self, card.type))
                elif column == 4:
                    item.setIcon(attribute_icon(self, card.attribute))
                table.setItem(row, column, item)
        table.blockSignals(False)
        sort_resumed(table, held)
        self._loading_drop_randomizer = False
        self._filter_drop_randomizer(c["randomizer_search"].text())
        self._sync_drop_randomizer_actions()

    def _filter_drop_randomizer(self, text):
        c = self.workspace_controls.get("Duelists", {})
        table = c.get("randomizer_table")
        if table is None:
            return
        for row in range(table.rowCount()):
            item = table.item(row, 0)
            cid = item.data(Qt.ItemDataRole.UserRole) if item else None
            table.setRowHidden(row, cid is None or not self._drop_randomizer_filter_wanted(cid, text))

    def _toggle_drop_randomizer_card(self, item):
        if getattr(self, "_loading_drop_randomizer", False) or item.column() != 0:
            return
        cid = item.data(Qt.ItemDataRole.UserRole)
        if cid not in self.project.cards:
            return
        selected = getattr(self, "drop_randomizer_selected", set())
        if item.checkState() == Qt.CheckState.Checked:
            selected.add(cid)
        else:
            selected.discard(cid)
        self.drop_randomizer_selected = selected
        self._sync_drop_randomizer_actions()

    def _sync_drop_randomizer_actions(self):
        c = self.workspace_controls.get("Duelists", {})
        selected = getattr(self, "drop_randomizer_selected", set())
        count = len(selected)
        c["randomizer_count"].setText(
            "No cards checked" if not count else f"{count} card{'s' if count != 1 else ''} checked")
        for key in ("randomize_pow", "randomize_bcd", "randomize_tec"):
            c[key].setEnabled(bool(count))

    def _clear_drop_randomizer_filters(self):
        self.drop_randomizer_advanced_filters = {"types": set(), "attributes": set(), "bounds": {}}
        c = self.workspace_controls["Duelists"]
        self._filter_drop_randomizer(c["randomizer_search"].text())

    def _open_drop_randomizer_advanced_filter(self):
        source = QFile(str(Path(__file__).resolve().parents[1] / "ui" / "equip_filter_dialog.ui"))
        if not source.open(QIODevice.OpenModeFlag.ReadOnly):
            raise RuntimeError(f"Could not open card filter form: {source.errorString()}")
        try:
            dialog = QUiLoader().load(source, self)
        finally:
            source.close()
        if dialog is None:
            raise RuntimeError("Could not load card filter form")
        dialog.setWindowTitle("Drop randomizer filters")
        dialog.setModal(True)
        types = dialog.findChild(QListWidget, "equipFilterTypes")
        attributes = dialog.findChild(QListWidget, "equipFilterAttributes")
        edits = {key: dialog.findChild(QLineEdit, name) for key, name in (
            ("atk_min", "equipFilterAtkMin"), ("atk_max", "equipFilterAtkMax"),
            ("def_min", "equipFilterDefMin"), ("def_max", "equipFilterDefMax"),
            ("level_min", "equipFilterLevelMin"), ("level_max", "equipFilterLevelMax"))}
        filters = getattr(self, "drop_randomizer_advanced_filters", {})
        for listing, choices, selected in (
                (types, declared_type_choices(self.project), filters.get("types", set())),
                (attributes, declared_attribute_choices(self.project), filters.get("attributes", set()))):
            for value, label in choices:
                entry = QListWidgetItem(label)
                entry.setData(Qt.ItemDataRole.UserRole, value)
                entry.setFlags(entry.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                entry.setCheckState(Qt.CheckState.Checked if value in selected else Qt.CheckState.Unchecked)
                listing.addItem(entry)
        decorate_type_items(self, types)
        decorate_attribute_items(self, attributes)
        for key, edit in edits.items():
            value = filters.get("bounds", {}).get(key)
            edit.setText("" if value is None else str(value))
        dialog.findChild(QPushButton, "clearButton").clicked.connect(
            lambda: (self._clear_checkable_list(types), self._clear_checkable_list(attributes),
                     [edit.clear() for edit in edits.values()]))
        dialog.findChild(QPushButton, "cancelButton").clicked.connect(dialog.reject)
        dialog.findChild(QPushButton, "applyButton").clicked.connect(dialog.accept)
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
            QMessageBox.warning(self, "Drop randomizer filters", str(problem))
            return
        self.drop_randomizer_advanced_filters = {
            "types": {types.item(i).data(Qt.ItemDataRole.UserRole) for i in range(types.count())
                      if types.item(i).checkState() == Qt.CheckState.Checked},
            "attributes": {attributes.item(i).data(Qt.ItemDataRole.UserRole) for i in range(attributes.count())
                           if attributes.item(i).checkState() == Qt.CheckState.Checked},
            "bounds": bounds,
        }
        self._filter_drop_randomizer(self.workspace_controls["Duelists"]["randomizer_search"].text())
    def _fixed_deck(self):
        """The duelist's fixed deck, while the deck pool is the one shown."""
        if self._selected_pool_name() != "deck":
            return None
        return fixed_decks.deck_of(self.project, self._selected_duelist_subject())
    def _show_fixed_widgets(self, layout, visible):
        for index in range(layout.count()):
            item = layout.itemAt(index)
            if item.widget() is not None:
                item.widget().setVisible(visible)
    def _refresh_fixed_deck(self):
        """Which of the two the detail pane shows, and the fixed deck's rows."""
        c = self.workspace_controls.get("Duelists")
        if not c or "fixed_table" not in c:
            return False
        if self.project is not self.fixed_stash_of:
            self.fixed_stash, self.fixed_stash_of = {}, self.project
        on_deck = self._selected_pool_name() == "deck"
        self._show_fixed_widgets(c["mode_row"], on_deck)
        deck = self._fixed_deck()
        c["weighted_radio"].blockSignals(True)
        c["fixed_radio"].setChecked(deck is not None)
        c["weighted_radio"].setChecked(deck is None)
        c["weighted_radio"].blockSignals(False)
        fixed = deck is not None
        c["table"].setVisible(not fixed)
        self._show_fixed_widgets(c["pool_actions"], not fixed)
        c["fixed_table"].setVisible(fixed)
        c["fixed_hint"].setVisible(fixed)
        self._show_fixed_widgets(c["fixed_actions"], fixed)
        if not fixed:
            return False
        table = c["fixed_table"]
        table.blockSignals(True)
        held = sort_paused(table)
        table.setRowCount(0)
        weights = roster.pools_of(self.project, self._selected_duelist_subject())["deck"]
        for cid in sorted(deck.cards):
            copies = deck.cards[cid]
            card = self.project.cards.get(cid)
            notes = []
            if card is None:
                notes.append("no such card")
            if copies > DECK_COPY_LIMIT:
                notes.append(f"more than the weighted deal's {DECK_COPY_LIMIT}")
            weight = weights.get(cid, 0)
            row = table.rowCount()
            table.insertRow(row)
            kind = type_name(self.project, card.type) if card else ""
            for column, value in enumerate((cid, card.name if card else "?", kind, copies,
                                            f"{weight * 100 / POOL_TOTAL:.2f}%" if weight else "",
                                            ", ".join(notes))):
                item = TableItem(str(value))
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, cid)
                self._tint_state(item, "removed" if card is None else "")
                table.setItem(row, column, item)
        # A card the editor could not place keeps its row, so its copies are
        # not quietly lost.
        for name, copies in deck.kept.items():
            row = table.rowCount()
            table.insertRow(row)
            for column, value in enumerate(("", name, "", copies, "",
                                            "no such card; the deck is left out")):
                item = TableItem(str(value))
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, f"kept:{name}")
                self._tint_state(item, "removed")
                table.setItem(row, column, item)
        sort_resumed(table, held)
        table.blockSignals(False)
        total = deck.total()
        good = total == DECK_SIZE and not deck.kept
        title = DUELIST_NAMES[self._selected_duelist()]
        # The selected tab already says this is the deck: show only how many
        # cards it holds beside the tabs.
        c["summary"].setText(f"{total:,}/{DECK_SIZE:,} cards")
        c["summary"].setStyleSheet("color:#7fd49b" if good else "color:#ff7777")
        return True
    def _switch_deck_mode(self, *_):
        c = self.workspace_controls["Duelists"]
        if self._selected_pool_name() != "deck" or self._copies_player_deck():
            return
        duelist = self._selected_duelist_subject()
        stash_key = self._selected_duelist_stash_key()
        if c["fixed_radio"].isChecked():
            if fixed_decks.deck_of(self.project, duelist) is None:
                if self.fixed_stash.get(stash_key):
                    fixed_decks.restore(self.project, self.fixed_stash.pop(stash_key))
                else:
                    # A start that deals: the forty the weighted deck most
                    # likely deals. Clear starts from nothing.
                    fixed_decks.set_deck(self.project, duelist,
                                         fixed_decks.most_likely(roster.pools_of(self.project, duelist)["deck"]))
        else:
            taken = fixed_decks.remove(self.project, duelist)
            if taken:
                self.fixed_stash[stash_key] = taken
        self._fixed_edited()
    def _fixed_edited(self):
        deck = self._fixed_deck()
        if deck:
            for cid in [c for c, n in deck.cards.items() if not n]:
                del deck.cards[cid]
        self._mark_dirty()
        self._refresh_duelists()
    def _selected_fixed_rows(self):
        table = self.workspace_controls["Duelists"]["fixed_table"]
        return [table.item(row, 0).data(Qt.ItemDataRole.UserRole)
                for row in sorted({i.row() for i in table.selectedItems()}) if table.item(row, 0)]
    def _select_fixed_card(self):
        deck = self._fixed_deck()
        chosen = self._selected_fixed_rows()
        if deck and len(chosen) == 1 and isinstance(chosen[0], int):
            self.workspace_controls["Duelists"]["copies"].setValue(deck.cards.get(chosen[0], 0))
    def _add_fixed_card(self):
        if self._copies_player_deck():
            return
        deck = self._fixed_deck()
        if deck is None:
            return
        cid = self._choose_one_card("Card to add to the fixed deck")
        if not cid:
            return
        copies = self.workspace_controls["Duelists"]["copies"].value()
        deck.cards[cid] = copies if 0 < copies <= DECK_SIZE else 1
        self._fixed_edited()
    def _set_fixed_copies(self):
        if self._copies_player_deck():
            return
        deck = self._fixed_deck()
        if deck is None:
            return
        copies = self.workspace_controls["Duelists"]["copies"].value()
        for cid in self._selected_fixed_rows():
            if isinstance(cid, int):
                deck.cards[cid] = copies
        self._fixed_edited()
    def _remove_fixed_cards(self):
        if self._copies_player_deck():
            return
        deck = self._fixed_deck()
        if deck is None:
            return
        for cid in self._selected_fixed_rows():
            if isinstance(cid, str) and cid.startswith("kept:"):
                deck.kept.pop(cid[5:], None)
            else:
                deck.cards.pop(cid, None)
        self._fixed_edited()
    def _copy_weighted_deck(self):
        if self._copies_player_deck():
            return
        deck = self._fixed_deck()
        if deck is None:
            return
        if deck.cards:
            answer = QMessageBox.question(
                self, "Fixed deck",
                f"Replace the {deck.total()} cards of this fixed deck with the {DECK_SIZE} the "
                "weighted deck most likely deals?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                return
        duelist = self._selected_duelist_subject()
        fixed_decks.set_deck(self.project, duelist,
                             fixed_decks.most_likely(roster.pools_of(self.project, duelist)["deck"]))
        self._fixed_edited()
    def _clear_fixed_deck(self):
        if self._copies_player_deck():
            return
        deck = self._fixed_deck()
        if deck is None:
            return
        deck.cards, deck.kept = {}, {}
        self._fixed_edited()
    def _revert_fixed_deck(self):
        """Back to the disc's: no fixed deck, and the weighted deck retail's."""
        if self._copies_player_deck():
            return
        duelist = self._selected_duelist_subject()
        answer = QMessageBox.question(
            self, "Revert to retail",
            f"Deal {roster.label(self.project, duelist)} the disc's weighted deck again? "
            "The fixed deck and the weighted deck's edits are taken out.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        fixed_decks.remove(self.project, duelist)
        self.fixed_stash.pop(self._selected_duelist_stash_key(), None)
        if isinstance(duelist, int):
            self.project.revert_pool(duelist, "deck")
        else:
            roster.pools_of(self.project, duelist)["deck"] = dict(roster.retail_pool(self.project, duelist, "deck"))
        self._fixed_edited()
    def _select_pool_card(self):
        c=self.workspace_controls["Duelists"];row=c["table"].currentRow()
        if row>=0:c["weight"].setValue(int(c["table"].item(row,3).text()))
    def _add_pool_card(self):
        if self._copies_player_deck():
            return
        cid=self._choose_one_card("Add card to pool")
        if cid:
            d=self._selected_duelist_subject();pool=roster.pools_of(self.project, d)[self._selected_pool_name()]
            pool[cid]=max(1,self.workspace_controls["Duelists"]["weight"].value())
            self._mark_dirty();self._refresh_duelists()
            return cid
    def _selected_pool_cards(self):
        table=self.workspace_controls["Duelists"]["table"]
        return [table.item(row,0).data(Qt.ItemDataRole.UserRole)
                for row in sorted({x.row() for x in table.selectedItems()}) if table.item(row,0)]
    def _set_pool_weight(self):
        if self._copies_player_deck():
            return
        pool=roster.pools_of(self.project, self._selected_duelist_subject())[self._selected_pool_name()]
        weight=self.workspace_controls["Duelists"]["weight"].value()
        for cid in self._selected_pool_cards():
            if weight:pool[cid]=weight
            else:pool.pop(cid,None)
        self._mark_dirty();self._refresh_duelist_pool()
    def _remove_pool_cards(self):
        if self._copies_player_deck():
            return
        pool=roster.pools_of(self.project, self._selected_duelist_subject())[self._selected_pool_name()]
        for cid in self._selected_pool_cards():pool.pop(cid,None)
        self._mark_dirty();self._refresh_duelist_pool()
    def _normalize_pool(self):
        if self._copies_player_deck():
            return
        d=self._selected_duelist_subject();pool=self._selected_pool_name()
        roster.pools_of(self.project, d)[pool]=poolmath.normalize(roster.pools_of(self.project, d)[pool])
        self._mark_dirty();self._refresh_duelist_pool()
    def _randomize_selected_drop_pool(self, pool_name):
        """Build one award table from the checked cards at equal odds."""
        if pool_name not in ("pow", "bcd", "tec"):
            return []
        chosen = sorted(getattr(self, "drop_randomizer_selected", set()) & set(self.project.cards))
        if not chosen:
            return []
        roster.pools_of(self.project, self._selected_duelist_subject())[pool_name] = \
            poolmath.normalize({card_id: 1 for card_id in chosen})
        self._mark_dirty()
        self._refresh_duelists()
        self.statusBar().showMessage(
            f"Randomized {POOL_LABELS[pool_name]} from {len(chosen)} checked cards.", 8000)
        return chosen
    def _revert_pool(self):
        if self._copies_player_deck():
            return
        d=self._selected_duelist_subject();pool=self._selected_pool_name()
        if isinstance(d, int):
            self.project.revert_pool(d,pool)
        else:
            roster.pools_of(self.project, d)[pool] = dict(roster.retail_pool(self.project, d, pool))
        self._mark_dirty();self._refresh_duelists()
    def goto_duelist(self, duelist, pool):
        controls = self.workspace_controls["Duelists"]
        controls["search"].clear()
        slot = next((s for s, record in sorted(self._duelist_layout().items())
                     if record.get("base") == duelist), None)
        if slot is None:
            return
        self.duelist_selected_slot = slot
        controls["page"].setCurrentIndex(slot // 40)
        if pool in POOLS:
            controls["pool"].setCurrentIndex(POOLS.index(pool))
        self._refresh_duelists()
