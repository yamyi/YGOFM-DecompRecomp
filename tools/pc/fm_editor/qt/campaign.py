from __future__ import annotations

import copy
import json
import re
import struct
import sys
from pathlib import Path, PurePosixPath

from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QPoint, QRect, QSize, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QFont, QIcon, QImage, QPainter, QPen, QPixmap, QPolygon
from PySide6.QtWidgets import (QCheckBox, QComboBox, QGraphicsItem, QFileDialog, QInputDialog, QLabel, QLineEdit,
                               QDialog, QDialogButtonBox, QMessageBox, QPlainTextEdit,
                               QAbstractItemView, QPushButton, QSpinBox, QTableWidget, QTableWidgetItem,
                               QTreeWidget, QTreeWidgetItem, QVBoxLayout, QHBoxLayout,
                               QFormLayout, QGroupBox, QListWidget, QListWidgetItem, QSplitter, QWidget, QMenu,
                               QGraphicsScene, QGraphicsTextItem, QSizePolicy, QScrollArea, QTabWidget, QLayout,
                               QFrame, QHeaderView)

from .common import TableItem, sort_paused, sort_resumed


class CampaignMixin:
    _DIALOGUE_PORTRAIT_FIRST_EFFECT_ID = 0x41
    _DIALOGUE_PORTRAIT_LAST_EFFECT_ID = 0x59
    # Keep this in lockstep with ``known()`` in src/pc/campaign/scenes.c.
    # A previous version of the page exposed aspirational commands here (for
    # example choices, duels, portrait animation, rewards, and fades), but
    # the runtime rejected those documents while loading the mod.  The scene
    # editor must never make a command that it cannot save as a runnable mod.
    _CAMPAIGN_RUNTIME_COMMANDS = frozenset((
        "retail_command", "label", "jump", "call_scene", "return",
        "wait", "dialogue", "background", "music", "sound", "stop_music",
        "camera", "set_flag", "set_variable", "if", "teleport",
        "game_over", "credits", "main_menu",
    ))
    _CAMPAIGN_JSON_COMMANDS = (
        ("Music", "music"), ("Stop music", "stop_music"), ("Sound effect", "sound"),
        ("Camera", "camera"), ("Set / clear flag", "set_flag"),
        ("Set variable", "set_variable"), ("Branch on condition", "if"),
        ("Jump to label", "jump"),
        ("Label", "label"), ("Call scene", "call_scene"), ("Return", "return"),
        ("Teleport", "teleport"),
        ("Imported stock command", "retail_command"),
        ("Game over", "game_over"),
        ("Credits", "credits"), ("Return to menu", "main_menu"),
    )
    _CAMPAIGN_STEP_TYPES = (
        ("Dialogue", "dialogue"), ("Show character", "character"),
        ("Hide character", "hide_character"), ("Set background", "background"),
        ("Wait", "wait"), *_CAMPAIGN_JSON_COMMANDS,
        ("Advanced command (JSON)", "__raw__"),
    )

    def _campaign_controls(self):
        page = self.workspace_forms["Campaign"]
        controls = {}
        types = {
            "sceneTree": "scenes", "sceneStepTable": "steps", "campaignDataEdit": "assets_edit",
            "campaignStatusLabel": "status", "sceneSearchEdit": "search",
            "stepTypeDisplayLabel": "step_type_label", "stepCharacterCombo": "character",
            "stepPoseCombo": "pose", "stepPositionCombo": "position",
            "stepBackgroundCombo": "background", "stepDialogueEdit": "dialogue",
            "stepTextSpeedSpin": "number", "stepAutoContinueCheck": "keep_box",
            "stepPortraitPreview": "portrait_preview", "stepBackgroundPreview": "background_preview",
            "scenePreviewImage": "preview", "sceneStepsContextLabel": "scene_context",
            "stepEditorContextLabel": "step_context", "stepDialogueCountLabel": "dialogue_count",
            "stepDialogueLabel": "dialogue_label", "stepTextSpeedLabel": "number_label",
            "stepCharacterLabel": "character_label", "stepPortraitLabel": "pose_label",
            "stepPositionLabel": "position_label", "stepBackgroundLabel": "background_label",
            "showUiFrameCheck": "show_frame",
            "stepStructuredFieldsHost": "structured_host",
        }
        for object_name, key in types.items():
            cls = QWidget if key == "structured_host" else QSpinBox if key == "number" else QCheckBox if key == "keep_box" or key == "show_frame" \
                else QPlainTextEdit if key in ("assets_edit", "dialogue") else QLineEdit if key == "search" \
                else QTableWidget if key == "steps" else QTreeWidget if key == "scenes" \
                else QComboBox if key in ("character", "pose", "position", "background") \
                else QLabel
            widget = page.findChild(cls, object_name)
            if widget is not None:
                controls[key] = widget
        controls.update(
            timeline_scenes=page.findChild(QTreeWidget, "timelineSceneTree"),
            timeline_search=page.findChild(QLineEdit, "timelineSceneSearchEdit"),
            timeline_events=page.findChild(QTableWidget, "timelineEventTable"),
            timeline_preview=page.findChild(QLabel, "timelinePreviewImage"),
            timeline_context=page.findChild(QLabel, "timelineFlowContext"),
            timeline_track=page.findChild(QWidget, "timelineTrackView"),
            scene_id_edit=page.findChild(QLineEdit, "sceneIdEdit"),
            scene_name_edit=page.findChild(QLineEdit, "sceneNameEdit"),
            scene_notes_edit=page.findChild(QPlainTextEdit, "sceneNotesEdit"),
            asset_backgrounds=page.findChild(QListWidget, "sceneAssetBackgroundsList"),
            asset_portraits=page.findChild(QListWidget, "sceneAssetPortraitsList"),
            asset_audio=page.findChild(QListWidget, "sceneAssetAudioList"),
            asset_background_search=page.findChild(QLineEdit, "sceneAssetBackgroundsSearch"),
            asset_portrait_search=page.findChild(QLineEdit, "sceneAssetPortraitsSearch"),
            asset_audio_search=page.findChild(QLineEdit, "sceneAssetAudioSearch"),
        )
        if controls.get("timeline_track") is not None:
            graphics = QGraphicsScene(controls["timeline_track"])
            graphics.setBackgroundBrush(QColor("#0b1422"))
            controls["timeline_track"].setScene(graphics)
            controls["timeline_track"].setRenderHint(QPainter.RenderHint.Antialiasing, True)
            controls["timeline_graphics"] = graphics
        self._campaign_widgets = controls
        self._campaign_page = page
        for name, sizes in (("sceneColumnsSplitter", (250, 420, 330, 270)),
                            ("sceneWorkSplitter", (470, 650)),
                            ("scenesSplitter", (650, 270))):
            splitter = page.findChild(QSplitter, name)
            if splitter is not None:
                QTimer.singleShot(0, lambda target=splitter, values=sizes: target.setSizes(list(values)))
        # The campaign page is loaded before the main window is shown, so the
        # preview label may not have its final geometry during the first draw.
        QTimer.singleShot(0, self._campaign_preview_changed)
        QTimer.singleShot(120, self._campaign_preview_changed)
        if getattr(self, "_campaign_bound_page", None) is page:
            # This method is also called on every workspace refresh. Restore
            # the controls created dynamically on the first call instead of
            # losing their references (the Flags tab would otherwise look
            # valid but never receive rows).
            controls.update(
                flags_search=page.findChild(QLineEdit, "campaignFlagsSearch"),
                flags_table=page.findChild(QTableWidget, "campaignFlagsTable"),
                flags_details=page.findChild(QPlainTextEdit, "campaignFlagsDetails"),
            )
            return controls
        self._campaign_bound_page = page

        self._campaign_scene_buttons = {}
        self._campaign_step_buttons = {}
        for name, key in (("addSceneButton", "_campaign_add_scene"),
                          ("duplicateSceneButton", "_campaign_duplicate_scene"),
                          ("renameSceneButton", "_campaign_rename_scene"),
                          ("removeSceneButton", "_campaign_remove_scene"),
                          ("revertToRetailButton", "_campaign_revert_to_retail"),
                          ("moveStepUpButton", "_campaign_move_step_up"),
                          ("moveStepDownButton", "_campaign_move_step_down"),
                          ("duplicateStepButton", "_campaign_duplicate_step"),
                          ("removeStepButton", "_campaign_remove_step"),
                          ("browseBackgroundButton", "_campaign_browse_background"),
                          ("previousPortraitButton", "_campaign_previous_pose"),
                          ("nextPortraitButton", "_campaign_next_pose"),
                          ("insertDialogueTokenButton", "_campaign_insert_token")):
            button = page.findChild(QPushButton, name)
            if button is not None:
                button.clicked.connect(getattr(self, key))
                if name.endswith("SceneButton"):
                    self._campaign_scene_buttons[name] = button
                elif name.endswith("StepButton") or name in ("moveStepUpButton", "moveStepDownButton"):
                    self._campaign_step_buttons[name] = button
        self._campaign_step_editor = page.findChild(QWidget, "stepEditorPanel")
        add_button = page.findChild(QPushButton, "addStepButton")
        if add_button is not None:
            self._campaign_step_buttons["addStepButton"] = add_button
            add_button.setText("＋ Insert command")
            add_button.setToolTip("Choose a command type; it is inserted after the selected command.")
            menu = QMenu(add_button)
            for label, kind in self._CAMPAIGN_STEP_TYPES:
                action = menu.addAction(label)
                action.triggered.connect(lambda _checked=False, value=kind: self._campaign_add_step(value))
            add_button.setMenu(menu)
        export_button = page.findChild(QPushButton, "exportSceneFlowButton")
        if export_button is not None:
            export_button.clicked.connect(self._campaign_export_scene_flow)
        controls["scenes"].currentItemChanged.connect(self._campaign_scene_changed)
        controls["scenes"].itemDoubleClicked.connect(self._campaign_edit_scene_json)
        controls["steps"].itemSelectionChanged.connect(self._campaign_step_changed)
        controls["search"].textChanged.connect(self._campaign_fill_scene_tree)
        for key in ("scene_id_edit", "scene_name_edit"):
            if controls.get(key) is not None:
                controls[key].editingFinished.connect(self._campaign_metadata_edited)
        if controls.get("scene_notes_edit") is not None:
            controls["scene_notes_edit"].textChanged.connect(self._campaign_metadata_edited)
        if controls.get("timeline_scenes") is not None:
            controls["timeline_scenes"].currentItemChanged.connect(self._campaign_timeline_scene_changed)
        if controls.get("timeline_search") is not None:
            controls["timeline_search"].textChanged.connect(self._campaign_fill_timeline_scene_tree)
        if controls.get("timeline_events") is not None:
            controls["timeline_events"].itemSelectionChanged.connect(self._campaign_timeline_event_changed)
        if controls.get("timeline_graphics") is not None:
            controls["timeline_graphics"].selectionChanged.connect(self._campaign_timeline_graph_selected)
        timeline_export = page.findChild(QPushButton, "timelineExportButton")
        if timeline_export is not None:
            timeline_export.clicked.connect(self._campaign_export_scene_flow)
        controls["character"].currentIndexChanged.connect(self._campaign_editor_changed)
        controls["pose"].currentIndexChanged.connect(self._campaign_editor_changed)
        controls["position"].currentIndexChanged.connect(self._campaign_editor_changed)
        controls["background"].currentIndexChanged.connect(self._campaign_editor_changed)
        controls["dialogue"].textChanged.connect(self._campaign_editor_changed)
        controls["number"].valueChanged.connect(self._campaign_editor_changed)
        controls["keep_box"].toggled.connect(self._campaign_editor_changed)
        if controls.get("structured_host") is not None and controls["structured_host"].layout() is None:
            controls["structured_host"].setLayout(QVBoxLayout())
        controls["show_frame"].toggled.connect(self._campaign_preview_changed)
        controls["assets_edit"].textChanged.connect(self._campaign_assets_edited)
        self._campaign_setup_asset_library()
        self._campaign_setup_story_navigator()
        self._campaign_setup_simple_storyboard()
        self._campaign_setup_flags_tab()
        timeline_frame = page.findChild(QCheckBox, "timelineShowFrameCheck")
        if timeline_frame is not None:
            timeline_frame.toggled.connect(controls["show_frame"].setChecked)
            controls["show_frame"].toggled.connect(timeline_frame.setChecked)
        controls["number"].setMaximum(65535)
        return controls

    def _campaign_story_folder(self):
        value = self.project.other.get("story")
        if isinstance(value, str) and value.strip():
            path = PurePosixPath(value.strip())
            if not path.is_absolute() and ".." not in path.parts:
                return path.as_posix().rstrip("/")
        return ""

    def _campaign_read(self, relative):
        blob = self.project.files.get(relative)
        if blob is not None:
            return blob
        if self.project.source_dir:
            path = Path(self.project.source_dir) / Path(relative)
            try:
                return path.read_bytes() if path.is_file() else None
            except OSError:
                return None
        return None

    def _campaign_json(self, relative, default=None):
        raw = self._campaign_read(relative)
        if raw is None:
            return copy.deepcopy(default)
        try:
            return json.loads(raw.decode("utf-8-sig"))
        except (UnicodeError, ValueError) as error:
            raise ValueError(f"{relative}: {error}") from error

    def _campaign_store_json(self, relative, value):
        self.project.files[relative] = (json.dumps(value, ensure_ascii=False, indent=4) + "\n").encode("utf-8")

    def _campaign_scene_files(self, folder):
        found = {name for name in self.project.files if PurePosixPath(name).parent.as_posix() == folder
                 and name.lower().endswith(".json") and PurePosixPath(name).name != "assets.json"}
        if self.project.source_dir:
            path = Path(self.project.source_dir) / folder
            try:
                if path.is_dir():
                    found.update((Path(folder) / item.name).as_posix() for item in path.glob("*.json")
                                 if item.name != "assets.json")
            except OSError:
                pass
        return sorted(found)

    def _campaign_load(self, force=False):
        if not force and getattr(self, "_campaign_project", None) is self.project:
            return
        self._campaign_project = self.project
        self._campaign_dirty = False
        self._campaign_folder = self._campaign_story_folder()
        self._campaign_records = []
        self._campaign_stock_error = ""
        self._campaign_stock_records = self._campaign_read_stock_scenes()
        self._campaign_documents = {}
        self._campaign_new_records = []
        self._campaign_dialogue_edits = {}
        self._campaign_selected_id = None
        self._campaign_active_row = None
        self._campaign_loading = True
        folder = self._campaign_folder
        warning = ""
        if folder:
            for relative in self._campaign_scene_files(folder):
                try:
                    document = self._campaign_json(relative)
                except ValueError as error:
                    warning = str(error)
                    continue
                if isinstance(document, list):
                    scenes = [value for value in document if isinstance(value, dict)]
                elif isinstance(document, dict):
                    scenes = [document]
                else:
                    continue
                self._campaign_documents[relative] = scenes
                for scene in scenes:
                    if scene.get("id"):
                        self._campaign_records.append({"scene": scene, "path": relative})
            try:
                self._campaign_assets = self._campaign_json(f"{folder}/assets.json", {}) or {}
            except ValueError as error:
                self._campaign_assets = {}
                warning = str(error)
        else:
            self._campaign_assets = {}
        self._campaign_fill_scene_tree()
        self._campaign_widgets["assets_edit"].setPlainText(
            json.dumps(self._campaign_assets, ensure_ascii=False, indent=2) if self._campaign_folder else "")
        self._campaign_refresh_asset_library()
        self._campaign_refresh_flags()
        status = (f"Showing {len(self._campaign_stock_records)} retail scene(s) and "
                  f"{len(self._campaign_records)} mod scene(s). Story package: {folder}/. "
                  "Select a retail scene and click Edit override to make an editable mod replacement."
                  if folder else f"Showing {len(self._campaign_stock_records)} retail game scenes. "
                  "Add a mod scene package, then click Edit override on a retail scene to replace it.")
        if warning:
            status = f"Could not read story data: {warning}"
        if self._campaign_stock_error:
            status += f" Retail scenes could not be decoded: {self._campaign_stock_error}"
        self._campaign_say(self._campaign_widgets.get("status"), status)
        self._campaign_loading = False
        current = self._campaign_widgets["scenes"].currentItem()
        if current is not None:
            self._campaign_scene_changed(current, None)

    def _campaign_read_stock_scenes(self):
        """Decode the game's own script bank for the read-only retail list."""
        story_listing = None
        try:
            # story_listing.py is a sibling of the fm_editor package under
            # tools/pc, rather than a module inside fm_editor itself.
            pc_tools = str(Path(__file__).resolve().parents[2])
            if pc_tools not in sys.path:
                sys.path.insert(0, pc_tools)
            import story_listing

            bank = story_listing.read_bank(self.files.wa)
            blocks, offsets = story_listing.disassemble(bank)
            text = story_listing.GameText(self.files.slus)
            names = story_listing.name_everything(blocks, offsets, text)
        except Exception as error:
            self._campaign_stock_error = str(error)
            return []

        by_scene = {scene: block for block in blocks for scene in block.scenes}
        by_offset = {block.offset: block for block in blocks}
        instruction_by_offset = {instruction.offset: instruction for block in blocks
                                 for instruction in block.instructions}
        records = []
        command_names = {
            0: "End", 1: "Background", 2: "Dialogue", 3: "Condition", 4: "Stage background",
            5: "Show background", 6: "Pan", 7: "Continue pan", 8: "Map", 9: "Character",
            10: "Audio", 11: "Music fade", 12: "Jump", 13: "Save prompt", 14: "Unused command",
            15: "Unused command", 16: "Screen fade", 17: "Duel results", 18: "Game over",
            19: "Credits", 20: "Pause", 21: "Deck check", 22: "Main menu",
        }

        def step_rows(instruction):
            try:
                lines = story_listing._write_instruction(instruction, offsets, names, text)
            except story_listing.StoryError as error:
                lines = [f"Unparsed retail command: {error}"]
            kind = command_names.get(instruction.opcode, "Retail command")
            for line in lines:
                row = {"type": kind, "description": str(line),
                       "opcode": instruction.opcode,
                       "command_offset": f"0x{instruction.offset:04X}",
                       "picture_id": (instruction.u16() & 0xFFF)
                       if instruction.opcode in (1, 4) else None}
                if instruction.opcode == 2:
                    row["dialogue_id"] = instruction.u16() & 0xFFF
                    row["dialogue_text"] = text.string("dialog", row["dialogue_id"]) or ""
                if instruction.opcode == 9:
                    row["sprite_id"] = instruction.operands[0]
                    row["sprite_flags"] = instruction.operands[1]
                if instruction.opcode == 16:
                    row["screen_fade"] = True
                yield row

        def dialogue_flow_rows(instruction):
            """Flatten the dialogue CFG in play order, keeping each route visible."""
            identifier = instruction.u16() & 0xFFF
            bank = text.banks.get("dialog")
            start = bank.ids.get(identifier) if bank else None
            if start is None:
                yield from step_rows(instruction)
                return

            ops = text.ops["dialog"]
            command_offset = f"0x{instruction.offset:04X}"
            expanded_offsets = set()
            event_budget = max(4096, min(20000, len(ops) * 2))
            event_count = 0

            def linear_offsets(at):
                """Offsets along a route's ordinary continuation, respecting jumps."""
                result = []
                seen = set()
                while at in ops and at not in seen:
                    seen.add(at); result.append(at)
                    op = ops[at]
                    value = str(op.value or "")
                    if op.kind == "end" or (op.kind == "code" and
                            (value.startswith("choose") or value in ("f8 17", "f8 18"))):
                        break
                    if op.kind == "jump":
                        if not op.targets: break
                        at = op.targets[0]
                    else:
                        at += op.length
                return result

            def common_join(routes):
                if len(routes) < 2 or not routes[0]:
                    return None
                later = [set(route) for route in routes[1:]]
                return next((offset for offset in routes[0]
                             if all(offset in route for route in later)), None)

            def route_name(kind, index=None):
                if kind == "choice": return f"Choice {index + 1}"
                if kind == "condition": return "Condition met"
                return "Continuation"

            def emit(at, path=(), stop=None, active=frozenset()):
                stop = stop or set()
                text_buffer = []

                def flush_text():
                    value = "".join(text_buffer).strip()
                    text_buffer.clear()
                    if value:
                        description = value if not path else f"[{ ' / '.join(path) }] {value}"
                        yield {"type": "Dialogue", "description": description,
                               "command_offset": command_offset,
                               "dialogue_id": identifier,
                               "dialogue_text": value,
                               "branch_path": " / ".join(path)}

                nonlocal event_count
                while at in ops and at not in stop and at not in active:
                    if at in expanded_offsets:
                        return
                    expanded_offsets.add(at)
                    event_count += 1
                    if event_count > event_budget:
                        yield {"type": "Flow truncated",
                               "description": "Safety limit reached while expanding dialogue routes.",
                               "command_offset": command_offset, "dialogue_id": identifier,
                               "branch_path": " / ".join(path)}
                        return
                    op = ops[at]
                    value = str(op.value or "")
                    if op.kind == "glyph":
                        text_buffer.append(op.value if isinstance(op.value, str) else text.glyphs.get(op.value, "?"))
                        at += op.length
                        continue
                    if op.kind == "nl":
                        text_buffer.append("\n")
                        at += op.length
                        continue
                    yield from flush_text()
                    if op.kind == "end":
                        return
                    if op.kind == "jump":
                        yield {"type": "Dialogue branch", "description":
                               f"[{ ' / '.join(path) }] Jump to dialogue section" if path else "Jump to dialogue section",
                               "command_offset": command_offset, "dialogue_id": identifier,
                               "control_offset": f"0x{op.offset:04X}",
                               "branch_targets": [f"0x{target:04X}" for target in op.targets],
                               "branch_path": " / ".join(path)}
                        for target in op.targets:
                            yield from emit(target, (*path, "Jump target"), stop, active | {at})
                        return
                    if op.kind == "code" and value == "page":
                        yield {"type": "Dialogue page", "description":
                               f"[{ ' / '.join(path) }] Wait for page advance" if path else "Wait for page advance",
                               "command_offset": command_offset, "dialogue_id": identifier,
                               "control_offset": f"0x{op.offset:04X}", "branch_path": " / ".join(path)}
                        at += op.length
                        continue

                    targets = list(op.targets)
                    if op.kind == "code" and value.startswith("if ") and targets:
                        fallthrough = at + op.length
                        join = common_join([linear_offsets(targets[0]), linear_offsets(fallthrough)])
                        details = self._campaign_human_controls([{
                            "offset": f"0x{op.offset:04X}", "control": value,
                            "targets": [f"0x{target:04X}" for target in targets]}])
                        row = {"type": "Dialogue condition",
                               "description": (details[0].get("action", "Test dialogue condition")
                                               if details else "Test dialogue condition"),
                               "command_offset": command_offset, "dialogue_id": identifier,
                               "control_offset": f"0x{op.offset:04X}",
                               "branch_targets": [f"0x{target:04X}" for target in targets],
                               "branch_path": " / ".join(path)}
                        if path: row["description"] = f"[{ ' / '.join(path) }] {row['description']}"
                        yield row
                        if join is not None:
                            yield {"type": "Dialogue route", "description": "Condition met route",
                                   "command_offset": command_offset, "dialogue_id": identifier,
                                   "branch_path": " / ".join((*path, "Condition met"))}
                            yield from emit(targets[0], (*path, "Condition met"), {join}, active | {at})
                            yield {"type": "Dialogue route", "description": "Condition not met route",
                                   "command_offset": command_offset, "dialogue_id": identifier,
                                   "branch_path": " / ".join((*path, "Condition not met"))}
                            yield from emit(fallthrough, (*path, "Condition not met"), {join}, active | {at})
                            at = join
                            continue
                        yield {"type": "Dialogue route", "description": "Condition met route",
                               "command_offset": command_offset, "dialogue_id": identifier,
                               "branch_path": " / ".join((*path, "Condition met"))}
                        yield from emit(targets[0], (*path, "Condition met"), set(), active | {at})
                        yield {"type": "Dialogue route", "description": "Condition not met route",
                               "command_offset": command_offset, "dialogue_id": identifier,
                               "branch_path": " / ".join((*path, "Condition not met"))}
                        yield from emit(fallthrough, (*path, "Condition not met"), set(), active | {at})
                        return

                    is_choice_jump = (op.kind == "code" and
                                      (value.startswith("choose") or value in ("f8 17", "f8 18")))
                    if is_choice_jump and targets:
                        yield {"type": "Dialogue choice", "description":
                               f"Choice routes ({len(targets)} option(s))" +
                               (f" · {' / '.join(path)}" if path else ""),
                               "command_offset": command_offset, "dialogue_id": identifier,
                               "control_offset": f"0x{op.offset:04X}",
                               "branch_targets": [f"0x{target:04X}" for target in targets],
                               "branch_path": " / ".join(path)}
                        routes = [linear_offsets(target) for target in targets]
                        join = common_join(routes)
                        for index, target in enumerate(targets):
                            label = route_name("choice", index)
                            yield {"type": "Dialogue route", "description": label,
                                   "command_offset": command_offset, "dialogue_id": identifier,
                                   "control_offset": f"0x{op.offset:04X}",
                                   "branch_target": f"0x{target:04X}",
                                   "branch_path": " / ".join((*path, label))}
                            yield from emit(target, (*path, label), {join} if join is not None else set(),
                                            active | {at})
                        if join is not None:
                            yield from emit(join, (*path, "After choice"), stop, active | {at})
                        return

                    if op.kind == "code" and value == "call" and targets:
                        # Inserted text may be invoked from multiple call sites.
                        # Remove its offsets from the branch de-duplication set after
                        # the recursive expansion so each invocation stays visible.
                        call_offsets = set(linear_offsets(targets[0]))
                        already_expanded = call_offsets & expanded_offsets
                        expanded_offsets.difference_update(call_offsets)
                        yield from emit(targets[0], (*path, "Inserted text"), set(), active | {at})
                        expanded_offsets.update(already_expanded)
                        at += op.length
                        continue

                    raw_control = {"offset": f"0x{op.offset:04X}", "control": value,
                                   "targets": [f"0x{target:04X}" for target in targets]}
                    decoded = self._campaign_human_controls([raw_control])
                    detail = decoded[0] if decoded else {"action": "Dialogue control"}
                    action = str(detail.get("action", "Dialogue control"))
                    event_type = {
                        "Display dialogue picture": "Dialogue image",
                        "Clear dialogue picture": "Dialogue image hidden",
                        "Pan dialogue camera": "Dialogue camera",
                        "Play voice": "Dialogue voice",
                        "Play sound effect": "Dialogue sound",
                        "Fade out background music": "Music fade",
                        "Play background music": "Music",
                        "Stop background music": "Music stopped",
                        "Wait for dialogue": "Dialogue pause",
                        "Wait for page advance": "Dialogue page",
                        "Show dialogue choices": "Dialogue choice",
                        "Branch to selected dialogue choice": "Dialogue branch",
                    }.get(action, action)
                    fields = [f"{key.replace('_', ' ')} {item}" for key, item in detail.items()
                              if key not in ("step", "action", "destinations")]
                    description = action + (": " + ", ".join(fields) if fields else "")
                    row = {"type": event_type, "description": description,
                           "command_offset": command_offset, "dialogue_id": identifier,
                           "control_offset": f"0x{op.offset:04X}",
                           "branch_path": " / ".join(path)}
                    if path: row["description"] = f"[{ ' / '.join(path) }] {description}"
                    if "picture_id" in detail:
                        row["picture_id"] = detail["picture_id"]
                    if detail.get("action") == "Clear dialogue picture":
                        row["clear_picture"] = True
                    for key in ("effect_id", "effect_name", "flags", "flags_hex", "flag_summary"):
                        if key in detail:
                            row[key] = detail[key]
                    yield row
                    at += op.length

                yield from flush_text()

            yield from emit(start)

        def dialogue_controls(instruction):
            """List, without rewriting, all nested text-bank control records."""
            if instruction.opcode != 2:
                return []
            bank = text.banks.get("dialog")
            if bank is None:
                return []
            start = bank.ids.get(instruction.u16() & 0xFFF)
            if start is None:
                return []
            ops = text.ops["dialog"]
            pending = [start]
            visited = set()
            controls = []
            while pending:
                at = pending.pop()
                while at in ops and at not in visited:
                    visited.add(at)
                    op = ops[at]
                    if op.kind == "code":
                        controls.append({
                            "offset": f"0x{op.offset:04X}",
                            "control": str(op.value or ""),
                            "targets": [f"0x{target:04X}" for target in op.targets],
                        })
                    pending.extend(target for target in op.targets if target)
                    if op.kind in ("end", "jump"):
                        break
                    at += op.length
            return controls

        def dialogue_flow(instruction):
            """Build a readable node graph from one dialogue's decoded stream."""
            if instruction.opcode != 2:
                return None
            bank = text.banks.get("dialog")
            if bank is None:
                return None
            identifier = instruction.u16() & 0xFFF
            start = bank.ids.get(identifier)
            if start is None:
                return None
            ops = text.ops["dialog"]
            ordered = []
            visited = set()
            pending = [start]
            while pending:
                at = pending.pop()
                while at in ops and at not in visited:
                    visited.add(at)
                    op = ops[at]
                    ordered.append(op)
                    pending.extend(target for target in reversed(op.targets) if target)
                    value = str(op.value or "")
                    is_choice_jump = value.startswith("choose") or value.startswith("f8 17") or value.startswith("f8 18")
                    is_script_jump = op.kind == "jump" or value == "jump"
                    if op.kind == "end" or is_script_jump or is_choice_jump:
                        break
                    at += op.length

            units = []
            op_to_unit = {}
            i = 0
            while i < len(ordered):
                op = ordered[i]
                if op.kind in ("glyph", "nl"):
                    offsets = []
                    content = []
                    last_item = None
                    while i < len(ordered) and ordered[i].kind in ("glyph", "nl") and (
                            not offsets or ordered[i].offset == offsets[-1] + ordered[i - 1].length):
                        item = ordered[i]
                        last_item = item
                        offsets.append(item.offset)
                        if item.kind == "nl":
                            content.append("\n")
                        else:
                            content.append(item.value if isinstance(item.value, str)
                                           else text.glyphs.get(item.value, "?"))
                        i += 1
                    unit = {"id": f"dialogue_step_{len(units) + 1:03d}",
                            "action": "Show dialogue text", "text": "".join(content),
                            "_offset": offsets[0],
                            "_length": last_item.offset + last_item.length - offsets[0],
                            "_targets": [], "_kind": "text", "_raw_value": ""}
                    for offset in offsets:
                        op_to_unit[offset] = unit["id"]
                    units.append(unit)
                    continue

                raw = {"offset": f"0x{op.offset:04X}", "control": str(op.value or ""),
                       "targets": [f"0x{target:04X}" for target in op.targets]}
                decoded = self._campaign_human_controls([raw])
                detail = decoded[0] if decoded else {"action": "Dialogue control"}
                unit = {"id": f"dialogue_step_{len(units) + 1:03d}",
                        "action": detail.get("action", "Dialogue control")}
                for key, value in detail.items():
                    if key not in ("step", "action", "destinations"):
                        unit[key] = value
                op_to_unit[op.offset] = unit["id"]
                unit["_offset"] = op.offset
                unit["_length"] = op.length
                unit["_targets"] = list(op.targets)
                unit["_kind"] = op.kind
                unit["_raw_value"] = str(op.value or "")
                units.append(unit)
                i += 1

            # Connect each dialogue node using decoded fallthrough and branch
            # targets. The serialized graph contains no bank addresses.
            for unit in units:
                offset = unit.pop("_offset", None)
                length = unit.pop("_length", 0)
                targets = unit.pop("_targets", [])
                kind = unit.pop("_kind", "")
                raw_value = unit.pop("_raw_value", "")
                is_choice_jump = raw_value.startswith("choose") or raw_value.startswith("f8 17") or raw_value.startswith("f8 18")
                is_script_jump = kind == "jump" or raw_value == "jump"
                destinations = [op_to_unit[target] for target in targets if target in op_to_unit]
                if is_choice_jump or is_script_jump:
                    if destinations:
                        unit["branches"] = [{"to": target} for target in destinations]
                elif destinations:
                    unit["branches"] = [{"when": "condition is met", "to": target}
                                         for target in destinations]
                next_offset = offset + length if offset is not None else None
                next_node = op_to_unit.get(next_offset)
                if next_node and not is_choice_jump and not is_script_jump and kind != "end":
                    unit["next"] = next_node

            return {"entry": units[0]["id"] if units else None, "steps": units}

        for number in range(len(offsets)):
            block = by_scene.get(number)
            steps = []
            imported_commands = []
            if block is not None:
                # Walk both outcomes of conditional commands and every local
                # jump. The former importer followed only the linear path and
                # silently dropped alternate campaign branches.
                reachable = set()
                pending = [block.offset]
                while pending:
                    cursor = pending.pop()
                    if cursor in reachable or cursor not in by_offset:
                        continue
                    reachable.add(cursor)
                    current = by_offset[cursor]
                    for instruction in current.instructions:
                        pending.extend(target for target in story_listing._targets(instruction)
                                       if target not in reachable)
                    if current.instructions:
                        last = current.instructions[-1]
                        if last.opcode not in story_listing.ENDS:
                            pending.append(last.offset + last.length)
                # Expand branches where encountered and resume at their shared join.
                allowed = {instruction.offset for offset in reachable
                           for instruction in by_offset[offset].instructions}
                instructions = []

                linear_command_cache = {}

                def linear_command_offsets(at):
                    origin = at
                    if origin in linear_command_cache:
                        return linear_command_cache[origin]
                    route = []
                    seen = set()
                    while at in allowed and at in instruction_by_offset and at not in seen:
                        seen.add(at)
                        route.append(at)
                        current = instruction_by_offset[at]
                        targets = story_listing._targets(current)
                        if current.opcode == 12:
                            if not targets: break
                            at = targets[0]
                        elif current.opcode in story_listing.ENDS:
                            break
                        else:
                            at += current.length
                    linear_command_cache[origin] = route
                    return route

                def shared_join(routes):
                    if len(routes) < 2: return None
                    others = [set(route) for route in routes[1:]]
                    return next((offset for offset in routes[0]
                                 if all(offset in route for route in others)), None)

                def add_route(description, target, path):
                    instructions.append((None, {"description": description, "target": target, "path": path}))

                walked_commands = set()
                command_budget = min(50000, max(4096, len(allowed) * 2))

                def walk_commands(at, path=(), stop=None, active=frozenset()):
                    stop = stop or set()
                    while (at in allowed and at in instruction_by_offset and at not in stop
                           and at not in active and at not in walked_commands
                           and len(walked_commands) < command_budget):
                        walked_commands.add(at)
                        current = instruction_by_offset[at]
                        instructions.append((current, path))
                        targets = story_listing._targets(current)
                        fallthrough = at + current.length
                        if current.opcode == 12:
                            if targets:
                                label = f"Jump to {targets[0]:04X}"
                                add_route(label, targets[0], (*path, label))
                                walk_commands(targets[0], (*path, label), stop, active | {at})
                            return
                        if current.opcode in (3, 21) and targets:
                            target = targets[0]
                            join = shared_join([linear_command_offsets(target),
                                                linear_command_offsets(fallthrough)])
                            taken, skipped = (("Condition met", "Condition not met") if current.opcode == 3
                                              else ("Deck check branch", "Deck check fallthrough"))
                            add_route(f"{taken} → {target:04X}", target, (*path, taken))
                            walk_commands(target, (*path, taken), {join} if join is not None else set(), active | {at})
                            if join is None:
                                add_route(skipped, fallthrough, (*path, skipped))
                                walk_commands(fallthrough, (*path, skipped), set(), active | {at})
                                return
                            add_route(skipped, fallthrough, (*path, skipped))
                            walk_commands(fallthrough, (*path, skipped), {join}, active | {at})
                            at = join
                            continue
                        if current.opcode in story_listing.ENDS: return
                        at = fallthrough

                walk_commands(block.offset)
                target_offsets = {target for instruction, _path in instructions
                                  if instruction is not None
                                  for target in story_listing._targets(instruction)}
                target_offsets.add(block.offset)
                label_ids = {offset: f"retail_{number:03d}_{offset:04X}"
                             for offset in target_offsets}
                for instruction, route in instructions:
                    if instruction is None:
                        marker = route
                        steps.append({"type": "Route", "description": marker["description"],
                                      "branch_path": " / ".join(marker["path"]),
                                      "command_offset": f"0x{marker['target']:04X}"})
                        continue
                    if instruction.offset in label_ids:
                        imported_commands.append({"command": "label", "id": label_ids[instruction.offset]})
                    opcode = instruction.opcode
                    imported = {"command": "retail_command", "opcode": opcode,
                                "offset": f"0x{instruction.offset:04X}",
                                "operands": list(instruction.operands)}
                    branch_offsets = story_listing._targets(instruction)
                    if branch_offsets:
                        imported["branch_targets"] = [
                            {"offset": f"0x{target:04X}", "label": label_ids.get(target, f"{target:04X}")}
                            for target in branch_offsets]
                    fallthrough = instruction.offset + instruction.length
                    if opcode not in story_listing.ENDS and opcode != 12:
                        imported["fallthrough_offset"] = f"0x{fallthrough:04X}"
                    try:
                        words = story_listing._write_instruction(instruction, offsets, names, text)
                    except story_listing.StoryError:
                        words = []
                    imported["editor_label"] = (words[0].strip() if words else
                                                 f"Retail opcode {opcode:02d}")
                    if route:
                        imported["flow_path"] = " / ".join(route)
                    if opcode == 2:
                        dialogue_id = instruction.u16() & 0xFFF
                        imported["dialogue_id"] = dialogue_id
                        imported["dialogue_text"] = text.string("dialog", dialogue_id) or ""
                        embedded = dialogue_controls(instruction)
                        if embedded:
                            imported["embedded_controls"] = embedded
                        flow = dialogue_flow(instruction)
                        if flow:
                            imported["dialogue_flow"] = flow
                    imported_commands.append(imported)
                    rows = dialogue_flow_rows(instruction) if opcode == 2 else step_rows(instruction)
                    for line in rows:
                        if route:
                            line["branch_path"] = " / ".join(route)
                            line["description"] = f"[{line['branch_path']}] {line['description']}"
                        if opcode in (3, 12, 21):
                            target = instruction.u16(2) if opcode == 3 else instruction.u16()
                            branch_label = label_ids.get(target, f"{target:04X}")
                            line["branch_target"] = branch_label
                            line["description"] = f"{line['description']}  → {branch_label}"
                        steps.append(line)
            label = names.name("scene", number)
            scene = {"id": f"retail_{number:03d}", "name": label, "scene_number": number}
            records.append({"scene": scene, "path": "Retail game", "stock": True,
                            "steps": steps, "commands": imported_commands,
                            "token": ("retail", number)})
        return records

    def _campaign_fill_scene_tree(self, *_):
        c = getattr(self, "_campaign_widgets", {})
        tree = c.get("scenes")
        if tree is None:
            return
        if not getattr(self, "_campaign_loading", False):
            if not self._campaign_commit_step():
                return
            self._campaign_active_row = None
        selected = self._campaign_selected_id
        query = c["search"].text().casefold().strip()
        tree.blockSignals(True)
        tree.clear()
        restore = None
        for record in [*self._campaign_stock_records, *self._campaign_records]:
            scene = record["scene"]
            if record.get("stock"):
                label = f"{int(scene['scene_number']):03d}  ·  {scene.get('name', 'Retail scene')}"
                token = record["token"]
                meta = f"Retail game · scene {scene['scene_number']:03d} · use Edit override to modify"
            else:
                label = str(scene.get("name") or scene.get("id") or "Unnamed scene")
                token = scene.get("id")
                meta = f"{scene.get('id', '')}  ·  {record['path']} · mod"
            searchable = [label, meta,str(scene.get("notes", ""))]
            searchable.extend(str(value) for step in record.get("steps", [])
                              for value in (step.get("description", ""), step.get("dialogue_text", "")))
            searchable.extend(str(value) for command in record.get("commands", [])
                              for value in (command.get("editor_label", ""), command.get("dialogue_text", "")))
            if query and not any(query in part.casefold() for part in searchable):
                continue
            item = QTreeWidgetItem([label])
            item.setToolTip(0, meta)
            item.setData(0, Qt.ItemDataRole.UserRole, token)
            tree.addTopLevelItem(item)
            if scene.get("id") == selected:
                restore = item
        if restore is None and tree.topLevelItemCount():
            restore = tree.topLevelItem(0)
        if restore is not None:
            tree.setCurrentItem(restore)
        tree.blockSignals(False)
        if restore is not None:
            self._campaign_scene_changed(restore, None)
        else:
            self._campaign_selected_id = None
            c["steps"].setRowCount(0)
            c["preview"].setText("No scenes match this search.")
        self._campaign_fill_timeline_scene_tree()

    def _campaign_fill_timeline_scene_tree(self, *_):
        c = getattr(self, "_campaign_widgets", {})
        tree = c.get("timeline_scenes")
        if tree is None:
            return
        query = c.get("timeline_search").text().casefold().strip() if c.get("timeline_search") else ""
        selected = getattr(self, "_campaign_selected_id", None)
        tree.blockSignals(True)
        tree.clear()
        restore = None
        for record in [*self._campaign_stock_records, *self._campaign_records]:
            scene = record["scene"]
            if record.get("stock"):
                label = f"{int(scene['scene_number']):03d}  ·  {scene.get('name', 'Retail scene')}"
                token = record["token"]
            else:
                label = str(scene.get("name") or scene.get("id") or "Unnamed scene")
                token = scene.get("id")
            searchable = (label, str(token), str(scene.get("chapter", "")),
                          str(scene.get("location", "")))
            if query and not any(query in value.casefold() for value in searchable):
                continue
            item = QTreeWidgetItem([label])
            item.setData(0, Qt.ItemDataRole.UserRole, token)
            tree.addTopLevelItem(item)
            if token == selected:
                restore = item
        if restore is not None:
            tree.setCurrentItem(restore)
        elif tree.topLevelItemCount():
            restore = tree.topLevelItem(0)
            tree.setCurrentItem(restore)
        tree.blockSignals(False)
        if restore is not None:
            self._campaign_timeline_scene_changed(restore, None)

    def _campaign_timeline_scene_changed(self, current, _previous):
        if current is None:
            return
        token = current.data(0, Qt.ItemDataRole.UserRole)
        primary = self._campaign_widgets["scenes"]
        for index in range(primary.topLevelItemCount()):
            item = primary.topLevelItem(index)
            if item.data(0, Qt.ItemDataRole.UserRole) == token:
                primary.setCurrentItem(item)
                return
        # The two scene browsers have independent search fields. Clear the
        # editor filter when a timeline-only search selects a hidden scene.
        search = self._campaign_widgets.get("search")
        if search is not None and search.text():
            search.clear()
            for index in range(primary.topLevelItemCount()):
                item = primary.topLevelItem(index)
                if item.data(0, Qt.ItemDataRole.UserRole) == token:
                    primary.setCurrentItem(item)
                    return

    def _campaign_populate_timeline(self):
        c = getattr(self, "_campaign_widgets", {})
        table = c.get("timeline_events")
        if table is None:
            return
        token = getattr(self, "_campaign_selected_id", None)
        stock = next((r for r in self._campaign_stock_records if r["token"] == token), None)
        if stock is not None:
            # The editor and timeline must address the same command rows.
            # ``stock['steps']`` is an intentionally expanded diagnostic walk
            # through every branch (and can contain the same native command
            # more than once).  Using it here made the timeline's row N point
            # at a different command than editor row N.
            outline = getattr(self, "_campaign_visible_stock_steps", None)
            if not isinstance(outline, list):
                outline = self._campaign_stock_outline(stock)
            rows = [(s.get("type", "Command"), s.get("description", "")) for s in outline]
            context = (f"Retail scene {stock['scene'].get('scene_number', 0):03d} · "
                       f"{len(rows)} native command(s) · read top to bottom; branch targets stay explicit")
        else:
            rows = [(phase.replace("on_", "") if phase != "commands" else "Scene",
                     self._campaign_step_description(command))
                    for phase, _index, command in self._campaign_step_refs()]
            scene = self._campaign_scene() or {}
            context = f"{scene.get('name', token or 'Scene')} · {len(rows)} event(s)"
        table.blockSignals(True)
        table.setRowCount(len(rows))
        for row, (kind, description) in enumerate(rows):
            for col, value in enumerate((str(row + 1), str(kind), str(description))):
                cell = QTableWidgetItem(value)
                cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
                cell.setData(Qt.ItemDataRole.UserRole, row)
                table.setItem(row, col, cell)
        table.blockSignals(False)
        if c.get("timeline_context") is not None:
            c["timeline_context"].setText(context)
        graphics = c.get("timeline_graphics")
        if graphics is not None:
            self._campaign_timeline_drawing = True
            graphics.clear()
            # A command is a labelled card in a stream, not an anonymous
            # pixel.  It deliberately uses order rather than elapsed time:
            # waits and dialogue can take variable time at runtime.
            width_per_event = 156
            left = 118
            lane_height = 30
            lanes = ("Background", "Portraits", "Dialogue", "Audio", "Effects", "Flow", "Other")
            colors = ("#355fc8", "#b34d9b", "#138b85", "#bb741f", "#ce4a4a", "#7452be", "#52647d")
            row_by_type = {}
            for row, (kind, description) in enumerate(rows):
                folded = kind.casefold()
                lane = (0 if any(word in folded for word in ("background", "image")) else
                        1 if any(word in folded for word in ("character", "portrait", "sprite")) else
                        2 if any(word in folded for word in ("dialogue", "choice", "text")) else
                        3 if any(word in folded for word in ("music", "audio", "voice", "sound")) else
                        4 if any(word in folded for word in ("fade", "effect", "camera", "shake", "flash")) else
                        5 if any(word in folded for word in ("branch", "condition", "jump", "flow", "duel")) else 6)
                row_by_type[row] = lane
            for lane, label in enumerate(lanes):
                y = lane * lane_height
                graphics.addLine(left - 4, y + 24, left + max(1, len(rows)) * width_per_event, y + 24,
                                 QPen(QColor("#2b3b50")))
                text = graphics.addText(label)
                text.setDefaultTextColor(QColor("#aebdd0"))
                text.setPos(4, y + 4)
            for row, (kind, description) in enumerate(rows):
                lane = row_by_type[row]
                x = left + row * width_per_event
                y = lane * lane_height + 4
                block = graphics.addRect(x, y, 146, 22, QPen(QColor(colors[lane])),
                                         QBrush(QColor(colors[lane])))
                block.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
                block.setData(0, row)
                block.setToolTip(f"{row + 1}. {kind}\n{description}")
                caption = graphics.addText(f"{row + 1}. {kind}"[:22])
                caption.setDefaultTextColor(QColor("white"))
                caption.setPos(2, -1)
                caption.setParentItem(block)
            # Draw the local control-flow links over the stream. Cross-scene
            # calls remain labelled on their card: their destination belongs
            # to a separate scene graph and must not be mistaken for a local
            # fall-through arrow.
            if stock is None:
                refs = self._campaign_step_refs()
                labels = {command.get("id"): row for row, (_phase, _index, command) in enumerate(refs)
                          if command.get("command") == "label" and command.get("id")}
                for row, (_phase, _index, command) in enumerate(refs):
                    targets = []
                    if command.get("command") == "jump":
                        targets = [command.get("to")]
                    elif command.get("command") == "if":
                        targets = [command.get("then"), command.get("else")]
                    for target in filter(None, targets):
                        target_row = labels.get(target)
                        pen = QPen(QColor("#f2bf4a") if target_row is not None else QColor("#dc5967"))
                        pen.setStyle(Qt.PenStyle.DashLine if target_row is None else Qt.PenStyle.SolidLine)
                        if target_row is None:
                            graphics.addLine(left + row * width_per_event + 73, lane_height * len(lanes),
                                             left + row * width_per_event + 73, lane_height * len(lanes) + 16, pen)
                            continue
                        source_lane, target_lane = row_by_type[row], row_by_type[target_row]
                        x1, y1 = left + row * width_per_event + 73, source_lane * lane_height + 26
                        x2, y2 = left + target_row * width_per_event + 73, target_lane * lane_height + 4
                        graphics.addLine(x1, y1, x2, y2, pen)
                for row, (_phase, _index, command) in enumerate(refs):
                    if command.get("command") == "call_scene":
                        note = graphics.addText("→ " + str(command.get("scene", "missing scene"))[:15])
                        note.setDefaultTextColor(QColor("#f2bf4a"))
                        note.setPos(left + row * width_per_event, row_by_type[row] * lane_height + 25)
            canvas_width = max(640, left + len(rows) * width_per_event + 12)
            graphics.setSceneRect(0, 0, canvas_width, lane_height * len(lanes) + 22)
            self._campaign_timeline_drawing = False
        row = self._campaign_widgets["steps"].currentRow()
        if 0 <= row < table.rowCount():
            table.selectRow(row)

    def _campaign_timeline_graph_selected(self):
        if getattr(self, "_campaign_timeline_drawing", False):
            return
        graphics = self._campaign_widgets.get("timeline_graphics")
        if graphics is None:
            return
        row = next((item.data(0) for item in graphics.selectedItems()
                    if item.data(0) is not None), None)
        if isinstance(row, int) and row >= 0:
            table = self._campaign_widgets.get("timeline_events")
            if table is not None and row < table.rowCount():
                table.selectRow(row)

    def _campaign_timeline_event_changed(self):
        row = self._campaign_widgets["timeline_events"].currentRow()
        if row < 0:
            return
        graphics = self._campaign_widgets.get("timeline_graphics")
        if graphics is not None:
            graphics.blockSignals(True)
            for item in graphics.selectedItems():
                item.setSelected(False)
            target = next((item for item in graphics.items()
                           if item.data(0) == row), None)
            if target is not None:
                target.setSelected(True)
            graphics.blockSignals(False)
        steps = self._campaign_widgets["steps"]
        if row < steps.rowCount():
            steps.selectRow(row)
            # selectRow() emits nothing when the same row was already active.
            # Refresh explicitly so the inspector follows timeline selection.
            self._campaign_step_changed()

    def _campaign_scene(self):
        for record in getattr(self, "_campaign_records", []):
            if record["scene"].get("id") == getattr(self, "_campaign_selected_id", None):
                return record["scene"]
        return None

    @staticmethod
    def _campaign_stock_outline(stock):
        """The readable, non-duplicated version of a retail scene.

        Retail scene decoding deliberately expands both sides of every branch
        for the timeline.  Showing that expansion in the normal editor made a
        four-command scene look like a wall of duplicated routes.  The scene
        outline instead has one line per native command; the Timeline tab is
        where a reader can inspect every route and embedded dialogue control.
        """
        friendly = {
            0: "End scene", 1: "Show background", 2: "Show text", 3: "Story condition",
            4: "Prepare background", 5: "Show prepared background", 6: "Move camera",
            7: "Continue camera move", 8: "Open map", 9: "Show character",
            10: "Play music / sound", 11: "Fade music", 12: "Go to another point",
            13: "Offer save", 16: "Fade screen", 17: "Show duel results",
            18: "Game over", 19: "Show credits", 20: "Wait", 21: "Check deck",
            22: "Return to menu",
        }
        source_steps = stock.get("steps", [])
        by_offset = {}
        visual_controls = {}
        dialogue_started = set()
        for step in source_steps:
            offset = step.get("command_offset")
            if offset and offset not in by_offset:
                by_offset[offset] = step
            # Dialogue F6 controls are real visible events, not incidental
            # metadata.  Keep their own row in the simple command stream so
            # an author can see a character arrive before its text begins.
            if (offset and offset not in dialogue_started and
                    step.get("type") in ("Show portrait", "Show shared effect") and
                    not (int(step.get("flags", 0)) & 0x80)):
                controls = visual_controls.setdefault(offset, [])
                signature = (step.get("effect_id"), step.get("flags", 0))
                if not any((item.get("effect_id"), item.get("flags", 0)) == signature
                               for item in controls):
                    controls.append(step)
            if offset and step.get("type") == "Dialogue":
                dialogue_started.add(offset)
        result, seen = [], set()
        previous_path = None
        # ``commands`` is emitted by the decoded control-flow walk.  Preserve
        # that order: command addresses are storage locations, not story
        # order, and sorting them can put a later branch before the event that
        # leads to it.
        for command in stock.get("commands", []):
            if command.get("command") == "label":
                continue
            offset = command.get("offset")
            if not offset or offset in seen:
                continue
            seen.add(offset)
            opcode = command.get("opcode")
            source = by_offset.get(offset, {})
            description = str(command.get("dialogue_text") or command.get("editor_label") or
                              source.get("description") or "")
            # Branch-walk annotations are useful diagnostic data, but not the
            # sentence an author needs while reading their story.
            description = re.sub(r"^\[[^\]]+\]\s*", "", description).strip()
            if opcode in (3, 12, 21):
                targets = command.get("branch_targets") or []
                names = [str(target.get("label") or target.get("offset") or "next point")
                         for target in targets if isinstance(target, dict)]
                if names:
                    description = f"{description}  → {' / '.join(names)}"
            # A retail branch is not a single linear list.  Mark only the
            # first command in each decoded route, keeping the stream short
            # while making it clear why a later command follows a condition.
            path = str(command.get("flow_path") or "").strip()
            if path and path != previous_path:
                description = f"↳ Route: {path} — {description}"
            previous_path = path
            if not description:
                description = friendly.get(opcode, "Retail event")
            item = dict(source)
            item.update(type=friendly.get(opcode, "Retail event"), description=description,
                        command_offset=offset, opcode=opcode)
            for visual in visual_controls.get(offset, []):
                effect_id = visual.get("effect_id")
                effect_name = str(visual.get("effect_name") or
                                  f"retail character effect {effect_id}")
                slot = str(visual.get("flag_summary") or "show character")
                is_portrait = (isinstance(effect_id, int) and
                               CampaignMixin._DIALOGUE_PORTRAIT_FIRST_EFFECT_ID <= effect_id <=
                               CampaignMixin._DIALOGUE_PORTRAIT_LAST_EFFECT_ID)
                result.append({"type": "Show portrait" if is_portrait else "Show character",
                               "description": f"{effect_name} · {slot}",
                               "command_offset": offset, "opcode": opcode,
                               "effect_id": effect_id, "flags": visual.get("flags", 0),
                               "retail_embedded_control": True})
            result.append(item)
        return result

    def _campaign_show_metadata(self, scene, editable=False):
        c = getattr(self, "_campaign_widgets", {})
        values = {
            "scene_id_edit": str(scene.get("id", "")) if scene else "",
            "scene_name_edit": str(scene.get("name", "")) if scene else "",
            "scene_chapter_edit": str(scene.get("chapter", "")) if scene else "",
            "scene_location_edit": str(scene.get("location", "")) if scene else "",
        }
        self._campaign_loading = True
        for key, value in values.items():
            widget = c.get(key)
            if widget is not None:
                widget.setText(value)
                widget.setEnabled(bool(scene) and editable)
        notes = c.get("scene_notes_edit")
        if notes is not None:
            notes.setPlainText(str(scene.get("notes", "")) if scene else "")
            notes.setEnabled(bool(scene) and editable)
        self._campaign_loading = False

    def _campaign_metadata_edited(self):
        if getattr(self, "_campaign_loading", False):
            return
        scene = self._campaign_scene()
        if scene is None:
            return
        c = self._campaign_widgets
        # A field the form does not carry leaves its key as the scene has it,
        # rather than taking it away for having nowhere to show it.
        id_edit = c.get("scene_id_edit")
        old_id = str(scene.get("id", ""))
        new_id = id_edit.text().strip() if id_edit is not None else old_id
        if new_id != old_id:
            if not re.fullmatch(r"[A-Za-z0-9_-]+", new_id):
                QMessageBox.warning(self, "Scene ID", "Use letters, numbers, _ or - for the scene ID.")
                if id_edit is not None:
                    id_edit.setText(old_id)
                return
            if any(record["scene"].get("id") == new_id and record["scene"] is not scene
                   for record in self._campaign_records):
                QMessageBox.warning(self, "Scene ID", f"Scene ID '{new_id}' is already in use.")
                if id_edit is not None:
                    id_edit.setText(old_id)
                return
            scene["id"] = new_id
            self._campaign_selected_id = new_id
            for record in self._campaign_records:
                for key in ("else_scene",):
                    if record["scene"].get(key) == old_id:
                        record["scene"][key] = new_id
                for phase in ("on_start", "commands", "on_end"):
                    commands = record["scene"].get(phase, [])
                    for command in commands if isinstance(commands, list) else []:
                        for key in ("scene", "win", "loss"):
                            if command.get(key) == old_id:
                                command[key] = new_id
        name_edit = c.get("scene_name_edit")
        if name_edit is not None:
            scene["name"] = name_edit.text().strip() or scene.get("id", "Unnamed scene")
        for key, widget_name in (("chapter", "scene_chapter_edit"),
                                 ("location", "scene_location_edit")):
            widget = c.get(widget_name)
            if widget is None:
                continue
            value = widget.text().strip()
            if value:
                scene[key] = value
            else:
                scene.pop(key, None)
        notes_edit = c.get("scene_notes_edit")
        if notes_edit is not None:
            notes = notes_edit.toPlainText().strip()
            if notes:
                scene["notes"] = notes
            else:
                scene.pop("notes", None)
        token = scene.get("id")
        for tree_name in ("scenes", "timeline_scenes"):
            tree = c.get(tree_name)
            if tree is None:
                continue
            for index in range(tree.topLevelItemCount()):
                item = tree.topLevelItem(index)
                if item.data(0, Qt.ItemDataRole.UserRole) == token:
                    item.setText(0, scene["name"])
                    item.setData(0, Qt.ItemDataRole.UserRole, token)
                    break
        self._campaign_editor_dirty()

    @staticmethod
    def _campaign_step_description(command):
        kind = str(command.get("command", "unknown"))
        # The stream is the primary editing surface.  Spell out flow commands
        # here so a writer never has to decode a JSON key or inspect a graph
        # just to understand where the story can go next.
        if kind == "label":
            return f"◆ Arrival point: {command.get('id') or 'name this point'}"
        if kind == "jump":
            return f"↪ Continue at: {command.get('to') or 'choose an arrival point'}"
        if kind == "if":
            test = command.get("test", {})
            if not isinstance(test, dict):
                test = {}
            condition = test.get("kind", "condition")
            if condition == "flag":
                condition = f"flag {test.get('id', '?')} is {test.get('value', True)}"
            elif condition == "variable":
                condition = f"{test.get('id', 'variable')} equals {test.get('value', 0)}"
            elif condition == "always":
                condition = "always"
            return (f"◇ If {condition}: yes → {command.get('then') or 'next command'}; "
                    f"no → {command.get('else') or 'next command'}")
        if kind == "call_scene":
            return f"⇢ Open scene: {command.get('scene') or 'choose a scene'}"
        if kind == "return":
            return "↩ Return to the scene that opened this one"
        if kind == "retail_command":
            return str(command.get("editor_label") or
                       f"Retail opcode {int(command.get('opcode', 0)):02d}")
        for key in ("text", "text_id", "id", "flag", "scene", "opponent", "place"):
            if command.get(key) is not None:
                value = str(command[key]).replace("\n", " ")
                return f"{kind}: {value[:110]}"
        return kind

    @classmethod
    def _campaign_story_line(cls, command, number):
        """A beginner-facing sentence for the one-column storyboard."""
        kind = str(command.get("command", ""))
        actions = {
            "background": "Show background", "music": "Play music",
            "sound": "Play sound effect", "dialogue": "Show text",
            "wait": "Wait", "stop_music": "Stop music",
            "teleport": "Go to map location", "game_over": "Game over",
            "credits": "Show credits", "main_menu": "Return to menu",
            "set_flag": "Set story flag", "set_variable": "Set variable",
        }
        if kind in actions:
            detail = command.get("text") if kind == "dialogue" else command.get("id")
            if detail is None and kind == "wait":
                detail = f"{command.get('frames', 0)} frames"
            text = str(detail or "").replace("\n", " ").strip()
            return f"{number}.  + {actions[kind]}" + (f": {text[:120]}" if text else "")
        return f"{number}.  {cls._campaign_step_description(command)}"

    def _campaign_setup_story_navigator(self):
        """Put the cross-scene map beside the command stream, not in a
        separate expert-only tab.  Double-clicking a connection follows it.
        """
        if getattr(self, "_campaign_story_navigator_bound", None) is self._campaign_page:
            return
        self._campaign_story_navigator_bound = self._campaign_page
        panel = QGroupBox("Story connections")
        panel.setToolTip("Scenes this scene opens, and scenes that open this one. Double-click a scene to follow it.")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)
        outgoing_label = QLabel("This scene opens")
        outgoing_label.setObjectName("muted")
        outgoing = QListWidget()
        outgoing.setObjectName("campaignOutgoingScenes")
        outgoing.setMaximumHeight(92)
        outgoing.setToolTip("Double-click to open that scene.")
        incoming_label = QLabel("Opened by")
        incoming_label.setObjectName("muted")
        incoming = QListWidget()
        incoming.setObjectName("campaignIncomingScenes")
        incoming.setMaximumHeight(92)
        incoming.setToolTip("Double-click to open that scene.")
        layout.addWidget(outgoing_label)
        layout.addWidget(outgoing)
        layout.addWidget(incoming_label)
        layout.addWidget(incoming)
        host = self._campaign_page.findChild(QFrame, "sceneInfoPanel")
        if host is not None and host.layout() is not None:
            host.layout().addWidget(panel)
        self._campaign_widgets["story_outgoing"] = outgoing
        self._campaign_widgets["story_incoming"] = incoming
        outgoing.itemDoubleClicked.connect(self._campaign_follow_story_connection)
        incoming.itemDoubleClicked.connect(self._campaign_follow_story_connection)

    def _campaign_setup_simple_storyboard(self):
        """Make the default scene page a story outline, not a dashboard.

        Preview, assets and the native-command inspector stay one click away.
        They are valuable while polishing, but they should not compete with
        the author's actual question: what happens next?
        """
        if getattr(self, "_campaign_simple_storyboard_bound", None) is self._campaign_page:
            return
        self._campaign_simple_storyboard_bound = self._campaign_page
        c = self._campaign_widgets
        splitter = self._campaign_page.findChild(QSplitter, "sceneColumnsSplitter")
        preview = self._campaign_page.findChild(QWidget, "scenePreviewColumn")
        assets = self._campaign_page.findChild(QWidget, "sceneAssetsColumn")
        connections = self._campaign_page.findChild(QFrame, "sceneInfoPanel")
        c["story_details_column"] = preview
        c["story_assets_column"] = assets
        c["story_connections_panel"] = connections
        if preview is not None:
            preview.setVisible(False)
        if assets is not None:
            assets.setVisible(False)
        if connections is not None:
            connections.setVisible(False)
        if splitter is not None:
            splitter.setSizes([330, 1040, 0, 0])
            splitter.setStretchFactor(0, 0)
            splitter.setStretchFactor(1, 1)

        header = self._campaign_page.findChild(QHBoxLayout, "sceneStepsHeader")
        if header is not None:
            details = QPushButton("Edit selected event")
            details.setToolTip("Show or hide the selected event's preview and detailed settings.")
            details.clicked.connect(self._campaign_toggle_story_details)
            assets_button = QPushButton("Assets")
            assets_button.setToolTip("Show or hide the asset library. Double-click an asset to assign it.")
            assets_button.clicked.connect(self._campaign_toggle_story_assets)
            connections_button = QPushButton("Connections")
            connections_button.setToolTip("Show which scenes lead here and where this scene goes.")
            connections_button.clicked.connect(self._campaign_toggle_story_connections)
            header.addWidget(details)
            header.addWidget(assets_button)
            header.addWidget(connections_button)
            c["story_details_button"] = details
            c["story_assets_button"] = assets_button
            c["story_connections_button"] = connections_button

        table = c.get("steps")
        if table is not None:
            # The row number and technical command kind are folded into a
            # single sentence.  Keeping the hidden columns preserves the
            # existing selection/editing code and its keyboard navigation.
            table.setColumnHidden(0, True)
            table.setColumnHidden(1, True)
            table.horizontalHeaderItem(2).setText("Story — read from top to bottom")
            table.horizontalHeader().setStretchLastSection(True)

    def _campaign_setup_flags_tab(self):
        """A single answer to “what controls this branch?” across the story."""
        if getattr(self, "_campaign_flags_tab_bound", None) is self._campaign_page:
            return
        self._campaign_flags_tab_bound = self._campaign_page
        tabs = self._campaign_page.findChild(QTabWidget, "campaignTabs")
        if tabs is None:
            return
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)
        title = QLabel("Flags & conditions")
        title.setObjectName("heading")
        hint = QLabel("Every story flag in one place. Select a flag to see where it is changed and where it decides a branch.")
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        search = QLineEdit()
        search.setObjectName("campaignFlagsSearch")
        search.setPlaceholderText("Find a flag, scene, or condition…")
        table = QTableWidget(0, 4)
        table.setObjectName("campaignFlagsTable")
        table.setHorizontalHeaderLabels(("Flag", "Changed in", "Used as a condition in", "Summary"))
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(True)
        # Keep this reference in numeric flag order.  Qt's live table sorting
        # reorders rows halfway through a refresh, which previously made flags
        # look duplicated or disappear.
        table.setSortingEnabled(False)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        details = QPlainTextEdit()
        details.setObjectName("campaignFlagsDetails")
        details.setReadOnly(True)
        details.setPlaceholderText("Select a flag to see its complete story usage.")
        details.setMaximumHeight(180)
        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addWidget(search)
        layout.addWidget(table, 1)
        layout.addWidget(QLabel("Selected flag"))
        layout.addWidget(details)
        # ``&`` is a Qt mnemonic marker.  Escape it so the tab says exactly
        # what it means instead of hiding the ampersand.
        tabs.addTab(page, "Flags && conditions")
        self._campaign_widgets.update(flags_search=search, flags_table=table, flags_details=details)
        search.textChanged.connect(self._campaign_refresh_flags)
        table.itemSelectionChanged.connect(self._campaign_show_flag_details)

    def _campaign_flag_name(self, value):
        """Give flags a useful name without pretending unknown flags are known.

        The retail scripts use numeric flags.  A small, reliable part of that
        range is documented by the game itself: flags 32–70 record defeated
        campaign opponents and flag 71 marks tournament completion.  The
        remaining flags are still shown, but are explicitly called story
        progress flags until their purpose is known.
        """
        if isinstance(value, int) and not isinstance(value, bool):
            try:
                # story_listing.py lives beside fm_editor rather than inside
                # it, so mirror the import setup used by retail-scene loading.
                pc_tools = str(Path(__file__).resolve().parents[2])
                if pc_tools not in sys.path:
                    sys.path.insert(0, pc_tools)
                import story_listing

                if value == story_listing.FLAG_TOURNAMENT_COMPLETE:
                    return f"Tournament complete (flag {value}, 0x{value:03X})"
                if (story_listing.FLAG_DUELIST_BEATEN_BASE < value <
                        story_listing.FLAG_TOURNAMENT_COMPLETE):
                    duelist = story_listing.GameText(self.files.slus).duelist(
                        value - story_listing.FLAG_DUELIST_BEATEN_BASE)
                    return f"Beat {duelist} (flag {value}, 0x{value:03X})"
            except Exception:
                # The editor must still work when no retail game files are
                # loaded.  The numeric identity remains clear in that case.
                pass
            return f"Story progress {value} (0x{value:03X})"
        value = str(value or "").strip()
        return value if value else "Unnamed flag"

    def _campaign_collect_flags(self):
        """Return a compact index of flag writes/checks from mod and retail scenes."""
        flags = {}

        def add(value, scene, action, condition=""):
            # Index by the underlying ID rather than display text.  This is
            # important once the display name becomes friendly and prevents
            # two flags with a similar label from merging accidentally.
            key = ("number", value) if isinstance(value, int) and not isinstance(value, bool) \
                else ("name", str(value or "").strip())
            name = self._campaign_flag_name(value)
            entry = flags.setdefault(key, {"name": name, "value": value,
                                           "changed": [], "checked": []})
            target = entry["checked"] if action == "checked" else entry["changed"]
            text = f"{scene}: {condition}" if condition else scene
            if text not in target:
                target.append(text)

        for record in getattr(self, "_campaign_records", []):
            scene = record.get("scene", {})
            title = str(scene.get("name") or scene.get("id") or "Mod scene")
            for _phase, _index, command in self._campaign_step_refs_for(scene):
                kind = command.get("command")
                if kind == "set_flag":
                    action = "set" if command.get("value", True) else "cleared"
                    add(command.get("id"), title, "changed", action)
                elif kind == "if" and isinstance(command.get("test"), dict):
                    test = command["test"]
                    if test.get("kind") == "flag":
                        state = "is set" if test.get("value", True) else "is clear"
                        add(test.get("id"), title, "checked", state)
                elif kind == "retail_command" and command.get("opcode") == 3:
                    operands = command.get("operands", [])
                    if isinstance(operands, list) and len(operands) >= 2 and all(isinstance(x, int) for x in operands[:2]):
                        word = operands[0] | operands[1] << 8
                        if word & 0x4000:
                            add(word & 0x3FFF, title, "changed", "set / clear (retail command)")
                        else:
                            add(word & 0x7FF, title, "checked", "is clear" if word & 0x8000 else "is set")

        for record in getattr(self, "_campaign_stock_records", []):
            scene = record.get("scene", {})
            title = f"Retail {int(scene.get('scene_number', 0)):03d} · {scene.get('name', 'scene')}"
            for command in record.get("commands", []):
                if command.get("opcode") != 3:
                    continue
                operands = command.get("operands", [])
                if not (isinstance(operands, list) and len(operands) >= 2 and
                        all(isinstance(x, int) for x in operands[:2])):
                    continue
                word = operands[0] | operands[1] << 8
                if word & 0x4000:
                    add(word & 0x3FFF, title, "changed", "set / clear (retail command)")
                else:
                    add(word & 0x7FF, title, "checked", "is clear" if word & 0x8000 else "is set")
        return flags

    def _campaign_refresh_flags(self, *_):
        c = getattr(self, "_campaign_widgets", {})
        table = c.get("flags_table")
        if table is None:
            return
        self._campaign_flags = self._campaign_collect_flags()
        query = c.get("flags_search").text().casefold().strip() if c.get("flags_search") else ""
        rows = []
        for key, usage in self._campaign_flags.items():
            name = usage["name"]
            changed, checked = usage["changed"], usage["checked"]
            text = " ; ".join((*changed, *checked))
            if not query or query in (name + " " + text).casefold():
                rows.append((key, name, usage["value"], changed, checked))
        # Numeric IDs are easier to scan than alphabetical descriptions.
        rows.sort(key=lambda item: (0, item[2]) if isinstance(item[2], int) and
                  not isinstance(item[2], bool) else (1, item[1].casefold()))
        table.blockSignals(True)
        table.setSortingEnabled(False)
        table.setRowCount(len(rows))
        for row, (key, name, _value, changed, checked) in enumerate(rows):
            values = (name, ", ".join(changed) or "—", ", ".join(checked) or "—",
                      f"{len(changed)} change(s) · {len(checked)} condition(s)")
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, key)
                table.setItem(row, column, item)
        table.blockSignals(False)
        if rows:
            table.selectRow(0)
        elif c.get("flags_details"):
            c["flags_details"].clear()

    def _campaign_show_flag_details(self):
        c = self._campaign_widgets
        table, details = c.get("flags_table"), c.get("flags_details")
        if table is None or details is None or table.currentRow() < 0:
            return
        item = table.item(table.currentRow(), 0)
        usage = getattr(self, "_campaign_flags", {}).get(item.data(Qt.ItemDataRole.UserRole), {}) if item else {}
        changed = usage.get("changed", [])
        checked = usage.get("checked", [])
        title = usage.get("name", "Flag")
        details.setPlainText(title + "\n\nChanged:\n" +
                             ("\n".join("• " + entry for entry in changed) or "• Never") +
                             "\n\nUsed as a condition:\n" +
                             ("\n".join("• " + entry for entry in checked) or "• Never"))

    def _campaign_toggle_story_details(self):
        c = self._campaign_widgets
        column = c.get("story_details_column")
        splitter = self._campaign_page.findChild(QSplitter, "sceneColumnsSplitter")
        if column is None:
            return
        show = not column.isVisible()
        column.setVisible(show)
        if splitter is not None:
            assets = c.get("story_assets_column")
            splitter.setSizes([330, 690 if show else 1040, 500 if show else 0,
                               350 if assets is not None and assets.isVisible() else 0])
        button = c.get("story_details_button")
        if button is not None:
            button.setText("Hide event editor" if show else "Edit selected event")

    def _campaign_toggle_story_assets(self):
        c = self._campaign_widgets
        column = c.get("story_assets_column")
        splitter = self._campaign_page.findChild(QSplitter, "sceneColumnsSplitter")
        if column is None:
            return
        show = not column.isVisible()
        column.setVisible(show)
        details_visible = bool(c.get("story_details_column") and c["story_details_column"].isVisible())
        if splitter is not None:
            splitter.setSizes([330, 690 if details_visible else 900, 500 if details_visible else 0,
                               350 if show else 0])
        button = c.get("story_assets_button")
        if button is not None:
            button.setText("Hide assets" if show else "Assets")

    def _campaign_toggle_story_connections(self):
        c = self._campaign_widgets
        panel = c.get("story_connections_panel")
        if panel is None:
            return
        panel.setVisible(not panel.isVisible())
        button = c.get("story_connections_button")
        if button is not None:
            button.setText("Hide connections" if panel.isVisible() else "Connections")

    def _campaign_refresh_story_navigator(self):
        c = getattr(self, "_campaign_widgets", {})
        outgoing, incoming = c.get("story_outgoing"), c.get("story_incoming")
        if outgoing is None or incoming is None:
            return
        outgoing.clear(); incoming.clear()
        scene = self._campaign_scene()
        if scene is None:
            return
        current = str(scene.get("id", ""))
        records = getattr(self, "_campaign_records", [])
        known = {str(record["scene"].get("id")): (record["scene"], record["scene"].get("id")) for record in records
                 if record.get("scene", {}).get("id")}
        # A retail save prompt continues at a numbered retail scene. Prefer an
        # override for that number when one exists, otherwise make the stock
        # scene navigable too.  This makes imported retail scenes much less
        # of a maze without pretending native commands are structured calls.
        for stock in getattr(self, "_campaign_stock_records", []):
            number = stock.get("scene", {}).get("scene_number")
            if isinstance(number, int):
                override = next((record["scene"] for record in records
                                 if record.get("scene", {}).get("scene_number") == number), None)
                known[f"retail_{number:03d}"] = ((override or stock["scene"]),
                                                   (override or stock).get("id") if override else stock["token"])

        def add(widget, target, prefix):
            target = str(target or "")
            destination = known.get(target)
            label = (destination[0].get("name") or target) if destination else f"Missing scene: {target or 'not chosen'}"
            item = QListWidgetItem(f"{prefix} {label}")
            item.setData(Qt.ItemDataRole.UserRole, destination[1] if destination else None)
            if destination is None:
                item.setForeground(QColor("#dc5967"))
                item.setToolTip("This connection has no matching mod scene. Create it or correct the scene id.")
            else:
                item.setToolTip(f"Open scene '{target}'")
            widget.addItem(item)

        targets = []
        for _phase, _index, command in self._campaign_step_refs_for(scene):
            if command.get("command") == "call_scene":
                targets.append(command.get("scene"))
            elif command.get("command") == "retail_command" and command.get("opcode") == 13:
                operands = command.get("operands", [])
                if (isinstance(operands, list) and len(operands) >= 4 and
                        all(isinstance(value, int) and not isinstance(value, bool) for value in operands[2:4])):
                    targets.append(f"retail_{operands[2] | operands[3] << 8:03d}")
        if targets:
            for target in dict.fromkeys(targets):
                add(outgoing, target, "⇢")
        else:
            item = QListWidgetItem("No other scene is opened here.")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            outgoing.addItem(item)
        callers = []
        retail_key = (f"retail_{int(scene['scene_number']):03d}"
                      if isinstance(scene.get("scene_number"), int) else None)
        for record in records:
            other = record.get("scene", {})
            if other is scene:
                continue
            if any((command.get("command") == "call_scene" and str(command.get("scene", "")) == current) or
                   (retail_key and command.get("command") == "retail_command" and command.get("opcode") == 13 and
                    isinstance(command.get("operands"), list) and len(command["operands"]) >= 4 and
                    all(isinstance(value, int) and not isinstance(value, bool) for value in command["operands"][2:4]) and
                    f"retail_{command['operands'][2] | command['operands'][3] << 8:03d}" == retail_key)
                   for _phase, _index, command in self._campaign_step_refs_for(other)):
                callers.append(other)
        if callers:
            for caller in callers:
                add(incoming, caller.get("id"), "↩")
        else:
            item = QListWidgetItem("No mod scene opens this scene.")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            incoming.addItem(item)

    def _campaign_follow_story_connection(self, item):
        target = item.data(Qt.ItemDataRole.UserRole)
        if not target:
            return
        tree = self._campaign_widgets.get("scenes")
        if tree is None:
            return
        for index in range(tree.topLevelItemCount()):
            candidate = tree.topLevelItem(index)
            if candidate.data(0, Qt.ItemDataRole.UserRole) == target:
                tree.setCurrentItem(candidate)
                return

    def _campaign_step_refs(self):
        scene = self._campaign_scene()
        if scene is None:
            return []
        refs = []
        for phase in ("on_start", "commands", "on_end"):
            commands = scene.get(phase, [])
            if isinstance(commands, list):
                refs.extend((phase, i, command) for i, command in enumerate(commands) if isinstance(command, dict))
        return refs

    @staticmethod
    def _campaign_human_controls(entries):
        """Turn listing-style dialogue bytecode into labeled, readable steps."""
        entries = [entry for entry in entries if isinstance(entry, dict)] if isinstance(entries, list) else []
        step_for_offset = {}
        for index, entry in enumerate(entries, 1):
            try:
                step_for_offset[int(str(entry.get("offset", "")), 16)] = f"dialogue_step_{index:03d}"
            except ValueError:
                pass
        decoded = []
        for entry in entries:
            parts = str(entry.get("control", "")).split()
            if not parts:
                continue
            kind = parts[0].casefold()
            values = []
            for part in parts[1:]:
                try:
                    values.append(int(part, 16))
                except ValueError:
                    pass
            step = {"step": f"dialogue_step_{len(decoded) + 1:03d}"}
            if kind == "state" and values:
                state = values[0] & 0x1F
                data = values[1:]
                if state == 0x05 and len(data) >= 2:
                    # The upper bits of this word carry display flags; the
                    # actual composed-picture ID occupies the low 12 bits.
                    picture_word = data[0] | data[1] << 8
                    picture = picture_word & 0x0FFF
                    step.update(action=("Clear dialogue picture" if picture == 0 else "Display dialogue picture"),
                                picture_id=picture)
                    if picture_word & 0x8000 and len(data) >= 5:
                        step["display_mode"] = data[2]
                        step["duration_frames"] = data[3] | data[4] << 8
                elif state == 0x0B and len(data) >= 6:
                    word = lambda i: data[i] | data[i + 1] << 8
                    step.update(action="Pan dialogue camera", x=word(0), y=word(2),
                                duration_frames=word(4))
                elif state in (0x0F, 0x10) and len(data) >= 2:
                    frames = data[0] | data[1] << 8
                    step.update(action="Wait for dialogue" if state == 0x0F else "Shake screen",
                                duration_frames=frames)
                else:
                    step.update(action=f"Set dialogue state {state}")
            elif kind == "fx" and values:
                effect_id = values[0]
                flags = values[1] if len(values) > 1 else 0
                if (CampaignMixin._DIALOGUE_PORTRAIT_FIRST_EFFECT_ID <= effect_id <=
                        CampaignMixin._DIALOGUE_PORTRAIT_LAST_EFFECT_ID):
                    effect_name = (f"Campaign portrait "
                                   f"{effect_id - CampaignMixin._DIALOGUE_PORTRAIT_FIRST_EFFECT_ID + 1:02d} "
                                   "of 25")
                    target = "portrait"
                else:
                    # The retail engine only stores a numeric resource ID for
                    # these two shared display-effect slots. There is no
                    # source name that would let the editor label effect 22
                    # as a particular animation without guessing.
                    effect_name = f"Shared display effect {effect_id} (0x{effect_id:02X})"
                    target = "shared effect"
                step.update(effect_id=effect_id, effect_name=effect_name,
                            flags=flags, flags_hex=f"0x{flags:02X}")
                if flags & 0x80:
                    if flags & 0x02:
                        action, operation = f"Stop {target} immediately", "Stop immediately"
                    elif flags & 0x01:
                        action, operation = (f"Stop {target} and wait for completion",
                                             "Stop and wait for completion")
                    else:
                        action, operation = f"Animate {target} out and stop", "Animate out and stop"
                    step.update(action=action, flag_summary=operation)
                elif flags & 0x40:
                    variant = flags & 0x03
                    step.update(action=f"Change {target} appearance",
                                flag_summary=f"Set appearance variant {variant} and wait")
                elif flags & 0x20:
                    enabled = bool(flags & 0x01)
                    step.update(action=f"Update {target} animation mode",
                                flag_summary=("Enable animation update" if enabled else
                                              "Disable animation update"))
                else:
                    if target == "portrait":
                        summary = "Show in the dedicated portrait slot"
                    else:
                        side = "right" if flags & 0x01 else "left"
                        summary = f"Show in the shared {side} slot"
                        if flags & 0x08:
                            summary += " with the alternate entrance"
                        if flags & 0x10:
                            summary += f"; appearance variant {(flags >> 1) & 0x03}"
                    step.update(action=f"Show {target}", flag_summary=summary)
            elif kind == "f8" and values:
                command_id, data = values[0], values[1:]
                if command_id == 0x10 and len(data) >= 2:
                    sound = data[0] | data[1] << 8
                    if sound & 0x8000:
                        step.update(action="Play voice", voice_id=sound & 0x7FFF)
                        if len(data) >= 4:
                            step["wait_frames"] = data[2] | data[3] << 8
                    else:
                        step.update(action="Play sound effect", sound_id=sound)
                elif command_id == 0x15 and data:
                    step.update(action="Fade out background music", fade_step=data[0] & 0x7F,
                                wait_for_completion=bool(data[0] & 0x80))
                elif command_id == 0x0E and len(data) >= 2:
                    step.update(action="Play background music", music_id=data[0] | data[1] << 8)
                elif command_id == 0x11 and data:
                    step.update(action="Stop background music", stop_mode=data[0])
                elif command_id == 0x16 and data:
                    step.update(action="Update background music", control=data[0])
                else:
                    step.update(action=f"Dialogue effect command {command_id}")
                    if data:
                        step["parameters"] = data
            elif kind in ("if", "set") and values:
                step.update(action="Test campaign flag" if kind == "if" else "Set campaign flag",
                            flag=values[0])
            elif kind == "choice" and values:
                step.update(action="Show dialogue choices", option_count=values[0] & 7)
            elif kind == "choose" and values:
                step["action"] = "Branch to selected dialogue choice"
                # The operands encode choice count/flags; actual destinations
                # are decoded separately by text_listing.Op.targets.
            elif kind == "page":
                step["action"] = "Wait for page advance"
            elif kind == "call" and values:
                step.update(action="Call dialogue section", _target_offsets=[values[0]])
            elif kind == "jump" and values:
                step.update(action="Jump to dialogue section", _target_offsets=[values[0]])
            elif kind == "nl":
                step["action"] = "Start new line"
            else:
                step["action"] = {"end": "End dialogue section"}.get(kind, "Dialogue control")
            raw_targets = entry.get("targets", [])
            if raw_targets and "_target_offsets" not in step:
                parsed_targets = []
                for target in raw_targets:
                    try:
                        parsed_targets.append(int(str(target), 16))
                    except ValueError:
                        continue
                if parsed_targets:
                    step["_target_offsets"] = parsed_targets
            decoded.append(step)

        # Resolve bytecode targets to readable step labels. Raw offsets stay
        # internal to the decoder and never appear in the export.
        for step in decoded:
            targets = step.pop("_target_offsets", None)
            if targets:
                step["destinations"] = [step_for_offset[target] for target in targets
                                        if target in step_for_offset]
        return decoded

    @classmethod
    def _campaign_human_retail_commands(cls, entries):
        entries = entries if isinstance(entries, list) else []
        executable = []
        label_offsets = {}
        pending_label = None
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            nested_command = entry.get("command")
            command = nested_command if isinstance(nested_command, dict) else entry
            if command.get("command") == "label":
                pending_label = command.get("id")
                continue
            node_id = f"command_{len(executable) + 1:03d}"
            if pending_label:
                label_offsets[pending_label] = node_id
                pending_label = None
            executable.append((node_id, command))

        offset_to_node = {}
        for node_id, command in executable:
            try:
                offset_to_node[int(str(command.get("offset", "")), 16)] = node_id
            except ValueError:
                pass
        label_to_node = dict(label_offsets)
        nodes = []
        for index, (node_id, command) in enumerate(executable):
            item = {"id": node_id, "order_hint": index + 1,
                    "action": str(command.get("editor_label") or "Retail campaign instruction")}
            if command.get("dialogue_id") is not None:
                item["dialogue"] = {"id": command["dialogue_id"],
                                    "timeline": copy.deepcopy(command.get("dialogue_flow", {}))}

            def resolve_offset(value):
                try:
                    return offset_to_node.get(int(str(value), 16))
                except (TypeError, ValueError):
                    return None

            opcode = command.get("opcode")
            targets = [target for target in command.get("branch_targets", [])
                       if isinstance(target, dict)]
            resolved = [(target, resolve_offset(target.get("offset"))) for target in targets]
            resolved = [(target, dest) for target, dest in resolved
                        if dest or target.get("label") in label_to_node]
            if resolved:
                if opcode == 12:
                    item["next"] = resolved[0][1] or label_to_node.get(resolved[0][0].get("label"))
                else:
                    item["branches"] = [
                        {"when": "condition is met",
                         "to": dest or label_to_node.get(target.get("label"))}
                        for target, dest in resolved]
            if opcode not in (0, 8, 12, 14, 15, 18, 19, 22):
                try:
                    fallthrough = int(str(command.get("fallthrough_offset", "")), 16)
                except ValueError:
                    fallthrough = None
                next_node = offset_to_node.get(fallthrough)
                if next_node:
                    item["next"] = next_node
            nodes.append(item)

        return {"entry": nodes[0]["id"] if nodes else None, "nodes": nodes}

    def _campaign_export_scene_flow(self):
        if not self._campaign_commit_step():
            return
        token = getattr(self, "_campaign_selected_id", None)
        stock = next((record for record in self._campaign_stock_records
                      if record.get("token") == token), None)
        scene = stock["scene"] if stock else self._campaign_scene()
        if scene is None:
            self._campaign_say(self._campaign_widgets.get("status"), "Select a scene before exporting its command flow.")
            return

        if stock:
            flow = self._campaign_human_retail_commands(stock.get("commands", []))
            commands = flow["nodes"]
            source = "retail"
            scene_info = {"id": scene.get("id"), "name": scene.get("name"),
                          "scene_number": scene.get("scene_number")}
            filename = f"scene-{int(scene['scene_number']):03d}-command-flow.json"
        else:
            commands = []
            for order, (phase, index, command) in enumerate(self._campaign_step_refs(), 1):
                entry = {"order": order, "phase": phase, "index": index,
                         "command": copy.deepcopy(command)}
                commands.append(entry)
            source = "mod"
            scene_info = {key: copy.deepcopy(scene.get(key)) for key in
                          ("id", "name", "scene_number", "entered") if key in scene}
            filename = f"{scene.get('id') or 'scene'}-command-flow.json"

        body = {
            "schema": "yogfm-campaign-command-flow/v4",
            "scene": scene_info,
            "source": source,
            "ordering": ("Retail flow is a graph: follow each node's next link; branch nodes include explicit destinations. "
                         "Dialogue timeline nodes preserve text, page waits, and embedded controls in stream order."
                         if source == "retail" else "scene phase order: on_start, commands, on_end"),
            "command_count": len(commands),
        }
        if source == "retail":
            body["flow"] = flow
        else:
            body["commands"] = commands
        # Include staged translations for dialogue IDs referenced in the flow.
        staged = getattr(self, "_campaign_dialogue_edits", {})
        dialogue_ids = {str(command.get("text_id")) for entry in commands
                        if isinstance(entry, dict)
                        for command in [entry.get("command", entry)]
                        if isinstance(command, dict) and isinstance(command.get("text_id"), str)}
        if staged and dialogue_ids:
            body["dialogue_text_edits"] = {key: staged[key] for key in sorted(dialogue_ids) if key in staged}
        default_path = str(Path.home() / filename)
        path, _ = QFileDialog.getSaveFileName(self, "Export scene command flow", default_path,
                                               "JSON files (*.json)")
        if not path:
            return
        try:
            Path(path).write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        except OSError as error:
            QMessageBox.warning(self, "Export scene command flow", str(error))
            return
        self._campaign_say(self._campaign_widgets.get("status"), f"Exported scene command flow to {path}")

    def _campaign_scene_changed(self, current, _previous):
        if getattr(self, "_campaign_loading", False):
            return
        if not self._campaign_commit_step():
            tree = self._campaign_widgets["scenes"]
            if _previous is not None:
                tree.blockSignals(True); tree.setCurrentItem(_previous); tree.blockSignals(False)
            return
        c = self._campaign_widgets
        token = current.data(0, Qt.ItemDataRole.UserRole) if current else None
        self._campaign_selected_id = token
        scene = self._campaign_scene()
        self._campaign_refresh_story_navigator()
        table = c["steps"]
        table.blockSignals(True)
        held_sort = sort_paused(table)
        table.setRowCount(0)
        stock = next((record for record in self._campaign_stock_records
                      if record["token"] == token), None)
        self._campaign_set_stock_mode(stock is not None)
        self._campaign_show_metadata(stock["scene"] if stock is not None else scene,
                                     editable=stock is None and scene is not None)
        revert_button = self._campaign_page.findChild(QPushButton, "revertToRetailButton")
        if revert_button is not None:
            revert_button.setEnabled(bool(scene and scene.get("scene_number") is not None and
                any(int(record["scene"].get("scene_number", -1)) == int(scene["scene_number"])
                    for record in self._campaign_stock_records)))
        if stock is not None:
            steps = self._campaign_stock_outline(stock)
            self._campaign_visible_stock_steps = steps
            table.setRowCount(len(steps))
            for row, step in enumerate(steps):
                story_line = f"{row + 1}.  + {step['type']}: {step['description']}"
                for column, value in enumerate((str(row + 1), step["type"], story_line)):
                    item = TableItem(value)
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    table.setItem(row, column, item)
            sort_resumed(table, held_sort)
            table.blockSignals(False)
            number = stock["scene"]["scene_number"]
            self._campaign_active_row = 0 if steps else None
            if steps:
                table.selectRow(0)
                self._campaign_show_stock_event(steps[0], stock)
            else:
                self._campaign_show_step(None)
            self._campaign_refresh_preview_steps()
            self._campaign_populate_timeline()
            return
        if scene is None:
            self._campaign_say(c.get("scene_context"), "No scene selected")
            sort_resumed(table, held_sort)
            table.blockSignals(False)
            self._campaign_show_step(None)
            return
        table.setRowCount(len(self._campaign_step_refs()))
        for row, (phase, index, command) in enumerate(self._campaign_step_refs()):
            values = (str(row + 1), phase.replace("on_", "") if phase != "commands" else "scene",
                      self._campaign_story_line(command, row + 1))
            for column, value in enumerate(values):
                item = TableItem(value)
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, (phase, index))
                table.setItem(row, column, item)
        sort_resumed(table, held_sort)
        table.blockSignals(False)
        number = scene.get("scene_number")
        extra = f" · game scene {number}" if number is not None else " · internal scene"
        self._campaign_say(c.get("scene_context"),
                           f"● Scene starts here · {scene.get('id', '')}{extra} · {table.rowCount()} event(s)")
        self._campaign_active_row = None
        if table.rowCount():
            table.selectRow(0)
        else:
            self._campaign_show_step(None)
        self._campaign_refresh_preview_steps()
        self._campaign_populate_timeline()

    def _campaign_set_stock_mode(self, stock):
        tree = self._campaign_widgets["scenes"]
        table = self._campaign_widgets["steps"]
        tree.setProperty("campaignStockScene", bool(stock))
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        for name, button in self._campaign_scene_buttons.items():
            button.setEnabled(not stock or name in ("addSceneButton", "duplicateSceneButton"))
        duplicate = self._campaign_scene_buttons.get("duplicateSceneButton")
        if duplicate is not None:
            duplicate.setText("Edit override" if stock else "Duplicate")
            duplicate.setToolTip("Create an editable override for this retail scene number"
                                 if stock else "Duplicate the selected mod scene")
        for button in self._campaign_step_buttons.values():
            button.setEnabled(not stock)
        # Stock scenes remain read-only, but their selected event should still
        # populate the inspector. Disabling the entire panel made it look inert.
        if self._campaign_step_editor is not None:
            self._campaign_step_editor.setEnabled(True)

    def _campaign_step_changed(self):
        table = self._campaign_widgets["steps"]
        row = table.currentRow()
        stock = next((record for record in self._campaign_stock_records
                      if record["token"] == getattr(self, "_campaign_selected_id", None)), None)
        if stock is not None:
            steps = getattr(self, "_campaign_visible_stock_steps", stock["steps"])
            self._campaign_active_row = row if 0 <= row < len(steps) else None
            if self._campaign_active_row is None:
                self._campaign_show_step(None)
            else:
                self._campaign_show_stock_event(steps[self._campaign_active_row], stock)
            self._campaign_refresh_preview_steps()
            return
        refs = self._campaign_step_refs()
        command = refs[row][2] if 0 <= row < len(refs) else None
        previous = self._campaign_active_row
        if not self._campaign_commit_step():
            if previous is not None:
                table.blockSignals(True); table.selectRow(previous); table.blockSignals(False)
            return
        self._campaign_active_row = row if command is not None else None
        self._campaign_show_step(command)
        self._campaign_refresh_preview_steps()

    def _campaign_show_step(self, command):
        c = self._campaign_widgets
        self._campaign_loading = True
        selected = self._campaign_kind_for_command(command) if command is not None else "__raw__"
        display = {value: label for label, value in self._CAMPAIGN_STEP_TYPES}
        if selected == "__raw__":
            display_text = "Advanced command (JSON)"
        elif selected == "retail_command":
            display_text = "Imported stock command"
        else:
            display_text = display.get(selected, selected.replace("_", " ").title())
        c["step_type_label"].setText(display_text if command is not None else "No command selected")
        self._campaign_say(c.get("step_context"), "Edit the selected command" if command else "No step selected")
        c["dialogue"].blockSignals(True)
        c["character"].blockSignals(True)
        c["pose"].blockSignals(True)
        c["position"].blockSignals(True)
        c["background"].blockSignals(True)
        c["keep_box"].blockSignals(True)
        if command is None:
            c["dialogue"].clear()
            c["dialogue_label"].setText("Command JSON")
            c["dialogue_label"].setVisible(False)
            c["dialogue"].setVisible(False)
            c["keep_box"].setVisible(False)
            c["number_label"].setVisible(False)
            c["number"].setVisible(False)
            c["dialogue_count"].setVisible(False)
            self._campaign_clear_structured_fields()
            c["character_label"].setVisible(False); c["character"].setVisible(False)
            c["pose_label"].setVisible(False); c["pose"].setVisible(False)
            c["position_label"].setVisible(False); c["position"].setVisible(False)
            c["background_label"].setVisible(False); c["background"].setVisible(False)
            for key in ("dialogue", "character", "pose", "position", "background", "keep_box"):
                c[key].blockSignals(False)
            self._campaign_loading = False
            return
        self._campaign_raw_step = (selected == "__raw__" or
                                   selected in {value for _, value in self._CAMPAIGN_JSON_COMMANDS})
        self._campaign_step_command = command
        if self._campaign_raw_step:
            c["dialogue_label"].setVisible(selected == "__raw__")
            c["dialogue"].setVisible(selected == "__raw__")
            c["character_label"].setVisible(False); c["character"].setVisible(False)
            c["pose_label"].setVisible(False); c["pose"].setVisible(False)
            c["position_label"].setVisible(False); c["position"].setVisible(False)
            c["background_label"].setVisible(False); c["background"].setVisible(False)
            if selected == "__raw__":
                c["dialogue_label"].setText("Complete command JSON")
                c["dialogue"].setPlainText(json.dumps(command, ensure_ascii=False, indent=2))
                self._campaign_clear_structured_fields()
            else:
                self._campaign_build_structured_fields(command, selected)
        else:
            self._campaign_clear_structured_fields()
            c["dialogue_label"].setText("Dialogue text" if selected == "dialogue" else "Step data")
            c["dialogue_label"].setVisible(selected == "dialogue")
            c["dialogue"].setVisible(selected == "dialogue")
            c["keep_box"].setVisible(selected == "dialogue")
            c["number_label"].setVisible(selected == "wait")
            c["number"].setVisible(selected == "wait")
            c["character_label"].setVisible(selected in ("dialogue", "character", "hide_character"))
            c["character"].setVisible(selected in ("dialogue", "character", "hide_character"))
            c["pose_label"].setVisible(selected in ("dialogue", "character", "hide_character"))
            c["pose"].setVisible(selected in ("dialogue", "character", "hide_character"))
            c["position_label"].setVisible(selected in ("dialogue", "character", "hide_character"))
            c["position"].setVisible(selected in ("dialogue", "character", "hide_character"))
            c["background_label"].setVisible(selected == "background")
            c["background"].setVisible(selected == "background")
            if selected == "dialogue":
                key = command.get("text_id")
                text = command.get("text", "")
                if key:
                    language_rel = f"{self._campaign_folder}/dialogue/en.json"
                    try:
                        text = (self._campaign_json(language_rel, {}) or {}).get(key, "")
                    except ValueError:
                        text = ""
                c["dialogue"].setPlainText(str(text))
                c["number"].setValue(max(0, min(255, int(command.get("text_speed", 0)))))
            else:
                c["dialogue"].clear()
            self._campaign_fill_reference_combos(command, selected)
            c["keep_box"].setChecked(bool(command.get("keep_box", False)))
            if selected == "wait":
                c["number"].setValue(max(0, min(65535, int(command.get("frames", 30)))))
        c["dialogue"].blockSignals(False)
        c["character"].blockSignals(False)
        c["pose"].blockSignals(False)
        c["position"].blockSignals(False)
        c["background"].blockSignals(False)
        c["keep_box"].blockSignals(False)
        c["dialogue_label"].setVisible(selected == "__raw__" or
                                        (not self._campaign_raw_step and selected == "dialogue"))
        c["dialogue"].setVisible(selected == "__raw__" or
                                 (not self._campaign_raw_step and selected == "dialogue"))
        c["keep_box"].setVisible(not self._campaign_raw_step and selected == "dialogue")
        c["number_label"].setVisible(not self._campaign_raw_step and selected in ("dialogue", "wait"))
        c["number"].setVisible(not self._campaign_raw_step and selected in ("dialogue", "wait"))
        c["number_label"].setText("Frames" if selected == "wait" else "Text speed")
        c["dialogue_count"].setVisible(not self._campaign_raw_step and selected == "dialogue")
        self._campaign_update_dialogue_count()
        self._campaign_refresh_previews(command)
        self._campaign_loading = False

    def _campaign_show_stock_event(self, event, stock):
        """Show read-only decoded details for a selected retail command/event."""
        self._campaign_show_step(None)
        c = self._campaign_widgets
        if not isinstance(event, dict):
            return
        c["step_type_label"].setText(str(event.get("type") or "Retail event"))
        self._campaign_say(c.get("step_context"), "Decoded stock event · read-only")
        host = c.get("structured_host")
        if host is None or host.layout() is None:
            return

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.setVerticalSpacing(6)
        group = QGroupBox("Event details (stock data is read-only)")
        group.setLayout(form)

        def add_value(label, value):
            if value is None or value == "":
                return
            text = json.dumps(value, ensure_ascii=False, indent=2) if isinstance(value, (dict, list)) else str(value)
            value_label = QLabel(text)
            value_label.setWordWrap(True)
            value_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            form.addRow(label, value_label)

        add_value("Event type", event.get("type"))
        add_value("Description", event.get("description"))
        add_value("Scene command offset", event.get("command_offset"))
        add_value("Dialogue control offset", event.get("control_offset"))
        add_value("Dialogue ID", event.get("dialogue_id"))
        add_value("Picture ID", event.get("picture_id"))
        if event.get("effect_name"):
            add_value("Dialogue effect", event.get("effect_name"))
            add_value("Effect ID", event.get("effect_id"))
            flags = event.get("flags_hex") or event.get("flags")
            summary = event.get("flag_summary")
            add_value("Effect flags", f"{flags} — {summary}" if summary else flags)
        add_value("Character ID", event.get("sprite_id"))
        add_value("Character flags / position", event.get("sprite_flags"))
        add_value("Branch target", event.get("branch_target"))
        add_value("Branch destinations", event.get("branch_targets"))
        add_value("Branch path", event.get("branch_path"))

        offset = str(event.get("command_offset", "")).casefold()
        command = next((item for item in stock.get("commands", [])
                        if isinstance(item, dict) and
                        str(item.get("offset", "")).casefold() == offset), None)
        if command:
            add_value("Stock instruction", command.get("editor_label"))
            add_value("Opcode", command.get("opcode"))
            control_offset = str(event.get("control_offset", "")).casefold()
            control = next((item for item in command.get("embedded_controls", [])
                            if isinstance(item, dict) and
                            str(item.get("offset", "")).casefold() == control_offset), None)
            if control:
                decoded = self._campaign_human_controls([control])
                if decoded:
                    add_value("Decoded dialogue control", decoded[0])

        dialogue = event.get("dialogue_text")
        if dialogue:
            text_view = QPlainTextEdit()
            text_view.setReadOnly(True)
            text_view.setMaximumHeight(140)
            text_view.setPlainText(str(dialogue))
            form.addRow("Dialogue text", text_view)
        if form.rowCount() == 0:
            add_value("Details", "No additional decoded properties for this event.")
        host.layout().addWidget(group)

    def _campaign_clear_structured_fields(self):
        host = self._campaign_widgets.get("structured_host")
        if host is None:
            return
        layout = host.layout()
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._campaign_structured_editors = []

    def _campaign_build_structured_fields(self, command, selected):
        """Render advanced commands as editable fields instead of a JSON blob."""
        self._campaign_clear_structured_fields()
        host = self._campaign_widgets.get("structured_host")
        if host is None:
            return
        title = {value: label for label, value in self._CAMPAIGN_JSON_COMMANDS}.get(selected, "Advanced command")
        group = QGroupBox(f"{title} command")
        form = QFormLayout(group)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.setVerticalSpacing(6)
        self._campaign_structured_editors = []

        def add_editor(key, value, label=None):
            if key in ("target", "to", "then", "else", "goto") and isinstance(value, str):
                editor = QComboBox()
                editor.addItem("— choose a label —", "")
                scene = self._campaign_scene() or {}
                labels = [str(item.get("id")) for item in scene.get("commands", [])
                          if isinstance(item, dict) and item.get("command") == "label" and item.get("id")]
                if value and value not in labels:
                    labels.insert(0, value)
                for target in labels:
                    editor.addItem(target, target)
                ix = editor.findData(value)
                editor.setCurrentIndex(max(0, ix))
                signal = editor.currentIndexChanged
            elif isinstance(value, bool):
                editor = QCheckBox()
                editor.setChecked(value)
                signal = editor.toggled
            elif isinstance(value, int) or key in ("opcode", "frames", "strength", "x", "y", "text_speed"):
                editor = QSpinBox()
                editor.setRange(-32768, 65535)
                editor.setValue(int(value or 0))
                signal = editor.valueChanged
            elif isinstance(value, (dict, list)):
                editor = QPlainTextEdit()
                editor.setMaximumHeight(90)
                editor.setPlainText(json.dumps(value, ensure_ascii=False, indent=2))
                signal = editor.textChanged
            else:
                editor = QLineEdit(str(value if value is not None else ""))
                signal = editor.textChanged
            editor.setProperty("campaignFieldKey", key)
            form.addRow(label or key.replace("_", " ").title(), editor)
            signal.connect(self._campaign_editor_changed)
            self._campaign_structured_editors.append((key, editor, type(value)))

        if selected == "screen":
            effects = QComboBox()
            for label, value in (("Screen shake", "shake"), ("Flash to white", "flash"),
                                 ("Letterbox bars", "letterbox")):
                effects.addItem(label, value)
            effect = command.get("effect")
            if command.get("command") in ("screen_shake", "flash", "letterbox"):
                effect = {"screen_shake": "shake", "flash": "flash", "letterbox": "letterbox"}.get(
                    command.get("command"), effect)
            ix = effects.findData(effect or "shake")
            effects.setCurrentIndex(max(0, ix))
            form.addRow("Effect", effects)
            strength = QSpinBox(); strength.setRange(0, 255)
            strength.setValue(int(command.get("strength", 28 if effect == "letterbox" else 4)))
            form.addRow("Strength / bar height", strength)
            frames = QSpinBox(); frames.setRange(0, 65535)
            frames.setValue(int(command.get("frames", 0 if effect == "letterbox" else 18)))
            frames.setToolTip("0 keeps letterbox bars visible until a later Letterbox step clears them.")
            form.addRow("Duration (frames)", frames)
            for widget in (effects, strength, frames):
                signal = widget.currentIndexChanged if isinstance(widget, QComboBox) else widget.valueChanged
                signal.connect(self._campaign_editor_changed)
            self._campaign_structured_editors.extend((
                ("effect", effects, str), ("strength", strength, int), ("frames", frames, int)))
            hint = QLabel("Shake uses strength and duration. Flash uses duration. Letterbox uses bar height; duration 0 means until cleared.")
            hint.setWordWrap(True)
            form.addRow(hint)
        else:
            # Keep structural keys and values available while giving each
            # command field its own native editor. This includes branch,
            # choice, duel, movement, asset, and imported retail operands.
            for key, value in command.items():
                if key in ("command", "embedded_controls"):
                    continue
                if key == "editor_label":
                    label = QLabel(str(value))
                    label.setWordWrap(True)
                    form.addRow("Stock instruction", label)
                    continue
                add_editor(key, value)
            if selected == "retail_command":
                nested = command.get("embedded_controls", [])
                if nested:
                    details = QListWidget()
                    details.setMaximumHeight(100)
                    for entry in nested:
                        if isinstance(entry, dict):
                            desc = entry.get("description") or entry.get("kind") or "Embedded dialogue control"
                            offset = entry.get("offset")
                            details.addItem(f"Byte {offset}: {desc}" if offset is not None else str(desc))
                    form.addRow("Embedded dialogue controls", details)
        if not self._campaign_structured_editors and selected != "retail_command":
            form.addRow(QLabel("This command has no fields yet. Add fields by editing the template or switch to Advanced command JSON."))
        host.layout().addWidget(group)

    def _campaign_commit_structured_fields(self, command, selected):
        if selected == "screen":
            fields = {key: editor for key, editor, _kind in self._campaign_structured_editors}
            effect = fields["effect"].currentData()
            command.clear()
            command.update(command="screen", effect=effect)
            if effect in ("shake", "letterbox"):
                command["strength"] = fields["strength"].value()
            if fields["frames"].value() or effect != "letterbox":
                command["frames"] = fields["frames"].value()
            return
        # Copy first so imported retail annotations and unknown future keys
        # survive if the current editor does not expose them.
        updated = copy.deepcopy(command)
        for key, editor, original_type in self._campaign_structured_editors:
            if isinstance(editor, QCheckBox):
                value = editor.isChecked()
            elif isinstance(editor, QComboBox):
                value = editor.currentData()
            elif isinstance(editor, QSpinBox):
                value = editor.value()
            elif isinstance(editor, QPlainTextEdit):
                try:
                    value = json.loads(editor.toPlainText())
                except ValueError as error:
                    raise ValueError(f"{key} must contain valid JSON.") from error
            else:
                value = editor.text()
            if original_type is int and isinstance(value, int):
                value = int(value)
            updated[key] = value
        command.clear()
        command.update(updated)

    def _campaign_fill_reference_combos(self, command, kind):
        c = self._campaign_widgets
        previous_loading = getattr(self, "_campaign_loading", False)
        self._campaign_loading = True
        assets = self._campaign_assets
        characters = {}
        root = self._campaign_folder
        if root:
            for relative in self._campaign_scene_files(f"{root}/characters"):
                try:
                    body = self._campaign_json(relative)
                except ValueError:
                    continue
                if isinstance(body, dict) and body.get("id"):
                    characters[body["id"]] = body
        character = c["character"]
        character.clear()
        for key, data in characters.items():
            character.addItem(data.get("display_name", key), key)
        char_key = command.get("speaker") if kind == "dialogue" else command.get("id")
        ix = character.findData(char_key)
        if ix >= 0: character.setCurrentIndex(ix)
        chosen = characters.get(char_key, {})
        pose = c["pose"]
        pose.clear()
        pose_names = list(chosen.get("portraits", {}))
        if kind in ("character", "hide_character"):
            sprites = assets.get("sprites", {})
            sprite = sprites.get(char_key, {}) if isinstance(sprites, dict) else {}
            folder = sprite.get("actor") if isinstance(sprite, dict) else None
            if folder and root:
                actor_path = Path(self.project.source_dir or "") / root / folder
                if actor_path.is_dir():
                    pose_names = sorted({p.stem.replace("-blink", "").replace("-talk", "")
                                         for p in actor_path.glob("*.png")})
                    pose_names = list(dict.fromkeys(pose_names))
        pose_names = pose_names or [""]
        for name in pose_names: pose.addItem(name or "Default", name)
        wanted = command.get("expression") if kind in ("character", "hide_character") else command.get("portrait")
        ix = pose.findData(wanted)
        if ix >= 0: pose.setCurrentIndex(ix)
        position = c["position"]
        position.clear()
        for value in ("far_left", "left", "center", "right", "far_right", "offscreen_left", "offscreen_right"):
            position.addItem(value.replace("_", " ").title(), value)
        raw_pos = command.get("position")
        pos_name = raw_pos if isinstance(raw_pos, str) else raw_pos.get("preset") if isinstance(raw_pos, dict) else None
        ix = position.findData(pos_name)
        if ix >= 0: position.setCurrentIndex(ix)
        background = c["background"]
        background.clear()
        binding = assets.get("backgrounds", {}) if isinstance(assets, dict) else {}
        if isinstance(binding, dict):
            for name in binding: background.addItem(str(name), str(name))
        ix = background.findData(command.get("id"))
        if ix >= 0: background.setCurrentIndex(ix)
        self._campaign_loading = previous_loading

    @staticmethod
    def _campaign_kind_for_command(command):
        if not isinstance(command, dict):
            return "__raw__"
        kind = command.get("command", "")
        simple = {"dialogue": "dialogue", "text": "dialogue", "say": "dialogue",
                  "character": "character", "show_character": "character", "spawn_character": "character",
                  "hide_character": "hide_character", "remove_character": "hide_character",
                  "background": "background", "wait": "wait", "pause": "wait",
                  "screen_shake": "screen", "flash": "screen", "letterbox": "screen"}
        return simple.get(kind, kind if kind in {value for _, value in CampaignMixin._CAMPAIGN_JSON_COMMANDS}
                          else "__raw__")

    @staticmethod
    def _campaign_command_template(kind):
        templates = {
            "music": {"command": "music", "id": ""},
            "stop_music": {"command": "stop_music"},
            "sound": {"command": "sound", "id": ""},
            "fade": {"command": "fade", "direction": "in", "frames": 30},
            "camera": {"command": "camera", "x": 0, "y": 0, "frames": 0},
            "set_flag": {"command": "set_flag", "id": "", "value": True},
            "set_variable": {"command": "set_variable", "id": "", "value": 0},
            "if": {"command": "if", "test": {"kind": "always"}, "then": "", "else": ""},
            "choice": {"command": "choice", "prompt_id": "", "options": [
                {"text_id": "", "goto": ""}, {"text_id": "", "goto": ""}]},
            "jump": {"command": "jump", "to": ""},
            "label": {"command": "label", "id": ""},
            "call_scene": {"command": "call_scene", "scene": ""},
            "return": {"command": "return"},
            "duel": {"command": "duel", "opponent": "", "win": "", "loss": ""},
            "teleport": {"command": "teleport", "place": ""},
            "move_character": {"command": "move_character", "id": "", "position": "center", "frames": 30},
            "animate_character": {"command": "animate_character", "id": "", "expression": ""},
            "screen": {"command": "screen", "effect": "shake", "strength": 4, "frames": 18},
            "retail_command": {"command": "retail_command", "opcode": 0,
                               "operands": [], "editor_label": "Imported stock command", "target": ""},
            "reward": {"command": "reward", "kind": "card", "id": ""},
            "save": {"command": "save"}, "results": {"command": "results"},
            "game_over": {"command": "game_over"}, "credits": {"command": "credits"},
            "main_menu": {"command": "main_menu"},
        }
        return copy.deepcopy(templates.get(kind, {"command": kind}))

    def _campaign_editor_changed(self, *_):
        if getattr(self, "_campaign_loading", False):
            return
        if not self._campaign_commit_step():
            return
        self._campaign_refresh_preview_steps()
        self._campaign_update_dialogue_count()
        self._campaign_editor_dirty()

    def _campaign_assets_edited(self):
        if not getattr(self, "_campaign_loading", False):
            self._campaign_editor_dirty()

    def _campaign_setup_asset_library(self):
        """Wire the visual asset lists once; their contents refresh with a mod.

        assets.json remains available as an escape hatch, but ordinary scene
        work should be choosing a visible, named asset rather than editing a
        JSON dictionary by hand.
        """
        c = self._campaign_widgets
        if getattr(self, "_campaign_asset_library_bound", None) is self._campaign_page:
            return
        self._campaign_asset_library_bound = self._campaign_page
        for list_key, search_key, group in (
                ("asset_backgrounds", "asset_background_search", "backgrounds"),
                ("asset_portraits", "asset_portrait_search", "portraits"),
                ("asset_audio", "asset_audio_search", "audio")):
            widget = c.get(list_key)
            if widget is not None:
                widget.setIconSize(QSize(96, 48))
                widget.itemDoubleClicked.connect(
                    lambda item, asset_group=group: self._campaign_assign_asset(asset_group, item))
            search = c.get(search_key)
            if search is not None:
                search.textChanged.connect(self._campaign_refresh_asset_library)
        raw_group = self._campaign_page.findChild(QGroupBox, "campaignRawGroup")
        if raw_group is not None and raw_group.layout() is not None:
            button = QPushButton("Run story preflight")
            button.setToolTip("Check scene flow, assets, labels, dialogue glyphs, and retail overrides before saving.")
            button.clicked.connect(self._campaign_show_preflight)
            raw_group.layout().addWidget(button)

    def _campaign_asset_usage(self, group, name):
        used = []
        for record in self._campaign_records:
            scene = record.get("scene", {})
            for _phase, _index, command in self._campaign_step_refs_for(scene):
                kind = command.get("command")
                if group == "backgrounds" and kind == "background" and command.get("id") == name:
                    used.append(scene.get("id", "scene"))
                elif group == "audio" and kind in ("music", "sound") and command.get("id") == name:
                    used.append(scene.get("id", "scene"))
                elif group == "portraits" and command.get("portrait") == name:
                    used.append(scene.get("id", "scene"))
        return used

    @staticmethod
    def _campaign_step_refs_for(scene):
        if not isinstance(scene, dict):
            return []
        return [(phase, index, command)
                for phase in ("on_start", "commands", "on_end")
                for index, command in enumerate(scene.get(phase, []))
                if isinstance(command, dict)]

    def _campaign_refresh_asset_library(self, *_):
        c = getattr(self, "_campaign_widgets", {})
        assets = getattr(self, "_campaign_assets", {})
        if not isinstance(assets, dict):
            return
        specs = (("asset_backgrounds", "asset_background_search", "backgrounds"),
                 ("asset_portraits", "asset_portrait_search", "portraits"),
                 ("asset_audio", "asset_audio_search", "audio"))
        for list_key, search_key, group in specs:
            widget = c.get(list_key)
            if widget is None:
                continue
            query = c.get(search_key).text().casefold().strip() if c.get(search_key) else ""
            bindings = assets.get(group, {})
            if group == "audio":
                bindings = {**(assets.get("music", {}) if isinstance(assets.get("music"), dict) else {}),
                            **(assets.get("sounds", {}) if isinstance(assets.get("sounds"), dict) else {}),
                            **(bindings if isinstance(bindings, dict) else {})}
            if not isinstance(bindings, dict):
                bindings = {}
            widget.clear()
            for name, record in sorted(bindings.items(), key=lambda item: str(item[0]).casefold()):
                name = str(name)
                used = self._campaign_asset_usage(group, name)
                description = f"{name} · used by {len(used)} scene(s)" if used else f"{name} · unused"
                if query and query not in description.casefold():
                    continue
                item = QListWidgetItem(description)
                item.setData(Qt.ItemDataRole.UserRole, name)
                item.setToolTip((", ".join(used) if used else "Not used by a mod scene") + "\nDouble-click to assign.")
                if group == "backgrounds" and isinstance(record, dict):
                    art = record.get("art")
                    if isinstance(art, str) and self._campaign_folder:
                        data = self._campaign_read(f"{self._campaign_folder}/{art}")
                        pixmap = QPixmap()
                        if data and pixmap.loadFromData(data):
                            item.setIcon(QIcon(pixmap.scaled(96, 48, Qt.AspectRatioMode.KeepAspectRatio,
                                                             Qt.TransformationMode.SmoothTransformation)))
                widget.addItem(item)

    def _campaign_assign_asset(self, group, item):
        name = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(name, str) or not self._campaign_commit_step():
            return
        refs = self._campaign_step_refs()
        row = getattr(self, "_campaign_active_row", None)
        if row is None or not 0 <= row < len(refs):
            self._campaign_say(self._campaign_widgets.get("status"), "Select an editable command before assigning an asset.")
            return
        _phase, _index, command = refs[row]
        kind = command.get("command")
        if group == "backgrounds" and kind == "background":
            command["id"] = name
        elif group == "audio" and kind in ("music", "sound"):
            command["id"] = name
        elif group == "portraits" and kind in ("dialogue", "character", "hide_character"):
            command["portrait" if kind == "dialogue" else "id"] = name
        else:
            self._campaign_say(self._campaign_widgets.get("status"),
                               f"{name} cannot be assigned to a {kind or 'selected'} command.")
            return
        self._campaign_refresh_step_row(row)
        self._campaign_refresh_previews(command)
        self._campaign_editor_dirty()
        self._campaign_say(self._campaign_widgets.get("status"), f"Assigned {name} to command {row + 1}.")

    def _campaign_preflight(self):
        problems = []
        runtime = self._campaign_validate_runtime()
        if runtime:
            problems.append(runtime)
        ids = {record["scene"].get("id") for record in self._campaign_records}
        assets = getattr(self, "_campaign_assets", {}) if isinstance(getattr(self, "_campaign_assets", {}), dict) else {}
        backgrounds = assets.get("backgrounds", {}) if isinstance(assets.get("backgrounds", {}), dict) else {}
        audio = set()
        for group in ("audio", "music", "sounds"):
            if isinstance(assets.get(group), dict): audio.update(map(str, assets[group]))
        glyphs = None
        try:
            import story_listing
            glyphs = set(story_listing.GameText(self.files.slus).glyphs.values())
        except Exception:
            pass
        for record in self._campaign_records:
            scene = record["scene"]
            labels = {command.get("id") for _p, _i, command in self._campaign_step_refs_for(scene)
                      if command.get("command") == "label"}
            for phase, index, command in self._campaign_step_refs_for(scene):
                where = f"{scene.get('id', 'scene')} {phase} command {index + 1}"
                kind = command.get("command")
                if kind == "jump" and command.get("to") not in labels:
                    problems.append(f"{where}: label '{command.get('to', '')}' does not exist in this scene.")
                if kind == "if":
                    for target in (command.get("then"), command.get("else")):
                        if target and target not in labels:
                            problems.append(f"{where}: branch label '{target}' does not exist in this scene.")
                if kind == "call_scene" and command.get("scene") not in ids:
                    problems.append(f"{where}: scene '{command.get('scene', '')}' does not exist.")
                if kind == "background" and command.get("id") and command.get("id") not in backgrounds:
                    problems.append(f"{where}: background '{command['id']}' is not bound in assets.")
                if kind in ("music", "sound") and command.get("id") and str(command["id"]) not in audio:
                    problems.append(f"{where}: audio '{command['id']}' is not bound in assets.")
                if kind == "dialogue":
                    text = command.get("text", "")
                    if isinstance(text, str) and glyphs is not None:
                        unknown = sorted({character for character in text if character not in glyphs and character not in "\n\r"})
                        if unknown:
                            problems.append(f"{where}: unavailable dialogue glyph(s): {''.join(unknown[:8])!r}.")
        retail = [record["scene"].get("scene_number") for record in self._campaign_records
                  if record["scene"].get("scene_number") is not None]
        for number in sorted({number for number in retail if retail.count(number) > 1}):
            problems.append(f"Retail scene {number:03d} has more than one override.")
        return problems

    def _campaign_show_preflight(self):
        if not self._campaign_commit_step():
            return
        problems = self._campaign_preflight()
        message = "Story preflight passed: the staged package is runnable." if not problems else \
                  "Story preflight found:\n\n" + "\n".join("• " + item for item in problems)
        QMessageBox.information(self, "Story preflight", message)
        self._campaign_say(self._campaign_widgets.get("status"),
                           "Story preflight passed." if not problems else f"Story preflight found {len(problems)} issue(s).")

    def _campaign_commit_step(self):
        if getattr(self, "_campaign_loading", False):
            return True
        row = getattr(self, "_campaign_active_row", None)
        c = getattr(self, "_campaign_widgets", {})
        if row is None or not c or "steps" not in c:
            return True
        refs = self._campaign_step_refs()
        if row >= len(refs): return True
        phase, index, command = refs[row]
        kind = self._campaign_kind_for_command(command)
        if kind == "__raw__":
            try:
                raw = json.loads(c["dialogue"].toPlainText())
                if not isinstance(raw, dict) or not isinstance(raw.get("command"), str):
                    raise ValueError("A command must be a JSON object with a command name.")
                command.clear(); command.update(raw)
            except ValueError:
                self._campaign_say(c.get("status"), "The advanced command must be valid JSON with a string 'command' field.")
                return False
        elif kind in {value for _, value in self._CAMPAIGN_JSON_COMMANDS}:
            try:
                self._campaign_commit_structured_fields(command, kind)
            except ValueError as error:
                self._campaign_say(c.get("status"), str(error))
                return False
        elif kind == "dialogue":
            command["command"] = "dialogue"
            text = c["dialogue"].toPlainText()
            key = command.get("text_id")
            if key:
                self._campaign_dialogue_edits[key] = text
            else:
                command["text"] = text
            character = c["character"].currentData()
            if character: command["speaker"] = character
            pose = c["pose"].currentData()
            if pose: command["portrait"] = pose
            position = c["position"].currentData()
            if position: command["position"] = position
            command["keep_box"] = c["keep_box"].isChecked()
            text_speed = c["number"].value()
            if text_speed:
                command["text_speed"] = text_speed
            else:
                command.pop("text_speed", None)
        elif kind == "wait":
            command.clear(); command.update(command="wait", frames=c["number"].value())
        elif kind == "background":
            command["command"] = "background"
            command["id"] = c["background"].currentData() or command.get("id", "")
        elif kind in ("character", "hide_character"):
            command["command"] = kind
            character = c["character"].currentData()
            if character: command["id"] = character
            pose = c["pose"].currentData()
            if pose: command["expression"] = pose
            position = c["position"].currentData()
            if position: command["position"] = position
        self._campaign_refresh_step_row(row)
        return True

    def _campaign_editor_dirty(self):
        if getattr(self, "_campaign_loading", False): return
        self._campaign_dirty = True
        self._mark_dirty()
        self._campaign_say(self._campaign_widgets.get("status"), "Story changes are staged. Apply story data or save the mod to write them.")

    def _campaign_update_dialogue_count(self):
        c = getattr(self, "_campaign_widgets", {})
        if "dialogue" in c:
            words = c["dialogue"].toPlainText()
            c["dialogue_count"].setText(f"{len(words)} characters · {words.count(chr(10)) + 1} line(s)")

    def _campaign_selected_step(self):
        table = self._campaign_widgets["steps"]
        return table.currentRow()

    def _campaign_mutate_commands(self, action):
        if not self._campaign_commit_step():
            return
        row = self._campaign_selected_step()
        refs = self._campaign_step_refs()
        if 0 <= row < len(refs):
            phase, index, command = refs[row]
            values = self._campaign_scene().get(phase, [])
            if action == "remove":
                del values[index]
                self._campaign_refresh_scene_selection(max(0, row - 1))
            elif action in ("up", "down"):
                target = index + (-1 if action == "up" else 1)
                if 0 <= target < len(values):
                    values[index], values[target] = values[target], values[index]
                    self._campaign_refresh_scene_selection(target if phase == "commands" else row)
            elif action == "duplicate":
                values.insert(index + 1, copy.deepcopy(command))
                self._campaign_refresh_scene_selection(row + 1)
        self._campaign_editor_dirty()

    def _campaign_refresh_scene_selection(self, row):
        item = self._campaign_widgets["scenes"].currentItem()
        if item is None: return
        self._campaign_active_row = None
        self._campaign_scene_changed(item, None)
        if self._campaign_widgets["steps"].rowCount():
            self._campaign_widgets["steps"].selectRow(min(row, self._campaign_widgets["steps"].rowCount() - 1))

    def _campaign_add_step(self, kind="dialogue"):
        if not self._campaign_commit_step():
            return
        scene = self._campaign_scene()
        if scene is None:
            return
        if kind in {value for _, value in self._CAMPAIGN_JSON_COMMANDS}:
            command = self._campaign_command_template(kind)
        elif kind == "dialogue":
            command = {"command": "dialogue", "text": ""}
        elif kind == "wait":
            command = {"command": "wait", "frames": 30}
        elif kind == "background":
            command = {"command": "background", "id": ""}
        elif kind == "character":
            command = {"command": "character", "id": "", "expression": "", "position": "center"}
        elif kind == "hide_character":
            command = {"command": "hide_character", "id": ""}
        elif kind == "__raw__":
            command = {"command": "custom"}
        else:
            command = {"command": kind}
        # Insert beside the selected command: writing a scene should feel like
        # editing a stream, not appending to a distant end of its JSON array.
        selected = self._campaign_selected_step()
        refs = self._campaign_step_refs()
        if 0 <= selected < len(refs):
            phase, index, _old = refs[selected]
            values = scene.setdefault(phase, [])
            values.insert(index + 1, command)
            row = selected + 1
        else:
            commands = scene.setdefault("commands", [])
            commands.append(command)
            row = len(scene.get("on_start", [])) + len(commands) - 1
        self._campaign_refresh_scene_selection(row)
        self._campaign_editor_dirty()

    def _campaign_remove_step(self): self._campaign_mutate_commands("remove")
    def _campaign_move_step_up(self): self._campaign_mutate_commands("up")
    def _campaign_move_step_down(self): self._campaign_mutate_commands("down")
    def _campaign_duplicate_step(self): self._campaign_mutate_commands("duplicate")

    def _campaign_add_scene(self):
        if not self._campaign_folder:
            self._campaign_folder = "scenes"
            self.project.other["story"] = "scenes"
            self._campaign_assets = {}
        used = {record["scene"].get("id") for record in self._campaign_records}
        number = 1
        while f"new_scene_{number}" in used: number += 1
        scene_id = f"new_scene_{number}"
        scene = {"id": scene_id, "name": f"New scene {number}", "entered": False, "commands": []}
        path = f"{self._campaign_folder}/{scene_id}.json"
        self._campaign_documents[path] = [scene]
        self._campaign_records.append({"scene": scene, "path": path})
        self._campaign_selected_id = scene_id
        self._campaign_fill_scene_tree()
        self._campaign_editor_dirty()

    def _campaign_duplicate_scene(self):
        token = getattr(self, "_campaign_selected_id", None)
        stock = next((record for record in self._campaign_stock_records
                      if record["token"] == token), None)
        if stock is not None:
            if not self._campaign_folder:
                self._campaign_folder = "scenes"
                self.project.other["story"] = self._campaign_folder
                self._campaign_assets = {}
            number = int(stock["scene"]["scene_number"])
            scene_id = f"retail_scene_{number:03d}_override"
            ids = {record["scene"].get("id") for record in self._campaign_records}
            suffix = 2
            base = scene_id
            while scene_id in ids:
                scene_id = f"{base}_{suffix}"
                suffix += 1
            answer = QMessageBox.question(
                self, "Create retail-scene override",
                f"Import retail scene {number:03d} ({stock['scene'].get('name', 'Retail scene')}) "
                "as an editable mod scene?\n\n"
                "The imported command sequence includes reachable branches and preserves embedded "
                "dialogue controls by retaining the original retail dialogue IDs. Select an imported "
                "command to edit its opcode, operands, and branch target in the step editor. Embedded "
                "dialogue controls are listed with the dialogue command that owns them.")
            if answer != QMessageBox.StandardButton.Yes:
                return
            scene = {"id": scene_id, "name": stock["scene"].get("name", scene_id),
                     "scene_number": number, "entered": False,
                     "commands": copy.deepcopy(stock.get("commands", []))}
            path = f"{self._campaign_folder}/{scene_id}.json"
            self._campaign_documents[path] = [scene]
            self._campaign_records.append({"scene": scene, "path": path})
            self._campaign_selected_id = scene_id
            self._campaign_fill_scene_tree()
            self._campaign_editor_dirty()
            return
        scene = self._campaign_scene()
        if scene is None: return
        duplicate = copy.deepcopy(scene)
        original = duplicate.get("id", "scene")
        candidate = f"{original}_copy"
        n = 2
        ids = {item["scene"].get("id") for item in self._campaign_records}
        while candidate in ids:
            candidate = f"{original}_copy{n}"; n += 1
        duplicate["id"] = candidate
        duplicate["name"] = f"{duplicate.get('name', original)} (copy)"
        duplicate.pop("scene_number", None)
        duplicate["entered"] = False
        path = f"{self._campaign_folder}/{candidate}.json"
        self._campaign_documents[path] = [duplicate]
        self._campaign_records.append({"scene": duplicate, "path": path})
        self._campaign_selected_id = candidate
        self._campaign_fill_scene_tree()
        self._campaign_editor_dirty()

    def _campaign_rename_scene(self):
        scene = self._campaign_scene()
        if scene is None: return
        name, ok = QInputDialog.getText(self, "Rename scene", "Scene id:", text=str(scene.get("id", "")))
        if not ok: return
        name = name.strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
            QMessageBox.warning(self, "Rename scene", "Use letters, numbers, _ or - for the scene id.")
            return
        if any(record["scene"].get("id") == name and record["scene"] is not scene for record in self._campaign_records):
            QMessageBox.warning(self, "Rename scene", "That scene id is already in use.")
            return
        old = scene.get("id")
        scene["id"] = name
        scene["name"] = name
        self._campaign_selected_id = name
        for record in self._campaign_records:
            for key in ("else_scene",):
                if record["scene"].get(key) == old: record["scene"][key] = name
            for phase in ("on_start", "commands", "on_end"):
                for command in record["scene"].get(phase, []) if isinstance(record["scene"].get(phase), list) else []:
                    for key in ("scene", "win", "loss"):
                        if command.get(key) == old: command[key] = name
        self._campaign_fill_scene_tree()
        self._campaign_editor_dirty()

    def _campaign_edit_scene_json(self, item, _column=0):
        scene = self._campaign_scene()
        if scene is None or item is None:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Scene data — {scene.get('id', '')}")
        dialog.resize(760, 620)
        layout = QVBoxLayout(dialog)
        editor = QPlainTextEdit(dialog)
        editor.setPlainText(json.dumps(scene, ensure_ascii=False, indent=2))
        layout.addWidget(editor)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel,
                                   parent=dialog)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            updated = json.loads(editor.toPlainText())
        except ValueError as error:
            QMessageBox.warning(self, "Scene data", f"Invalid JSON: {error}")
            return
        if not isinstance(updated, dict) or not isinstance(updated.get("id"), str) or not updated["id"].strip():
            QMessageBox.warning(self, "Scene data", "A scene must be an object with a non-empty string 'id'.")
            return
        if any(record["scene"].get("id") == updated["id"] and record["scene"] is not scene
               for record in self._campaign_records):
            QMessageBox.warning(self, "Scene data", f"Scene id '{updated['id']}' is already in use.")
            return
        old_id = scene.get("id")
        scene.clear(); scene.update(updated)
        if old_id != scene.get("id"):
            self._campaign_selected_id = scene["id"]
        self._campaign_fill_scene_tree()
        self._campaign_editor_dirty()

    def _campaign_remove_scene(self):
        scene = self._campaign_scene()
        if scene is None: return
        answer = QMessageBox.question(self, "Remove scene", f"Remove scene '{scene.get('id')}' from this mod?")
        if answer != QMessageBox.StandardButton.Yes: return
        if not self._campaign_commit_step(): return
        self._campaign_active_row = None
        removed_id = scene.get("id")
        self._campaign_records = [record for record in self._campaign_records if record["scene"] is not scene]
        for path, scenes in self._campaign_documents.items():
            self._campaign_documents[path] = [value for value in scenes if value is not scene]
        self._campaign_selected_id = None
        self._campaign_fill_scene_tree()
        self._campaign_say(self._campaign_widgets.get("status"), f"Removed scene {removed_id}. References to it may need updating.")
        self._campaign_editor_dirty()

    def _campaign_revert_to_retail(self):
        scene = self._campaign_scene()
        if scene is None or scene.get("scene_number") is None:
            return
        number = int(scene["scene_number"])
        stock = next((record for record in self._campaign_stock_records
                      if int(record["scene"].get("scene_number", -1)) == number), None)
        if stock is None:
            return
        answer = QMessageBox.question(
            self, "Revert to retail scene",
            f"Remove the mod override for retail scene {number:03d} and restore the stock scene?\n\n"
            "This removes that scene document from the staged story package.")
        if answer != QMessageBox.StandardButton.Yes:
            return
        scene_id = scene.get("id")
        record = next((item for item in self._campaign_records if item["scene"] is scene), None)
        if record is not None:
            document = self._campaign_documents.get(record["path"], [])
            self._campaign_documents[record["path"]] = [entry for entry in document if entry is not scene]
            self._campaign_records.remove(record)
        self._campaign_selected_id = stock["token"]
        self._campaign_fill_scene_tree()
        self._campaign_editor_dirty()
        self._campaign_say(self._campaign_widgets.get("status"), 
            f"Removed override {scene_id}; retail scene {number:03d} is active again. Apply or save the mod.")

    def _campaign_refresh_step_row(self, row):
        table = self._campaign_widgets["steps"]
        refs = self._campaign_step_refs()
        if 0 <= row < len(refs):
            table.setItem(row, 2, QTableWidgetItem(self._campaign_story_line(refs[row][2], row + 1)))
        scene = self._campaign_scene()
        if scene is not None:
            self._campaign_say(self._campaign_widgets.get("scene_context"), 
                f"● Scene starts here · {scene.get('id', '')} · {len(refs)} event(s)")
        self._campaign_refresh_story_navigator()
        self._campaign_refresh_flags()
        self._campaign_populate_timeline()

    def _campaign_refresh_preview_steps(self):
        """Refresh the preview using the selected command-table row as its playhead."""
        self._campaign_preview_changed()

    def _campaign_refresh_previews(self, command=None):
        c = self._campaign_widgets
        self._campaign_set_image(c["background_preview"], command)
        preview_image = self._campaign_mod_scene_preview(command)
        if preview_image is not None and not preview_image.isNull():
            refs = self._campaign_step_refs()
            selected_index = getattr(self, "_campaign_active_row", None)
            prior = [entry[2] for entry in refs[:selected_index + 1]] \
                if isinstance(selected_index, int) else []
            dialogue = ""
            for item in prior:
                if item.get("command") != "dialogue":
                    continue
                dialogue = (item.get("text") or
                            self._campaign_dialogue_edits.get(item.get("text_id"), ""))
                if item.get("text_id") and not dialogue:
                    try:
                        dialogue = (self._campaign_json(
                            f"{self._campaign_folder}/dialogue/en.json", {}) or {}).get(item["text_id"], "")
                    except (KeyError, ValueError):
                        dialogue = ""
            if dialogue or (self._campaign_widgets.get("show_frame") and
                            self._campaign_widgets["show_frame"].isChecked()):
                preview_image = self._campaign_with_dialogue_frame(preview_image, dialogue)
            preview_image = self._campaign_apply_preview_effects(preview_image, prior)
            c["preview"].setPixmap(preview_image.scaled(
                c["preview"].contentsRect().size(), Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))
            c["preview"].setText("")
            timeline_preview = c.get("timeline_preview")
            if timeline_preview is not None:
                timeline_preview.setPixmap(preview_image.scaled(
                    timeline_preview.contentsRect().size(), Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation))
                timeline_preview.setText("")
        else:
            self._campaign_set_image(c["preview"], command, large=True)
            if c.get("timeline_preview") is not None:
                self._campaign_set_image(c["timeline_preview"], command, large=True)
        c["portrait_preview"].setText(str(c["pose"].currentText() or "—"))

    @staticmethod
    def _campaign_apply_preview_effects(image, commands):
        """Render persistent screen effects and a representative timed-effect frame."""
        result = QPixmap(image)
        letterbox_height = 0
        timed_effect = None
        for index, command in enumerate(commands):
            if not isinstance(command, dict):
                continue
            kind = command.get("command")
            effect = command.get("effect") if kind == "screen" else {
                "screen_shake": "shake", "flash": "flash", "letterbox": "letterbox"}.get(kind)
            if not effect:
                continue
            default_strength = 28 if effect == "letterbox" else 4
            strength = int(command.get("strength", default_strength))
            if effect == "letterbox":
                letterbox_height = strength
            elif index == len(commands) - 1:
                timed_effect = (effect, strength)
        if timed_effect:
            effect, strength = timed_effect
            if effect == "shake":
                shifted = QPixmap(result.size())
                shifted.fill(Qt.GlobalColor.black)
                painter = QPainter(shifted)
                painter.drawPixmap(max(-8, min(8, strength)), 0, result)
                painter.end()
                result = shifted
            elif effect == "flash":
                painter = QPainter(result)
                painter.fillRect(result.rect(), QColor(255, 255, 255, 150))
                painter.end()
        if letterbox_height:
            height = max(0, min(80, letterbox_height))
            painter = QPainter(result)
            painter.fillRect(0, 0, result.width(), height, Qt.GlobalColor.black)
            painter.fillRect(0, result.height() - height, result.width(), height, Qt.GlobalColor.black)
            painter.end()
        return result

    def _campaign_mod_scene_preview(self, selected_command):
        """Compose a mod background and its visible actor for the selected step."""
        scene = self._campaign_scene()
        if scene is None:
            return None
        refs = self._campaign_step_refs()
        index = getattr(self, "_campaign_active_row", None)
        if not isinstance(index, int):
            return None
        prior = [entry[2] for entry in refs[:index + 1]]
        background = None
        for item in prior:
            kind = item.get("command")
            if kind in ("background", "set_background"):
                background = item
            elif kind == "fade" or kind == "screen_fade":
                # A screen fade clears the scene to black. A later background
                # command starts drawing the next scene image again.
                background = None
        canvas = QPixmap(320, 240)
        canvas.fill(Qt.GlobalColor.black)
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        if background is not None:
            binding = self._campaign_assets.get("backgrounds", {}).get(background.get("id"))
            art = binding.get("art") if isinstance(binding, dict) else None
            blob = self._campaign_read(f"{self._campaign_folder}/{art}") if art and self._campaign_folder else None
            bg = QPixmap()
            if blob and bg.loadFromData(blob):
                painter.drawPixmap(0, 0, 320, 160, bg)

        visible = {}
        for item in prior:
            kind = item.get("command")
            if kind in ("character", "show_character", "spawn_character"):
                visible[item.get("id")] = item
            elif kind in ("hide_character", "remove_character"):
                visible.pop(item.get("id"), None)
            elif kind == "dialogue" and item.get("speaker"):
                visible[item["speaker"]] = {
                    "id": item["speaker"], "expression": item.get("portrait"),
                    "position": item.get("position", "center")}
        characters = {}
        for relative in self._campaign_scene_files(f"{self._campaign_folder}/characters"):
            try:
                data = self._campaign_json(relative)
            except ValueError:
                continue
            if isinstance(data, dict) and data.get("id"):
                characters[data["id"]] = data
        sprite_assets = self._campaign_assets.get("sprites", {})
        for character_id, state in visible.items():
            character = characters.get(character_id, {})
            sprite_id = character.get("sprite", character_id)
            sprite = sprite_assets.get(sprite_id, {}) if isinstance(sprite_assets, dict) else {}
            folder = sprite.get("actor") if isinstance(sprite, dict) else None
            if not folder:
                continue
            expression = state.get("expression") or sprite.get("default") or "neutral"
            actor_blob = self._campaign_read(f"{self._campaign_folder}/{folder}/{expression}.png")
            if not actor_blob:
                expression = sprite.get("default", "neutral")
                actor_blob = self._campaign_read(f"{self._campaign_folder}/{folder}/{expression}.png")
            actor = QPixmap()
            if actor_blob:
                actor.loadFromData(actor_blob)
            if actor.isNull():
                continue
            size = sprite.get("size")
            if isinstance(size, list) and len(size) == 2:
                width, height = int(size[0]), int(size[1])
            else:
                height = 176
                width = max(8, round(actor.width() * height / max(1, actor.height()) / 8) * 8)
            actor = actor.scaled(width, height, Qt.AspectRatioMode.IgnoreAspectRatio,
                                 Qt.TransformationMode.SmoothTransformation)
            anchor = sprite.get("anchor", [width // 2, height])
            if not isinstance(anchor, list) or len(anchor) != 2:
                anchor = [width // 2, height]
            position = state.get("position", "center")
            if isinstance(position, dict):
                preset = position.get("preset", "center")
                px = {"far_left": 32, "left": 80, "center": 160, "right": 240,
                      "far_right": 288, "offscreen_left": -32, "offscreen_right": 352}.get(preset, 160)
                py = 160
                if "x" in position: px = int(position["x"])
                if "y" in position: py = int(position["y"])
                offset = position.get("offset", {})
                if isinstance(offset, dict):
                    px += int(offset.get("x", 0)); py += int(offset.get("y", 0))
            else:
                px = {"far_left": 32, "left": 80, "center": 160, "right": 240,
                      "far_right": 288, "offscreen_left": -32, "offscreen_right": 352}.get(position, 160)
                py = 160
            painter.drawPixmap(px - int(anchor[0]), py - int(anchor[1]), actor)
        painter.end()
        return canvas

    def _campaign_set_image(self, label, command=None, large=False):
        label.clear()
        if not command or command.get("command") not in ("background", "set_background"):
            label.setText("Choose a background step to preview." if large else "No background")
            return
        asset = self._campaign_assets.get("backgrounds", {}).get(command.get("id"))
        art_path = asset.get("art") if isinstance(asset, dict) else None
        if not art_path:
            label.setText(str(command.get("id", "Retail background")))
            return
        relative = f"{self._campaign_folder}/{art_path}"
        blob = self._campaign_read(relative)
        pixmap = QPixmap()
        if blob and pixmap.loadFromData(blob):
            label.setPixmap(pixmap.scaled(label.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                          Qt.TransformationMode.SmoothTransformation))
        else:
            label.setText(f"Missing image: {art_path}")

    @staticmethod
    def _campaign_stock_path_offsets(stock, target_offset):
        """Find one executable route from scene entry to a selected stock command."""
        def number(value):
            try:
                return int(str(value), 16)
            except (TypeError, ValueError):
                return None

        commands = {}
        for entry in stock.get("commands", []):
            command = entry.get("command_data") if isinstance(entry.get("command_data"), dict) else entry
            if command.get("command") == "retail_command":
                offset = number(command.get("offset"))
                if offset is not None:
                    commands[offset] = command
        target = number(target_offset)
        if target is None or target not in commands or not commands:
            return None
        start = next(iter(commands))
        pending = [(start, (start,))]
        visited = set()
        while pending:
            offset, path = pending.pop(0)
            if offset == target:
                return set(path)
            if offset in visited:
                continue
            visited.add(offset)
            command = commands.get(offset, {})
            opcode = command.get("opcode")
            branches = [number(target.get("offset")) for target in command.get("branch_targets", [])
                        if isinstance(target, dict)]
            branches = [value for value in branches if value in commands]
            fallthrough = number(command.get("fallthrough_offset"))
            edges = branches if opcode == 12 else (
                ([fallthrough] if fallthrough in commands else []) +
                (branches if opcode in (3, 21) else []))
            if opcode in (0, 8, 14, 15, 18, 19, 22):
                edges = []
            for destination in edges:
                if destination not in visited:
                    pending.append((destination, (*path, destination)))
        return None

    def _campaign_stock_steps_through(self, stock, selected):
        """Return the decoded state leading to one visible native command.

        Retail dialogue expands into several hidden controls.  The command
        table deliberately hides that noise, so resolve its command offset
        back to the first line of dialogue before rebuilding the preview.
        """
        steps = stock.get("steps", [])
        if isinstance(selected, dict):
            target = selected.get("command_offset")
        elif isinstance(selected, int) and 0 <= selected < len(steps):
            target = steps[selected].get("command_offset")
        else:
            return []
        # Route markers deliberately share their destination's offset.  They
        # are navigation notes, not the native command itself; selecting one
        # here used to stop before the following Background/Dialogue row and
        # consequently produced a black preview.
        matches = [index for index, step in enumerate(steps)
                   if step.get("command_offset") == target and step.get("type") != "Route"]
        if not matches:
            return []
        if selected.get("retail_embedded_control"):
            # The friendly Show character row is an F6 control inside the
            # following native dialogue command.  It must show the state
            # immediately after F6, *before* that command starts printing.
            selected_index = next((index for index in matches
                                   if steps[index].get("effect_id") == selected.get("effect_id") and
                                   int(steps[index].get("flags", 0)) == int(selected.get("flags", 0))),
                                  matches[0])
        else:
            # For one Show text command, stop at its first printed line.
            # Effects immediately before it (including Show portrait) are
            # then visible; replaying the whole dialogue would end after its
            # portrait-hide code.
            selected_index = next((index for index in matches
                                   if steps[index].get("dialogue_text")), matches[0])
        route = self._campaign_stock_path_offsets(stock, target)
        if route is None:
            return steps[:selected_index + 1]
        active = []
        for step in steps[:selected_index + 1]:
            offset = step.get("command_offset")
            try:
                offset = int(str(offset), 16) if offset is not None else None
            except (TypeError, ValueError):
                offset = None
            if offset is None or offset in route:
                active.append(step)
        return active

    def _campaign_preview_changed(self, *_):
        token = getattr(self, "_campaign_selected_id", None)
        stock = next((record for record in getattr(self, "_campaign_stock_records", [])
                      if record["token"] == token), None)
        if stock is not None:
            number = stock["scene"]["scene_number"]
            index = getattr(self, "_campaign_active_row", None)
            outline = getattr(self, "_campaign_visible_stock_steps", None)
            if not isinstance(outline, list):
                outline = self._campaign_stock_outline(stock)
            selected = outline[index] if isinstance(index, int) and 0 <= index < len(outline) else None
            active = self._campaign_stock_steps_through(stock, selected) if selected else []
            selected_detail = active[-1] if active else selected
            dialogue_step = next((step for step in reversed(active)
                                  if step.get("dialogue_text") and step.get("dialogue_id") is not None), None)
            dialogue = dialogue_step.get("dialogue_text", "") if dialogue_step else ""
            picture = None
            sprites = [None, None]
            shared_effects = [None, None]
            portrait_effect_id = None
            faded = False
            for step in active:
                if step.get("screen_fade"):
                    picture, faded = None, True
                if step.get("clear_picture"):
                    picture, faded = None, True
                elif step.get("picture_id") is not None:
                    picture, faded = step["picture_id"], False
                sprite_id = step.get("sprite_id")
                if sprite_id is not None:
                    flags = int(step.get("sprite_flags", 0))
                    slot = 1 if flags & 0x80 else 0
                    sprites[slot] = (sprite_id, flags)
                effect_id = step.get("effect_id")
                # Effects below 0x41 are the original campaign character
                # resources.  The game keeps one in each shared side slot;
                # their texture lives in the 50-sector display-effect bank,
                # rather than in the small dialogue-portrait bank below.
                if isinstance(effect_id, int) and 0 <= effect_id < self._DIALOGUE_PORTRAIT_FIRST_EFFECT_ID:
                    flags = int(step.get("flags", 0))
                    slot = flags & 1
                    if flags & 0x80:
                        shared_effects[slot] = None
                    elif not flags & 0x60:
                        shared_effects[slot] = effect_id
                if isinstance(effect_id, int) and (
                        self._DIALOGUE_PORTRAIT_FIRST_EFFECT_ID <= effect_id <=
                        self._DIALOGUE_PORTRAIT_LAST_EFFECT_ID):
                    if int(step.get("flags", 0)) & 0x80:
                        portrait_effect_id = None
                    else:
                        portrait_effect_id = effect_id
            pixmap = self._campaign_retail_background(picture) if picture is not None and not faded else QPixmap()
            if pixmap.isNull():
                pixmap = QPixmap(320, 240)
                pixmap.fill(Qt.GlobalColor.black)
            scene_pixmap = QPixmap(320, 240)
            scene_pixmap.fill(Qt.GlobalColor.black)
            painter = QPainter(scene_pixmap)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
            if not pixmap.isNull() and picture is not None and not faded:
                painter.drawPixmap(0, 0, 320, 160, pixmap)
            for slot, sprite in enumerate(sprites):
                if sprite is None:
                    continue
                actor = self._campaign_retail_sprite(sprite[0])
                if actor.isNull():
                    continue
                height = 176
                actor = actor.scaled(max(1, round(actor.width() * height / max(1, actor.height()))), height,
                                     Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation)
                x = (252 if slot else 160) - actor.width() // 2
                painter.drawPixmap(x, 160 - actor.height(), actor)
            for slot, effect_id in enumerate(shared_effects):
                if effect_id is None:
                    continue
                actor = self._campaign_retail_shared_effect(effect_id)
                if actor.isNull():
                    continue
                # The native effect object begins just outside the matching
                # edge and slides in.  This static preview uses its settled
                # position, above the dialogue box, so the author can see
                # which retail character is active.
                height = min(176, actor.height())
                actor = actor.scaled(max(1, round(actor.width() * height / max(1, actor.height()))), height,
                                     Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation)
                x = (0 if slot == 0 else 320 - actor.width())
                painter.drawPixmap(x, 160 - actor.height(), actor)
            if portrait_effect_id is not None:
                portrait = self._campaign_retail_portrait(portrait_effect_id)
                if not portrait.isNull():
                    painter.drawPixmap(240, 96, portrait)
            painter.end()
            pixmap = scene_pixmap
            preview = self._campaign_widgets["preview"]
            show_frame = self._campaign_widgets.get("show_frame")
            if dialogue or (show_frame and show_frame.isChecked()):
                pixmap = self._campaign_with_dialogue_frame(pixmap, dialogue)
            preview.setWordWrap(False)
            preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
            target = preview.contentsRect().size()
            if target.width() < 64 or target.height() < 64:
                target = QSize(640, 360)
            preview.setPixmap(pixmap.scaled(target, Qt.AspectRatioMode.KeepAspectRatio,
                                            Qt.TransformationMode.SmoothTransformation))
            timeline_preview = self._campaign_widgets.get("timeline_preview")
            if timeline_preview is not None:
                timeline_target = timeline_preview.contentsRect().size()
                if timeline_target.width() < 64 or timeline_target.height() < 64:
                    timeline_target = QSize(640, 360)
                timeline_preview.setPixmap(pixmap.scaled(timeline_target, Qt.AspectRatioMode.KeepAspectRatio,
                                                         Qt.TransformationMode.SmoothTransformation))
                timeline_preview.setText("")
            preview.setToolTip(f"Retail scene {number:03d}: {selected_detail['description']}" if selected_detail
                               else f"Retail scene {number:03d}")
            self._campaign_widgets["background_preview"].setText(
                "Screen is faded to black" if faded else
                f"Retail picture 0x{picture:03X}" if picture is not None else
                "No background yet; sprites are shown over black.")
            return
            lines = [f"Retail scene {number:03d} · {stock['scene']['name']}"]
            if selected:
                lines.extend(("", f"Step {index + 1} · {selected['type']}", selected["description"]))
            else:
                lines.extend(("", *(f"{step['type']}: {step['description']}" for step in steps[:12])))
                if len(steps) > 12:
                    lines.append(f"… {len(steps) - 12} more steps")
            picture = (backdrop_step.get("picture_id") if backdrop_step else None)
            reason = getattr(self, "_campaign_preview_error", "")
            message = (f"Retail backdrop 0x{picture:03X} contains no visible pixels; "
                       "the game may be keeping the previous scene image."
                       if picture is not None and "no visible pixels" in reason else
                       f"Could not decode retail backdrop 0x{picture:03X}." if picture is not None
                       else "This step has no active background image.")
            if reason:
                message += f" Decoder detail: {reason}"
            lines.extend(("", message))
            preview = self._campaign_widgets["preview"]
            preview.setWordWrap(True)
            preview.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            preview.setText("\n".join(lines))
            backdrop = self._campaign_widgets["background_preview"]
            backdrop.setWordWrap(True)
            backdrop.setText("Retail backdrop details appear in the storyboard.")
            return
        refs = self._campaign_step_refs()
        index = getattr(self, "_campaign_active_row", None)
        command = refs[index][2] if isinstance(index, int) and 0 <= index < len(refs) else None
        self._campaign_refresh_previews(command)

    def _campaign_retail_sprite(self, sprite_id):
        """Decode one stock campaign character with the game's sheet script."""
        cache = getattr(self, "_campaign_retail_sprite_cache", None)
        if cache is None:
            cache = self._campaign_retail_sprite_cache = {}
        sprite_id = int(sprite_id)
        if sprite_id in cache:
            return cache[sprite_id]
        result = QPixmap()
        try:
            if not 1 <= sprite_id <= 64:
                return result
            pc_tools = str(Path(__file__).resolve().parents[1])
            if pc_tools not in sys.path:
                sys.path.insert(0, pc_tools)
            import character_sheet

            character = character_sheet.Character(self.files.wa, sprite_id)
            pose = 0
            body = character.frames(pose, 0)
            if body:
                sheets = [character.parts(body[0][1])]
                eyes = character.shapes(pose, 1)
                mouths = character.shapes(pose, 2)
                if eyes:
                    sheets.append(character.parts(eyes[0]))
                if mouths:
                    sheets.append(character.parts(mouths[0]))
                rows, bounds = character_sheet.draw(character, sheets)
                if rows and bounds:
                    _x, _y, width, height = bounds
                    image = QImage(b"".join(rows), width, height, width * 4,
                                   QImage.Format.Format_RGBA8888).copy()
                    result = QPixmap.fromImage(image)
        except (IndexError, ValueError, ImportError, AttributeError):
            pass
        cache[sprite_id] = result
        return result

    def _campaign_retail_portrait(self, effect_id):
        """Decode the campaign portrait selected by a dialogue F6 control."""
        cache = getattr(self, "_campaign_retail_portrait_cache", None)
        if cache is None:
            cache = self._campaign_retail_portrait_cache = {}
        if effect_id in cache:
            return cache[effect_id]
        result = QPixmap()
        try:
            index = effect_id - self._DIALOGUE_PORTRAIT_FIRST_EFFECT_ID
            if not 0 <= index <= self._DIALOGUE_PORTRAIT_LAST_EFFECT_ID - self._DIALOGUE_PORTRAIT_FIRST_EFFECT_ID:
                return result
            pc_tools = str(Path(__file__).resolve().parents[2])
            if pc_tools not in sys.path:
                sys.path.insert(0, pc_tools)
            import extract_images
            offset = 0xF35000 + index * 0x980
            palette = extract_images.read_palette(self.files.wa, offset + 0x900, 64)
            palette.extend([0] * (256 - len(palette)))
            width, height, rgba = extract_images.decode(self.files.wa, offset, 24, 48, 8, palette)
            result = QPixmap.fromImage(QImage(rgba, width, height, width * 4,
                                               QImage.Format.Format_RGBA8888).copy())
        except (ImportError, IndexError, ValueError, struct.error):
            pass
        cache[effect_id] = result
        return result

    def _campaign_retail_shared_effect(self, effect_id):
        """Render F6's shared character with its retail sprite script.

        The 50-sector effect record is a texture *and* a command script.  A
        raw texture crop loses the separate face/body layers, which is why it
        produced a broken High Mage.  ``character_sheet`` already implements
        that record format and composes its initial retail pose faithfully.
        """
        try:
            effect_id = int(effect_id)
        except (TypeError, ValueError):
            return QPixmap()
        if not 1 <= effect_id < self._DIALOGUE_PORTRAIT_FIRST_EFFECT_ID:
            return QPixmap()
        return self._campaign_retail_sprite(effect_id)

    def _campaign_retail_background(self, picture_id):
        """Decode a retail story picture using the game's exact chunk maps."""
        self._campaign_preview_error = ""
        try:
            picture_id = int(picture_id)
            mode = (picture_id >> 8) & 0xF
            index = ((picture_id >> 4) & 0xF) * 10 + (picture_id & 0xF)
            modes = ((0, 0x21, 50), (0x672, 0x51, 42), (0x13BC, 0x71, 13))
            if mode not in (0, 1, 2) or index >= modes[mode][2]:
                self._campaign_preview_error = f"unsupported picture mode/index {mode}/{index}"
                return QPixmap()

            base_sector, stride, _ = modes[mode]
            record_offset = (0x21D5 + base_sector + index * stride) * 2048
            pixel_data = memoryview(self.files.wa)[record_offset:record_offset + (stride - 1) * 2048]
            palette_offset = record_offset + (stride - 1) * 2048
            from extract_images import expand, read_palette

            static_chunks = (
                (0,0,128,160,0,0), (0,256,128,160,128,0),
                (0,416,64,80,256,0), (64,416,64,80,256,80),
            )
            compound_masks = (
                3,3,3,1,1,1,1,1,1,1,1,0,1,0,1,1,1,1,1,1,1,0,1,0,
                1,2,1,1,0,0,0,0,3,1,2,1,1,1,3,3,1,1,
            )
            panorama_sizes = (
                (512,160),(320,256),(512,256),(320,256),(512,256),(512,256),
                (320,256),(512,256),(320,256),(344,256),(512,256),(512,256),(512,256),
            )
            panorama_l2 = {1,3,4,5,6,7,8}
            panorama_l3 = {0,6,7,8,9,10,11,12}
            panorama_l2_chunks = (
                (0,1024,128,160,0,0),(0,1280,128,160,128,0),
                (0,1440,64,80,256,0),(64,1440,64,80,256,80),
            )
            panorama_l3_chunks = (
                (0,1536,256,160,0,0),(128,1696,64,80,256,0),
                (192,1696,64,80,256,80),
            )
            panorama_placements = (
                (0x82,0,0,0,0),(1,0,0,0,0),(0,0,0,0,0),(1,0,0,0,0),
                (1,0,0,0,0),(1,0,0,0,0),(3,0,0,0,0),(3,0,96,192,0),
                (3,0,0,0,0),(2,0,0,0,0),(3,0,0,0,0),(3,0,0,0,0),(3,0,0,0,0),
            )

            def layer_image(chunks, layer_width, layer_height, bpp, clut_offset, colors):
                palette = read_palette(self.files.wa, palette_offset + clut_offset, colors)
                indices = bytearray(layer_width * layer_height)
                for source_x, source_y, chunk_w, chunk_h, dest_x, dest_y in chunks:
                    for row in range(chunk_h):
                        sy, dy = source_y + row, dest_y + row
                        if dy < 0 or dy >= layer_height:
                            continue
                        for col in range(chunk_w):
                            sx, dx = source_x + col, dest_x + col
                            if dx < 0 or dx >= layer_width:
                                continue
                            if bpp == 8:
                                value = pixel_data[sy * 128 + sx]
                            else:
                                packed = pixel_data[sy * 128 + sx // 2]
                                value = (packed & 0xF) if sx % 2 == 0 else (packed >> 4)
                            indices[dy * layer_width + dx] = value
                rgba = bytearray(layer_width * layer_height * 4)
                colors_rgba = [bytes(expand(word)) for word in palette]
                for at, color_index in enumerate(indices):
                    rgba[at * 4:at * 4 + 4] = colors_rgba[color_index]
                return QImage(bytes(rgba), layer_width, layer_height, layer_width * 4,
                              QImage.Format.Format_RGBA8888).copy()

            if mode == 0:
                width, height = 320, 160
                base = layer_image(static_chunks, width, height, 8, 0, 256)
                layers = []
            elif mode == 1:
                width, height = 320, 160
                base = layer_image(static_chunks, width, height, 8, 0, 256)
                mask = compound_masks[index]
                layers = []
                if mask & 1:
                    chunks = tuple((x,y + 512,w,h,cx,cy) for x,y,w,h,cx,cy in static_chunks)
                    layers.append((layer_image(chunks, 320, 160, 8, 0x200, 256), 0, 0, False))
                if mask & 2:
                    chunks = ((0,1024,256,160,0,0),(128,1184,64,80,256,0),
                              (192,1184,64,80,256,80))
                    # ScriptImage_CreateObject uses GsALON | GsAONE for this
                    # 4bpp layer: additive semi-transparency, not SourceOver.
                    layers.append((layer_image(chunks, 320, 160, 4, 0x400, 16), 0, 0, True))
            else:
                width, height = panorama_sizes[index]
                base_chunks = tuple((0,256 * (x // 128),min(128,width - x),height,x,0)
                                    for x in range(0, width, 128))
                base = layer_image(base_chunks, width, height, 8, 0, 256)
                mask, x1, y1, x2, y2 = panorama_placements[index]
                layers = []
                if index in panorama_l2 and mask & 1:
                    layers.append((layer_image(panorama_l2_chunks, 320, 160, 8, 0x200, 256), x1, y1, False))
                if index in panorama_l3 and mask & 2:
                    layers.append((layer_image(panorama_l3_chunks, 320, 160, 4, 0x400, 16), x2, y2, True))

            canvas = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
            canvas.fill(Qt.GlobalColor.transparent)
            painter = QPainter(canvas)
            painter.drawImage(0, 0, base)
            for layer, x, y, additive in layers:
                painter.setCompositionMode(
                    QPainter.CompositionMode.CompositionMode_Plus if additive
                    else QPainter.CompositionMode.CompositionMode_SourceOver
                )
                painter.drawImage(x, y, layer)
            painter.end()
            return QPixmap.fromImage(canvas)
        except Exception as error:
            self._campaign_preview_error = str(error)
            return QPixmap()

    @staticmethod
    def _campaign_with_dialogue_frame(background, dialogue=""):
        """Place the 320x160 scene over a pixel-styled 320x80 dialogue frame."""
        canvas = QImage(320, 240, QImage.Format.Format_ARGB32_Premultiplied)
        canvas.fill(QColor(5, 7, 12))
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        painter.drawPixmap(0, 0, 320, 160, background, 0, 0, 320, 160)
        polygon = lambda points: QPolygon([QPoint(x, y) for x, y in points])

        # The retail text box opens at (16, 176) with size 288x48. The game
        # draws a stone six-point outline around it; this pixel-art frame
        # keeps the same footprint while remaining legible at preview scale.
        outer = [(3,153),(317,153),(320,160),(320,232),(313,239),(7,239),(0,232),(0,160)]
        painter.setPen(QColor(28, 25, 25)); painter.setBrush(QColor(74, 68, 61))
        painter.drawPolygon(polygon(outer))
        painter.setPen(QColor(141, 132, 116)); painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPolygon(polygon([(5,157),(315,157),(316,161),(316,230),(311,235),(9,235),(4,230),(4,161)]))
        # Broken highlights and dark seams suggest the repeating carved stone
        # blocks of the retail border without blurring the 320x240 preview.
        for x in range(10, 316, 24):
            painter.setPen(QColor(46, 42, 38))
            painter.drawLine(x, 159, x, 165)
            painter.drawLine(x, 229, x, 234)
        for y in range(166, 228, 16):
            painter.setPen(QColor(44, 40, 37))
            painter.drawLine(3, y, 9, y)
            painter.drawLine(310, y, 317, y)
        painter.setPen(QColor(101, 91, 78))
        painter.drawRect(8, 161, 303, 70)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(8, 14, 32))
        painter.drawRect(13, 174, 294, 54)
        painter.setPen(QColor(22, 31, 55))
        painter.drawLine(16, 177, 304, 177)
        if dialogue:
            font = QFont("monospace")
            font.setPixelSize(9)
            painter.setFont(font)
            painter.setPen(QColor(230, 230, 230))
            text_flags = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
            text_flags |= Qt.AlignmentFlag(int(Qt.TextFlag.TextWordWrap))
            painter.drawText(QRect(18, 180, 276, 43),
                             text_flags, dialogue)
        # Retail's small advance marker sits in the lower-right corner.
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(230, 112, 0))
        painter.drawPolygon(polygon([(293,210),(299,217),(305,210),(302,210),(302,204),(296,204),(296,210)]))
        painter.setBrush(QColor(92, 20, 12))
        painter.drawRect(291, 219, 16, 5)
        painter.end()
        return QPixmap.fromImage(canvas)

    def _campaign_browse_background(self):
        if not self._campaign_folder:
            self._campaign_add_scene()
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Choose background layers (base first)", "", "PNG images (*.png)")
        if not paths:
            return
        modes = ("Static background (320 × 160)", "Compound background (320 × 160)",
                 "Cutscene panorama (512 × 256)")
        mode_label, ok = QInputDialog.getItem(self, "Background composition", "Background type:", modes, 0, False)
        if not ok:
            return
        mode = modes.index(mode_label)
        width, height = ((512, 256) if mode == 2 else (320, 160))
        max_index = (49, 41, 12)[mode]
        picture_index, ok = QInputDialog.getInt(
            self, "Background target", f"Retail picture index to repaint (0–{max_index}):", 0, 0, max_index)
        if not ok:
            return
        # StoryArt's ids use the same mode/high nibble and decimal low nibble
        # as the retail picture table. Repaint replaces the complete record,
        # which is required for compound and panorama pictures with overlays.
        picture_id = (mode << 8) | ((picture_index // 10) << 4) | (picture_index % 10)
        source_paths = [Path(value) for value in paths]
        name = re.sub(r"[^A-Za-z0-9_-]+", "_", source_paths[0].stem).strip("_") or "background"
        assets = self._campaign_assets.setdefault("backgrounds", {})
        candidate = name
        n = 2
        while candidate in assets:
            candidate = f"{name}_{n}"
            n += 1
        relative_art = f"backgrounds/{candidate}.png"
        layer_records = []
        canvas = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
        canvas.fill(Qt.GlobalColor.transparent)
        painter = QPainter(canvas)
        try:
            for index, source in enumerate(source_paths):
                raw = source.read_bytes()
                image = QImage()
                if not image.loadFromData(raw):
                    raise ValueError(f"{source.name} is not a readable image")
                # Keep source layers distinct from the runtime's flattened
                # repaint PNG; otherwise applying twice would paint the
                # composed result as the base and then composite overlays a
                # second time.
                relative_layer = f"backgrounds/{candidate}-source-{index:02d}.png"
                self.project.files[f"{self._campaign_folder}/{relative_layer}"] = raw
                if index == 0:
                    x = y = 0
                else:
                    x, accepted = QInputDialog.getInt(
                        self, f"Layer {index}", f"{source.name} — horizontal position:", 0, -width, width)
                    if not accepted:
                        painter.end()
                        return
                    y, accepted = QInputDialog.getInt(
                        self, f"Layer {index}", f"{source.name} — vertical position:", 0, -height, height)
                    if not accepted:
                        painter.end()
                        return
                painter.drawImage(x, y, image)
                layer_records.append({"path": relative_layer, "x": x, "y": y})
            painter.end()
            encoded = QByteArray()
            buffer = QBuffer(encoded)
            if not buffer.open(QIODevice.OpenModeFlag.WriteOnly) or not canvas.save(buffer, "PNG"):
                raise ValueError("Could not encode the composed PNG")
            buffer.close()
            self.project.files[f"{self._campaign_folder}/{relative_art}"] = bytes(encoded)
        except (OSError, ValueError) as error:
            if painter.isActive():
                painter.end()
            QMessageBox.warning(self, "Background import", str(error))
            return
        assets[candidate] = {
            "repaint": picture_id,
            "art": relative_art,
            "composition": {"mode": ("static", "compound", "cutscene")[mode],
                            "width": width, "height": height, "layers": layer_records},
        }
        self._campaign_widgets["background"].addItem(candidate, candidate)
        self._campaign_widgets["background"].setCurrentIndex(self._campaign_widgets["background"].count() - 1)
        self._campaign_widgets["assets_edit"].setPlainText(json.dumps(self._campaign_assets, indent=2, ensure_ascii=False))
        self._campaign_editor_dirty()

    def _campaign_previous_pose(self): self._campaign_step_pose(-1)
    def _campaign_next_pose(self): self._campaign_step_pose(1)
    def _campaign_step_pose(self, delta):
        combo = self._campaign_widgets["pose"]
        if combo.count(): combo.setCurrentIndex((combo.currentIndex() + delta) % combo.count())

    def _campaign_insert_token(self):
        editor = self._campaign_widgets["dialogue"]
        cursor = editor.textCursor()
        cursor.insertText("{player_name}")
        editor.setTextCursor(cursor)

    def _campaign_apply_assets(self):
        c = self._campaign_widgets
        text = c["assets_edit"].toPlainText().strip()
        if not text:
            assets = {}
        else:
            try: assets = json.loads(text)
            except ValueError as error:
                self._campaign_say(c.get("status"), f"Invalid assets.json: {error}")
                return False
            if not isinstance(assets, dict):
                self._campaign_say(c.get("status"), "assets.json must contain a JSON object.")
                return False
        if not self._campaign_folder and assets:
            self._campaign_folder = "scenes"
            self.project.other["story"] = self._campaign_folder
        try:
            self._campaign_rebuild_composed_backgrounds(assets)
        except (OSError, ValueError) as error:
            self._campaign_say(c.get("status"), f"Could not compose story background: {error}")
            return False
        self._campaign_assets = assets
        self._campaign_refresh_asset_library()
        if self._campaign_folder:
            self._campaign_store_json(f"{self._campaign_folder}/assets.json", assets)
            row = self._campaign_widgets["steps"].currentRow()
            refs = self._campaign_step_refs()
            command = refs[row][2] if 0 <= row < len(refs) else None
            self._campaign_fill_reference_combos(command or {},
                self._campaign_kind_for_command(command) if command else "")
        return True

    def _campaign_rebuild_composed_backgrounds(self, assets):
        """Rebuild flattened runtime PNGs from editable story layer records.

        assets.json keeps each layer and offset as authoring data. StoryArt's
        runtime format consumes a single repaint PNG, so the editor composes
        those layers in order whenever assets are applied.
        """
        backgrounds = assets.get("backgrounds", {})
        if not isinstance(backgrounds, dict):
            return
        for name, record in backgrounds.items():
            if not isinstance(record, dict):
                continue
            composition = record.get("composition")
            if not isinstance(composition, dict):
                continue
            width, height = int(composition.get("width", 0)), int(composition.get("height", 0))
            if (width, height) not in ((320, 160), (512, 256)):
                raise ValueError(f"{name}: expected 320×160 or 512×256 canvas")
            layers = composition.get("layers")
            if not isinstance(layers, list) or not layers:
                raise ValueError(f"{name}: composition needs at least one layer")
            image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
            image.fill(Qt.GlobalColor.transparent)
            painter = QPainter(image)
            try:
                for layer in layers:
                    if not isinstance(layer, dict) or not isinstance(layer.get("path"), str):
                        raise ValueError(f"{name}: each layer needs a relative path")
                    rel = PurePosixPath(layer["path"])
                    if rel.is_absolute() or ".." in rel.parts:
                        raise ValueError(f"{name}: layer path must stay inside the story package")
                    data = self._campaign_read(f"{self._campaign_folder}/{rel.as_posix()}")
                    source = QImage()
                    if not data or not source.loadFromData(data):
                        raise ValueError(f"{name}: could not read layer {rel.as_posix()}")
                    painter.drawImage(int(layer.get("x", 0)), int(layer.get("y", 0)), source)
            finally:
                painter.end()
            encoded = QByteArray()
            buffer = QBuffer(encoded)
            if not buffer.open(QIODevice.OpenModeFlag.WriteOnly) or not image.save(buffer, "PNG"):
                buffer.close()
                raise ValueError(f"{name}: could not encode composed image")
            buffer.close()
            art = record.get("art")
            rel_art = PurePosixPath(art) if isinstance(art, str) else PurePosixPath("backgrounds") / f"{name}.png"
            if rel_art.is_absolute() or ".." in rel_art.parts:
                raise ValueError(f"{name}: output path must stay inside the story package")
            record["art"] = rel_art.as_posix()
            self.project.files[f"{self._campaign_folder}/{rel_art.as_posix()}"] = bytes(encoded)

    def _apply_campaign(self):
        c = getattr(self, "_campaign_widgets", None)
        if not c:
            value = self.project.other.get("story")
            if value is None: return True
            return isinstance(value, str)
        if not self._campaign_commit_step():
            return False
        error = self._campaign_validate_runtime()
        if error:
            self._campaign_say(c.get("status"), error)
            QMessageBox.warning(self, "Story validation", error)
            return False
        if not getattr(self, "_campaign_dirty", False):
            return True
        if not self._campaign_apply_assets():
            return False
        folder = self._campaign_folder
        if folder:
            self.project.other["story"] = folder
            for path, scenes in self._campaign_documents.items():
                self._campaign_store_json(path, scenes)
            if self._campaign_dialogue_edits:
                relative = f"{folder}/dialogue/en.json"
                try: translations = self._campaign_json(relative, {}) or {}
                except ValueError as error:
                    self._campaign_say(c.get("status"), str(error)); return False
                translations.update(self._campaign_dialogue_edits)
                self._campaign_store_json(relative, translations)
        self._campaign_dirty = False
        self._campaign_say(c.get("status"), f"Story package staged: {folder or '(none)'}. Save the mod to write its files.")
        self._mark_dirty()
        return True

    def _campaign_validate_runtime(self):
        """Return the first scene-package error the native runner would reject.

        This deliberately validates the common structural failures at author
        time.  The C runner remains the final authority for numeric ranges and
        retail-command operand shapes, but this prevents a bad command from
        being written to a mod only to fail silently at game launch.
        """
        seen = set()
        for record in self._campaign_records:
            scene = record.get("scene", {})
            scene_id = scene.get("id") if isinstance(scene, dict) else None
            if not isinstance(scene_id, str) or not scene_id.strip():
                return "Every story scene needs a non-empty id."
            if scene_id in seen:
                return f"Scene id '{scene_id}' is used more than once."
            seen.add(scene_id)
            for phase in ("on_start", "commands", "on_end"):
                commands = scene.get(phase, [])
                if not isinstance(commands, list):
                    return f"Scene '{scene_id}' has a non-list '{phase}' section."
                for index, command in enumerate(commands, 1):
                    if not isinstance(command, dict):
                        return f"Scene '{scene_id}' {phase} command {index} is not an object."
                    kind = command.get("command")
                    if kind not in self._CAMPAIGN_RUNTIME_COMMANDS:
                        return (f"Scene '{scene_id}' {phase} command {index} uses '{kind}', "
                                "which the current PC story runtime does not support.")
        return ""

    def _refresh_campaign(self):
        c = self._campaign_controls()
        self._campaign_load()
        self._campaign_refresh_flags()

    # What each command does, for the reference beside the editor. The
    # commands themselves are _CAMPAIGN_STEP_TYPES; this says which family a
    # command belongs to and what it is for.
    _CAMPAIGN_REFERENCE = {
        "Visual": (("Set background", "Change the background picture."),
                   ("Show character", "Draw a character's portrait."),
                   ("Hide character", "Take a portrait away."),
                   ("Dialogue", "Show a line of dialogue."),
                   ("Fade", "Fade the screen in or out."),
                   ("Camera", "Move the camera."),
                   ("Screen effect", "A shake, a flash and the like."),
                   ("Animate character", "Play a portrait's animation."),
                   ("Move character", "Move a portrait across the screen.")),
        "Audio": (("Music", "Start a music track."),
                  ("Stop music", "Stop whatever is playing."),
                  ("Sound effect", "Play one sound.")),
        "Flow": (("Wait", "Hold for a number of frames."),
                 ("Branch on condition", "Go elsewhere when a flag or variable says so."),
                 ("Choice", "Ask the player, then branch on the answer."),
                 ("Jump to label", "Go to a label in this scene."),
                 ("Label", "A place a jump or a branch may name."),
                 ("Call scene", "Run another scene, then come back."),
                 ("Return", "Leave this scene for the one that called it.")),
        "System": (("Set / clear flag", "Set a story flag the game keeps."),
                   ("Set variable", "Set a story variable."),
                   ("Initiate duel", "Start a duel."),
                   ("Teleport", "Put the player somewhere on the map."),
                   ("Reward", "Give cards, starchips or both."),
                   ("Offer save", "Ask whether to save."),
                   ("Show results", "The duel's result screen."),
                   ("Game over", "End the run."),
                   ("Credits", "Roll the credits."),
                   ("Return to menu", "Leave for the main menu.")),
    }

    def _style_scene_editor(self, page, optional):
        """The Scene editor's own look: the panels as cards, the columns'
        share of the width, and the reference filled in."""
        for name in ("scenesPanel", "sceneInfoPanel", "sceneEditorPanel", "sceneStepsPanel",
                     "scenePreviewPanel", "stepEditorPanel", "sceneAssetsPanel",
                     "commandReferencePanel"):
            panel = optional(QFrame, name)
            if panel is not None:
                panel.setStyleSheet(
                    f"QFrame#{name} {{ background:#101b2b; border:1px solid #26374c;"
                    " border-radius:10px; }")
        for name in ("scenesTitle", "sceneInfoTitle", "sceneEditorTitle", "sceneStepsTitle",
                     "scenePreviewTitle", "stepEditorTitle", "sceneAssetsTitle",
                     "commandReferenceTitle"):
            title = optional(QLabel, name)
            if title is not None:
                title.setStyleSheet("font-size:16px;font-weight:650;color:#f3f7fc")
        columns = page.findChild(QSplitter, "sceneColumnsSplitter")
        if columns is not None:
            # These must fit beside the workspace navigation at the editor's
            # default 1580px window width. Larger values make QSplitter let
            # child frames overpaint each other instead of keeping columns.
            for index, (floor, stretch) in enumerate(((250, 3), (400, 5), (330, 4), (270, 3))):
                columns.widget(index).setMinimumWidth(floor)
                columns.setStretchFactor(index, stretch)
        for name, tables in (("commandRef%sTable", self._CAMPAIGN_REFERENCE),):
            for key, rows in tables.items():
                table = optional(QTableWidget, name % key)
                if table is None:
                    continue
                table.setColumnCount(2)
                table.setHorizontalHeaderLabels(["Command", "What it does"])
                table.setRowCount(len(rows))
                table.verticalHeader().setVisible(False)
                table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
                table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
                for r, (command, what) in enumerate(rows):
                    table.setItem(r, 0, QTableWidgetItem(command))
                    item = QTableWidgetItem(what)
                    item.setToolTip(what)
                    table.setItem(r, 1, item)
                header = table.horizontalHeader()
                header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
                header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        # The scene buttons wrap rather than squeeze each other to initials.
        host = page.findChild(QWidget, "sceneListColumn")
        for name in ("addSceneButton", "duplicateSceneButton", "removeSceneButton",
                     "renameSceneButton", "addStepButton", "moveStepUpButton",
                     "moveStepDownButton", "duplicateStepButton", "removeStepButton",
                     "importSceneButton", "exportSceneFlowButton", "copyToNewSceneButton",
                     "previewFromHereButton"):
            button = optional(QPushButton, name)
            if button is not None:
                button.setMinimumWidth(0)
                button.setStyleSheet("padding:6px 9px")
        # The scene and command actions wrap onto another line rather than
        # being squeezed down to initials.
        from .common import FlowLayout
        for panel_name, buttons in (
                ("scenesPanel", ("addSceneButton", "duplicateSceneButton",
                                 "removeSceneButton", "renameSceneButton")),
                ("sceneStepsPanel", ("addStepButton", "moveStepUpButton", "moveStepDownButton",
                                     "duplicateStepButton", "removeStepButton"))):
            panel = optional(QFrame, panel_name)
            widgets = [optional(QPushButton, n) for n in buttons]
            widgets = [w for w in widgets if w is not None]
            if panel is None or not widgets or getattr(self, "_campaign_flowed", None) is page:
                continue
            host = QWidget(panel)
            flow = FlowLayout(spacing=6)
            flow.setContentsMargins(0, 0, 0, 0)
            for widget in widgets:
                widget.setParent(host)
                flow.addWidget(widget)
            host.setLayout(flow)
            panel.layout().addWidget(host)
        self._campaign_flowed = page
        # The preview needs room for its picture and the lines under it.
        panel = optional(QFrame, "scenePreviewPanel")
        if panel is not None:
            panel.setMinimumHeight(330)
        # A header's hint sits beside its title: it must give way rather than
        # push the title off the panel.
        for name in ("sceneStepsContextLabel", "sceneStepsContextAlt", "stepEditorContextLabel",
                     "scenePreviewSeparator", "sceneAssetsHint", "stepDialogueCountLabel"):
            hint = optional(QLabel, name)
            if hint is not None:
                hint.setWordWrap(True)
                hint.setMinimumWidth(0)
                hint.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        # The picture takes what the column gives it, never the other way.
        preview = optional(QLabel, "scenePreviewImage")
        if preview is not None:
            preview.setMinimumSize(QSize(220, 150))
        assets = optional(QTabWidget, "sceneAssetTabs")
        if assets is not None:
            # Asset names stay readable at narrow widths; Qt exposes the
            # remaining categories through tab-bar scroll buttons.
            assets.setElideMode(Qt.TextElideMode.ElideNone)
            assets.setUsesScrollButtons(True)
        reference = optional(QTabWidget, "commandReferenceTabs")
        if reference is not None:
            reference.setElideMode(Qt.TextElideMode.ElideRight)
            reference.setUsesScrollButtons(False)
        chapters = optional(QComboBox, "sceneChapterFilter")
        if chapters is not None and chapters.count() == 0:
            chapters.addItem("All chapters", None)
            chapters.currentIndexChanged.connect(self._campaign_fill_scene_tree)

    @staticmethod
    def _campaign_say(widget, text):
        """Put a line on a display-only label, where the form has one. These
        (the status line and the two context lines) are the page's own choice
        to show or leave out, so the module never depends on them."""
        if widget is not None:
            widget.setText(text)

    def _campaign_fill_gaps(self, page):
        """Make the controls the form no longer carries, in the places it
        leaves for them. The page's own layout decides where they go; this
        only sees that the module has something to talk to."""
        from PySide6.QtWidgets import QVBoxLayout as _V
        if page.findChild(QWidget, "stepStructuredFieldsHost") is None:
            layout = page.findChild(QLayout, "stepStructuredFieldsLayout")
            if layout is not None:
                host = QWidget(page)
                host.setObjectName("stepStructuredFieldsHost")
                host.setLayout(_V())
                layout.addWidget(host)
        status_row = page.findChild(QLayout, "campaignStatusRow")
        if status_row is not None and page.findChild(QLabel, "campaignStatusLabel") is None:
            status = QLabel(page)
            status.setObjectName("campaignStatusLabel")
            status.setWordWrap(True)
            status_row.addWidget(status)
        header = page.findChild(QLayout, "scenePreviewHeader")
        if header is not None and page.findChild(QCheckBox, "showUiFrameCheck") is None:
            check = QCheckBox("UI frame", page)
            check.setObjectName("showUiFrameCheck")
            header.addWidget(check)

    def _configure_campaign_page(self, page, controls, get, optional):
        self._campaign_fill_gaps(page)
        self._style_scene_editor(page, optional)
        # The previews scale their picture to the label's own size, so a label
        # that takes its size from the picture ratchets up every pass and
        # crowds the text under it off the panel. Ignored means the layout
        # decides and the picture follows, never the other way round.
        for key in ("scenePreviewImage", "timelinePreviewImage"):
            label = optional(QLabel, key)
            if label is not None:
                label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
                label.setScaledContents(False)
                label.setMinimumHeight(200)
        # It holds a picture or a line about one; without wrapping, the line
        # was drawn past both sides of the 120px box it sits in.
        backdrop = optional(QLabel, "stepBackgroundPreview")
        if backdrop is not None:
            backdrop.setWordWrap(True)
            backdrop.setMinimumWidth(150)
        # The step editor's own column: wide enough for a field and its name,
        # and it scrolls rather than stacking its rows on each other.
        scroll = optional(QScrollArea, "stepEditorScroll")
        if scroll is not None:
            scroll.setWidgetResizable(True)
            scroll.setMinimumWidth(330)
            scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        # The raw assets box is the page's own; the status line is optional.
        controls.update(data=get(QPlainTextEdit, "campaignDataEdit"),
                        status=optional(QLabel, "campaignStatusLabel"))
        self._campaign_controls()
