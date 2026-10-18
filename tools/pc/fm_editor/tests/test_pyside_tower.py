"""The modern editor's Tower page (Phases 1-3 of the Tkinter migration):
workspace registration, the tower's own settings, and the floor list. A port
of what tests/test_tower_tab.py drives in the Tk window, for the part of the
page this pass implements. The Stage picker/artwork and the Tower-only
duelist sync are covered only where this pass wires them; story artwork
previews are not wired up yet.
"""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import json
import tempfile
from pathlib import Path
import unittest
from unittest import mock
from types import SimpleNamespace

try:
    from PySide6.QtWidgets import QApplication, QMessageBox
    from PySide6.QtCore import Qt
    from fm_editor.pyside_app import ModernEditor
except ImportError:
    QApplication = None
from fm_editor import manifest, roster, tower
from fm_editor.tests.test_data import fixture


@unittest.skipIf(QApplication is None, 'PySide6 is not installed')
class TowerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = QApplication.instance() or QApplication([])

    def setUp(self):
        from fm_editor import settings
        self.config = tempfile.TemporaryDirectory()
        self.addCleanup(self.config.cleanup)
        patcher = mock.patch.object(settings, "path",
                                    lambda: Path(self.config.name) / "fm-editor" / "settings.json")
        patcher.start()
        self.addCleanup(patcher.stop)
        f = fixture()
        with mock.patch.object(ModernEditor, '_load_game', return_value=SimpleNamespace(wa=f.wa, source='synthetic')), \
             mock.patch('fm_editor.pyside_app.gamedata.load_game', return_value=f.game()), \
             mock.patch.object(ModernEditor, '_render_preview'):
            self.window = ModernEditor()
        self.addCleanup(self.window.deleteLater)

    def tower_page(self):
        self.window.select_workspace('Tower')
        return self.window.workspace_controls['Tower']

    # --- workspace foundation -----------------------------------------------------

    def test_the_tower_workspace_opens_without_touching_an_empty_mod(self):
        w = self.window
        c = self.tower_page()
        self.assertEqual(w.current_workspace, 'Tower')
        self.assertFalse(c['enabled'].isChecked())
        self.assertNotIn('tower', w.project.other)

    def test_enabling_the_tower_adds_a_default_floor(self):
        w = self.window
        c = self.tower_page()
        c['enabled'].setChecked(True)
        self.assertIn('tower', w.project.other)
        self.assertEqual(len(w.project.other['tower']['floors']), 1)
        self.assertTrue(w.dirty)

    # --- the tower's own settings --------------------------------------------------

    def test_the_tower_s_own_fields_round_trip(self):
        w = self.window
        c = self.tower_page()
        c['enabled'].setChecked(True)
        c['name'].setText('My Tower')
        c['label'].setText('CLIMB')
        c['music'].setText('0x10')
        c['on_lose'].setCurrentText('restart')
        c['on_leave'].setCurrentText('checkpoint')
        c['drops'].setCurrentText('5')
        c['dim'].setChecked(True)
        c['save_states'].setChecked(False)
        c['cheats'].setChecked(False)
        c['scene'].setCurrentText('card shop')
        value = w.project.other['tower']
        self.assertEqual(value['name'], 'My Tower')
        self.assertEqual(value['label'], 'CLIMB')
        self.assertEqual(value['music'], 16)
        self.assertEqual(value['on_lose'], 'restart')
        self.assertEqual(value['on_leave'], 'checkpoint')
        self.assertEqual(value['drops'], 5)
        self.assertTrue(value['dim'])
        self.assertIs(value['save_states'], False)
        self.assertIs(value['cheats'], False)
        # A typed name with no prior "scene" to compare against is kept as
        # the name, not resolved to its number: tower.py reads either.
        self.assertEqual(value['scene'], 'card shop')

    def test_unlock_conditions_combine_into_one_object(self):
        w = self.window
        c = self.tower_page()
        c['enabled'].setChecked(True)
        c['unlock'].setCurrentText('conditions')
        c['unlock_beat'].setText('Simon Muran')
        c['unlock_wins'].setText('5')
        c['unlock_story'].setText('0x6E0')
        c['unlock_card'].setText('Kuriboh')
        c['unlock_copies'].setValue(3)
        c['ending_seen'].setChecked(True)
        unlock = w.project.other['tower']['unlock']
        self.assertEqual(unlock, {'after_ending': True, 'beat': 'Simon Muran', 'wins': 5, 'story': '0x6E0',
                                  'card': 'Kuriboh', 'copies': 3})

    def test_unlock_after_ending_alone_is_the_plain_string(self):
        w = self.window
        c = self.tower_page()
        c['enabled'].setChecked(True)
        c['unlock'].setCurrentText('after_ending')
        self.assertEqual(w.project.other['tower']['unlock'], 'after_ending')

    def test_an_untouched_tower_survives_every_edit_unchanged(self):
        """Edited fields that still read what the mod already wrote must not
        rewrite (and so reorder, or mark dirty) its own keys."""
        w = self.window
        written = {'label': 'TOWER', 'name': 'Hand Tower', 'floors': [{'duelist': 'Seto'}],
                  'a_future_key': 42}
        w.project.other['tower'] = written
        c = self.tower_page()
        w.dirty = False
        w._commit_tower()
        self.assertIs(w.project.other['tower'], written)
        self.assertFalse(w.dirty)

    def test_unknown_top_level_keys_are_kept(self):
        w = self.window
        w.project.other['tower'] = {'floors': [{'duelist': 1}], 'a_future_key': 'kept'}
        c = self.tower_page()
        c['name'].setText('Touch it')
        self.assertEqual(w.project.other['tower'].get('a_future_key'), 'kept')

    def test_the_guide_dialog_opens(self):
        w = self.window
        self.tower_page()
        w._tower_show_guide()
        self.assertTrue(w.tower_guide_dialog.isVisible())
        w.tower_guide_dialog.close()

    def test_start_from_example_asks_before_replacing_a_tower(self):
        w = self.window
        c = self.tower_page()
        w._tower_start_example()
        self.assertTrue(c['enabled'].isChecked())
        self.assertIn('floors', w.project.other['tower'])
        with mock.patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.No) as q:
            before = w.project.other['tower']
            w._tower_start_example()
            self.assertTrue(q.called)
            self.assertIs(w.project.other['tower'], before)      # declined: unchanged
        with mock.patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes):
            w._tower_start_example()
        self.assertEqual(w.project.other['tower']['name'], tower.example_tower()['name'])

    # --- the floor list -------------------------------------------------------------

    def test_add_remove_move_floors(self):
        w = self.window
        c = self.tower_page()
        c['enabled'].setChecked(True)      # one floor already
        c['floor_opponent'].setCurrentText('Seto')
        w._add_tower_floor()
        c['floor_opponent'].setCurrentText('Teana')
        self.assertEqual([f['duelist'] for f in w.project.other['tower']['floors']], ['Seto', 'Teana'])
        w._move_tower_floor(-1)
        self.assertEqual([f['duelist'] for f in w.project.other['tower']['floors']], ['Teana', 'Seto'])
        w._remove_tower_floor()
        self.assertEqual([f['duelist'] for f in w.project.other['tower']['floors']], ['Seto'])

    def test_selecting_a_floor_shows_its_own_fields(self):
        w = self.window
        c = self.tower_page()
        c['enabled'].setChecked(True)
        c['floor_opponent'].setCurrentText('Seto')
        c['no_fusions'].setChecked(True)
        w._add_tower_floor()
        c['floor_opponent'].setCurrentText('Teana')
        tree = c['floor_tree']
        tree.setCurrentItem(tree.topLevelItem(0))
        self.assertEqual(c['floor_opponent'].currentText(), 'Seto')
        self.assertTrue(c['no_fusions'].isChecked())
        tree.setCurrentItem(tree.topLevelItem(1))
        self.assertEqual(c['floor_opponent'].currentText(), 'Teana')
        self.assertFalse(c['no_fusions'].isChecked())

    def test_switching_floors_commits_the_one_left(self):
        """Phase 3's "commit pending floor edits before changing selection":
        typed text in a field must not vanish on switching floors."""
        w = self.window
        c = self.tower_page()
        c['enabled'].setChecked(True)
        w._add_tower_floor()
        tree = c['floor_tree']
        tree.setCurrentItem(tree.topLevelItem(0))
        c['before_duel'].setPlainText('Show me what you have learned.')
        tree.setCurrentItem(tree.topLevelItem(1))
        self.assertEqual(w.project.other['tower']['floors'][0]['before'], 'Show me what you have learned.')

    def test_floor_field_lp_rules_and_checkpoint_round_trip(self):
        w = self.window
        c = self.tower_page()
        c['enabled'].setChecked(True)
        c['floor_field'].setCurrentText('Forest')
        c['player_lp'].setText('2000')
        c['opponent_lp'].setText('4000')
        c['no_fusions'].setChecked(True)
        c['no_equips'].setChecked(True)
        c['checkpoint'].setChecked(True)
        floor = w.project.other['tower']['floors'][0]
        self.assertEqual(floor['field'], 'Forest')
        self.assertEqual(floor['life_points'], {'player': 2000, 'opponent': 4000})
        self.assertTrue(floor['no_fusions'])
        self.assertTrue(floor['no_equips'])
        self.assertTrue(floor['checkpoint'])

    def test_reward_cards_starchips_and_unlocks_round_trip(self):
        w = self.window
        c = self.tower_page()
        c['enabled'].setChecked(True)
        c['reward_cards'].setText('Kuriboh, Baby Dragon')
        c['reward_starchips'].setText('250')
        c['reward_unlock_pick'].addItem('Teana')
        c['reward_unlock_pick'].setCurrentText('Teana')
        w._tower_add_unlock()
        c['reward_unlock_pick'].setCurrentText('Seto')
        w._tower_add_unlock()
        reward = w.project.other['tower']['floors'][0]['reward']
        self.assertEqual(reward['cards'], ['Kuriboh', 'Baby Dragon'])
        self.assertEqual(reward['starchips'], 250)
        self.assertEqual(reward['unlock_duelist'], ['Teana', 'Seto'])
        w._tower_remove_unlock()
        # tower.names_value unwraps a single survivor to a plain string.
        self.assertEqual(w.project.other['tower']['floors'][0]['reward']['unlock_duelist'], 'Teana')

    def test_deck_and_story_text_round_trip(self):
        w = self.window
        c = self.tower_page()
        c['enabled'].setChecked(True)
        c['floor_deck'].setPlainText('Blue-eyes White Dragon x3\nDark Magician')
        c['before_duel'].setPlainText('Good luck.')
        c['after_win'].setPlainText('Well fought.')
        floor = w.project.other['tower']['floors'][0]
        self.assertEqual(floor['deck'], {'Blue-eyes White Dragon': 3, 'Dark Magician': 1})
        self.assertEqual(floor['before'], 'Good luck.')
        self.assertEqual(floor['after'], 'Well fought.')

    def test_unlock_opponent_follows_the_duelist_until_touched_by_hand(self):
        w = self.window
        added = roster.add_copy(w.project, 1, 'Tower Exclusive')
        tower.set_tower_only(w.project, added.key, True)
        c = self.tower_page()
        c['enabled'].setChecked(True)
        c['floor_opponent'].setCurrentText(roster.identity(w.project, added))
        self.assertTrue(c['unlock_opponent'].isChecked())      # follows the tower-only default
        self.assertNotIn('unlock_opponent', w.project.other['tower']['floors'][0])
        c['unlock_opponent'].setChecked(False)                 # touched by hand: now written
        self.assertIs(w.project.other['tower']['floors'][0]['unlock_opponent'], False)

    def test_too_many_floors_is_refused(self):
        w = self.window
        c = self.tower_page()
        c['enabled'].setChecked(True)
        w.tower_floors = [tower.new_floor() for _ in range(tower.TOWER_MAX_FLOORS)]
        w._fill_tower_floors()
        w._add_tower_floor()
        self.assertEqual(len(w.tower_floors), tower.TOWER_MAX_FLOORS)
        self.assertIn('at most', c['status'].text())

    # --- tower-only duelists ---------------------------------------------------------

    def test_tower_only_duelists_sync_with_the_added_roster(self):
        w = self.window
        added = roster.add_copy(w.project, 1, 'Custom Guy')
        c = self.tower_page()
        self.assertIn(added.key, c['only_keys'])
        index = c['only_keys'].index(added.key)
        c['only_list'].item(index).setCheckState(Qt.CheckState.Checked)
        self.assertEqual(tower.tower_only(w.project), [added.key])
        c['only_list'].item(index).setCheckState(Qt.CheckState.Unchecked)
        self.assertEqual(tower.tower_only(w.project), [])

    # --- validation and mod info -----------------------------------------------------

    def test_the_status_line_reports_tower_check_problems(self):
        w = self.window
        c = self.tower_page()
        c['enabled'].setChecked(True)
        c['floor_opponent'].setCurrentText('No Such Duelist At All')
        self.assertTrue(c['status'].text())
        self.assertIn('No Such Duelist At All', c['status'].text())

    def test_mod_info_does_not_show_or_overwrite_the_tower(self):
        w = self.window
        c = self.tower_page()
        c['enabled'].setChecked(True)
        c['name'].setText('Protected Tower')
        mi = w.workspace_controls.get('Mod info')
        if mi is None:
            w.select_workspace('Mod info')
            mi = w.workspace_controls['Mod info']
        else:
            w.select_workspace('Mod info')
        shown = json.loads(mi['other'].toPlainText()) if mi['other'].toPlainText().strip() else {}
        self.assertNotIn('tower', shown)
        mi['other'].setPlainText(json.dumps({'textures': ['a/']}))
        self.assertTrue(w._apply_mod_info())
        self.assertEqual(w.project.other['tower']['name'], 'Protected Tower')

    # --- the Stage: directives, previews and PNGs -----------------------------------

    def test_scene_and_character_directives_insert_before_the_cursor(self):
        w = self.window
        c = self.tower_page()
        c['enabled'].setChecked(True)
        w.tower_last_story = 'intro'
        c['intro'].setPlainText('Welcome to the tower.')
        c['intro'].moveCursor(c['intro'].textCursor().MoveOperation.Start)
        c['stage_scene'].setCurrentText('card shop')
        w._tower_insert(f"[scene: {c['stage_scene'].currentText()}]")
        self.assertEqual(c['intro'].toPlainText(), '[scene: card shop]\nWelcome to the tower.')
        c['stage_side'].setCurrentText('left')
        c['stage_character'].setCurrentText('3')
        c['stage_expression'].setValue(2)
        w._tower_character()
        self.assertEqual(c['intro'].toPlainText(),
                         '[scene: card shop]\n[left: 3 expression 2]\nWelcome to the tower.')
        self.assertEqual(w.project.other['tower']['intro'],
                         [{'scene': 'card shop', 'characters': {'left': {'character': 3, 'expression': 2}},
                           'text': 'Welcome to the tower.'}])

    def test_opponent_and_nobody_directives(self):
        w = self.window
        c = self.tower_page()
        c['enabled'].setChecked(True)
        c['floor_opponent'].setCurrentText('Seto')
        w.tower_last_story = 'before_duel'
        c['before_duel'].setPlainText('Show me what you have learned.')
        c['before_duel'].moveCursor(c['before_duel'].textCursor().MoveOperation.Start)
        c['stage_side'].setCurrentText('right')
        w._tower_insert(f"[{c['stage_side'].currentText()}: opponent]")
        c['stage_side'].setCurrentText('left')
        w._tower_insert(f"[{c['stage_side'].currentText()}: none]")
        before = w.project.other['tower']['floors'][0]['before']
        self.assertEqual(before, [{'characters': {'right': 'opponent', 'left': 'none'},
                                   'text': 'Show me what you have learned.'}])

    def test_focus_tracking_inserts_into_the_right_story_box(self):
        """tower_tab.py's own last_story: the Stage inserts into whichever
        story box was last focused, not always the first one."""
        w = self.window
        c = self.tower_page()
        c['enabled'].setChecked(True)
        c['ending'].setPlainText('The tower is yours.')
        w.show()      # a hidden widget's setFocus() does not dispatch a real FocusIn
        self.qt.processEvents()
        c['ending'].setFocus()
        self.qt.processEvents()
        self.assertEqual(w.tower_last_story, 'ending')
        c['ending'].moveCursor(c['ending'].textCursor().MoveOperation.Start)
        w._tower_insert('[scene: throne room]')
        self.assertEqual(c['intro'].toPlainText(), '')
        self.assertTrue(c['ending'].toPlainText().startswith('[scene: throne room]\n'))

    def test_bust_directive_uses_the_duelist_s_own_expression(self):
        from fm_editor.tests.test_bust import CALM, figure
        w = self.window
        added = roster.add_copy(w.project, 1, 'Ghost')
        roster.give_bust(w.project, added, figure(CALM), 'calm')
        c = self.tower_page()      # refresh after the bust exists
        c['enabled'].setChecked(True)
        self.assertIn(roster.identity(w.project, added), [c['stage_duelist'].itemText(i)
                                                           for i in range(c['stage_duelist'].count())])
        c['stage_duelist'].setCurrentText(roster.identity(w.project, added))
        self.assertIn('calm', [c['stage_bust_expression'].itemText(i)
                               for i in range(c['stage_bust_expression'].count())])
        c['stage_bust_expression'].setCurrentText('calm')
        c['stage_side'].setCurrentText('right')
        w.tower_last_story = 'intro'
        c['intro'].setPlainText('Hello.')
        c['intro'].moveCursor(c['intro'].textCursor().MoveOperation.Start)
        w._tower_bust()
        self.assertTrue(c['intro'].toPlainText().startswith(
            f"[right: {roster.identity(w.project, added)} expression calm]\n"))

    def test_scene_png_is_imported_and_survives_save_and_reopen(self):
        from fm_editor import pngio
        w = self.window
        c = self.tower_page()
        c['enabled'].setChecked(True)
        w.tower_last_story = 'intro'
        c['intro'].setPlainText('Welcome.')
        c['intro'].moveCursor(c['intro'].textCursor().MoveOperation.Start)
        image = pngio.Image(8, 8, bytes([10, 20, 30, 255]) * 64)
        with tempfile.TemporaryDirectory() as tmp:
            png_path = Path(tmp) / 'myscene.png'
            pngio.write(str(png_path), image)
            with mock.patch('fm_editor.pyside_app.QFileDialog.getOpenFileName', return_value=(str(png_path), '')):
                w._tower_scene_png()
        self.assertIn('tower/myscene.png', w.project.files)
        self.assertEqual(c['intro'].toPlainText(), '[scene: tower/myscene.png]\nWelcome.')
        w.project.info.id = 'towerart'
        w.project.info.name = 'Tower Art'
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / 'mod'
            manifest.save_mod(w.project, str(folder))
            again, notes = manifest.open_mod(w.retail, str(folder))
            self.assertEqual(notes, [])
            self.assertEqual(again.other['tower']['intro'], [{'scene': 'tower/myscene.png', 'text': 'Welcome.'}])
            # save_mod writes staged project.files to disk; open_mod reads
            # mod.json only and leaves the fresh project's own `files`
            # empty, so ownership is checked on disk, under source_dir.
            self.assertTrue((Path(again.source_dir) / 'tower/myscene.png').is_file())

    def test_character_png_with_flip_is_imported(self):
        from fm_editor import pngio
        w = self.window
        c = self.tower_page()
        c['enabled'].setChecked(True)
        w.tower_last_story = 'intro'
        c['intro'].setPlainText('Hi.')
        c['intro'].moveCursor(c['intro'].textCursor().MoveOperation.Start)
        c['stage_side'].setCurrentText('right')
        c['stage_flip'].setChecked(True)
        image = pngio.Image(8, 8, bytes([1, 2, 3, 255]) * 64)
        with tempfile.TemporaryDirectory() as tmp:
            png_path = Path(tmp) / 'hero.png'
            pngio.write(str(png_path), image)
            with mock.patch('fm_editor.pyside_app.QFileDialog.getOpenFileName', return_value=(str(png_path), '')):
                w._tower_character_png()
        self.assertIn('tower/hero.png', w.project.files)
        self.assertEqual(c['intro'].toPlainText(), '[right: tower/hero.png flip]\nHi.')
        self.assertEqual(w.project.other['tower']['intro'],
                         [{'characters': {'right': {'image': 'tower/hero.png', 'flip': True}}, 'text': 'Hi.'}])

    def test_the_preview_does_not_crash_without_real_disc_art(self):
        """The synthetic test fixture has no real scene/character sectors;
        tower_art.py must return None for them, not raise."""
        w = self.window
        c = self.tower_page()
        c['enabled'].setChecked(True)
        c['stage_scene'].setCurrentText('card shop')
        c['stage_character'].setCurrentText('3')
        w._tower_preview()
        self.assertTrue(c['scene_preview'].pixmap() is None or c['scene_preview'].pixmap().isNull())

    # --- Problems navigation ----------------------------------------------------------

    def test_a_tower_floor_problem_jumps_to_its_floor(self):
        from fm_editor.validate import Issue
        w = self.window
        c = self.tower_page()
        c['enabled'].setChecked(True)
        w._add_tower_floor()
        w._add_tower_floor()
        w.select_workspace('Cards')
        w.go_to(Issue('error', 'Tower', 'tower.floors[2].deck', 'something'))
        self.assertEqual(w.current_workspace, 'Tower')
        self.assertEqual(w.tower_current, 2)

    def test_a_tower_problem_without_a_floor_just_opens_the_page(self):
        """app.py's own go_to only selects the tab for a Tower issue; a
        global setting's problem (no "floors[N]" in "where") must not crash
        looking for a floor to select -- selecting the workspace already
        refreshes it to floor 0, same as opening the page any other way."""
        from fm_editor.validate import Issue
        w = self.window
        c = self.tower_page()
        c['enabled'].setChecked(True)
        w._add_tower_floor()
        w.select_workspace('Cards')
        w.go_to(Issue('warning', 'Tower', 'tower.music', 'something'))
        self.assertEqual(w.current_workspace, 'Tower')
        self.assertEqual(w.tower_current, 0)

    def test_an_out_of_range_floor_target_does_not_crash(self):
        from fm_editor.validate import Issue
        w = self.window
        c = self.tower_page()
        c['enabled'].setChecked(True)
        w.select_workspace('Cards')
        w.go_to(Issue('error', 'Tower', 'tower.floors[99]', 'something'))
        self.assertEqual(w.current_workspace, 'Tower')
        self.assertEqual(w.tower_current, 0)

    def test_double_clicking_a_tower_line_in_problems_navigates_too(self):
        w = self.window
        c = self.tower_page()
        c['enabled'].setChecked(True)
        c['floor_opponent'].setCurrentText('No Such Duelist At All')
        w._add_tower_floor()
        w.select_workspace('Problems')
        pc = w.workspace_controls['Problems']
        w._refresh_problems()
        row = next(r for r, i in enumerate(pc['issues']) if i.area == 'Tower' and 'floors[0]' in i.where)
        pc['table'].cellDoubleClicked.emit(row, 0)
        self.assertEqual(w.current_workspace, 'Tower')
        self.assertEqual(w.tower_current, 0)

    # --- Phase 7: integration ----------------------------------------------------------

    def test_undo_and_redo_restore_tower_edits(self):
        w = self.window
        c = self.tower_page()
        c['enabled'].setChecked(True)
        c['name'].setText('Before')
        w._flush_history()
        c['name'].setText('After')
        w._flush_history()
        self.assertEqual(w.project.other['tower']['name'], 'After')
        w.undo()
        self.assertEqual(w.project.other['tower']['name'], 'Before')
        self.assertEqual(w.workspace_controls['Tower']['name'].text(), 'Before')
        w.undo()
        self.assertNotIn('tower', w.project.other)
        w.redo()
        w.redo()
        self.assertEqual(w.project.other['tower']['name'], 'After')

    def test_a_mod_imported_with_its_own_tower_shows_it_unchanged(self):
        """An imported tower (mod.json already has one) must display as
        written, and visiting the page without touching anything must not
        change a byte of it on the next save."""
        w = self.window
        hand_tower = {
            'label': 'ASCEND', 'name': 'Hand-Written Tower', 'unlock': {'wins': 3},
            'floors': [{'duelist': 'Seto', 'reward': {'starchips': 50}},
                      {'duelist': 'Teana', 'field': 'Yami'}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'source'
            source.mkdir()
            (source / 'mod.json').write_text(json.dumps({
                'id': 'imported-tower', 'name': 'Imported', 'tower': hand_tower,
            }), encoding='utf-8')
            project, notes = manifest.open_mod(w.retail, str(source))
            self.assertEqual(notes, [])
            w.project = project
            w._reload_pages()
            c = self.tower_page()
            self.assertTrue(c['enabled'].isChecked())
            self.assertEqual(c['name'].text(), 'Hand-Written Tower')
            self.assertEqual(c['label'].text(), 'ASCEND')
            self.assertEqual(c['floor_tree'].topLevelItemCount(), 2)
            w.select_workspace('Mod info')     # visiting another page commits Tower on the way out
            self.assertEqual(w.project.other['tower'], hand_tower)
            with tempfile.TemporaryDirectory() as tmp2:
                out = Path(tmp2) / 'mod'
                manifest.save_mod(w.project, str(out))
                reopened, notes2 = manifest.open_mod(w.retail, str(out))
            self.assertEqual(notes2, [])
            self.assertEqual(reopened.other['tower'], hand_tower)

    def test_save_and_reopen_round_trips_the_tower(self):
        w = self.window
        c = self.tower_page()
        c['enabled'].setChecked(True)
        c['name'].setText('Saved Tower')
        c['floor_opponent'].setCurrentText('Seto')
        w.project.info.id = 'tower-mod'
        w.project.info.name = 'Tower Mod'
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / 'mod'
            manifest.save_mod(w.project, str(folder))
            again, notes = manifest.open_mod(w.retail, str(folder))
        self.assertEqual(notes, [])
        self.assertEqual(again.other['tower']['name'], 'Saved Tower')
        self.assertEqual(again.other['tower']['floors'][0]['duelist'], 'Seto')


if __name__ == '__main__':
    unittest.main()
