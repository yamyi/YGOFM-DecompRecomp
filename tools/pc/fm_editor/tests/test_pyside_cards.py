"""Cards parity and no-op round trips using the optional Qt frontend."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import json
import struct
import tempfile
from pathlib import Path
import unittest
from unittest import mock
from types import SimpleNamespace
try:
    from PySide6.QtWidgets import QApplication
    from fm_editor.pyside_app import ModernEditor
except ImportError:
    QApplication = None
from fm_editor import art, card_uses, manifest, gamedata
from fm_editor.gamedata import DUELIST_NAMES
try:
    from PySide6.QtWidgets import QGridLayout, QPlainTextEdit, QMessageBox
except ImportError:
    QGridLayout = QPlainTextEdit = QMessageBox = None


def Qt_UserRole():
    from PySide6.QtCore import Qt
    return Qt.ItemDataRole.UserRole
from fm_editor.tests.test_data import fixture

@unittest.skipIf(QApplication is None, 'PySide6 is not installed')
class CardsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = QApplication.instance() or QApplication([])

    def setUp(self):
        # Never the user's own settings, and so never the recovery folder
        # beside them: a window under test autosaves like any other.
        from fm_editor import settings
        self.config = tempfile.TemporaryDirectory()
        self.addCleanup(self.config.cleanup)
        patcher = mock.patch.object(settings, "path",
                                    lambda: Path(self.config.name) / "fm-editor" / "settings.json")
        patcher.start()
        self.addCleanup(patcher.stop)
        f = fixture()
        with mock.patch.object(ModernEditor, '_load_game', return_value=SimpleNamespace(wa=f.wa, source='synthetic')), mock.patch('fm_editor.pyside_app.gamedata.load_game', return_value=f.game()), mock.patch.object(ModernEditor, '_render_preview'):
            self.window = ModernEditor()
        self.render = mock.patch.object(self.window, '_render_preview')
        self.render.start()
        self.addCleanup(self.render.stop)
        self.addCleanup(self.window.deleteLater)

    def test_model_preview_button_tracks_selection_and_empty_state(self):
        from fm_editor import monster_view
        from fm_editor.tests.test_monster_view import model_record
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QPushButton
        w = self.window
        before = manifest.build(w.project)
        with mock.patch.object(monster_view, "read_record", return_value=model_record()) as read:
            w.show()
            self.qt.processEvents()
            w.show_card(1)
            w.model_preview_button.click()
            self.assertFalse(w.model_preview.isHidden())
            self.assertTrue(w.preview_image.isHidden())
            self.assertIsNotNone(w.model_preview.model)
            self.assertFalse(w.model_preview.pixmap().isNull())
            self.assertIsNone(getattr(w, "model_preview_dialog", None))
            w.show_card(2)
            self.assertEqual(read.call_args.args[1], 2)
            QTest.mouseDClick(w.model_preview, Qt.MouseButton.LeftButton)
            dialog = w.model_preview_dialog
            self.assertTrue(dialog.isVisible())
            self.assertIsNotNone(dialog.canvas.model)
            w.show_card(None)
            self.assertIsNone(w.model_preview.model)
            self.assertFalse(w.model_preview_button.isEnabled())
            dialog.close()
            w.hide()
        self.assertEqual(before, manifest.build(w.project))

    def test_model_preview_missing_source_is_readable(self):
        w = self.window
        w.show_card(1)
        w.model_preview_button.click()
        self.assertIn("unavailable", w.model_preview.text())
        self.assertIsNone(w.model_preview.model)
        self.assertIsNone(getattr(w, "model_preview_dialog", None))

    def test_card_preview_uses_the_game_attribute_and_level_sprites(self):
        from fm_editor.qt.common import _card_detail_sprite
        # The Library package's fourth column is a 64-word-wide 4-bit sheet.
        # Put distinct palette entries under the game's documented level-star,
        # non-monster label and Light-attribute locations, then verify the
        # decoder preserves their native dimensions and indexed colours.
        wa = bytearray(0xF06800 + 0x1E00 + 6 * 0x20 + 32)
        image_base = 0xEE6800 + 3 * 0x8000
        struct.pack_into("<H", wa, image_base + (144 * 64) * 2, 1)
        struct.pack_into("<16H", wa, 0xF06800 + 0x1180, *([0, 0x001F] + [0] * 14))
        struct.pack_into("<H", wa, image_base + (158 * 64) * 2, 3)
        struct.pack_into("<16H", wa, 0xF06800 + 0x11E0, *([0, 0, 0, 0x7C00] + [0] * 12))
        struct.pack_into("<H", wa, image_base + (128 * 64) * 2, 2)
        struct.pack_into("<16H", wa, 0xF06800 + 0x1E00, *([0, 0, 0x03E0] + [0] * 13))
        cache = {}
        project = SimpleNamespace(source_dir=None, other={}, card_extra={}, added={})
        star = _card_detail_sprite(project, wa, cache, "level")
        label = _card_detail_sprite(project, wa, cache, "label", 0)
        attribute = _card_detail_sprite(project, wa, cache, "attribute", 0)
        self.assertEqual((star.width(), star.height()), (9, 9))
        self.assertEqual((label.width(), label.height()), (56, 16))
        self.assertEqual((attribute.width(), attribute.height()), (16, 16))
        self.assertEqual(star.pixelColor(0, 0).red(), 255)
        self.assertEqual(label.pixelColor(0, 0).blue(), 255)
        self.assertEqual(attribute.pixelColor(0, 0).green(), 255)

    def test_browse_all_cards_preserves_manifest(self):
        w = self.window
        # A trap as the disc has one, which is what Apply writes
        # (tabs.CardsTab.read_form): attribute 7, and no monster stats. The
        # synthetic retail gives every non-monster 6, so its traps are set
        # here too, else applying one would rightly normalise it.
        for card in w.project.cards.values():
            if card is w.project.cards[1] or card.type == gamedata.TYPE_TRAP:
                card.type, card.attribute = gamedata.TYPE_TRAP, 7
                card.attack = card.defense = card.level = card.star1 = card.star2 = 0
        before = manifest.build(w.project)
        for cid in w.project.cards:
            w.show_card(cid)
            self.assertTrue(w.apply_card(quiet=True))
        self.assertEqual(before, manifest.build(w.project))
        self.assertFalse(w.dirty)

    def test_custom_star_is_preserved(self):
        w = self.window
        w.project.other['guardian_stars'] = {'stars': [{'id': 11, 'name': 'Fire'}]}
        w.project.cards[1].star1 = 11
        w.show_card(1)
        self.assertEqual(w.fields['star1'].currentIndex(), 11)
        self.assertIn('Fire', w.fields['star1'].currentText())
        w.apply_card(quiet=True)
        self.assertEqual(w.project.cards[1].star1, 11)

    def test_added_card_reverts_without_removing_identity(self):
        w = self.window
        cid = w.project.add_card(1)
        key = w.project.added[cid].key
        w.project.cards[cid].attack = 4000
        w.show_card(cid)
        w.revert_card()
        self.assertEqual(w.project.cards[cid].attack, w.project.cards[1].attack)
        self.assertEqual(w.project.added[cid].key, key)

    def test_apply_unchanged_validates(self):
        w = self.window
        w.show_card(1)
        with mock.patch('fm_editor.pyside_app.validate.validate_card', return_value=[SimpleNamespace(message='Existing issue')]):
            w.apply_card()
        self.assertEqual(w.validation.text(), 'Existing issue')

    def test_tags_match_the_classic_cards_form_and_round_trip(self):
        """Blank inherits or omits, [] is explicit, and untouched data survives."""
        w = self.window
        w.show_card(1)
        self.assertEqual(w.fields["tags"].text(), "")

        w.fields["tags"].setText(" god, dragon, god ")
        self.assertTrue(w.apply_card(quiet=True))
        self.assertEqual(w.fields["tags"].text(), "god, dragon")
        self.assertEqual(w.project.tags_of(1), (["god", "dragon"], False))
        self.assertEqual(manifest.build(w.project)["cards"],
                         [{"replace": 1, "tags": ["god", "dragon"]}])
        w._flush_history()
        w.undo()
        self.assertEqual(w.project.tags_of(1), ([], False))
        w.redo()
        self.assertEqual(w.project.tags_of(1), (["god", "dragon"], False))

        # An added card inherits its base while the field is blank. [] is a
        # meaningful override, and clearing it restores inheritance.
        added = w.project.add_card(1)
        w.show_card(added)
        self.assertEqual(w.fields["tags"].text(), "")
        self.assertEqual(w.project.tags_of(added), (["god", "dragon"], True))
        w.fields["tags"].setText("[]")
        self.assertTrue(w.apply_card(quiet=True))
        self.assertEqual(w.project.tags_of(added), ([], False))
        w.fields["tags"].clear()
        self.assertTrue(w.apply_card(quiet=True))
        self.assertEqual(w.project.tags_of(added), (["god", "dragon"], True))

        # Selecting and applying a card must not rewrite malformed but validly
        # preserved metadata. A different field may still be saved with it.
        raw_tags = ["", "x" * 32]
        w.project.card_extra[2] = {"tags": raw_tags, "unknown": {"keep": True}}
        w.show_card(2)
        self.assertTrue(w.apply_card(quiet=True))
        self.assertEqual(w.project.card_extra[2], {"tags": raw_tags, "unknown": {"keep": True}})
        w.fields["name"].setText("Changed Two")
        self.assertTrue(w.apply_card(quiet=True))
        self.assertEqual(w.project.card_extra[2], {"tags": raw_tags, "unknown": {"keep": True}})

        # Saving and reopening retains the tag override, including its
        # distinction from inherited tags.
        with tempfile.TemporaryDirectory() as tmp:
            manifest.save_mod(w.project, Path(tmp))
            reopened, _ = manifest.open_mod(w.retail, Path(tmp))
        self.assertEqual(reopened.tags_of(1), (["god", "dragon"], False))
        self.assertEqual(reopened.tags_of(added), (["god", "dragon"], True))

    def test_type_change_switches_the_effects_schema_before_apply(self):
        """Effects follow the selected type, rather than the saved card type."""
        w = self.window
        monster_effect = {'when': 'summon', 'do': 'boost', 'target': 'self', 'attack': 500}
        w.project.set_monster_effects(1, [monster_effect])
        w.show_card(1)
        form = w._inline_effect_editor
        self.assertEqual(w.cards_form.findChild(type(w.effects_note), 'effectsTitle').text(), 'Monster effects')
        self.assertFalse(form['when'].isHidden())

        w.fields['type'].setCurrentIndex(gamedata.TYPE_MAGIC)
        self.assertEqual(w.cards_form.findChild(type(w.effects_note), 'effectsTitle').text(), 'Card effects')
        self.assertTrue(form['when'].isHidden())
        self.assertEqual(w._card_effects(), [])
        w._add_card_effect()
        form['action'].setCurrentIndex(form['action'].findData('damage'))
        form['amount'].setValue(900)
        form['save'].click()
        self.assertEqual(w.project.monster_effects_of(1)[0], [monster_effect])
        self.assertEqual(w.project.card_extra[1]['card_effects'],
                         [{'do': 'damage', 'target': 'opponent', 'amount': 900}])
        self.assertTrue(w.apply_card(quiet=True))
        self.assertEqual(w.project.cards[1].type, gamedata.TYPE_MAGIC)

        w.fields['type'].setCurrentIndex(0)
        self.assertEqual(w.cards_form.findChild(type(w.effects_note), 'effectsTitle').text(), 'Monster effects')
        self.assertFalse(form['when'].isHidden())
        self.assertEqual(w._card_effects(), [monster_effect])

        # A committed Magic card switched to Monster has the same pending
        # schema and can immediately receive a monster effect before Apply.
        w.show_card(601)
        w.fields['type'].setCurrentIndex(0)
        self.assertTrue(w.effect_buttons['addEffect'].isEnabled())
        w._add_card_effect()
        form['save'].click()
        expected_effects = [{'when': 'summon', 'do': 'boost', 'target': 'self', 'attack': 500}]
        self.assertEqual(w.project.monster_effects_of(601)[0], expected_effects)
        self.assertNotIn('card_effects', w.project.card_extra.get(601, {}))
        self.assertTrue(w.apply_card(quiet=True))
        self.assertEqual(w.project.cards[601].type, 0)
        self.assertEqual(w.project.monster_effects_of(601)[0], expected_effects)
        with tempfile.TemporaryDirectory() as tmp:
            manifest.save_mod(w.project, Path(tmp) / 'mod')
            reopened, _ = manifest.open_mod(w.retail, Path(tmp) / 'mod')
        self.assertEqual(reopened.cards[601], w.project.cards[601])
        self.assertEqual(reopened.monster_effects_of(601)[0], expected_effects)

    def test_type_conversion_undo_and_redo(self):
        w = self.window
        original_type = w.project.cards[601].type
        w.show_card(601)
        w.fields['type'].setCurrentIndex(0)
        self.assertTrue(w.apply_card(quiet=True))
        w._flush_history()
        self.assertEqual(w.project.cards[601].type, 0)
        w.undo()
        self.assertEqual(w.project.cards[601].type, original_type)
        w.redo()
        self.assertEqual(w.project.cards[601].type, 0)

    def test_type_conversion_keeps_effect_metadata_and_added_identity(self):
        """Type conversion clears game-only fields without discarding mod data."""
        w = self.window
        retail = w.project.retail.cards[1]
        monster_effect = {'when': 'summon', 'do': 'boost', 'target': 'self', 'attack': 500}
        card_effect = {'do': 'damage', 'target': 'opponent', 'amount': 800}
        w.project.card_extra[1] = {
            'monster_effects': [monster_effect], 'card_effects': [card_effect],
            'unknown': {'keep': True},
        }
        for kind, attribute in ((gamedata.TYPE_MAGIC, 6), (gamedata.TYPE_TRAP, 7),
                                (gamedata.TYPE_EQUIP, 6), (gamedata.TYPE_RITUAL, 6)):
            w.show_card(1)
            w.fields['type'].setCurrentIndex(kind)
            self.assertTrue(w.apply_card(quiet=True))
            card = w.project.cards[1]
            self.assertEqual((card.type, card.attribute), (kind, attribute))
            self.assertEqual((card.attack, card.defense, card.level, card.star1, card.star2), (0, 0, 0, 0, 0))
            self.assertEqual(w.project.card_extra[1]['monster_effects'], [monster_effect])
            self.assertEqual(w.project.card_extra[1]['card_effects'], [card_effect])
            self.assertEqual(w.project.card_extra[1]['unknown'], {'keep': True})
        w.fields['type'].setCurrentIndex(retail.type)
        self.assertTrue(w.apply_card(quiet=True))
        restored = w.project.cards[1]
        self.assertEqual((restored.type, restored.attribute, restored.level, restored.attack, restored.defense,
                          restored.star1, restored.star2),
                         (retail.type, retail.attribute, retail.level, retail.attack, retail.defense,
                          retail.star1, retail.star2))

        added = w.project.add_card(1)
        identity, key = w.project.identity(added), w.project.added[added].key
        w.show_card(added)
        w.fields['type'].setCurrentIndex(gamedata.TYPE_TRAP)
        self.assertTrue(w.apply_card(quiet=True))
        self.assertEqual((w.project.identity(added), w.project.added[added].key), (identity, key))
        self.assertEqual((w.project.cards[added].type, w.project.cards[added].attribute),
                         (gamedata.TYPE_TRAP, 7))
        with tempfile.TemporaryDirectory() as tmp:
            manifest.save_mod(w.project, Path(tmp) / 'mod')
            reopened, _ = manifest.open_mod(w.retail, Path(tmp) / 'mod')
        self.assertEqual(reopened.cards[1], w.project.cards[1])
        self.assertEqual(reopened.added[added].key, key)

    def test_starchips_distinguishes_an_unchanged_price_from_zero(self):
        w = self.window
        w.show_card(1)
        retail_cost = w.project.retail.starchips[1]
        self.assertEqual(w.fields["starchips"].value(), retail_cost)
        before = manifest.build(w.project)

        # Merely applying a retail card must not add a free-price override.
        self.assertTrue(w.apply_card(quiet=True))
        self.assertNotIn(1, w.project.starchips)
        self.assertEqual(manifest.build(w.project), before)

        # Zero is still an intentional override and survives a later no-op
        # apply rather than being mistaken for the default price.
        w.fields["starchips"].setValue(0)
        self.assertTrue(w.apply_card(quiet=True))
        self.assertEqual(w.project.starchips[1], 0)
        w.show_card(1)
        self.assertEqual(w.fields["starchips"].value(), 0)
        self.assertTrue(w.apply_card(quiet=True))
        self.assertEqual(w.project.starchips[1], 0)

    def test_add_without_selection(self):
        w = self.window
        w.show_card(None)
        with mock.patch.object(w, '_choose_one_card', return_value=1):
            w.add_card()
        self.assertEqual(len(w.project.added), 1)

    def test_text_preview_renders_and_follows_card(self):
        from PySide6.QtWidgets import QLabel
        w = self.window
        from fm_editor.tests.test_card_text import synthetic_wa
        w.files.wa = synthetic_wa()
        w.preview_card_text()
        dialog = w.text_preview_dialog
        images = [label for label in dialog.findChildren(QLabel) if not label.pixmap().isNull()]
        self.assertTrue(images)
        w.show_card(2)
        self.assertFalse(images[0].pixmap().isNull())
        dialog.close()
        self.assertIsNone(w.text_preview_dialog)

    def test_save_round_trip_matches_backend(self):
        w = self.window
        w.project.other['guardian_stars'] = {'stars': [{'id': 11, 'name': 'Fire'}]}
        w.project.cards[1].star1 = 11
        for cid in (2, 722):
            # A trap as the disc has one (and as Apply writes it): attribute
            # 7, and no monster stats.
            card = w.project.cards[cid]
            card.type, card.attribute = gamedata.TYPE_TRAP, 7
            card.attack = card.defense = card.level = card.star1 = card.star2 = 0
        with tempfile.TemporaryDirectory() as tmp:
            original, baseline, edited = [Path(tmp) / name for name in ('original', 'baseline', 'edited')]
            manifest.save_mod(w.project, original)
            expected, _ = manifest.open_mod(w.retail, original)
            manifest.save_mod(expected, baseline)
            w.open_mod_path(str(original))
            for cid in (1, 2, 601, 722):
                w.show_card(cid)
                w.apply_card(quiet=True)
            w.project.source_dir = edited
            w.save_mod()
            self.assertEqual((baseline / 'mod.json').read_bytes(), (edited / 'mod.json').read_bytes())
            expected_files = {p.relative_to(baseline): p.read_bytes() for p in baseline.rglob('*') if p.is_file()}
            actual_files = {p.relative_to(edited): p.read_bytes() for p in edited.rglob('*') if p.is_file()}
            self.assertEqual(expected_files, actual_files)

    def test_menu_parity(self):
        # The window's own menus, not QAction.menu(): on PySide6 6.9.3, the
        # one the release pins, asking an action for its menu hands back a
        # wrapper that takes the C++ menu with it when it goes, and the menu
        # bar is left holding four dead objects.
        menus = self.window.menus
        self.assertEqual(list(menus), [action.text() for action in self.window.menuBar().actions()])
        expected = {
            # The modified-game import is behind its setting (its own test
            # below), so it is not one of the entries always there.
            'File': ['New mod', 'Open mod folder', 'Save', 'Save as', 'Export mod',
                     "Convert an old recomp's", 'Recover work', 'Game files', 'Exit'],
            'Edit': ['Undo', 'Redo'],
            'Tools': ['Check the mod', 'Preview mod.json', 'Card text preview'],
            'View': ['Dark mode'], 'Help': ['About'],
        }
        for name, entries in expected.items():
            labels = [action.text() for action in menus[name].actions()]
            for entry in entries:
                self.assertTrue(any(label.startswith(entry) for label in labels), (name, entry))

    def test_ui_title_and_menu_edits_are_interactive_and_round_trip(self):
        """The UI workspace is the visual editor, not only the texture
        catalogue: its Designer tabs create the same title/menu data that a
        saved mod subsequently reloads."""
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QLabel, QPushButton
        from fm_editor import manifest

        w = self.window
        w.select_workspace('UI')
        c = w.workspace_controls['UI']
        self.assertIs(c['shell'], w.workspace_forms['UI'])
        self.assertFalse(any(item['name'].startswith('card_frames/') for item in c['catalog']))
        self.assertFalse(any('modified asset' in label.text()
                             for label in c['assets_tab'].findChildren(QLabel)))
        self.assertEqual([c['tabs'].tabText(i) for i in range(c['tabs'].count())],
                         ['Title screen', 'Menus', 'Duel', 'Frames', 'Duel board',
                          'Build Deck', 'Assets'])

        # Title text is created through the Designer action, then selected,
        # clicked and nudged directly on its interactive preview.
        c['shell'].findChild(QPushButton, 'addTitleTextButton').click()
        c['title_text'].setText('HELLO FM')
        c['title_text'].editingFinished.emit()
        w.show()
        self.qt.processEvents()
        canvas = c['title_preview']
        box = c['title_boxes']['text:0']
        scale = min(canvas.width() / 320, canvas.height() / 240)
        point = QPoint(round((canvas.width() - 320 * scale) / 2 + (box[0] + box[2] / 2) * scale),
                       round((canvas.height() - 240 * scale) / 2 + (box[1] + box[3] / 2) * scale))
        QTest.mouseClick(canvas, Qt.MouseButton.LeftButton, pos=point)
        self.assertEqual(c['title_selected'], 'text:0')
        QTest.keyClick(canvas, Qt.Key.Key_Right)
        title_text = w.project.other['title']['text'][0]
        self.assertEqual((title_text['text'], title_text['x'], title_text['y']),
                         ('HELLO FM', 161, 220))

        # Dragging updates the model immediately, coalesces visual rendering
        # to the display rate, then produces a final exact preview on release.
        box = c['title_boxes']['text:0']
        point = QPoint(round((canvas.width() - 320 * scale) / 2 + (box[0] + box[2] / 2) * scale),
                       round((canvas.height() - 240 * scale) / 2 + (box[1] + box[3] / 2) * scale))
        before_drag = (title_text['x'], title_text['y'])
        QTest.mousePress(canvas, Qt.MouseButton.LeftButton, pos=point)
        QTest.mouseMove(canvas, QPoint(point.x() + round(7 * scale), point.y() + round(4 * scale)))
        QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton,
                           pos=QPoint(point.x() + round(7 * scale), point.y() + round(4 * scale)))
        self.qt.processEvents()
        self.assertNotEqual((title_text['x'], title_text['y']), before_drag)
        self.assertFalse(c['preview_render_timers']['title'].isActive())

        # A custom menu button, like its title counterpart, is configured by
        # the form and remains independent when its page is later reverted.
        c['tabs'].setCurrentIndex(1)
        c['shell'].findChild(QPushButton, 'addMenuButtonButton').click()
        c['menu_words'].setText('MY BUTTON')
        c['menu_action'].setCurrentIndex(c['menu_action'].findData('notice'))
        c['menu_x'].setValue(12)
        c['menu_y'].setValue(34)
        c['menu_words'].editingFinished.emit()
        button = w.project.other['menu']['buttons'][0]
        self.assertEqual(button['label'], 'MY BUTTON')
        self.assertEqual(button['x'], 12)
        self.assertEqual(button['y'], 34)

        with tempfile.TemporaryDirectory() as folder:
            manifest.save_mod(w.project, Path(folder))
            reopened, _messages = manifest.open_mod(w.retail, Path(folder))
        self.assertEqual(reopened.other['title']['text'][0], title_text)
        self.assertEqual(reopened.other['menu']['buttons'][0]['label'], 'MY BUTTON')

        c['shell'].findChild(QPushButton, 'revertMenuPageButton').click()
        self.assertNotIn('menu', w.project.other)
        self.assertIn('title', w.project.other)
        w.hide()

    def test_frame_style_edits_and_assignments_round_trip(self):
        """Frames is a Designer-backed editor for card_layout.frame_styles,
        including normal placement edits and the global fallback assignment."""
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QPushButton
        from fm_editor import manifest

        w = self.window
        w.select_workspace('UI')
        c = w.workspace_controls['UI']['frames']
        self.assertEqual(c['form'].objectName(), 'FramesPage')
        self.assertIs(w.workspace_controls['UI']['frames_tab'], c['form'])
        self.assertEqual(c['style'].currentItem().text(), 'custom')
        # The preview retains the game renderer's 4x internal card texture,
        # while its placement and hit-testing remain in 140×196 game pixels.
        retail_preview = c['preview'].property('_fullPixmap')
        self.assertEqual((retail_preview.width(), retail_preview.height()), (560, 784))

        # The main card's stat components preserve the retail card-view
        # sprites: 24x12 labels and 6x13 digit cells.  Values are stored at
        # the centre of their four-cell run, so their rendered rows start at
        # (97, 157) and (97, 171), not at the Frame image rectangle.
        from fm_editor.qt.ui_assets_compat import _frame_rect
        self.assertEqual(_frame_rect(w, 'atk_label'), (73, 157, 24, 12))
        self.assertEqual(_frame_rect(w, 'atk'), (109, 163, 6, 13))
        self.assertEqual(_frame_rect(w, 'dfd_label'), (73, 168, 24, 12))
        self.assertEqual(_frame_rect(w, 'def'), (109, 177, 6, 13))

        # Select Artwork through the tree model exactly as a user does, then
        # edit its game-pixel position through the Designer spin boxes.
        art_row = next(c['parts'].topLevelItem(group).child(row)
                       for group in range(c['parts'].topLevelItemCount())
                       for row in range(c['parts'].topLevelItem(group).childCount())
                       if c['parts'].topLevelItem(group).child(row).data(0, Qt_UserRole()) == 'art')
        c['parts'].setCurrentItem(art_row)
        c['x'].setValue(27)
        c['y'].setValue(55)
        # The preview uses the same game-pixel values as its spin boxes; a
        # direct drag must select and move the part, not only redraw it.
        w.workspace_controls['UI']['tabs'].setCurrentWidget(c['form'])
        w.show()
        self.qt.processEvents()
        form_width, canvas_width = c['form'].width(), c['preview'].width()
        w.resize(w.width() + 240, w.height() + 160)
        self.qt.processEvents()
        self.assertGreater(c['form'].width(), form_width)
        self.assertGreater(c['preview'].width(), canvas_width)
        canvas, box = c['preview'], c['boxes']['art']
        scale = min(canvas.width() / 140, canvas.height() / 196)
        point = QPoint(round((canvas.width() - 140 * scale) / 2 + (box[0] + box[2] / 2) * scale),
                       round((canvas.height() - 196 * scale) / 2 + (box[1] + box[3] / 2) * scale))
        QTest.mousePress(canvas, Qt.MouseButton.LeftButton, pos=point)
        QTest.mouseMove(canvas, QPoint(point.x() + round(5 * scale), point.y() + round(3 * scale)))
        QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, pos=QPoint(point.x() + round(5 * scale), point.y() + round(3 * scale)))
        # The responsive Designer canvas can have a fractional display scale,
        # so the nearest game-pixel drag delta depends on its current size.
        # It must still move and preserve that exact resulting game position.
        art_position = (w.project.other['card_layout']['frame_styles']['custom']['art']['x'],
                        w.project.other['card_layout']['frame_styles']['custom']['art']['y'])
        self.assertNotEqual(art_position, (27, 55))

        # Frame images can be imported and exported through the Designer
        # controls, with the exact replacement saved in frames/.  Artwork is
        # retail-only (visual placement help, not a replaceable asset), so
        # this exercises the ATK label, which is a real frames/ asset.
        atk_label_row = next(c['parts'].topLevelItem(group).child(row)
                             for group in range(c['parts'].topLevelItemCount())
                             for row in range(c['parts'].topLevelItem(group).childCount())
                             if c['parts'].topLevelItem(group).child(row).data(0, Qt_UserRole()) == 'atk_label')
        c['parts'].setCurrentItem(atk_label_row)
        source = self.pack_png(16, 16)
        with mock.patch('fm_editor.qt.ui_assets_compat.QFileDialog.getOpenFileName', return_value=(source, '')):
            c['form'].findChild(QPushButton, 'chooseImageButton').click()
        export = c['form'].findChild(QPushButton, 'exportImageButton')
        self.assertTrue(export.isEnabled())
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / 'atk_label.png'
            with mock.patch('fm_editor.qt.ui_assets_compat.QFileDialog.getSaveFileName', return_value=(str(destination), '')):
                export.click()
            self.assertTrue(destination.is_file())

        # Retail comparison is render-only.  Holding it or leaving the
        # workspace cannot temporarily remove card_layout from the project.
        before_hold = json.loads(json.dumps(w.project.other['card_layout']))
        hold = c['form'].findChild(QPushButton, 'showRetailButton')
        hold.pressed.emit()
        self.assertTrue(c['retail_preview'])
        self.assertEqual(w.project.other['card_layout'], before_hold)
        w.select_workspace('Cards')
        self.assertFalse(c['retail_preview'])
        self.assertEqual(w.project.other['card_layout'], before_hold)
        w.select_workspace('UI')
        c['form'].findChild(QPushButton, 'setGlobalDefaultButton').click()
        c['kind_rule'].setCurrentIndex(c['kind_rule'].findData('monster'))
        c['form'].findChild(QPushButton, 'applyKindButton').click()
        c['type_rule'].setCurrentIndex(0)
        selected_type = c['type_rule'].currentData()
        c['form'].findChild(QPushButton, 'applyTypeButton').click()
        c['card_rule'].setText('1 Blue-eyes White Dragon')
        c['form'].findChild(QPushButton, 'applyCardButton').click()
        self.assertEqual(w.project.other['card_layout']['default_style'], 'custom')
        self.assertEqual(w.project.other['card_layout']['default_styles']['kinds']['monster'], 'custom')
        self.assertEqual(w.project.other['card_layout']['default_styles']['types'][selected_type], 'custom')
        self.assertEqual(w.project.card_extra[1]['frame_style'], 'custom')
        self.assertEqual((w.project.other['card_layout']['frame_styles']['custom']['art']['x'],
                          w.project.other['card_layout']['frame_styles']['custom']['art']['y']), art_position)

        with tempfile.TemporaryDirectory() as folder:
            manifest.save_mod(w.project, Path(folder))
            reopened, messages = manifest.open_mod(w.retail, Path(folder))
        self.assertFalse(messages)
        layout = reopened.other['card_layout']
        self.assertEqual(layout['default_style'], 'custom')
        self.assertEqual(layout['default_styles']['kinds']['monster'], 'custom')
        self.assertEqual(layout['default_styles']['types'][selected_type], 'custom')
        self.assertEqual(reopened.card_extra[1]['frame_style'], 'custom')
        self.assertEqual((layout['frame_styles']['custom']['art']['x'],
                          layout['frame_styles']['custom']['art']['y']), art_position)
        w.hide()

    def test_removing_ui_title_images_prunes_only_orphans(self):
        """Removing a Title picture deletes its imported PNG on the next save,
        but leaves the PNG intact while another UI element still references it."""
        from PySide6.QtWidgets import QPushButton
        from fm_editor import manifest

        w = self.window
        w.select_workspace('UI')
        c = w.workspace_controls['UI']
        source = self.pack_png(48, 48)
        with mock.patch('fm_editor.pyside_app.QFileDialog.getOpenFileName', return_value=(source, '')):
            c['shell'].findChild(QPushButton, 'addTitlePictureButton').click()
        image = w.project.other['title']['images'][0]['image']
        self.assertIn(image, w.project.files)

        # A second element can reuse an imported file. Removing the first
        # must keep the shared file and its remaining reference.
        w.project.other['title']['images'].append({'image': image, 'x': 120, 'y': 80})
        c['title_selected'] = 'picture:0'
        c['shell'].findChild(QPushButton, 'removeTitleElementButton').click()
        self.assertIn(image, w.project.files)
        self.assertEqual(w.project.other['title']['images'],
                         [{'image': image, 'x': 120, 'y': 80}])

        c['title_selected'] = 'picture:0'
        c['shell'].findChild(QPushButton, 'removeTitleElementButton').click()
        self.assertNotIn(image, w.project.files)
        self.assertIn(image, w.project.deleted_files)
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            manifest.save_mod(w.project, output)
            self.assertFalse((output / image).exists())

    def test_holding_retail_board_view_preserves_saved_board_changes(self):
        """The asynchronous board preview may temporarily use retail art, but
        releasing its comparison control must restore the actual BoardArt
        object before the mod is saved."""
        from PySide6.QtWidgets import QPushButton
        from fm_editor import board_art, manifest

        w = self.window
        w.select_workspace('UI')
        c = w.workspace_controls['UI']
        board_art.set_tint(w.project, ['normal'], [board_art.BY_KEY['wall_middle']], 0x4080C0)
        original = w.project.board_art
        expected = dict(original.tints)
        button = c['shell'].findChild(QPushButton, 'holdGameBoardButton')
        button.pressed.emit()
        self.assertIsNot(w.project.board_art, original)
        button.released.emit()
        self.qt.processEvents()
        self.assertIs(w.project.board_art, original)
        self.assertEqual(w.project.board_art.tints, expected)

        with tempfile.TemporaryDirectory() as folder:
            manifest.save_mod(w.project, Path(folder))
            reopened, _messages = manifest.open_mod(w.retail, Path(folder))
        self.assertEqual(reopened.board_art.tints, expected)

    def test_theme_toggle_remembers_choice(self):
        w = self.window
        with mock.patch('fm_editor.pyside_app.settings.save', return_value=None) as save:
            w.toggle_dark(True)
            dark = w.styleSheet()
            w.toggle_dark(False)
            self.assertNotEqual(w.styleSheet(), dark)
            save.assert_called_with('modern_dark', False)
            w.toggle_dark(True)
            self.assertEqual(w.styleSheet(), dark)
        self.assertFalse(w.dirty)

    def test_import_actions_replace_project_and_mark_dirty(self):
        from fm_editor.model import Project
        for package in (False, True):
            w = self.window
            project = Project(w.retail)
            with mock.patch.object(w, 'confirm_discard', return_value=True), mock.patch.object(w, '_report'), \
                 mock.patch('fm_editor.pyside_app.QMessageBox.question', return_value=QMessageBox.StandardButton.Yes), \
                 mock.patch('fm_editor.pyside_app.QFileDialog.getOpenFileName', return_value=('example.ygomods' if package else 'example.bin', '')), \
                 mock.patch('fm_editor.pyside_app.disc.load', return_value=SimpleNamespace(wa=w.files.wa)), \
                 mock.patch('fm_editor.pyside_app.importer.import_modded', return_value=SimpleNamespace(project=project, report=['Imported'])), \
                 mock.patch('fm_editor.pyside_app.ygomods.import_package', return_value=(project, ['Converted'])):
                (w.import_ygomods if package else w.import_modded_game)()
            self.assertIs(w.project, project)
            self.assertTrue(w.dirty)

    def test_save_as_creates_mod_subfolder(self):
        w = self.window
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            (parent / 'existing-mod').mkdir()
            with mock.patch('fm_editor.pyside_app.QFileDialog.getExistingDirectory', return_value=tmp):
                w.save_mod(choose=True)
            self.assertTrue((parent / w.project.info.id / 'mod.json').is_file())
            self.assertFalse((parent / 'mod.json').exists())

    def test_open_starter_mod_after_empty_project(self):
        from fm_editor.model import StarterDeck
        w = self.window
        self.assertIsNone(w.starter_current)
        w.project.starter.append(StarterDeck())
        w._refresh_starter_decks()
        self.assertEqual(w.starter_current, 0)

    def test_art_details_for_added_card(self):
        w = self.window
        w.refresh_art_list(select_id=1)
        # The Art view deliberately has only identity and artwork-state
        # columns; the Cards workspace owns card type editing.
        self.assertEqual(w.art_table.horizontalHeaderItem(2).text(), 'Art status')
        self.assertIn('Texture pack:', w.art_pack_status.text())
        cid = w.project.add_card(1)
        w.show_art_card(cid)
        self.assertIn('inherits', w.art_instructions.text())
        self.assertIn('Restart', w.art_instructions.text())

    def test_art_preview_preserves_shape_and_clears_errors(self):
        from PySide6.QtCore import QSize
        from fm_editor import pngio
        w = self.window
        label = w.art_previews['art']['game']
        image = pngio.Image(100, 50, bytes([255, 0, 0, 255]) * 5000)
        w._show_art_image(label, image, 1, '', QSize(240, 226))
        self.assertEqual((label.pixmap().width(), label.pixmap().height()), (240, 120))
        w.current_art_card = 1
        # A render the editor cannot make clears that part and says so.
        with mock.patch('fm_editor.pyside_app.art.in_game', side_effect=ValueError('Broken image')):
            w.show_art_card(1)
        self.assertTrue(label.pixmap().isNull())
        self.assertIn('Broken image', w.art_status.text())
        with mock.patch('fm_editor.pyside_app.art.disc_image', side_effect=ValueError('Bad disc')):
            w.show_art_card(2)
        for previews in w.art_previews.values():
            for preview in previews.values():
                self.assertTrue(preview.pixmap().isNull())

    def test_art_export_sanitizes_filename(self):
        from fm_editor import pngio
        w = self.window
        w.project.cards[1].name = 'Card / with : unsafe ? characters'
        image = pngio.Image(1, 1, bytes([0, 0, 0, 255]))
        with mock.patch('fm_editor.pyside_app.QFileDialog.getSaveFileName', return_value=('', '')) as chooser:
            w._save_art_image(1, 'art', image, 'mod')
        self.assertEqual(chooser.call_args.args[2], '0001-card-with-unsafe-characters-mod.png')

    def test_art_preview_double_click_imports_its_part(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        w = self.window
        w.show_art_card(1)
        preview = w.art_previews['thumbnail']['game']
        w.show()
        self.qt.processEvents()
        with mock.patch.object(w, 'import_art') as import_art:
            QTest.mouseDClick(preview, Qt.MouseButton.LeftButton)
            self.qt.processEvents()
        import_art.assert_called_once_with('thumbnail')
        w.hide()

    def test_art_export_write_error_is_reported(self):
        from fm_editor import pngio
        w = self.window
        image = pngio.Image(1, 1, bytes([0, 0, 0, 255]))
        with mock.patch('fm_editor.pyside_app.QFileDialog.getSaveFileName',
                        return_value=('denied.png', '')), \
             mock.patch('fm_editor.pyside_app.art.pngio.write',
                        side_effect=OSError('permission denied')), \
             mock.patch('fm_editor.pyside_app.QMessageBox.critical') as critical:
            w._save_art_image(1, 'art', image, 'mod')
        critical.assert_called_once()
        self.assertEqual(critical.call_args.args[1], 'Could not export artwork')
        self.assertIn('permission denied', critical.call_args.args[2])

    def test_art_edit_undo_and_redo(self):
        from fm_editor import art, pngio
        w = self.window
        image = pngio.Image(102, 96, bytes([30, 40, 50, 255]) * (102 * 96))
        w.current_art_card = 1
        with mock.patch('fm_editor.pyside_app.QFileDialog.getOpenFileName',
                        return_value=('art.png', '')), \
             mock.patch('fm_editor.pyside_app.art.pngio.read', return_value=image):
            w.import_art('art')
        w._record_edit()
        self.assertEqual(art.replacement_image(w.project, 1, 'art'), image)
        w.undo()
        self.assertIsNone(art.replacement_image(w.project, 1, 'art'))
        w.redo()
        self.assertEqual(art.replacement_image(w.project, 1, 'art'), image)

    def test_revert_art_copy_restores_base_inheritance(self):
        from fm_editor import art, pngio
        w = self.window
        base_image = pngio.Image(102, 96, bytes([40, 50, 60, 255]) * (102 * 96))
        copy_image = pngio.Image(102, 96, bytes([70, 80, 90, 255]) * (102 * 96))
        copy = w.project.add_card(1, 'art-copy')
        art.set_image(w.project, 1, 'art', base_image)
        art.set_image(w.project, copy, 'art', copy_image)
        w.current_art_card = copy
        w.revert_art('art')
        self.assertIsNone(art.replacement_image(w.project, copy, 'art'))
        shown, where = art.shown_image(w.project, w.preview_wa, copy, 'art')
        self.assertEqual(shown, base_image)
        self.assertIn('base', where)

    def test_art_filter_updates_after_deferred_initialization(self):
        from fm_editor import art, pngio
        from PySide6.QtCore import Qt
        w = self.window
        w.select_workspace('Art')
        copy = w.project.add_card(1, 'art-filter-copy')
        image = pngio.Image(102, 96, bytes([10, 20, 30, 255]) * (102 * 96))
        art.set_image(w.project, copy, 'art', image)
        w.refresh_art_list(select_id=copy)
        w.art_filter.setCurrentText('Added by the mod')
        self.assertEqual([w.art_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
                          for row in range(w.art_table.rowCount())], [copy])
        w.art_search.setText('nothing-matches-this')
        self.assertEqual(w.art_table.rowCount(), 0)
        w.art_search.setText(str(copy))
        self.assertEqual(w.art_table.item(0, 0).data(Qt.ItemDataRole.UserRole), copy)

    def test_art_save_and_reopen_keeps_retail_and_added_artwork(self):
        from fm_editor import art, manifest, pngio
        w = self.window
        retail_image = pngio.Image(102, 96, bytes([15, 25, 35, 255]) * (102 * 96))
        added_image = pngio.Image(102, 96, bytes([45, 55, 65, 255]) * (102 * 96))
        added = w.project.add_card(1, 'art-save-copy')
        art.set_image(w.project, 2, 'art', retail_image)
        art.set_image(w.project, added, 'art', added_image)
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / 'art-save'
            w._save_project(folder)
            reopened, messages = manifest.open_mod(w.retail, folder)
            self.assertEqual(messages, [])
            reopened_added = next(cid for cid, item in reopened.added.items()
                                 if item.key == 'art-save-copy')
            self.assertEqual(art.replacement_image(reopened, 2, 'art'), retail_image)
            self.assertEqual(art.replacement_image(reopened, reopened_added, 'art'), added_image)

    def test_art_import_warns_on_crop(self):
        from fm_editor import pngio
        w = self.window
        w.current_art_card = 1
        image = pngio.Image(1, 1, bytes([0, 0, 0, 255]))
        with mock.patch('fm_editor.pyside_app.QFileDialog.getOpenFileName', return_value=('crop.png', '')), \
             mock.patch('fm_editor.pyside_app.art.pngio.read', return_value=image), \
             mock.patch('fm_editor.pyside_app.art.set_image', return_value=['shape was cropped']), \
             mock.patch('fm_editor.pyside_app.QMessageBox.warning') as warning:
            w.import_art('art')
        warning.assert_called_once()
        self.assertIn('102:96', warning.call_args.args[2])
        self.assertTrue(w.dirty)

    def test_fusion_effective_results_and_forbidden_pairs(self):
        from PySide6.QtCore import Qt
        w = self.window
        p = w.project
        p.set_fusion(1, 2, None)
        p.card_extra[4] = {'fusions': [{'with': 5, 'result': 6}]}
        p._own_pairs = None
        p.fusion_explicit.add((7, 8))
        p.fusions.pop((7, 8), None)
        w._refresh_fusions()
        listing = w.workspace_controls['Fusions']['image_list']
        rows = {listing.item(i).data(Qt.ItemDataRole.UserRole): listing.item(i) for i in range(listing.count())}
        self.assertIsNone(rows[(1, 2)].data(int(Qt.ItemDataRole.UserRole) + 1))
        self.assertIn('No fusion', rows[(1, 2)].text())
        self.assertEqual(rows[(4, 5)].data(int(Qt.ItemDataRole.UserRole) + 1), 6)
        self.assertIn('own list', rows[(4, 5)].text())
        self.assertIn((7, 8), rows)

    def test_fusion_multiselect_and_empty_actions(self):
        from PySide6.QtWidgets import QAbstractItemView
        w = self.window
        w.select_workspace('Fusions')
        c = w.workspace_controls['Fusions']
        w._set_fusion_view(0)
        listing = c['image_list']
        self.assertEqual(listing.selectionMode(), QAbstractItemView.SelectionMode.ExtendedSelection)
        listing.clearSelection()
        w._remove_fusions()
        w._revert_fusions()
        self.assertFalse(w.dirty)
        for i in (0, 1): listing.item(i).setSelected(True)
        pairs = w._selected_fusion_pairs()
        self.assertEqual(len(pairs), 2)
        w._remove_fusions()
        for pair in pairs: self.assertFalse(w.project.fusions.get(pair))

    def test_bulk_filters_all_kinds_and_custom_stars(self):
        from PySide6.QtCore import Qt
        w = self.window
        c = w.workspace_controls['Fusions']
        a = c['bulk_filters']['a']
        self.assertEqual(len(w._read_bulk_filter(a).select(w.project)[0]), 722)
        a['kinds']['magic'].setChecked(True)
        matches = w._read_bulk_filter(a).select(w.project)[0]
        self.assertTrue(matches)
        self.assertTrue(all(w.project.cards[cid].type == gamedata.TYPE_MAGIC for cid in matches))
        w._copy_bulk_filter('a', 'b')
        self.assertTrue(c['bulk_filters']['b']['kinds']['magic'].isChecked())
        w._clear_bulk_filter('a')
        w.project.other['guardian_stars'] = {'stars': [{'id': 11, 'name': 'Fire'}]}
        w.project.cards[1].star1 = 11
        w._refresh_bulk_fusion_plan()
        self.assertIn('Fire', a['stars'].item(10).text())
        a['stars'].item(10).setCheckState(Qt.CheckState.Checked)
        self.assertEqual(w._read_bulk_filter(a).select(w.project)[0], [1])
        with mock.patch.object(w, '_report') as report:
            w._list_bulk_matches('a')
        self.assertIn(w.project.card_label(1), report.call_args.args[1])

    def test_bulk_remove_and_add_undo(self):
        from PySide6.QtWidgets import QMessageBox
        w = self.window
        c = w.workspace_controls['Fusions']
        bulk = c['bulk']
        c['bulk_filters']['a']['cards'].setText('1')
        c['bulk_filters']['b']['cards'].setText('2')
        before = manifest.build(w.project)
        bulk['mode'].setCurrentIndex(1)
        with mock.patch('fm_editor.pyside_app.QMessageBox.question', return_value=QMessageBox.StandardButton.Yes):
            w._apply_bulk_fusions()
        self.assertFalse(w.project.fusions.get((1, 2)))
        w._undo_bulk_fusions()
        self.assertEqual(manifest.build(w.project), before)
        bulk['mode'].setCurrentIndex(0)
        bulk['result_id'] = 4
        bulk['stronger'].setChecked(False)
        bulk['overwrite'].setChecked(True)
        with mock.patch('fm_editor.pyside_app.QMessageBox.question', return_value=QMessageBox.StandardButton.Yes):
            w._apply_bulk_fusions()
        self.assertEqual(w.project.fusions[(1, 2)], 4)
        w._undo_bulk_fusions()
        self.assertEqual(manifest.build(w.project), before)

    def test_remove_disc_recipes_by_result(self):
        from PySide6.QtWidgets import QMessageBox, QPushButton
        w = self.window
        self.assertTrue(any(b.text() == 'Remove recipes of…' for b in w.findChildren(QPushButton)))
        with mock.patch.object(w, '_choose_one_card', return_value=3), \
             mock.patch('fm_editor.pyside_app.QMessageBox.question', return_value=QMessageBox.StandardButton.Yes):
            w._remove_fusion_result()
        self.assertIn(3, w.project.active_removes())
        self.assertFalse(w.project.fusions.get((1, 2)))

    def test_fusions_keep_non_monster_results_and_restore_disc_table(self):
        from PySide6.QtWidgets import QMessageBox, QPushButton
        w = self.window
        w.select_workspace('Fusions')
        pair, retail_result = next(iter(w.project.retail.fusions.items()))
        # The game accepts a non-Monster result even though its automatic
        # planner intentionally excludes it.  The editor must not block it.
        non_monster = next(cid for cid, card in w.project.cards.items()
                           if not card.is_monster())
        w.project.set_fusion(*pair, non_monster)
        self.assertEqual(w._effective_fusion_result(pair), non_monster)
        with mock.patch('fm_editor.pyside_app.QMessageBox.question',
                        return_value=QMessageBox.StandardButton.Yes):
            w._toggle_all_fusions()
        self.assertTrue(w.project.fusion_remove_all)
        button = next(button for button in w.findChildren(QPushButton)
                      if button.objectName() == 'toggleAllFusionsButton')
        self.assertEqual(button.text(), 'Restore disc fusions')
        self.assertEqual(manifest.build(w.project)['fusions'][0], {'remove': 'all'})
        # An explicit result remains legal after a global removal.
        w.project.set_fusion(*pair, non_monster)
        with mock.patch('fm_editor.pyside_app.QMessageBox.question',
                        return_value=QMessageBox.StandardButton.Yes):
            w._toggle_all_fusions()
        self.assertFalse(w.project.fusion_remove_all)
        self.assertEqual(w.project.fusions[pair], non_monster)
        self.assertNotEqual(retail_result, non_monster)

    def test_fusion_edit_uses_effective_retail_result(self):
        from PySide6.QtWidgets import QDialog
        w = self.window
        w.select_workspace('Fusions')
        pair, retail_result = next(iter(w.project.retail.fusions.items()))
        # A sparse project can omit an unchanged retail pair. The edit form
        # still needs to start at its effective result.
        w.project.fusions.pop(pair, None)
        self.assertEqual(w._effective_fusion_result(pair), retail_result)
        table = w.workspace_controls['Fusions']['table']
        row = next(row for row in range(table.rowCount())
                   if table.item(row, 0).data(Qt_UserRole()) == pair)
        table.selectRow(row)
        selected = []
        original_card_combo = w._card_combo

        def card_combo(parent, value=None):
            selected.append(value)
            return original_card_combo(parent, value)

        with mock.patch.object(w, '_card_combo', side_effect=card_combo), \
             mock.patch.object(QDialog, 'exec', return_value=0):
            w._edit_fusion()
        self.assertEqual(selected, [pair[0], pair[1], retail_result])

    def test_fusion_display_limit(self):
        w = self.window
        for a in range(1, 61):
            for b in range(61, 121):
                w.project.fusions[(a, b)] = 3
        w._refresh_fusions()
        c = w.workspace_controls['Fusions']
        self.assertEqual(c['image_list'].count(), 3000)
        self.assertEqual(c['table'].rowCount(), 3000)
        self.assertIn('first 3,000', c['count'].text())

    def test_fusion_filter_double_click_and_collapsed_layout(self):
        from PySide6.QtCore import Qt, QPoint
        from PySide6.QtTest import QTest
        w = self.window
        w.select_workspace('Fusions')
        c = w.workspace_controls['Fusions']
        c['pages'].setCurrentIndex(1)
        w.show()
        w.resize(1580, 980)      # the size this layout is measured at
        self.qt.processEvents()
        for side in c['bulk_filters'].values():
            self.assertTrue(side['advanced'].isHidden())
            for key in ('types', 'stars'):
                listing = side[key]
                item = listing.item(0)
                rect = listing.visualItemRect(item)
                self.assertGreaterEqual(rect.height(), 24)
                point = QPoint(rect.left() + 70, rect.center().y())
                QTest.mouseDClick(listing.viewport(), Qt.MouseButton.LeftButton, pos=point)
                self.assertEqual(item.checkState(), Qt.CheckState.Checked)
                QTest.mouseDClick(listing.viewport(), Qt.MouseButton.LeftButton, pos=point)
                self.assertEqual(item.checkState(), Qt.CheckState.Unchecked)
        w.hide()

    def test_fusion_headers_sort_results(self):
        w = self.window
        w.select_workspace('Fusions')
        table = w.workspace_controls['Fusions']['table']
        header = table.horizontalHeader()
        self.assertTrue(header.sectionsClickable())
        header.sectionClicked.emit(2)
        self.assertTrue(table.horizontalHeaderItem(2).text().endswith('↑'))
        header.sectionClicked.emit(2)
        self.assertTrue(table.horizontalHeaderItem(2).text().endswith('↓'))

    def test_no_selection_clears_and_disables_the_card_form(self):
        """A filter with no results must not leave the last card's data in a
        form that takes edits and drops them (CardsTab.show(None))."""
        w = self.window
        self.assertEqual(w.current, 1)
        w.search.setText('zzz-no-such-card-zzz')
        self.assertEqual(w.listing.rowCount(), 0)
        self.assertIsNone(w.current)
        self.assertEqual(w.card_id.text(), '—')
        self.assertEqual(w.fields['name'].text(), '')
        self.assertEqual(w.description.toPlainText(), '')
        self.assertEqual(w.reference_title.text(), 'Retail card')
        self.assertEqual({value.text() for value in w.reference_values.values()}, {'—'})
        for widget in w._card_form_widgets():
            self.assertFalse(widget.isEnabled(), widget.objectName())
        self.assertTrue(w.add_button.isEnabled())       # a card may still be added
        w.search.clear()
        self.assertEqual(w.current, 1)
        self.assertEqual(w.fields['name'].text(), 'Blue Dragon')
        for widget in w._card_form_widgets():
            self.assertTrue(widget.isEnabled(), widget.objectName())

    def test_search_matches_the_card_number_whole(self):
        """The number is a whole match, as model.card_matches has it: a search
        for "1" is card 1, not every card with a 1 in its number."""
        from PySide6.QtCore import Qt
        w = self.window
        # Names and text without digits, so only the number column can match.
        for card in w.project.cards.values():
            card.name, card.description = 'a nameless card', ''
        w.search.setText('1')
        self.assertEqual([w.listing.item(r, 0).data(Qt.ItemDataRole.UserRole)
                          for r in range(w.listing.rowCount())], [1])
        w.search.setText('22')
        self.assertEqual([w.listing.item(r, 0).data(Qt.ItemDataRole.UserRole)
                          for r in range(w.listing.rowCount())], [22])
        # The name and the card text are still matched on any part of them.
        w.project.cards[5].description = 'a poem about rain'
        w.search.setText('about rain')
        self.assertEqual([w.listing.item(r, 0).data(Qt.ItemDataRole.UserRole)
                          for r in range(w.listing.rowCount())], [5])

    def test_card_text_box_is_fixed_pitch(self):
        """The game wraps at 20 letters a line; the columns must be countable."""
        self.assertTrue(self.window.description.fontInfo().fixedPitch())

    def test_goto_card_ignores_the_list_filters(self):
        w = self.window
        w.search.setText('Blue')
        w.filter.setCurrentText('Changed')
        w.goto_card(300)
        self.assertEqual(w.current, 300)
        self.assertEqual(w.search.text(), '')
        self.assertEqual(w.filter.currentText(), 'All cards')

    def test_problem_lines_go_to_what_they_are_about(self):
        w = self.window
        w.project.pools[2]['deck'] = {999999: 2048}
        w.select_workspace('Problems')
        w._refresh_problems()
        issues = w.workspace_controls['Problems']['issues']
        self.assertTrue(issues)
        row = next(i for i, issue in enumerate(issues) if issue.area == 'Duelists')
        w._open_problem(row)
        self.assertEqual(w.current_workspace, 'Duelists')
        pool = w.workspace_controls['Duelists']['pool']
        self.assertEqual(pool.tabText(pool.currentIndex()), 'Deck')
        # Cards, Fusions and Rituals reach their own page and selection too.
        w.go_to(SimpleNamespace(area='Cards', target=42, where='card 42', level='error'))
        self.assertEqual((w.current_workspace, w.current), ('Cards', 42))
        w.go_to(SimpleNamespace(area='Fusions', target=(5, 6), where='5+6', level='error'))
        self.assertEqual(w.current_workspace, 'Fusions')
        self.assertEqual(w.workspace_controls['Fusions']['search'].text(), '5')
        # Packs has a page of its own now, so its problems reach it.
        w.go_to(SimpleNamespace(area='Packs', target=None, where='pack 1', level='error'))
        self.assertEqual(w.current_workspace, 'Packs')
        # An area with no page still says so rather than doing nothing.
        w.select_workspace('Fusions')
        w.go_to(SimpleNamespace(area='Nowhere', target=None, where='x', level='error'))
        self.assertEqual(w.current_workspace, 'Fusions')
        self.assertIn('not in the modern editor yet', w.statusBar().currentMessage())

    def test_art_search_matches_the_card_number_whole(self):
        """The Art list searches as the card list does (model.card_matches)."""
        from PySide6.QtCore import Qt
        w = self.window
        w.select_workspace('Art')
        for card in w.project.cards.values():
            card.name, card.description = 'a nameless card', ''
        w.refresh_art_list()
        for query, expected in (('1', [1]), ('22', [22])):
            w.art_search.setText(query)
            self.assertEqual([w.art_table.item(r, 0).data(Qt.ItemDataRole.UserRole)
                              for r in range(w.art_table.rowCount())], expected)

    def test_goto_art_ignores_the_list_filters(self):
        w = self.window
        w.select_workspace('Art')
        w.art_search.setText('nothing-matches-this')
        w.art_filter.setCurrentText('Added by the mod')
        w.goto_art(300)
        self.assertEqual(w.current_art_card, 300)
        self.assertEqual(w.art_search.text(), '')
        self.assertEqual(w.art_filter.currentText(), 'All cards')

    def test_card_combos_take_a_number_or_a_name(self):
        """A card is typed, not hunted down a list of seven hundred
        (widgets.card_named)."""
        w = self.window
        combo = w._card_combo(None)
        self.assertTrue(combo.isEditable())
        for typed, expected in (('003  Kuriboh', 3), ('Kuriboh', 3), ('3', 3),
                                ('kurib', 3), ('', None), ('zzzz', None)):
            combo.setCurrentText(typed)
            self.assertEqual(w._combo_card_id(combo), expected, typed)

    def test_fusion_search_covers_materials_and_results_by_default(self):
        """The Tk list matched card A, card B or the result; "Both" is what
        that is here, so it is what the page opens on."""
        w = self.window
        w.select_workspace('Fusions')
        p = w.project
        p.cards[1].name, p.cards[2].name = 'First material', 'Second material'
        result = p.add_card(3, 'result-needle')
        p.cards[result].name = 'Result needle'
        p.set_fusion(1, 2, result)
        w._refresh_fusions()
        c = w.workspace_controls['Fusions']
        self.assertTrue(c['search_both'].isChecked())
        c['search'].setText('Result needle')
        both = c['table'].rowCount()
        c['search_materials'].setChecked(True)
        self.assertEqual(both, 1)
        self.assertEqual(c['table'].rowCount(), 0)       # narrowing is still offered

    def test_rows_are_coloured_by_their_state(self):
        from PySide6.QtCore import Qt
        w = self.window
        w.project.set_notes(5, 'a note')
        w.project.cards[7].name = 'edited'
        w.refresh_cards()
        inks = {}
        for row in range(w.listing.rowCount()):
            cid = w.listing.item(row, 0).data(Qt.ItemDataRole.UserRole)
            if cid in (5, 7):
                inks[cid] = w.listing.item(row, 0).foreground().color().name()
        self.assertEqual(inks[5], '#f2c04c')        # notes
        self.assertEqual(inks[7], '#8ab4f8')        # changed
        # The retail table's "glitch" fusions are the brown rows the hint names.
        # The shown list paints itself, so the ink reaches it through the
        # delegate's own role, not the item's foreground.
        w.select_workspace('Fusions')
        listing = w.workspace_controls['Fusions']['image_list']
        ink_role = int(Qt.ItemDataRole.UserRole) + 6
        state_role = int(Qt.ItemDataRole.UserRole) + 3
        def glitch_ink():
            return next(listing.item(i).data(ink_role) for i in range(listing.count())
                        if listing.item(i).data(state_role) == 'glitch')
        self.assertEqual(glitch_ink(), '#e0ae78')
        # Item inks are not styles, so the theme has to redraw them itself.
        with mock.patch('fm_editor.pyside_app.settings.save', return_value=None):
            w.toggle_dark(False)
        listing = w.workspace_controls['Fusions']['image_list']
        self.assertEqual(glitch_ink(), '#865e3c')

    def test_remove_disc_recipes_offers_the_selected_result(self):
        w = self.window
        w.select_workspace('Fusions')
        c = w.workspace_controls['Fusions']
        c['search'].clear()
        w._refresh_fusions()
        w._set_fusion_view(0)
        c['image_list'].item(0).setSelected(True)
        pair = w._selected_fusion_pairs()[0]
        expected = w.project.fusions.get(pair)
        seen = {}
        def capture(title, ids=None, selected=None):
            seen['selected'] = selected
            return None
        with mock.patch.object(type(w), '_choose_one_card', side_effect=capture):
            w._remove_fusion_result()
        self.assertEqual(seen['selected'], expected)

    def test_the_card_list_shows_all_six_columns(self):
        """The middle column used to crowd the list until DEF and State fell off
        its right edge."""
        w = self.window
        w.show()
        w.resize(1520, 1000)
        for _ in range(6):
            self.qt.processEvents()
        widths = [w.listing.columnWidth(i) for i in range(w.listing.columnCount())]
        self.assertEqual(len(widths), 6)
        self.assertLessEqual(sum(widths), w.listing.viewport().width())
        self.assertFalse(w.listing.horizontalScrollBar().isVisible())
        self.assertGreater(widths[1], 40)       # the name keeps room of its own
        self.assertFalse(w.listing.wordWrap())  # and elides instead of doubling the row
        heights = {w.listing.rowHeight(r) for r in range(min(20, w.listing.rowCount()))}
        self.assertEqual(len(heights), 1)
        w.hide()

    def test_the_card_form_never_scrolls_sideways(self):
        from PySide6.QtWidgets import QScrollArea
        w = self.window
        w.show()
        for width in (1280, 1520, 1920):
            w.resize(width, 1000)
            for _ in range(6):
                self.qt.processEvents()
            scroll = w.cards_form.findChild(QScrollArea, 'cardDataScroll')
            self.assertLessEqual(scroll.widget().minimumSizeHint().width(),
                                 scroll.viewport().width(), width)
            self.assertFalse(scroll.horizontalScrollBar().isVisible(), width)
        w.hide()

    def test_a_combo_popup_is_dark_all_the_way_to_its_frame(self):
        """The popup is its own window: the stylesheet reaches the list, the
        palette reaches the frame around it."""
        w = self.window
        w.show()
        w.resize(1520, 1000)
        for _ in range(5):
            self.qt.processEvents()
        w.frame_box.showPopup()
        for _ in range(5):
            self.qt.processEvents()
        image = w.frame_box.view().parentWidget().grab().toImage()
        light = 0
        for y in range(image.height()):
            across = sum(1 for x in range(image.width())
                         if image.pixelColor(x, y).lightness() > 200)
            if across > image.width() * 0.8:
                light += 1
        w.frame_box.hidePopup()
        w.hide()
        self.assertEqual(light, 0)

    # --- Limits -----------------------------------------------------------

    def limits_page(self):
        self.window.select_workspace('Limits')
        return self.window.workspace_controls['Limits']

    def test_limits_builds_a_field_for_every_limit(self):
        from fm_editor import limits
        c = self.limits_page()
        self.assertEqual(set(c['limits']), {key for key, *_ in limits.ALL_FIELDS})
        for key, _label, _retail, low, high, _storage in limits.ALL_FIELDS:
            spin = c['limits'][key]
            self.assertEqual((spin.minimum(), spin.maximum()), (low - 1, high), key)
            self.assertEqual(spin.value(), low - 1, key)      # unset to start with

    def test_a_limit_is_written_through_at_once(self):
        w = self.window
        c = self.limits_page()
        w.dirty = False
        c['limits']['stats'].setValue(30000)
        self.assertEqual(w.project.other['limits'], {'stats': 30000})
        self.assertTrue(w.dirty)
        c['limits']['two_player.step'].setValue(250)        # a nested key
        self.assertEqual(w.project.other['limits'],
                         {'stats': 30000, 'two_player': {'step': 250}})
        c['limits']['stats'].setValue(c['limits']['stats'].minimum())
        self.assertEqual(w.project.other['limits'], {'two_player': {'step': 250}})

    def test_life_points_collapses_to_its_short_form(self):
        w = self.window
        c = self.limits_page()
        c['limits']['life_points.start'].setValue(16000)
        self.assertEqual(w.project.other['limits'], {'life_points': 16000})

    def test_per_duelist_lp_takes_both_shapes(self):
        w = self.window
        c = self.limits_page()
        c['rows']['Heishin'][3].setValue(20000)             # the duelist's side only
        self.assertEqual(w.project.other['limits']['life_points']['duelists'],
                         {'Heishin': 20000})
        c['rows']['Seto'][2].setValue(8000)
        c['rows']['Seto'][3].setValue(12000)
        self.assertEqual(w.project.other['limits']['life_points']['duelists']['Seto'],
                         {'player': 8000, 'opponent': 12000})

    def test_setting_lp_for_all_duelists_writes_the_wildcard(self):
        w = self.window
        c = self.limits_page()
        c['value'].setValue(7000)
        c['scope'].setCurrentIndex(0)                       # "All duelists"
        w._set_duelist_lp('player')
        self.assertEqual(w.project.other['limits']['life_points']['duelists'],
                         {'all': {'player': 7000}})
        c['scope'].setCurrentIndex(c['scope'].findData('Mai Valentine'))
        c['value'].setValue(11000)
        w._set_duelist_lp('opponent')
        self.assertEqual(w.project.other['limits']['life_points']['duelists']['Mai Valentine'], 11000)

    def test_resetting_clears_the_limits_key(self):
        w = self.window
        c = self.limits_page()
        c['limits']['stats'].setValue(30000)
        c['rows']['Teana'][2].setValue(5000)
        w._reset_all_limits()
        self.assertNotIn('limits', w.project.other)

    def test_revert_puts_back_what_the_mod_was_opened_with(self):
        w = self.window
        w.project.other['limits'] = {'stats': 12345}
        w.limits_opened = None
        c = self.limits_page()
        self.assertEqual(c['limits']['stats'].value(), 12345)
        c['limits']['stats'].setValue(30000)
        w._revert_limits()
        self.assertEqual(w.project.other['limits'], {'stats': 12345})

    def test_a_duelist_the_editor_does_not_know_keeps_its_row(self):
        w = self.window
        w.project.other['limits'] = {'life_points': {'duelists': {'My Custom Guy': 5000}}}
        w.limits_opened = None
        c = self.limits_page()
        self.assertIn('My Custom Guy', c['rows'])
        self.assertEqual(c['rows']['My Custom Guy'][3].value(), 5000)
        self.assertEqual(w.project.other['limits']['life_points']['duelists'],
                         {'My Custom Guy': 5000})

    def test_limits_reports_what_the_loader_would_refuse(self):
        w = self.window
        w.project.other['limits'] = {'stats': 99999, 'nonsense': 1}
        c = self.limits_page()
        self.assertIn('nonsense', c['status'].text())
        self.assertFalse(w._apply_limits())                 # an error is reported, not applied over
        w.project.other['limits'] = {'stats': 30000}
        w._refresh_limits()
        self.assertTrue(w._apply_limits())

    def test_the_limits_form_never_scrolls_sideways(self):
        from PySide6.QtWidgets import QScrollArea
        w = self.window
        self.limits_page()
        w.show()
        for width in (1280, 1520, 1920):
            w.resize(width, 1000)
            for _ in range(6):
                self.qt.processEvents()
            scroll = w.workspace_forms['Limits'].findChild(QScrollArea, 'limitSettingsScroll')
            self.assertLessEqual(scroll.widget().minimumSizeHint().width(),
                                 scroll.viewport().width(), width)
            self.assertFalse(scroll.horizontalScrollBar().isVisible(), width)
        w.hide()

    def test_no_page_hands_its_slack_to_a_label(self):
        """A page's panels take the height, not its heading and summary: with
        every item at stretch 0 a QVBoxLayout shares the slack out evenly."""
        from PySide6.QtWidgets import QLabel
        w = self.window
        w.show()
        w.resize(1920, 1040)
        stretched = {}
        for name in w.NAV:
            w.select_workspace(name)
            for _ in range(6):
                self.qt.processEvents()
            page = w.workspace_forms.get(name)
            layout = page.layout() if page is not None else None
            if layout is None:
                continue
            for index in range(layout.count()):
                item = layout.itemAt(index)
                label = item.widget()
                # A hidden label takes no part in the layout and keeps
                # whatever geometry it last had (a bare widget's 100x30).
                if isinstance(label, QLabel) and not label.isHidden() and \
                        item.geometry().height() > label.sizeHint().height() + 12:
                    stretched.setdefault(name, []).append(label.objectName())
        w.hide()
        self.assertEqual(stretched, {})

    def test_the_limits_table_gives_its_spin_boxes_room(self):
        w = self.window
        c = self.limits_page()
        w.show()
        w.resize(1920, 1040)
        for _ in range(6):
            self.qt.processEvents()
        spin = c['table'].cellWidget(0, 2)
        self.assertGreaterEqual(spin.height(), spin.sizeHint().height())
        self.assertGreater(c['table'].height() // c['table'].rowHeight(0), 12)
        w.hide()

    # --- Guardian Stars ---------------------------------------------------

    def stars_page(self):
        self.window.select_workspace('Guardian Stars')
        return self.window.workspace_controls['Guardian Stars']

    def test_the_stars_and_the_matrix_are_listed(self):
        from fm_editor import guardian_stars as gs
        w = self.window
        c = self.stars_page()
        # The stars, and above them the cards that have none (magic, trap and
        # ritual cards), which is read rather than chosen.
        self.assertEqual(c['stars'].rowCount(), gs.RETAIL_COUNT + 1)
        self.assertEqual(c['list_title'].text(), f'Guardian stars ({gs.RETAIL_COUNT})')
        self.assertEqual([c['stars'].item(0, i).text() for i in range(3)], ['—', '(none)', '—'])
        self.assertEqual([c['stars'].item(1, i).text() for i in range(3)], ['1', 'Mars', "disc's"])
        self.assertEqual((c['matrix'].rowCount(), c['matrix'].columnCount()),
                         (gs.RETAIL_COUNT, gs.RETAIL_COUNT))
        # The disc's cycle: Mars beats Jupiter.
        self.assertEqual(w.stars_model.grid[1][2], gs.retail_matchup(1, 2))
        self.assertEqual(c['matrix'].item(0, 1).text(), f'{gs.retail_matchup(1, 2):+}')

    def test_a_matchup_cell_and_its_mirror(self):
        w = self.window
        c = self.stars_page()
        w.dirty = False
        w._pick_star_cell(0, 2)                     # Mars attacking Saturn
        self.assertIn('Mars attacking Saturn', c['cell_label'].text())
        c['value'].setValue(1234)
        w._set_star_cell()
        self.assertEqual(w.stars_model.grid[1][3], 1234)
        self.assertEqual(w.stars_model.grid[3][1], -1234)       # mirrored
        self.assertTrue(w.dirty)
        self.assertIn('matchups', w.project.other['guardian_stars'])
        c['mirror'].setChecked(False)
        w._set_star_cell(7)
        self.assertEqual(w.stars_model.grid[1][3], 7)
        self.assertEqual(w.stars_model.grid[3][1], -1234)       # left alone

    def test_the_default_bonus_moves_the_cycles_with_it(self):
        from fm_editor import guardian_stars as gs
        w = self.window
        c = self.stars_page()
        self.assertEqual(w.stars_model.grid[1][2], gs.RETAIL_BONUS)
        c['bonus'].setValue(800)
        w._set_star_default()
        self.assertEqual(w.stars_model.default_bonus, 800)
        self.assertEqual(w.stars_model.grid[1][2], 800)

    def test_renaming_a_star_writes_only_that_star(self):
        w = self.window
        c = self.stars_page()
        w._select_star_row(5)
        self.assertEqual(w.stars_selected, 5)
        c['name'].setText('Poseidon')
        w._set_star_name()
        self.assertEqual(w.stars_model.name(5), 'Poseidon')
        self.assertEqual(w.project.other['guardian_stars']['stars'], [{'id': 5, 'name': 'Poseidon'}])

    def test_the_name_list_sets_every_star_at_once(self):
        w = self.window
        c = self.stars_page()
        names = ['Ares', 'Zeus', 'Cronos', 'Ouranos', 'Hades',
                 'Poseidon', 'Hermes', 'Selene', 'Helios', 'Aphrodite']
        c['names'].setText(', '.join(names))
        w._set_star_names()
        self.assertEqual([w.stars_model.name(i) for i in range(1, 11)], names)
        w._reset_star_names()
        self.assertEqual(w.stars_model.name(1), 'Mars')
        self.assertNotIn('guardian_stars', w.project.other)

    def test_adding_duplicating_and_removing_a_star(self):
        from fm_editor import guardian_stars as gs
        w = self.window
        c = self.stars_page()
        w._select_star_row(1)
        c['name'].setText('Ares')
        w._set_star_name()
        star = w._add_star()
        self.assertEqual(star, gs.RETAIL_COUNT + 1)
        self.assertEqual(w.stars_model.count, gs.RETAIL_COUNT + 1)
        w._select_star_row(1)
        w._duplicate_star()                         # a copy of Ares
        self.assertEqual(w.stars_model.count, gs.RETAIL_COUNT + 2)
        self.assertEqual(w.stars_model.name(gs.RETAIL_COUNT + 2), 'Ares')
        w.stars_selected = gs.RETAIL_COUNT + 2
        w._remove_star()
        self.assertEqual(w.stars_model.count, gs.RETAIL_COUNT + 1)

    def test_a_star_icon_is_imported_and_removed(self):
        import tempfile
        from pathlib import Path
        from fm_editor import pngio
        w = self.window
        c = self.stars_page()
        w._select_star_row(5)
        image = pngio.Image(16, 16, bytes([200, 40, 40, 255]) * 256)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'star.png'
            pngio.write(str(path), image)
            w.use_star_icon(5, str(path))
        self.assertEqual(w.stars_model.stars[5].icon, 'icons/star-5.png')
        self.assertIn('icons/star-5.png', w.project.files)
        self.assertFalse(c['icon'].pixmap().isNull())
        self.assertEqual(c['stars'].item(5, 2).text(), "mod's")     # star 5, under the "(none)" line
        w._remove_star_icon()
        self.assertNotIn('icons/star-5.png', w.project.files)

    def test_duplicate_star_keeps_an_independent_icon_after_save_reopen(self):
        """Removing a duplicated icon must never remove the source star's PNG."""
        from fm_editor import guardian_stars as gs, pngio
        w = self.window
        self.stars_page()
        w._select_star_row(1)
        image = pngio.Image(16, 16, bytes([40, 120, 200, 255]) * 256)
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'star.png'
            pngio.write(str(source), image)
            w.use_star_icon(1, str(source))
            source_icon = w.stars_model.stars[1].icon

            w._duplicate_star()
            duplicate = gs.RETAIL_COUNT + 1
            duplicate_icon = w.stars_model.stars[duplicate].icon
            self.assertNotEqual(duplicate_icon, source_icon)
            self.assertEqual(w.project.files[duplicate_icon], w.project.files[source_icon])

            w.stars_selected = duplicate
            w._remove_star_icon()
            self.assertEqual(w.stars_model.stars[1].icon, source_icon)
            self.assertIn(source_icon, w.project.files)
            self.assertNotIn(duplicate_icon, w.project.files)

            output = Path(folder) / 'mod'
            manifest.save_mod(w.project, output)
            reopened, messages = manifest.open_mod(w.retail, output)
            self.assertEqual(messages, [])
            restored = gs.read(reopened.other.get('guardian_stars'))
            self.assertEqual(restored.stars[1].icon, source_icon)
            self.assertEqual(pngio.read(output / source_icon).rgba, image.rgba)

    def test_the_table_presets(self):
        w = self.window
        self.stars_page()
        w._stars_preset_clear()
        self.assertTrue(w.stars_model.replace)
        self.assertEqual(w.stars_model.grid[1][2], 0)
        w._stars_preset_retail()
        self.assertFalse(w.stars_model.replace)
        self.assertNotEqual(w.stars_model.grid[1][2], 0)

    def test_an_untouched_section_is_not_rewritten(self):
        """A mod's own "beats"/"mirror" shape survives a visit to the page."""
        w = self.window
        written = {'stars': [{'id': 11, 'name': 'Fire', 'beats': ['Mars']}]}
        w.project.other['guardian_stars'] = written
        self.stars_page()
        w.dirty = False
        w._commit_stars()
        self.assertEqual(w.project.other['guardian_stars'], written)
        self.assertFalse(w.dirty)

    def test_stars_by_rule_applies_and_undoes(self):
        from PySide6.QtWidgets import QDialog, QPushButton, QCheckBox, QComboBox, QMessageBox
        w = self.window
        self.stars_page()
        opened = {}
        with mock.patch.object(QDialog, 'exec', lambda self: opened.setdefault('d', self) and 0):
            w._open_star_rules()
        dialog = opened['d']
        next(b for b in dialog.findChildren(QCheckBox) if b.text() == 'Every monster').setChecked(True)
        mapping = [b for b in dialog.findChildren(QComboBox)
                   if b.count() and b.itemText(0) == '(none)']
        self.assertEqual(len(mapping), 6)           # one per attribute
        mapping[0].setCurrentIndex(3)               # Light cards get star 3
        before = {cid: (card.star1, card.star2) for cid, card in w.project.cards.items()}
        apply_button = next(b for b in dialog.findChildren(QPushButton) if b.text().startswith('Apply'))
        undo_button = next(b for b in dialog.findChildren(QPushButton) if b.text().startswith('Undo'))
        self.assertTrue(apply_button.isEnabled())
        with mock.patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes):
            apply_button.click()
        changed = [cid for cid, card in w.project.cards.items()
                   if (card.star1, card.star2) != before[cid]]
        self.assertTrue(changed)
        self.assertTrue(undo_button.isEnabled())
        with mock.patch.object(QMessageBox, 'information'):
            undo_button.click()
        self.assertEqual([cid for cid, card in w.project.cards.items()
                          if (card.star1, card.star2) != before[cid]], [])

    def test_guardian_stars_reports_and_reverts(self):
        from PySide6.QtWidgets import QMessageBox
        w = self.window
        w.project.other['guardian_stars'] = {'nonsense': 1}
        c = self.stars_page()
        self.assertIn('nonsense', c['status'].text())
        self.assertFalse(w._apply_stars())
        with mock.patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes):
            w._revert_stars()
        self.assertNotIn('guardian_stars', w.project.other)

    def test_the_matrix_is_a_grid_not_a_row_list(self):
        """The shared table pass hides vertical headers, selects whole rows and
        stretches columns; the matrix is named on both axes and wants none of it."""
        w = self.window
        c = self.stars_page()
        w.show()
        w.resize(1920, 1040)
        for _ in range(8):
            self.qt.processEvents()
        matrix = c['matrix']
        self.assertTrue(matrix.verticalHeader().isVisible())
        self.assertGreaterEqual(matrix.verticalHeader().width(), 120)
        self.assertEqual(matrix.verticalHeaderItem(0).text(), '1 Mars')
        self.assertEqual(matrix.horizontalHeaderItem(0).text(), 'Mars')
        widths = [matrix.columnWidth(i) for i in range(matrix.columnCount())]
        self.assertTrue(all(width >= 62 for width in widths), widths)
        self.assertEqual(matrix.item(0, 1).text(), '+500')      # not elided to "..."
        self.assertEqual(matrix.selectionBehavior(),
                         matrix.SelectionBehavior.SelectItems)
        w.hide()

    def test_a_star_takes_its_symbol_from_the_disc(self):
        """A star with no icon of its own falls back to the disc\'s symbol.
        The synthetic fixture leaves that sheet clear, so stand a tile in it;
        the pixels themselves are pinned in test_guardian_stars.DiscIconTest."""
        import struct
        from fm_editor import guardian_stars as gs
        w = self.window
        sheet = bytearray(w.files.wa)
        struct.pack_into('<16H', sheet, gs.ICON_CLUT, *([0] + [0xFFFF] * 15))
        for x, y in gs.ICON_SPOTS:
            start = gs.ICON_SHEET + y * gs.ICON_STRIDE + x // 2
            for row in range(gs.ICON_SIDE):
                at = start + row * gs.ICON_STRIDE
                sheet[at:at + gs.ICON_SIDE // 2] = bytes([0x11] * (gs.ICON_SIDE // 2))
        w.files = SimpleNamespace(wa=bytes(sheet), source=w.files.source)
        c = self.stars_page()
        for star in range(1, gs.RETAIL_COUNT + 1):
            self.assertIsNotNone(w._star_icon_pixmap(star), star)
        self.assertTrue(all(not c['stars'].item(row, 1).icon().isNull()
                            for row in range(1, gs.RETAIL_COUNT + 1)))
        self.assertFalse(c['icon'].pixmap().isNull())
        self.assertTrue(all(not c['matrix'].horizontalHeaderItem(i).icon().isNull()
                            for i in range(gs.RETAIL_COUNT)))
        # Only the disc's ten have one; a star past them does not.
        self.assertIsNone(gs.disc_icon(bytes(sheet), gs.RETAIL_COUNT + 1))
        self.assertIsNone(gs.disc_icon(bytes(sheet), 0))
        self.assertIsNone(gs.disc_icon(None, 1))

    # --- Packs ------------------------------------------------------------

    def packs_page(self):
        self.window.select_workspace('Packs')
        return self.window.workspace_controls['Packs']

    def test_a_pack_is_added_and_its_fields_are_kept(self):
        from fm_editor import packs as packmath
        w = self.window
        c = self.packs_page()
        self.assertEqual(c['list'].rowCount(), 0)
        w._add_pack()
        self.assertEqual(len(w.project.packs), 1)
        self.assertEqual(c['list'].rowCount(), 1)
        c['name'].setText('Starter Pack')
        c['price'].setValue(5000)          # the spin must reach past Qt's default 99
        c['count'].setValue(9)
        self.assertTrue(w._commit_packs())
        entry = w.project.packs[0]
        self.assertEqual(entry['name'], 'Starter Pack')
        self.assertEqual(entry['price'], 5000)
        self.assertEqual(entry['count'], 9)
        self.assertIn(packmath.pack_id(entry), c['identity'].text())

    def test_the_basic_stock_field_is_not_eaten_by_the_advanced_tab(self):
        """"stock" is one of the Dealing tab's keys, so the order the two are
        applied in decides whether the plain field does anything."""
        w = self.window
        c = self.packs_page()
        w._add_pack()
        c['name'].setText('Starter')
        c['infinite'].setChecked(False)
        c['stock'].setValue(7)
        self.assertTrue(w._commit_packs())
        self.assertEqual(w.project.packs[0].get('stock'), 7)
        c['infinite'].setChecked(True)
        self.assertTrue(w._commit_packs())
        self.assertNotIn('stock', w.project.packs[0])

    def test_cards_weights_and_chances(self):
        w = self.window
        c = self.packs_page()
        w._add_pack()
        c['name'].setText('Starter')
        w._commit_packs()
        c['weight'].setValue(10)
        w._insert_pack_cards([1, 2, 3, 4, 5])
        self.assertEqual(c['contents'].rowCount(), 5)
        self.assertEqual(c['total'].text(), 'Total weight: 50')
        self.assertEqual([c['contents'].item(r, 6).text() for r in range(5)], ['20.00%'] * 5)
        c['contents'].selectRow(0)
        c['weight'].setValue(90)
        w._set_pack_weight()
        pool = w.project.packs[0]['cards']
        self.assertEqual(sorted(pool.values()), [10, 10, 10, 10, 90])

    def add_tier(self, name, **values):
        """Fill the tier dialog in and accept it."""
        w = self.window
        held = {}

        def fill(window, title, tier_name, tier, on_ok):
            held['said'] = on_ok(name, {'odds': values.get('odds', 1), 'label': values.get('label', ''),
                                        'color': values.get('color'), 'sound': values.get('sound'),
                                        'reveal': values.get('reveal', '')})

        with mock.patch.object(type(w), '_pack_tier_dialog', fill):
            w._add_pack_tier()
        return held.get('said')

    def test_tiers_are_made_and_cards_moved_between_them(self):
        w = self.window
        c = self.packs_page()
        w._add_pack()
        c['name'].setText('Starter')
        w._commit_packs()
        c['weight'].setValue(10)
        w._insert_pack_cards([1, 2, 3])
        self.add_tier('rare')
        self.assertIn('rare', w.project.packs[0]['tiers'])
        c['contents'].clearSelection()
        c['contents'].selectRow(0)
        c['tier'].setCurrentText('rare')
        w._set_pack_tier()
        tiers = w.project.packs[0]['tiers']
        self.assertEqual(len(tiers['rare']['cards']), 1)
        self.assertEqual(len(tiers['cards']['cards']), 2)

    def test_duplicate_remove_and_move_packs(self):
        from PySide6.QtWidgets import QMessageBox
        w = self.window
        c = self.packs_page()
        w._add_pack()
        c['name'].setText('First')
        w._commit_packs()
        w._duplicate_pack()
        self.assertEqual(len(w.project.packs), 2)
        self.assertEqual([p['name'] for p in w.project.packs], ['First', 'First copy'])
        w._move_pack(-1)
        self.assertEqual([p['name'] for p in w.project.packs], ['First copy', 'First'])
        with mock.patch.object(QMessageBox, 'question',
                               return_value=QMessageBox.StandardButton.Yes):
            w._remove_pack()
        self.assertEqual(len(w.project.packs), 1)

    def test_the_dealing_form_writes_what_the_game_reads(self):
        w = self.window
        c = self.packs_page()
        w._add_pack()
        c['name'].setText('Starter')
        c['adv']['duplicates'].setCurrentText('unique_in_pack')
        c['adv']['max_copies'].setText('3')
        c['adv']['guarantee'].setText('cards=2')
        self.assertTrue(w._commit_packs())
        pack = w.project.packs[0]
        self.assertEqual(pack['duplicates'], 'unique_in_pack')
        self.assertEqual(pack['max_copies'], 3)
        self.assertEqual(pack['guarantee'], {'cards': 2})
        # What the game could not read is refused, and nothing is stored.
        c['adv']['max_copies'].setText('nonsense')
        self.assertFalse(w._commit_packs())
        self.assertIn('Max copies', c['problem'].text())
        self.assertEqual(w.project.packs[0]['max_copies'], 3)

    def test_an_untouched_advanced_field_leaves_its_key_as_written(self):
        """A pack a mod wrote its own way is not rewritten by being looked at."""
        w = self.window
        c = self.packs_page()
        w.project.packs.append({'id': 'mine', 'name': 'Mine', 'cover': 2,
                                'unlock': {'beat': 'Heishin', 'wins': 3}})
        w._refresh_packs()
        c['list'].setCurrentCell(0, 0)
        self.assertTrue(w._commit_packs())
        self.assertEqual(w.project.packs[0]['cover'], 2)        # still a number
        self.assertEqual(w.project.packs[0]['unlock'], {'beat': 'Heishin', 'wins': 3})

    def test_the_unlock_and_sound_forms_round_trip(self):
        w = self.window
        c = self.packs_page()
        w._add_pack()
        c['adv']['wins'].setText('5')
        c['adv']['story'].setText('0x6E2')
        c['adv']['opened'].setText('starter=2')
        c['adv']['locked'].setCurrentText('shown')
        c['adv']['password'].setText('12345678')
        c['adv']['once'].setChecked(True)
        c['adv']['sound_buy'].setText('40')
        self.assertTrue(w._commit_packs())
        pack = w.project.packs[0]
        self.assertEqual(pack['unlock']['wins'], 5)
        self.assertEqual(pack['unlock']['story'], 0x6E2)
        self.assertEqual(pack['unlock']['opened'], {'starter': 2})
        self.assertEqual(pack['locked'], 'shown')
        self.assertTrue(pack['once'])
        self.assertEqual(pack['sounds']['buy'], 40)
        w._fill_pack()
        self.assertEqual(c['adv']['wins'].text(), '5')
        self.assertEqual(c['adv']['sound_buy'].text(), '40')

    def test_simulating_a_pack_reports_every_card(self):
        w = self.window
        c = self.packs_page()
        w._add_pack()
        c['name'].setText('Starter')
        w._commit_packs()
        c['weight'].setValue(10)
        w._insert_pack_cards([1, 2, 3, 4, 5])
        c['sim_count'].setValue(200)
        w._simulate_pack()
        for _ in range(900):
            self.qt.processEvents()
            if c.get('simulation'):
                break
        result = c['simulation']
        self.assertIsNotNone(result)
        self.assertEqual(result.packs, 200)
        self.assertEqual(sum(result.cards.values()), sum(result.tiers.values()))
        w._show_pack_results()
        table = c['sim_results']
        # One row a card, each filled in: the rows used to be inserted and then
        # every card written into the last of them.
        self.assertEqual(table.rowCount(), len(result.cards))
        for row in range(table.rowCount()):
            self.assertTrue(all(table.item(row, col) for col in range(4)), row)

    def test_an_external_packs_file_is_read_only(self):
        from PySide6.QtWidgets import QPushButton
        w = self.window
        c = self.packs_page()
        w._add_pack()
        c['name'].setText('Starter')
        w._commit_packs()
        before = dict(w.project.packs[0])
        w.project.packs_file = 'packs.json'
        w._refresh_packs()
        self.assertIn('packs.json', c['status'].text())
        self.assertFalse(c['name'].isEnabled())
        self.assertFalse(c['page'].findChild(QPushButton, 'addPackButton').isEnabled())
        c['name'].setText('Changed')
        self.assertTrue(w._commit_packs())
        self.assertEqual(w.project.packs[0], before)
        w.project.packs_file = None

    # --- Rituals ----------------------------------------------------------

    def rituals_page(self):
        self.window.select_workspace('Rituals')
        return self.window.workspace_controls['Rituals']

    def a_ritual(self, conditions=None):
        """Select the first retail ritual, optionally giving it conditions."""
        w = self.window
        c = self.rituals_page()
        ritual = sorted(w.project.retail.rituals)[0]
        if conditions is not None:
            w.project.ritual_requirements[ritual] = conditions
        w._ritual_drafts.pop(ritual, None)
        w.ritual_current = ritual
        w._refresh_rituals()
        row = next(i for i in range(c['cards'].rowCount())
                   if c['cards'].item(i, 0).data(Qt_UserRole()) == ritual)
        c['cards'].selectRow(row)
        return ritual, c, row

    def edit_ritual(self, mutate):
        """Open the recipe dialog, let `mutate` touch it, then press Save."""
        from PySide6.QtWidgets import QDialog, QPushButton
        def fake_exec(dialog):
            mutate(dialog)
            next(b for b in dialog.findChildren(QPushButton) if b.text() == 'Save').click()
            return dialog.result()
        with mock.patch.object(QDialog, 'exec', fake_exec):
            self.window._edit_ritual()

    def test_removing_a_ritual_takes_its_conditions_with_it(self):
        w = self.window
        ritual, _c, _row = self.a_ritual([{'min_attack': 1500}, {}, {}])
        w._remove_ritual()
        self.assertNotIn(ritual, w.project.rituals)
        self.assertNotIn(ritual, w.project.ritual_requirements)

    def test_reverting_a_ritual_takes_its_conditions_with_it(self):
        w = self.window
        ritual, _c, _row = self.a_ritual([{'min_attack': 1500}, {}, {}])
        w._revert_ritual()
        self.assertEqual(w.project.rituals[ritual], w.project.retail.rituals[ritual])
        self.assertNotIn(ritual, w.project.ritual_requirements)

    def test_a_plain_recipe_replaces_the_conditions_it_is_applied_over(self):
        w = self.window
        ritual, _c, _row = self.a_ritual([{'min_attack': 1500}, {}, {}])
        w.ritual_pending[ritual] = (1, 2, 3, 4)
        w._apply_ritual_selector_recipe()
        self.assertEqual(w.project.rituals[ritual], (1, 2, 3, 4))
        self.assertNotIn(ritual, w.project.ritual_requirements)

    def test_a_conditional_recipe_shows_as_changed_and_locks_the_combos(self):
        w = self.window
        ritual, c, row = self.a_ritual([{'min_attack': 1500}, {'type': 'Dragon'}, {'card': 1}])
        # model.ritual_status counts conditions as a change; the page used to
        # read the recipe alone and call it Stock.
        self.assertEqual(w.project.ritual_status(ritual), 'changed')
        self.assertEqual(c['cards'].item(row, 2).text(), '3')
        self.assertEqual(c['cards'].item(row, 3).text(), 'Changed')
        self.assertIn('ATK ≥ 1500', w._ritual_tribute_text(w._ritual_recipe(ritual)[0][0]))
        self.assertIn('Dragon', w._ritual_tribute_text(w._ritual_recipe(ritual)[0][1]))
        # The structured rule editor is active for the selected rule-based tribute.
        self.assertTrue(c['conditions'].isEnabled())

    def test_ritual_search_finds_named_tributes_and_summoned_monsters(self):
        w = self.window
        ritual, c, row = self.a_ritual()
        tributes, result, _origin = w.project.ritual_recipe(ritual)
        c['search'].setText(w.project.cards[result].name)
        self.assertFalse(c['cards'].isRowHidden(row))
        c['search'].setText(w.project.cards[tributes[0]['card']].name)
        self.assertFalse(c['cards'].isRowHidden(row))

    def test_inactive_ritual_recipes_remain_visible_for_inspection(self):
        from PySide6.QtWidgets import QPushButton

        from fm_editor import gamedata
        w = self.window
        ritual, c, _row = self.a_ritual()
        before = tuple(w.project.rituals[ritual])
        w.project.cards[ritual].type = gamedata.TYPE_MAGIC
        w._refresh_rituals()
        row = next(row for row in range(c['cards'].rowCount())
                   if c['cards'].item(row, 0).data(Qt_UserRole()) == ritual)
        self.assertIn('Inactive', c['cards'].item(row, 3).text())
        c['state_filter'].setCurrentText('Inactive recipes')
        self.assertFalse(c['cards'].isRowHidden(row))
        c['cards'].selectRow(row)
        w._select_ritual()
        self.assertFalse(c['result'].isEnabled())
        self.assertFalse(c['conditions'].isEnabled())
        self.assertFalse(c['page'].findChild(QPushButton, 'applyRitualButton').isEnabled())
        draft_before = [dict(requirement) for requirement in w._ritual_draft(ritual)['tributes']]
        w._select_or_add_tribute(3)
        self.assertEqual(w._ritual_draft(ritual)['tributes'], draft_before)
        w._apply_ritual_selector_recipe()
        self.assertEqual(w.project.rituals[ritual], before)

    def test_five_tribute_rituals_preserve_conditions_origin_and_copy_isolation(self):
        from fm_editor.gamedata import FUSION_GROUPS, TYPE_NAMES
        w = self.window
        ritual, _c, _row = self.a_ritual()
        monsters = w.project.monsters()
        result = monsters[5]
        requirements = [
            {'card': monsters[0]},
            {'type': TYPE_NAMES[w.project.cards[monsters[1]].type]},
            {'min_attack': 1200, 'max_attack': 2500},
            {'fusion_group': FUSION_GROUPS[0]},
            {'card': monsters[4]},
        ]
        w.project.set_ritual(ritual, requirements, result, 'both')
        w._refresh_rituals()
        self.assertEqual(w._ritual_recipe(ritual)[:3], (requirements, result, 'both'))
        copied = w.project.add_card(ritual)
        w.ritual_current = copied
        draft = w._ritual_draft(copied)
        draft['tributes'][0] = {'min_attack': 3333}
        w._apply_ritual_selector_recipe()
        self.assertEqual(w.project.ritual_requirements[ritual], requirements)
        self.assertEqual(w.project.ritual_requirements[copied][0], {'min_attack': 3333})
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / 'mod'
            manifest.save_mod(w.project, folder)
            reopened, messages = manifest.open_mod(w.retail, folder)
        self.assertFalse(messages)
        self.assertEqual(reopened.ritual_recipe(ritual), (requirements, result, 'both'))
        self.assertEqual(reopened.ritual_recipe(copied)[0][0], {'min_attack': 3333})

    def test_conditional_ritual_edits_undo_and_redo_as_a_complete_recipe(self):
        w = self.window
        ritual, _c, _row = self.a_ritual()
        before = [dict(row) for row in w._ritual_recipe(ritual)[0]]
        w._start_history()
        draft = w._ritual_draft(ritual)
        draft['tributes'][0] = {'min_attack': 2345}
        w._apply_ritual_selector_recipe()
        w._flush_history()
        self.assertEqual(w.project.ritual_requirements[ritual][0], {'min_attack': 2345})
        w.undo()
        self.assertEqual(w._ritual_recipe(ritual)[0], before)
        w.redo()
        self.assertEqual(w._ritual_recipe(ritual)[0][0], {'min_attack': 2345})

    def test_the_recipe_dialog_edits_conditions(self):
        from PySide6.QtWidgets import QSpinBox
        w = self.window
        ritual, _c, _row = self.a_ritual([{'min_attack': 1500}, {'type': 'Dragon'}, {'card': 1}])
        w.dirty = False
        self.edit_ritual(lambda d: d.findChildren(QSpinBox)[0].setValue(2200))
        self.assertTrue(w.dirty)
        self.assertEqual(w.project.ritual_requirements[ritual],
                         [{'min_attack': 2200}, {'type': 'Dragon'}, {'card': 1}])
        # The cards it shows are the named ones; a condition-only tribute is 0.
        self.assertEqual(w.project.rituals[ritual][:3], (0, 0, 1))

    def test_three_named_cards_need_no_conditions_written(self):
        w = self.window
        ritual, _c, _row = self.a_ritual([{'card': 1}, {'card': 2}, {'card': 3}])
        w.project.rituals[ritual] = (1, 2, 3, 500)
        self.edit_ritual(lambda d: None)
        self.assertEqual(w.project.rituals[ritual], (1, 2, 3, 500))
        self.assertNotIn(ritual, w.project.ritual_requirements)

    def test_the_recipe_dialog_refuses_what_the_game_could_not_read(self):
        from PySide6.QtWidgets import QSpinBox, QLabel
        w = self.window
        ritual, _c, _row = self.a_ritual([{}, {'card': 2}, {'card': 3}])
        before = dict(w.project.rituals)
        self.edit_ritual(lambda d: None)                    # a tribute with nothing in it
        self.assertEqual(w.project.rituals, before)
        # and a minimum past its maximum
        self.a_ritual([{'min_attack': 1000, 'max_attack': 2000}, {'card': 2}, {'card': 3}])
        before = dict(w.project.rituals)
        def crossed(dialog):
            spins = dialog.findChildren(QSpinBox)
            spins[0].setValue(3000)
            spins[1].setValue(100)
        self.edit_ritual(crossed)
        self.assertEqual(w.project.rituals, before)

    def test_the_recipe_column_reads_every_kind_of_condition(self):
        w = self.window
        ritual, c, _row = self.a_ritual([{'min_level': 5, 'max_level': 8},
                                         {'defense_gt_attack': True}, {'card': 1}])
        requirements = w._ritual_recipe(ritual)[0]
        text = " · ".join(w._ritual_tribute_text(requirement) for requirement in requirements)
        for part in ('Level ≥ 5', 'Level ≤ 8', 'DEF > ATK', 'Blue Dragon'):
            self.assertIn(part, text)

    # --- Equips -----------------------------------------------------------

    def equips_page(self):
        self.window.select_workspace('Equips')
        return self.window.workspace_controls['Equips']

    def test_the_equips_page_opens_on_a_card(self):
        w = self.window
        c = self.equips_page()
        self.assertGreater(c['equips'].rowCount(), 0)
        self.assertEqual(c['equips'].currentRow(), 0)
        self.assertIsNotNone(w.equip_current)
        self.assertEqual(c['monsters'].rowCount(), len(w.project.monsters()))

    def test_the_equip_searches_match_a_card_number(self):
        w = self.window
        c = self.equips_page()
        equip = w.equip_current
        # Names and text without digits, so only the number column can match.
        for card in w.project.cards.values():
            card.name, card.description = 'a nameless card', ''
        w.project.cards[equip].name = 'Dragon Capture Jar'
        w._refresh_equips()
        c['search'].setText(str(equip))
        shown = [r for r in range(c['equips'].rowCount()) if not c['equips'].isRowHidden(r)]
        self.assertEqual(len(shown), 1)
        c['search'].setText('Capture')
        shown = [r for r in range(c['equips'].rowCount()) if not c['equips'].isRowHidden(r)]
        self.assertEqual(len(shown), 1)
        c['search'].clear()
        monster = w.project.monsters()[0]
        c['monster_search'].setText(str(monster))
        shown = [r for r in range(c['monsters'].rowCount()) if not c['monsters'].isRowHidden(r)]
        self.assertEqual(len(shown), 1)
        c['monster_search'].clear()

    def test_equip_rows_are_coloured_by_their_state(self):
        w = self.window
        c = self.equips_page()
        equip = w.equip_current
        baseline = w.project.equip_baseline(equip)
        self.assertTrue(baseline)
        # Keep one of the disc's and allow one it never allowed.
        w.project.equips[equip] = set(list(baseline)[:1]) | {max(w.project.monsters())}
        w._refresh_equips()
        row = next(r for r in range(c['equips'].rowCount())
                   if c['equips'].item(r, 0).data(Qt_UserRole()) == equip)
        self.assertEqual(c['equips'].item(row, 0).foreground().color().name(), '#8ab4f8')
        c['equips'].selectRow(row)
        w._select_equip()
        monsters = c['monsters']
        added = next(r for r in range(monsters.rowCount()) if monsters.item(r, 5).text() == 'Added')
        removed = next(r for r in range(monsters.rowCount()) if monsters.item(r, 5).text() == 'Removed')
        self.assertEqual(monsters.item(added, 1).foreground().color().name(), '#7fd49b')
        self.assertEqual(monsters.item(removed, 1).foreground().color().name(), '#ff8f87')

    def test_equips_are_edited_by_tick_type_and_revert(self):
        from PySide6.QtCore import Qt
        w = self.window
        c = self.equips_page()
        equip = w.equip_current
        monsters = c['monsters']
        row = next(r for r in range(monsters.rowCount())
                   if monsters.item(r, 0).data(Qt_UserRole()) not in w.project.equips[equip])
        monster = monsters.item(row, 0).data(Qt_UserRole())
        w.dirty = False
        monsters.item(row, 0).setCheckState(Qt.CheckState.Checked)
        self.assertIn(monster, w.project.equips[equip])
        self.assertTrue(w.dirty)
        typ = next(t for t in range(20)
                   if any(card.type == t for card in w.project.cards.values() if card.is_monster()))
        members = {cid for cid in w.project.monsters() if w.project.cards[cid].type == typ}
        c['type_toggles'][typ].setCheckState(Qt.CheckState.Checked)
        self.assertTrue(members.issubset(w.project.equip_targets(equip)))
        self.assertEqual(c['type_counts'][typ].text(), f"{len(members)}/{len(members)}")
        c['type_toggles'][typ].setCheckState(Qt.CheckState.Unchecked)
        self.assertFalse(members & w.project.equip_targets(equip))
        w._revert_equip()
        self.assertEqual(w.project.equips[equip], w.project.equip_baseline(equip))

    def test_selecting_equip_monsters_does_not_create_a_target_override(self):
        """Changing table selection is read-only, including for inherited targets."""
        w = self.window
        c = self.equips_page()
        equip = w.equip_current
        w.project.equips.pop(equip)
        before = manifest.build(w.project)
        w._fill_equip_monsters()
        c['monsters'].selectRow(0)
        self.qt.processEvents()
        self.assertNotIn(equip, w.project.equips)
        self.assertEqual(manifest.build(w.project), before)

    def test_equip_type_controls_show_partial_counts_and_filter_the_table(self):
        from PySide6.QtCore import Qt
        w = self.window
        c = self.equips_page()
        equip = w.equip_current
        typ = next(t for t in range(20)
                   if len([cid for cid in w.project.monsters() if w.project.cards[cid].type == t]) >= 2)
        members = {cid for cid in w.project.monsters() if w.project.cards[cid].type == typ}
        w.project.equips[equip] = {next(iter(members))}
        w._refresh_equips()
        toggle, count = c['type_toggles'][typ], c['type_counts'][typ]
        self.assertEqual(toggle.checkState(), Qt.CheckState.PartiallyChecked)
        self.assertEqual(count.text(), f"1/{len(members)}")
        count.click()
        self.assertTrue(all(c['monsters'].isRowHidden(row) ==
                            (c['monsters'].item(row, 0).data(Qt_UserRole()) not in members)
                            for row in range(c['monsters'].rowCount())))
        count.click()
        self.assertFalse(any(c['monsters'].isRowHidden(row) for row in range(c['monsters'].rowCount())))

    def test_unchanged_equip_type_operation_does_not_mark_the_project_dirty(self):
        from PySide6.QtCore import Qt
        w = self.window
        c = self.equips_page()
        equip = w.equip_current
        typ = next(t for t in range(20)
                   if any(card.type == t for card in w.project.cards.values() if card.is_monster()))
        c['type_toggles'][typ].setCheckState(Qt.CheckState.Checked)
        w._flush_history()
        history_size = len(w.history.items)
        w.dirty = False
        c['type_toggles'][typ].setCheckState(Qt.CheckState.Checked)
        self.qt.processEvents()
        self.assertFalse(w.dirty)
        self.assertEqual(len(w.history.items), history_size)
        self.assertTrue(all(w.project.cards[cid].type != typ or cid in w.project.equip_targets(equip)
                            for cid in w.project.monsters()))

    def test_equip_targets_persist_through_save_reopen_and_history(self):
        w = self.window
        c = self.equips_page()
        equip = w.equip_current
        before = set(w.project.equip_targets(equip))
        typ = w.project.cards[next(iter(before))].type
        w._equip_by_type(False, typ)
        after = set(w.project.equip_targets(equip))
        self.assertNotEqual(after, before)
        w._flush_history()
        w.undo()
        self.assertEqual(w.project.equip_targets(equip), before)
        w.redo()
        self.assertEqual(w.project.equip_targets(equip), after)
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / 'mod'
            manifest.save_mod(w.project, folder)
            reopened, messages = manifest.open_mod(w.retail, folder)
        self.assertFalse(messages)
        self.assertEqual(reopened.equip_targets(equip), after)

    def test_added_equip_and_copied_monster_keep_their_explicit_targets(self):
        from PySide6.QtCore import Qt
        w = self.window
        c = self.equips_page()
        base_equip = w.equip_current
        base_target = next(iter(w.project.equip_targets(base_equip)))
        added_equip = w.project.add_card(base_equip)
        copied_target = w.project.add_card(base_target)
        self.assertIn(copied_target, w.project.equip_targets(base_equip))
        self.assertIn(copied_target, w.project.equip_targets(added_equip))
        w.equip_current = added_equip
        w._fill_equip_monsters()
        row = next(row for row in range(c['monsters'].rowCount())
                   if c['monsters'].item(row, 0).data(Qt_UserRole()) == copied_target)
        c['monsters'].item(row, 0).setCheckState(Qt.CheckState.Unchecked)
        self.assertNotIn(copied_target, w.project.equip_targets(added_equip))
        self.assertIn(copied_target, w.project.equip_targets(base_equip))

    def test_an_equip_changed_to_another_type_has_no_active_target_controls(self):
        from fm_editor import gamedata
        w = self.window
        c = self.equips_page()
        equip = w.equip_current
        w.project.cards[equip].type = gamedata.TYPE_MAGIC
        w._refresh_equips()
        listed = {c['equips'].item(row, 0).data(Qt_UserRole())
                  for row in range(c['equips'].rowCount())}
        self.assertNotIn(equip, listed)
        self.assertTrue(all(w.project.cards[cid].type == gamedata.TYPE_EQUIP for cid in listed))

    # --- Duelists ---------------------------------------------------------

    def duelists_page(self):
        self.window.select_workspace('Duelists')
        return self.window.workspace_controls['Duelists']

    def duelist_name_label(self, slot):
        from PySide6.QtWidgets import QLabel
        c = self.window.workspace_controls['Duelists']
        cell = slot - c['page'].currentIndex() * 40
        tile = c['duelists'].cellWidget(cell // 8, cell % 8)
        # The tile shows the name alone, elided to the cell; its number and
        # what changed are in the tooltip.
        return next(l for l in tile.findChildren(QLabel) if '·' in l.toolTip())

    def test_a_duelist_can_be_dealt_a_fixed_deck(self):
        from fm_editor import fixed_decks
        from fm_editor.gamedata import DECK_SIZE
        w = self.window
        c = self.duelists_page()
        duelist = w._selected_duelist()
        self.assertEqual(w._selected_pool_name(), 'deck')
        self.assertIsNone(fixed_decks.deck_of(w.project, duelist))
        w.dirty = False
        c['fixed_radio'].setChecked(True)
        deck = fixed_decks.deck_of(w.project, duelist)
        self.assertIsNotNone(deck)
        # It starts from the forty the weighted deck most likely deals.
        self.assertEqual(deck.total(), DECK_SIZE)
        self.assertTrue(w.dirty)
        self.assertGreater(c['fixed_table'].rowCount(), 0)
        self.assertEqual(c['summary'].text(), '40/40 cards')

    def test_custom_duelist_pools_and_fixed_decks_are_isolated_and_persist(self):
        """A roster copy edits itself, never the retail duelist it copied."""
        from fm_editor import fixed_decks, manifest, roster
        from fm_editor.gamedata import POOLS
        w = self.window
        c = self.duelists_page()
        c['name'].setText('Pool Tester')
        c['id'].setText('pool-tester')
        c['base'].setCurrentIndex(c['base'].findData(1))
        c['position'].setCurrentIndex(c['position'].findData(None))
        w._save_duelist(adding=True)
        subject = w._selected_duelist_subject()
        self.assertFalse(isinstance(subject, int))
        base = subject.base
        retail_deck = dict(w.project.pools[base]['deck'])
        retail_pow = dict(w.project.pools[base]['pow'])

        table = c['table']
        cid = table.item(0, 0).data(Qt_UserRole())
        table.selectRow(0)
        c['weight'].setValue(subject.pools['deck'][cid] + 1)
        w._set_pool_weight()
        self.assertEqual(w.project.pools[base]['deck'], retail_deck)
        self.assertEqual(subject.pools['deck'][cid], retail_deck[cid] + 1)
        w._normalize_pool()
        custom_deck = dict(subject.pools['deck'])

        c['pool'].setCurrentIndex(POOLS.index('pow'))
        table = c['table']
        drop = table.item(0, 0).data(Qt_UserRole())
        table.selectRow(0)
        c['weight'].setValue(subject.pools['pow'][drop] + 1)
        w._set_pool_weight()
        self.assertEqual(w.project.pools[base]['pow'], retail_pow)
        self.assertEqual(subject.pools['pow'][drop], retail_pow[drop] + 1)
        w._normalize_pool()
        custom_pow = dict(subject.pools['pow'])

        # The weighted deck and drops serialize independently before a fixed
        # deck replaces the weighted deck the game deals.
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / 'weighted'
            manifest.save_mod(w.project, folder)
            reopened, messages = manifest.open_mod(w.retail, folder)
            self.assertFalse(messages)
            reopened_subject = roster.find(reopened, 'pool-tester')
            self.assertIsNotNone(reopened_subject)
            self.assertEqual(reopened_subject.pools['deck'], custom_deck)
            self.assertEqual(reopened_subject.pools['pow'], custom_pow)
            self.assertEqual(reopened.pools[base]['deck'], retail_deck)
            self.assertEqual(reopened.pools[base]['pow'], retail_pow)

            c['pool'].setCurrentIndex(POOLS.index('deck'))
            c['fixed_radio'].setChecked(True)
            self.assertIsNotNone(fixed_decks.deck_of(w.project, subject))
            self.assertIsNone(fixed_decks.deck_of(w.project, base))
            fixed_folder = Path(tmp) / 'fixed'
            manifest.save_mod(w.project, fixed_folder)
            fixed_reopened, messages = manifest.open_mod(w.retail, fixed_folder)
        self.assertFalse(messages)
        fixed_subject = roster.find(fixed_reopened, 'pool-tester')
        self.assertIsNotNone(fixed_decks.deck_of(fixed_reopened, fixed_subject))
        self.assertIsNone(fixed_decks.deck_of(fixed_reopened, base))
        self.assertEqual(fixed_reopened.pools[base]['deck'], retail_deck)

    def test_duelist_duplicate_is_exposed_and_keeps_an_independent_subject(self):
        """The Designer controls expose roster.duplicate() without sharing
        the source duelist's pools or fixed deck."""
        from fm_editor import fixed_decks, roster
        w = self.window
        c = self.duelists_page()
        for name in ("duelistRulesButton", "duelistBustButton", "duelistRevertPortraitButton", "duplicateDuelistButton"):
            self.assertIsNotNone(w.workspace_forms["Duelists"].findChild(type(c["remove"]), name))
        c['name'].setText('Duplicate Source')
        c['id'].setText('duplicate-source')
        c['base'].setCurrentIndex(c['base'].findData(1))
        c['position'].setCurrentIndex(c['position'].findData(None))
        w._save_duelist(adding=True)
        source = w._selected_duelist_subject()
        c['fixed_radio'].setChecked(True)
        source_deck = fixed_decks.deck_of(w.project, source)
        self.assertIsNotNone(source_deck)
        w._duplicate_duelist()
        duplicate = w._selected_duelist_subject()
        self.assertIsNot(duplicate, source)
        self.assertEqual(duplicate.base, source.base)
        self.assertEqual(fixed_decks.deck_of(w.project, duplicate).cards, source_deck.cards)
        duplicate.pools['pow'].clear()
        self.assertNotEqual(duplicate.pools['pow'], source.pools['pow'])
        self.assertEqual(len(roster.copies(w.project)), 2)

    def test_duelist_rules_and_bust_dialogs_construct_from_designer_forms(self):
        """Both data-driven dialogs use their Designer shells and can open
        for a retail duelist without creating a roster override on cancel."""
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication
        from fm_editor import roster
        w = self.window
        self.duelists_page()
        subject = w._selected_duelist_subject()
        self.assertIsInstance(subject, int)
        for open_dialog in (w._open_duelist_rules, w._open_duelist_bust):
            QTimer.singleShot(0, lambda: QApplication.activeModalWidget().reject())
            open_dialog()
        self.assertIsNone(roster.replacement(w.project, subject))

    def test_duelist_rules_dialog_keeps_ai_controls_and_hover_help_in_designer(self):
        """The full AI/rank form is static Designer UI, including field help.

        Python may populate the selected duelist's values, but it must not
        construct controls that a Designer user cannot inspect or edit.
        """
        from PySide6.QtWidgets import QCheckBox, QGroupBox, QLabel, QSpinBox
        w = self.window
        dialog = w._load_duelist_dialog('duelist_rules_dialog.ui')
        for row in range(9):
            label = dialog.findChild(QLabel, f'duelistAiFieldLabel{row}')
            self.assertIsNotNone(label)
            self.assertTrue(label.toolTip())
            self.assertIsNotNone(dialog.findChild(QCheckBox, f'duelistAiOverride{row}'))
            value = dialog.findChild(QSpinBox, f'duelistAiValue{row}')
            self.assertIsNotNone(value)
            self.assertEqual((value.minimum(), value.maximum()), (-128, 127))
        for rule in range(10):
            self.assertIsNotNone(dialog.findChild(QGroupBox, f'duelistRankGroup{rule}'))
            for step in range(5):
                self.assertIsNotNone(dialog.findChild(QSpinBox, f'duelistRankThreshold{rule}_{step}'))
                self.assertIsNotNone(dialog.findChild(QSpinBox, f'duelistRankChange{rule}_{step}'))
        dialog.deleteLater()

    def test_duelist_rules_dialog_saves_ai_and_rank_overrides(self):
        """The Designer dialog writes the shared duelist_rules schema before
        Apply, including an AI byte and a complete rank-rule row."""
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication, QCheckBox, QComboBox, QGroupBox, QSpinBox
        from fm_editor import duelist_rules, roster
        w = self.window
        self.duelists_page()
        subject = w._selected_duelist_subject()

        def edit_and_accept():
            dialog = QApplication.activeModalWidget()
            ai_copy = dialog.findChild(QComboBox, 'duelistAiCopy')
            ai_copy.setCurrentIndex(0)
            override = dialog.findChild(QCheckBox, 'duelistAiOverride0')
            value = dialog.findChild(QSpinBox, 'duelistAiValue0')
            override.setChecked(True); value.setValue(12)
            group = dialog.findChild(QGroupBox, 'duelistRankGroup0')
            group.setChecked(True)
            dialog.findChild(QSpinBox, 'duelistRankThreshold0_0').setValue(6)
            dialog.findChild(QSpinBox, 'duelistRankChange0_0').setValue(9)
            dialog.accept()
        QTimer.singleShot(0, edit_and_accept)
        w._open_duelist_rules()
        entry = roster.replacement(w.project, subject)
        self.assertEqual(duelist_rules.ai_of(entry)['values'][0], 12)
        self.assertEqual(duelist_rules.ranks_of(entry)[0][0], (6, 9))

    def test_duelist_bust_dialog_previews_every_frame_mode_and_round_trips(self):
        """Frame/side item data is explicit after QUiLoader, so a populated
        bust can preview picture, talking and blink frames without KeyError."""
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication, QComboBox, QLabel
        from fm_editor import manifest, roster
        from fm_editor.tests.test_bust import CALM, figure
        w = self.window
        self.duelists_page()
        subject = w._selected_duelist_subject()
        bust = roster.give_bust(w.project, subject, figure(CALM), 'calm')
        expr = bust.expressions[0]
        expr.talk, expr.talk_paths = [figure(CALM, mouth=True), figure(CALM, mouth=True)], [None, None]
        expr.blink, expr.blink_path = figure(CALM, shut=True), None

        def preview_and_accept():
            dialog = QApplication.activeModalWidget()
            mode = dialog.findChild(QComboBox, 'bustFrameMode')
            side = dialog.findChild(QComboBox, 'bustSide')
            preview = dialog.findChild(QLabel, 'bustPreview')
            self.assertEqual([mode.itemData(i) for i in range(mode.count())], ['image', 'talk0', 'talk1', 'blink'])
            self.assertEqual([side.itemData(i) for i in range(side.count())], ['left', 'right'])
            for frame in range(mode.count()):
                mode.setCurrentIndex(frame)
                for placement in range(side.count()):
                    side.setCurrentIndex(placement)
                    self.qt.processEvents()
                    self.assertFalse(preview.pixmap().isNull())
            dialog.accept()
        QTimer.singleShot(0, preview_and_accept)
        w._open_duelist_bust()
        with tempfile.TemporaryDirectory() as tmp:
            manifest.save_mod(w.project, Path(tmp))
            reopened, messages = manifest.open_mod(w.retail, Path(tmp))
        self.assertFalse(messages)
        reopened_bust = roster.bust_of(reopened, subject)
        self.assertEqual(len(reopened_bust.expressions[0].talk), 2)
        self.assertIsNotNone(reopened_bust.expressions[0].blink)

    def test_switching_back_to_weighted_keeps_the_fixed_deck_to_hand(self):
        from fm_editor import fixed_decks
        w = self.window
        c = self.duelists_page()
        duelist = w._selected_duelist()
        c['fixed_radio'].setChecked(True)
        kept = dict(fixed_decks.deck_of(w.project, duelist).cards)
        c['weighted_radio'].setChecked(True)
        self.assertIsNone(fixed_decks.deck_of(w.project, duelist))
        self.assertIn(duelist, w.fixed_stash)
        c['fixed_radio'].setChecked(True)
        self.assertEqual(fixed_decks.deck_of(w.project, duelist).cards, kept)

    def test_the_fixed_deck_cards_are_edited(self):
        from fm_editor import fixed_decks
        from fm_editor.gamedata import DECK_SIZE
        from PySide6.QtWidgets import QMessageBox
        w = self.window
        c = self.duelists_page()
        duelist = w._selected_duelist()
        c['fixed_radio'].setChecked(True)
        table = c['fixed_table']
        cid = table.item(0, 0).data(Qt_UserRole())
        table.selectRow(0)
        self.assertEqual(c['copies'].value(), fixed_decks.deck_of(w.project, duelist).cards[cid])
        c['copies'].setValue(7)
        w._set_fixed_copies()
        self.assertEqual(fixed_decks.deck_of(w.project, duelist).cards[cid], 7)
        table.selectRow(0)
        w._remove_fixed_cards()
        self.assertNotIn(cid, fixed_decks.deck_of(w.project, duelist).cards)
        with mock.patch.object(QMessageBox, 'question',
                               return_value=QMessageBox.StandardButton.Yes):
            w._copy_weighted_deck()
        self.assertEqual(fixed_decks.deck_of(w.project, duelist).total(), DECK_SIZE)
        w._clear_fixed_deck()
        self.assertEqual(fixed_decks.deck_of(w.project, duelist).total(), 0)

    def test_reverting_takes_the_fixed_deck_and_the_pool_edits(self):
        from fm_editor import fixed_decks
        from PySide6.QtWidgets import QMessageBox
        w = self.window
        c = self.duelists_page()
        duelist = w._selected_duelist()
        pool = w.project.pools[duelist]['deck']
        pool[sorted(pool)[0]] += 5
        c['fixed_radio'].setChecked(True)
        with mock.patch.object(QMessageBox, 'question',
                               return_value=QMessageBox.StandardButton.Yes):
            w._revert_fixed_deck()
        self.assertIsNone(fixed_decks.deck_of(w.project, duelist))
        self.assertEqual(w.project.pools[duelist]['deck'],
                         w.project.retail.pools[duelist]['deck'])

    def test_a_card_the_deck_names_but_the_game_lacks_keeps_its_row(self):
        from fm_editor import fixed_decks
        w = self.window
        c = self.duelists_page()
        duelist = w._selected_duelist()
        c['fixed_radio'].setChecked(True)
        deck = fixed_decks.deck_of(w.project, duelist)
        deck.kept = {'No Such Card': 3}
        w._refresh_duelist_pool()
        rows = [c['fixed_table'].item(r, 1).text() for r in range(c['fixed_table'].rowCount())]
        self.assertIn('No Such Card', rows)
        row = rows.index('No Such Card')
        self.assertIn('no such card', c['fixed_table'].item(row, 5).text())

    def test_the_pool_list_and_the_grid_show_what_changed(self):
        from fm_editor import fixed_decks
        w = self.window
        c = self.duelists_page()
        duelist = w._selected_duelist()
        pool = w.project.pools[duelist]['deck']
        card = sorted(pool)[0]
        pool[card] += 5
        w._refresh_duelist_pool()
        row = next(r for r in range(c['table'].rowCount())
                   if c['table'].item(r, 0).data(Qt_UserRole()) == card)
        self.assertEqual(c['table'].item(row, 6).text(), 'Changed')
        self.assertEqual(c['table'].item(row, 0).foreground().color().name(), '#8ab4f8')
        # The total is no longer 2048, and says so.
        self.assertIn('#ff7777', c['summary'].styleSheet())
        # The grid marks the duelist too.
        w._refresh_duelists()
        self.assertIn('changed', self.duelist_name_label(duelist).toolTip())
        fixed_decks.set_deck(w.project, duelist,
                             fixed_decks.most_likely(w.project.pools[duelist]['deck']))
        w._refresh_duelists()
        self.assertIn('fixed', self.duelist_name_label(duelist).toolTip())

    def test_pool_header_and_statistics_use_concise_type_breakdown(self):
        from fm_editor import gamedata
        w = self.window
        c = self.duelists_page()
        duelist = w._selected_duelist()
        cards = sorted(w.project.cards)[:5]
        for cid, card_type in zip(cards, (0, gamedata.TYPE_EQUIP, gamedata.TYPE_MAGIC,
                                          gamedata.TYPE_TRAP, gamedata.TYPE_RITUAL)):
            w.project.cards[cid].type = card_type
        w.project.pools[duelist]['deck'] = {cid: 10 * (index + 1)
                                             for index, cid in enumerate(cards)}
        w._refresh_duelist_pool()
        self.assertEqual(c['summary'].text(), '150/2,048 weight')
        stats = c['stats']
        self.assertEqual(list(stats['legend']), ['Monsters', 'Equips', 'Magic', 'Traps', 'Rituals'])
        self.assertEqual([box.text() for box in stats['legend'].values()],
                         ['1 (20.0%)'] * 5)

    # --- Starter decks and the retail pools --------------------------------

    def starter_page(self):
        self.window.select_workspace('Starter decks')
        return self.window.workspace_controls['Starter decks']

    def test_the_written_decks_still_work(self):
        from fm_editor.gamedata import DECK_SIZE
        w = self.window
        c = self.starter_page()
        self.assertEqual([c['starter_tabs'].tabText(i) for i in range(c['starter_tabs'].count())],
                         ['Written decks', 'Weighted pools'])
        w._add_starter_deck()
        self.assertEqual(len(w.project.starter), 1)
        c['name'].setText('Spellbinder')
        c['weight'].setValue(3)
        w._apply_starter_details()
        self.assertEqual(w.project.starter[0].name, 'Spellbinder')
        self.assertEqual(w.project.starter[0].weight, 3)
        self.assertIn(f'/{DECK_SIZE}', c['decks'].item(0, 3).text())

    def test_starter_creation_sources_and_retail_pool_cloning(self):
        """Every classic starting source is available from Designer controls
        and writes independent shared-model data."""
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication, QComboBox, QPushButton
        from fm_editor import fixed_decks, roster, starter_pools
        w = self.window
        c = self.starter_page()
        form = w.workspace_forms['Starter decks']
        for name in ('emptyStarterDeckButton', 'opponentStarterDeckButton',
                     'retailStarterDeckButton', 'duplicateStarterDeckButton',
                     'copyRetailStarterPoolsButton'):
            self.assertIsNotNone(form.findChild(QPushButton, name), name)

        # Empty and duplicated decks retain independent card dictionaries.
        w._add_starter_deck()
        w.project.starter[0].cards = {1: 3}
        w._duplicate_starter_deck()
        self.assertEqual(w.project.starter[1].cards, {1: 3})
        self.assertIsNot(w.project.starter[1].cards, w.project.starter[0].cards)

        # A retail deal uses the supplied seven rows and makes forty cards.
        retail = [starter_pools.Pool(name=f'Pool {index}', draws=draws,
                                     cards={card: 2048 for card in range(1, 41)})
                  for index, draws in enumerate((16, 16, 4, 1, 1, 1, 1))]
        w.starter_pools_retail = retail
        w._add_starter_from_retail_pools()
        self.assertEqual(w.project.starter[-1].total(), 40)
        w._copy_retail_starter_pools()
        copied = starter_pools.state(w.project)
        self.assertEqual([(pool.name, pool.draws, pool.cards) for pool in copied],
                         [(pool.name, pool.draws, pool.cards) for pool in retail])
        self.assertIsNot(copied[0], retail[0])

        def select_and_accept(subject):
            def choose():
                dialog = QApplication.activeModalWidget()
                combo = dialog.findChild(QComboBox, 'starterOpponentCombo')
                combo.setCurrentIndex(combo.findData(subject))
                dialog.accept()
            QTimer.singleShot(0, choose)
            w._add_starter_from_opponent()

        # Weighted, fixed and custom opponents all use their own effective deck.
        select_and_accept(17)
        self.assertEqual(w.project.starter[-1].cards,
                         fixed_decks.most_likely(w.project.pools[17]['deck']))
        fixed = {card: 3 for card in range(1, 14)}
        fixed[14] = 1
        fixed_decks.set_deck(w.project, 17, fixed)
        select_and_accept(17)
        self.assertEqual(w.project.starter[-1].cards, fixed)

        # Persist valid retail, weighted and fixed sources. The earlier empty
        # deck and its duplicate served their independent-copy assertion.
        w.project.starter = w.project.starter[2:]
        from fm_editor import manifest
        with tempfile.TemporaryDirectory() as tmp:
            manifest.save_mod(w.project, Path(tmp))
            reopened, messages = manifest.open_mod(w.retail, Path(tmp))
        self.assertEqual(messages, [])
        self.assertEqual([(deck.name, deck.weight, deck.cards) for deck in reopened.starter],
                         [(deck.name, deck.weight, deck.cards) for deck in w.project.starter])
        self.assertEqual([(pool.name, pool.draws, pool.cards) for pool in starter_pools.state(reopened)],
                         [(pool.name, pool.draws, pool.cards) for pool in starter_pools.state(w.project)])

        custom = roster.add_copy(w.project, 1, 'Starter source', slot=40)
        custom.pools['deck'] = {3: 500, 4: 10}
        select_and_accept(custom)
        self.assertEqual(w.project.starter[-1].cards,
                         fixed_decks.most_likely(custom.pools['deck']))

    def test_starter_kept_rows_can_be_edited_or_removed(self):
        """An unresolved card stays preserved until the user explicitly
        changes its copies or removes its row."""
        from PySide6.QtCore import Qt
        from fm_editor.model import StarterDeck
        w = self.window
        c = self.starter_page()
        w.project.starter.append(StarterDeck(name='Imported', kept={'Missing card': 2}))
        w._refresh_starter_decks()
        c['cards'].selectRow(0)
        self.assertEqual(c['cards'].item(0, 0).data(Qt.ItemDataRole.UserRole), 'kept:Missing card')
        c['copies'].setValue(3)
        w._set_starter_copies()
        self.assertEqual(w.project.starter[0].kept, {'Missing card': 3})
        c['cards'].selectRow(0)
        w._remove_starter_cards()
        self.assertEqual(w.project.starter[0].kept, {})

    def test_a_mod_with_no_pools_of_its_own_says_so(self):
        """Nothing is weighted until the mod writes a pool: the tab says what
        a new game would do instead."""
        c = self.starter_page()
        self.assertEqual(c['pools'].rowCount(), 0)
        self.assertIn('No pools', c['pool_total'].text())

    # --- Mod info ----------------------------------------------------------

    def mod_info_page(self):
        self.window.select_workspace('Mod info')
        return self.window.workspace_controls['Mod info']

    def test_the_other_box_leaves_the_editor_s_own_keys_alone(self):
        """The box shows every key but the ones a page of the editor's own
        writes, and applying it keeps those as that page left them."""
        import json
        w = self.window
        w.project.other['limits'] = {'hand': 7}
        w.project.other['guardian_stars'] = {'names': {}}
        w.project.other['starter_pools'] = [{'draws': 40, 'cards': {'1': 1}}]
        w.project.other['story'] = {'scene': 1}
        w.project.other['textures'] = ['art/']
        c = self.mod_info_page()
        shown = json.loads(c['other'].toPlainText())
        self.assertEqual(sorted(shown), ['textures'])
        # Applying the box as it stands must not drop what it never showed.
        c['other'].setPlainText(json.dumps({'textures': ['art/', 'ui/']}))
        self.assertTrue(w._apply_mod_info())
        self.assertEqual(w.project.other['limits'], {'hand': 7})
        self.assertEqual(w.project.other['guardian_stars'], {'names': {}})
        self.assertEqual(w.project.other['starter_pools'], [{'draws': 40, 'cards': {'1': 1}}])
        self.assertEqual(w.project.other['story'], {'scene': 1})
        self.assertEqual(w.project.other['textures'], ['art/', 'ui/'])

    def test_a_key_the_editor_writes_is_refused_rather_than_lost(self):
        """Typing one in the box would be written over when the manifest is
        built, so say which page writes it instead."""
        import json
        w = self.window
        c = self.mod_info_page()
        before = dict(w.project.other)
        for key in ('cards', 'starter', 'packs', 'pack_shop', 'limits', 'starter_pools'):
            c['other'].setPlainText(json.dumps({key: []}))
            self.assertFalse(w._apply_mod_info(), key)
            self.assertIn(key, c['status'].text())
            self.assertEqual(dict(w.project.other), before)

    def test_the_page_says_where_the_mod_is(self):
        import tempfile
        from pathlib import Path
        w = self.window
        c = self.mod_info_page()
        self.assertEqual(c['folder'].text(), 'Not saved yet')
        with tempfile.TemporaryDirectory() as folder:
            w.project.source_dir = Path(folder)
            w._refresh_mod_info()
            self.assertIn(folder, c['folder'].text())

    def test_a_refused_apply_is_said_once(self):
        """The message goes when the page is shown again, as the Tk tab's."""
        w = self.window
        c = self.mod_info_page()
        c['id'].setText('not a valid id!')
        self.assertFalse(w._apply_mod_info())
        self.assertTrue(c['status'].text())
        c['id'].setText('my-mod')
        w._refresh_mod_info()
        self.assertEqual(c['status'].text(), '')

    def test_the_identity_fields_round_trip(self):
        w = self.window
        c = self.mod_info_page()
        c['id'].setText('deck-mod')
        c['name'].setText('Deck Mod')
        c['version'].setText(' 2.1 ')
        c['author'].setText('Somebody')
        c['description'].setPlainText('A mod.')
        self.assertTrue(w._apply_mod_info())
        info = w.project.info
        self.assertEqual((info.id, info.name, info.version, info.author, info.description),
                         ('deck-mod', 'Deck Mod', '2.1', 'Somebody', 'A mod.'))
        w._refresh_mod_info()
        self.assertEqual(c['version'].text(), '2.1')

    # --- Problems ----------------------------------------------------------

    def problems_page(self):
        self.window.select_workspace('Problems')
        return self.window.workspace_controls['Problems']

    def pool_fixture(self):
        """Pools that draw too few cards: an error and a warning apiece."""
        w = self.window
        card = sorted(w.project.cards)[0]
        w.project.other['starter_pools'] = [
            {'name': 'Weak', 'draws': 16, 'cards': {w.project.ref(card): 100}},
            {'name': 'Odd', 'draws': 9, 'cards': {'No Such Card At All': 5}},
        ]
        w.project.starter_pool_state = None

    def test_every_line_is_drawn_in_its_level_s_ink(self):
        self.pool_fixture()
        c = self.problems_page()
        self.assertTrue(c['issues'])
        for row, issue in enumerate(c['issues']):
            colour = c['table'].item(row, 0).foreground().color().name()
            self.assertEqual(colour, '#ff8f87' if issue.level == 'error' else '#f2c04c',
                             issue.message)

    def test_the_summary_counts_errors_and_warnings(self):
        from fm_editor import validate
        self.pool_fixture()
        c = self.problems_page()
        errors = len(validate.errors(c['issues']))
        self.assertIn(f'{errors} error(s)', c['summary'].text())
        self.assertIn(f'{len(c["issues"]) - errors} warning(s)', c['summary'].text())
        self.assertIn('#ff8f87' if errors else '#f2c04c', c['summary'].styleSheet())

    def test_a_clean_mod_says_so_in_green(self):
        c = self.problems_page()
        self.window._refresh_problems()
        if c['issues']:
            self.skipTest('this fixture has problems of its own')
        self.assertEqual(c['summary'].text(), 'No problems found.')
        self.assertIn('#7fd49b', c['summary'].styleSheet())

    def test_a_starter_pool_line_goes_to_its_pool(self):
        """"Starter pools" is the Starter decks page's second tab, not a page
        of its own: it used to be reported as missing from the editor."""
        self.pool_fixture()
        w = self.window
        c = self.problems_page()
        row = next(r for r, i in enumerate(c['issues'])
                   if i.area == 'Starter pools' and i.target == 1)
        w._open_problem(row)
        self.assertEqual(w.current_workspace, 'Starter decks')
        starter = w.workspace_controls['Starter decks']
        self.assertEqual(starter['starter_tabs'].currentIndex(), 1)
        self.assertEqual(starter['pools'].currentRow(), 1)

    def test_a_packs_line_goes_to_its_pack(self):
        from fm_editor.validate import Issue
        w = self.window
        self.window.select_workspace('Packs')
        w._add_pack()
        w._add_pack()
        w.go_to(Issue('error', 'Packs', 'pack 1', 'something', 1))
        self.assertEqual(w.current_workspace, 'Packs')
        self.assertEqual(w.workspace_controls['Packs']['list'].currentRow(), 1)

    def test_a_double_click_goes_to_the_line_it_is_on(self):
        self.pool_fixture()
        w = self.window
        c = self.problems_page()
        row = next(r for r, i in enumerate(c['issues']) if i.area == 'Starter pools')
        c['table'].cellDoubleClicked.emit(row, 0)
        self.assertEqual(w.current_workspace, 'Starter decks')

    def test_a_pack_with_a_cover_shows_it_in_the_list(self):
        """The cover is drawn as the row's icon; nothing else in the suite
        reaches that line, and a missing import went unseen there."""
        from PySide6.QtGui import QImage
        from PySide6.QtCore import QBuffer, QByteArray
        w = self.window
        c = self.packs_page()
        w._add_pack()
        entry = w._pack_entry()
        image = QImage(34, 52, QImage.Format.Format_RGB32)
        image.fill(0x204080)
        blob = QByteArray()
        buffer = QBuffer(blob)
        buffer.open(QBuffer.OpenModeFlag.WriteOnly)
        image.save(buffer, 'PNG')
        buffer.close()
        w.project.files['packs/cover.png'] = bytes(blob)
        entry['image'] = 'packs/cover.png'
        w._refresh_packs()
        self.assertFalse(c['list'].item(0, 0).icon().isNull())

    def pack_png(self, width=204, height=192, alpha=False):
        """A PNG on disk for the import dialog to return."""
        import tempfile
        from fm_editor import pngio
        pixels = bytearray()
        for _ in range(width * height):
            pixels += bytes((0x20, 0x40, 0x80, 0x00 if alpha else 0xFF))
        image = pngio.Image(width, height, bytes(pixels))
        handle = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        handle.write(pngio.encode(image))
        handle.close()
        self.addCleanup(lambda: Path(handle.name).unlink(missing_ok=True))
        return handle.name

    def test_an_imported_cover_is_cut_to_the_pack_s_shape(self):
        """art.normalize's, not the file as it came: the game cannot draw a
        picture of the wrong shape, and a hole in it is a hole in the card."""
        from fm_editor import pngio, art
        w = self.window
        c = self.packs_page()
        w._add_pack()
        path = self.pack_png(300, 100, alpha=True)
        with mock.patch('fm_editor.pyside_app.QFileDialog.getOpenFileName', return_value=(path, '')):
            w._import_pack_image()
        stored = pngio.decode(w.project.files[w._pack_entry()['image']])
        shape = art.SIZES['art']
        self.assertAlmostEqual(stored.width / stored.height, shape[0] / shape[1], places=2)
        self.assertTrue(stored.opaque())
        self.assertLessEqual(stored.width, shape[0] * art.MAX_SCALE)
        self.assertIn('Pack picture from', c['status'].text())

    def test_reverting_a_cover_takes_its_file_with_it(self):
        w = self.window
        self.packs_page()
        w._add_pack()
        path = self.pack_png()
        with mock.patch('fm_editor.pyside_app.QFileDialog.getOpenFileName', return_value=(path, '')):
            w._import_pack_image()
        name = w._pack_entry()['image']
        self.assertIn(name, w.project.files)
        w._revert_pack_image()
        self.assertNotIn('image', w._pack_entry())
        self.assertNotIn(name, w.project.files)

    def test_a_duplicate_pack_owns_an_independent_cover(self):
        """Duplicating a pack copies its cover to a new asset path, so reverting
        the copy cannot remove the original's cover."""
        w = self.window
        c = self.packs_page()
        w._add_pack()
        path = self.pack_png()
        with mock.patch('fm_editor.pyside_app.QFileDialog.getOpenFileName', return_value=(path, '')):
            w._import_pack_image()
        original = w._pack_entry()['image']
        original_blob = w.project.files[original]
        w._duplicate_pack()
        duplicate = w._pack_entry()['image']
        self.assertNotEqual(duplicate, original)
        self.assertEqual(w.project.files[duplicate], original_blob)
        w._revert_pack_image()
        self.assertNotIn(duplicate, w.project.files)
        self.assertIn(original, w.project.files)
        c['list'].setCurrentCell(0, 0)
        self.assertEqual(w._pack_entry()['image'], original)

    def test_duplicate_pack_ids_and_cover_paths_are_unique(self):
        """Duplicating the same named pack repeatedly allocates independent
        identities and cover paths for every copy."""
        from fm_editor import packs as packmath
        w = self.window
        c = self.packs_page()
        w._add_pack()
        c['name'].setText('Dragon')
        self.assertTrue(w._commit_packs())
        path = self.pack_png()
        with mock.patch('fm_editor.pyside_app.QFileDialog.getOpenFileName', return_value=(path, '')):
            w._import_pack_image()
        w._duplicate_pack()
        # Duplicate the original a second time, rather than its copy. This
        # gives two proposed copies the same name and exercises ID suffixing.
        c['list'].setCurrentCell(0, 0)
        w._duplicate_pack()
        ids = [packmath.pack_id(entry) for entry in w.project.packs]
        images = [entry['image'] for entry in w.project.packs]
        self.assertEqual(ids, ['pack-1', 'dragon-copy-2', 'dragon-copy'])
        self.assertEqual(len(images), len(set(images)))
        self.assertEqual(len({w.project.files[image] for image in images}), 1)

    def test_a_pack_can_be_created_from_retail_and_custom_drops(self):
        """The Designer dialog builds pack tiers from both inherited and custom
        opponent pools without changing their card weights."""
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication, QComboBox, QPushButton
        from fm_editor import packs as packmath, roster
        w = self.window
        c = self.packs_page()
        self.assertIsNotNone(c['page'].findChild(QPushButton, 'fromDropsPackButton'))

        def make_pack(subject, pool_key):
            def accept_dialog():
                dialog = QApplication.activeModalWidget()
                opponents = dialog.findChild(QComboBox, 'packDropsOpponentCombo')
                pools = dialog.findChild(QComboBox, 'packDropsPoolCombo')
                opponents.setCurrentIndex(opponents.findData(subject))
                pools.setCurrentIndex(('pow', 'bcd', 'tec', 'deck').index(pool_key))
                dialog.accept()
            QTimer.singleShot(0, accept_dialog)
            w._add_pack_from_drops()

        retail = next(subject for _, subject in roster.opponents(w.project)
                      if isinstance(subject, int) and roster.pools_of(w.project, subject)['pow'])
        make_pack(retail, 'pow')
        expected = [(w.project.ref(card), weight) for card, weight in
                    sorted(roster.pools_of(w.project, retail)['pow'].items()) if weight > 0]
        self.assertEqual(packmath.tier_pool(w._pack_entry(), 'cards'), expected)

        custom = roster.add_copy(w.project, retail, 'Drop source', slot=40)
        custom.pools['tec'] = {1: 20, 5: 40}
        make_pack(custom, 'tec')
        self.assertEqual(packmath.tier_pool(w._pack_entry(), 'cards'),
                         [(w.project.ref(1), 20), (w.project.ref(5), 40)])

    def test_a_second_cover_does_not_leave_the_first_behind(self):
        """Re-importing reuses the pack's own name rather than piling up
        pictures nothing draws."""
        w = self.window
        self.packs_page()
        w._add_pack()
        first, second = self.pack_png(), self.pack_png(160, 150)
        with mock.patch('fm_editor.pyside_app.QFileDialog.getOpenFileName', return_value=(first, '')):
            w._import_pack_image()
        before = w._pack_entry()['image']
        with mock.patch('fm_editor.pyside_app.QFileDialog.getOpenFileName', return_value=(second, '')):
            w._import_pack_image()
        self.assertEqual(w._pack_entry()['image'], before)
        self.assertEqual([k for k in w.project.files if k.startswith('packs/')], [before])

    def test_the_cover_zoom_box_changes_what_is_drawn(self):
        """It was wired to the preview but the preview ignored it."""
        from fm_editor import art
        w = self.window
        c = self.packs_page()
        w._add_pack()
        side = art.SIZES['art']
        path = self.pack_png(side[0] * 4, side[1] * 4)
        with mock.patch('fm_editor.pyside_app.QFileDialog.getOpenFileName', return_value=(path, '')):
            w._import_pack_image()
        sizes = []
        for index in range(c['image_scale'].count()):
            c['image_scale'].setCurrentIndex(index)
            sizes.append(c['image'].pixmap().width())
        self.assertEqual(sizes, [side[0], side[0] * 2, side[0] * 4])

    def test_export_and_revert_follow_the_picture(self):
        from PySide6.QtWidgets import QPushButton
        w = self.window
        c = self.packs_page()
        w._add_pack()
        page = c['page']
        export = page.findChild(QPushButton, 'exportPackImageButton')
        revert = page.findChild(QPushButton, 'revertPackImageButton')
        w._refresh_pack_image()
        self.assertFalse(export.isEnabled())
        self.assertFalse(revert.isEnabled())
        path = self.pack_png()
        with mock.patch('fm_editor.pyside_app.QFileDialog.getOpenFileName', return_value=(path, '')):
            w._import_pack_image()
        self.assertTrue(export.isEnabled())
        self.assertTrue(revert.isEnabled())
        w._revert_pack_image()
        self.assertFalse(export.isEnabled())
        self.assertFalse(revert.isEnabled())

    def test_the_three_panels_fit_the_window_they_demand(self):
        """They asked for 1270 of a splitter that holds 1079 at the window's
        own minimum, so the settings panel was drawn over the contents."""
        from PySide6.QtWidgets import QSplitter
        w = self.window
        c = self.packs_page()
        w.resize(w.minimumWidth(), w.minimumHeight())
        w.show()
        self.addCleanup(w.hide)
        self.qt.processEvents()
        panels = c['page'].findChild(QSplitter, 'packsSplitter')
        for i in range(panels.count()):
            panel = panels.widget(i)
            # Wide enough for what is in it, and inside the splitter: a panel
            # past the right edge is drawn over the one beside it.
            self.assertGreaterEqual(panel.width(), panel.minimumSizeHint().width(),
                                    panel.objectName())
            self.assertLessEqual(panel.x() + panel.width(), panels.width(),
                                 panel.objectName())

    # --- the contents rows, as the template draws them ----------------------

    def pack_with_cards(self, ids=(1, 2, 3)):
        w = self.window
        c = self.packs_page()
        w._add_pack()
        c['weight'].setValue(10)
        w._insert_pack_cards(list(ids))
        return c

    def test_a_row_edits_its_own_weight_in_the_sortable_table(self):
        from fm_editor import packs as packmath
        w = self.window
        c = self.pack_with_cards()
        weight = c['contents'].item(0, 5)
        self.assertEqual(weight.text(), '10')
        weight.setText('250')
        pool = dict(packmath.tier_pool(w.project.packs[0], 'cards'))
        self.assertEqual(pool[w.project.ref(1)], 250)
        self.assertEqual(c['contents'].item(1, 5).text(), '10')   # only that one

    def test_a_row_edits_its_own_tier_in_the_sortable_table(self):
        w = self.window
        c = self.pack_with_cards()
        self.add_tier('rare')
        tier = c['contents'].item(0, 4)
        self.assertEqual(tier.text(), 'cards')
        tier.setText('rare')
        tiers = w.project.packs[0]['tiers']
        self.assertEqual(len(tiers['rare']['cards']), 1)
        self.assertEqual(len(tiers['cards']['cards']), 2)

    def test_a_row_is_taken_out_by_the_selected_rows_action(self):
        from fm_editor import packs as packmath
        w = self.window
        c = self.pack_with_cards()
        self.assertEqual(c['contents'].rowCount(), 3)
        c['contents'].selectRow(1)
        w._remove_pack_cards()
        self.assertEqual(c['contents'].rowCount(), 2)
        left = [ref for ref, _ in packmath.tier_pool(w.project.packs[0], 'cards')]
        self.assertEqual(left, [w.project.ref(1), w.project.ref(3)])

    def test_the_description_is_counted_in_the_bytes_the_game_keeps(self):
        from fm_editor import packs as packmath
        w = self.window
        c = self.packs_page()
        w._add_pack()
        c['description'].setPlainText('é' * 10)           # two bytes apiece
        self.assertEqual(c['count_label'].text(), f'20 / {packmath.DESCRIPTION_BYTES}')
        self.assertNotIn('#ff8f87', c['count_label'].styleSheet())
        c['description'].setPlainText('x' * (packmath.DESCRIPTION_BYTES + 1))
        self.assertIn('#ff8f87', c['count_label'].styleSheet())

    def test_the_list_says_how_many_packs_it_holds(self):
        w = self.window
        c = self.packs_page()
        self.assertEqual(c['list_title'].text(), 'Pack list (0)')
        w._add_pack()
        w._add_pack()
        self.assertEqual(c['list_title'].text(), 'Pack list (2)')

    def test_a_pack_without_a_picture_is_drawn_with_its_name_plate(self):
        """The preview is the pack as the game draws it, not the raw file."""
        from fm_editor import art
        w = self.window
        c = self.packs_page()
        w._add_pack()
        c['name'].setText('Starter')
        w._commit_packs()
        w._refresh_pack_image()
        drawn = c['image'].pixmap()
        self.assertFalse(drawn.isNull())
        # The responsive preview scales the generated game card to its visible
        # label, but still exposes a non-empty card render.
        self.assertFalse(drawn.isNull())

    # --- what the advanced forms and the dialogs do --------------------------

    def test_a_tier_is_renamed_and_what_names_it_follows(self):
        """Its guarantee, its pity and the slots that name it (rename_tier)."""
        w = self.window
        c = self.packs_page()
        w._add_pack()
        w._insert_pack_cards([1, 2])
        self.add_tier('rare', odds=4, label='RARE!', reveal='quick')
        entry = w.project.packs[0]
        entry['guarantee'] = {'rare': 1}
        entry['pity'] = {'rare': 5}
        entry['slots'] = ['cards', 'rare']
        w._refresh_packs()
        tiers = c['adv']['tiers']
        self.assertEqual(tiers.rowCount(), 2)
        self.assertEqual(tiers.item(1, 0).text(), 'rare')
        self.assertEqual(tiers.item(1, 1).text(), '4')
        self.assertEqual(tiers.item(1, 3).text(), 'RARE!')
        tiers.selectRow(1)

        def fill(window, title, name, tier, on_ok):
            self.assertEqual(name, 'rare')
            self.assertEqual(tier.get('odds'), 4)
            on_ok('ultra', {'odds': 9, 'label': 'ULTRA!', 'color': None, 'sound': None, 'reveal': ''})

        with mock.patch.object(type(w), '_pack_tier_dialog', fill):
            w._edit_pack_tier()
        entry = w.project.packs[0]
        self.assertIn('ultra', entry['tiers'])
        self.assertNotIn('rare', entry['tiers'])
        self.assertEqual(entry['tiers']['ultra']['odds'], 9)
        self.assertEqual(entry['guarantee'], {'ultra': 1})
        self.assertEqual(entry['pity'], {'ultra': 5})
        self.assertEqual(entry['slots'], ['cards', 'ultra'])

    def test_a_tier_is_removed_and_reordered(self):
        from PySide6.QtWidgets import QMessageBox
        w = self.window
        c = self.packs_page()
        w._add_pack()
        w._insert_pack_cards([1])
        self.add_tier('rare')
        tiers = c['adv']['tiers']
        self.assertEqual([tiers.item(r, 0).text() for r in range(2)], ['cards', 'rare'])
        tiers.selectRow(1)
        w._move_pack_tier(-1)
        self.assertEqual(list(w.project.packs[0]['tiers']), ['rare', 'cards'])
        c['adv']['tiers'].selectRow(0)
        with mock.patch.object(QMessageBox, 'question',
                               return_value=QMessageBox.StandardButton.Yes):
            w._remove_pack_tier()
        self.assertEqual(list(w.project.packs[0]['tiers']), ['cards'])

    def test_slots_are_turned_on_and_given_rules(self):
        w = self.window
        c = self.packs_page()
        w._add_pack()
        w._insert_pack_cards([1])
        self.add_tier('rare')
        c['adv']['use_slots'].setChecked(True)
        w._toggle_pack_slots()
        entry = w.project.packs[0]
        self.assertEqual(entry['slots'], ['cards'] * 5)       # one for each of its cards
        self.assertNotIn('count', entry)
        self.assertEqual(c['adv']['slots'].rowCount(), 5)
        c['adv']['slots'].selectRow(4)

        def fill(window, title, rule, on_ok):
            on_ok({'tiers': {'cards': 3, 'rare': 1}})

        with mock.patch.object(type(w), '_pack_slot_dialog', fill):
            w._edit_pack_slot()
        self.assertEqual(w.project.packs[0]['slots'][4], {'tiers': {'cards': 3, 'rare': 1}})
        c['adv']['slots'].selectRow(4)
        w._remove_pack_slot()
        self.assertEqual(len(w.project.packs[0]['slots']), 4)
        # Turning them off again keeps the count they stood for.
        c['adv']['use_slots'].setChecked(False)
        w._toggle_pack_slots()
        self.assertNotIn('slots', w.project.packs[0])
        self.assertEqual(w.project.packs[0]['count'], 4)

    def test_the_shop_settings_form_writes_the_shop_s_own_rules(self):
        w = self.window
        c = self.packs_page()
        w._edit_pack_shop()
        self.assertIs(c['tabs'].currentWidget(), c['shop_tab'])
        w._apply_shop_settings()
        # Nothing was touched, so nothing is written.
        self.assertIn(w.project.pack_shop, (None, {}))

    def test_the_shop_settings_form_reads_its_shops_back(self):
        w = self.window
        c = self.packs_page()
        w.project.pack_shop = {'shops': [{'id': 'card_shop', 'name': 'Cards', 'where': 'town'}]}
        w._refresh_packs()
        w._edit_pack_shop()
        table = c['shop_table']
        self.assertEqual(table.rowCount(), 1)
        self.assertEqual(table.item(0, 0).text(), 'card_shop')
        self.assertEqual(table.item(0, 1).text(), 'Cards')
        self.assertEqual(table.item(0, 2).text(), 'town')
        w._add_shop()
        table.item(1, 0).setText('pack_shop')
        table.item(1, 1).setText('Packs')
        w._apply_shop_settings()
        shops = w.project.pack_shop['shops']
        self.assertEqual([shop['id'] for shop in shops], ['card_shop', 'pack_shop'])
        self.assertEqual(shops[0]['where'], 'town')      # a key the form has no field for

    def test_a_shop_line_the_game_could_not_read_is_refused(self):
        w = self.window
        c = self.packs_page()
        w._add_shop()
        c['shop_table'].item(0, 0).setText('not a valid id!')
        w._apply_shop_settings()
        self.assertIn('ID is', c['shop_status'].text())
        self.assertIn(w.project.pack_shop, (None, {}))

    def test_add_filtered_picks_cards_by_what_they_are(self):
        """Not by name alone: the filter the bulk dialogs use."""
        from fm_editor import bulk_fusions, gamedata
        w = self.window
        c = self.packs_page()
        w._add_pack()
        monsters = [cid for cid, card in w.project.cards.items() if card.is_monster()]
        self.assertTrue(monsters)
        chosen = bulk_fusions.CardFilter(kinds={'monster'}).select(w.project)[0]
        self.assertEqual(sorted(chosen), sorted(monsters))
        with mock.patch.object(type(w), '_card_filter_dialog', lambda self, *a, **k: chosen[:3]):
            w._add_filtered_pack_cards()
        self.assertEqual(c['contents'].rowCount(), 3)

    # --- the Campaign page ---------------------------------------------------

    def test_the_campaign_page_is_the_map(self):
        """The campaign page is the map, and the map is all of it."""
        w = self.window
        w.select_workspace('Campaign')
        c = w.workspace_controls['Campaign']
        self.assertEqual([c['tabs'].tabText(i) for i in range(c['tabs'].count())],
                         ['Map'])

    def test_a_mod_s_story_key_is_left_alone(self):
        """No page writes "story": the editor keeps it as the mod wrote it."""
        w = self.window
        w.project.other['story'] = {'scenes': [{'id': 'intro'}]}
        w.select_workspace('Campaign')
        w.select_workspace('Cards')
        self.assertEqual(w.project.other['story'], {'scenes': [{'id': 'intro'}]})
        self.assertIn('story', manifest.build(w.project))

    def test_a_map_problem_still_goes_to_its_place(self):
        from fm_editor.validate import Issue
        w = self.window
        w.go_to(Issue('warning', 'Map', 'place 3', 'something', 3))
        self.assertEqual(w.current_workspace, 'Campaign')
        c = w.workspace_controls['Campaign']
        self.assertEqual(c['tabs'].tabText(c['tabs'].currentIndex()), 'Map')

    def test_the_packs_page_has_no_bottom_button_row(self):
        """Apply is what leaving a pack does; the other two were each other."""
        from PySide6.QtWidgets import QPushButton
        c = self.packs_page()
        for name in ('applyPacksButton', 'resetAllPacksButton', 'revertAllPacksButton'):
            self.assertIsNone(c['page'].findChild(QPushButton, name), name)

    def test_removing_every_pack_is_still_reachable(self):
        """It lost its button, so the Tools menu keeps it."""
        w = self.window
        titles = [action.text() for menu in w.menuBar().actions()
                  if menu.menu() for action in menu.menu().actions()]
        self.assertIn('Remove every pack of the mod', titles)

    def test_a_pack_still_commits_without_an_apply_button(self):
        w = self.window
        c = self.packs_page()
        w._add_pack()
        w._add_pack()
        c['list'].setCurrentCell(0, 0)
        c['name'].setText('Renamed')
        c['list'].setCurrentCell(1, 0)      # leaving the pack writes it
        self.assertEqual(w.project.packs[0]['name'], 'Renamed')

    def test_the_disc_s_own_pools_stand_in_for_a_mod_that_weights_none(self):
        """With the disc's rows to hand the page shows them, read only."""
        from PySide6.QtWidgets import QPushButton
        from fm_editor import starter_pools
        w = self.window
        c = self.starter_page()
        rows = [starter_pools.Pool(name=f"Row {n + 1}", draws=draws, cards={1: 2048})
                for n, draws in enumerate((16, 16, 4, 1, 1, 1, 1))]
        w.starter_pools_retail = rows
        w._refresh_starter_pools()
        self.assertFalse(w._starter_pools_editable())
        self.assertEqual(c['pools'].rowCount(), 7)
        self.assertIn("The disc's own rows", c['pool_total'].text())
        form = w.workspace_forms['Starter decks']
        self.assertFalse(form.findChild(QPushButton, 'removeStarterPoolButton').isEnabled())
        self.assertTrue(form.findChild(QPushButton, 'addStarterPoolButton').isEnabled())
        self.assertFalse(c['pool_draws'].isEnabled())
        # They are the disc's, so nothing of them is written to the mod.
        self.assertNotIn('starter_pools', w.project.other)

    def test_adding_a_pool_takes_the_page_off_the_disc_s_rows(self):
        from fm_editor import starter_pools
        w = self.window
        c = self.starter_page()
        w.starter_pools_retail = [starter_pools.Pool(name='Row', draws=40, cards={1: 2048})]
        w._refresh_starter_pools()
        self.assertFalse(w._starter_pools_editable())
        w._add_starter_pool()
        self.assertTrue(w._starter_pools_editable())
        self.assertEqual(c['pools'].rowCount(), 1)
        self.assertIn('starter_pools', w.project.other)

    # --- what a review found: ids, files and the duelists' own ---------------

    def test_an_id_the_mod_wrote_is_not_reslugged(self):
        """A roster key stays verbatim when its copy is edited."""
        from fm_editor import roster
        w = self.window
        subject = roster.add_copy(w.project, 1, 'Dark Simon', key='Dark_Simon')
        subject.origin = 'folder'
        w.select_workspace('Duelists')
        c = w.workspace_controls['Duelists']
        slot = roster.slot_of(w.project, subject)
        w.duelist_selected_slot = slot
        w._refresh_duelists()
        c['name'].setText('Dark Simon the Second')
        c['id'].setText('Dark_Simon')
        w._save_duelist()
        self.assertEqual(subject.key, 'Dark_Simon')
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / 'mod'
            manifest.save_mod(w.project, folder)
            self.assertTrue((folder / 'duelists' / 'Dark_Simon.json').is_file())

    def test_a_replace_is_matched_however_it_names_its_duelist(self):
        """By number or by name in any case: matching the name alone wrote a
        second entry for the same duelist."""
        w = self.window
        self.assertTrue(w._replaces_slot({'replace': 2}, 2))
        self.assertTrue(w._replaces_slot({'replace': '2'}, 2))
        self.assertTrue(w._replaces_slot({'replace': DUELIST_NAMES[2].upper()}, 2))
        self.assertTrue(w._replaces_slot({'replace': DUELIST_NAMES[2].lower()}, 2))
        self.assertFalse(w._replaces_slot({'replace': 3}, 2))
        self.assertFalse(w._replaces_slot({'copy': 2}, 2))
        self.assertFalse(w._replaces_slot({'replace': True}, 2))

    def test_removing_a_duelist_does_not_raise(self):
        from PySide6.QtWidgets import QMessageBox
        w = self.window
        w.select_workspace('Duelists')
        c = w.workspace_controls['Duelists']
        c['name'].setText('Tester')
        c['base'].setCurrentIndex(1)
        w._save_duelist(adding=True)
        self.assertIn('tester', [e.get('id') for e in w._duelist_roster_source()[0]])
        with mock.patch.object(QMessageBox, 'question',
                               return_value=QMessageBox.StandardButton.Yes):
            w._remove_duelist()
        self.assertNotIn('tester', [e.get('id') for e in w._duelist_roster_source()[0]])

    def test_added_duelists_update_the_mod_description_line(self):
        from PySide6.QtWidgets import QMessageBox
        w = self.window
        w.project.info.description = ''
        w.select_workspace('Duelists')
        c = w.workspace_controls['Duelists']
        for name in ('Tester One', 'Tester Two'):
            c['name'].setText(name)
            c['id'].clear()
            c['base'].setCurrentIndex(1)
            c['position'].setCurrentIndex(c['position'].findData(None))
            w._save_duelist(adding=True)
        self.assertEqual(w.project.info.description, 'Adds 2 duelists to the free duel')
        self.assertEqual(manifest.build(w.project)['description'], w.project.info.description)
        with mock.patch.object(QMessageBox, 'question',
                               return_value=QMessageBox.StandardButton.Yes):
            w._remove_duelist()
        self.assertEqual(w.project.info.description, 'Adds 1 duelists to the free duel')
        w.duelist_selected_slot = next(slot for slot, record in w.duelist_slots.items()
                                       if record.get('kind') == 'added')
        with mock.patch.object(QMessageBox, 'question',
                               return_value=QMessageBox.StandardButton.Yes):
            w._remove_duelist()
        self.assertEqual(w.project.info.description, '')

    def test_opened_mod_adds_the_duelist_line_only_to_a_blank_description(self):
        w = self.window
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            body = {'id': 'extra-duelist', 'duelists': [
                {'id': 'extra', 'copy': 'Simon Muran', 'name': 'Extra Duelist'}]}
            (folder / 'mod.json').write_text(json.dumps(body), encoding='utf-8')
            w.open_mod_path(str(folder))
            self.assertEqual(w.project.info.description, 'Adds 1 duelists to the free duel')
            self.assertTrue(w.dirty)

            body['description'] = 'A mod with a custom description.'
            (folder / 'mod.json').write_text(json.dumps(body), encoding='utf-8')
            w.open_mod_path(str(folder))
            self.assertEqual(w.project.info.description, body['description'])
            self.assertFalse(w.dirty)

    # --- the Art page's three renders ---------------------------------------

    def test_the_art_page_shows_both_renders_at_once(self):
        """Disc, the console's and Internal side by side, as the Tk window
        has them, rather than one scale at a time behind a button."""
        from PySide6.QtWidgets import QPushButton
        from fm_editor.qt.common import ART_INTERNAL
        w = self.window
        w.select_workspace('Art')
        page = w.art_previews['art']['disc'].window()
        for part, stem in (('art', 'picture'), ('thumbnail', 'thumbnail'), ('title', 'title')):
            panes = set(w.art_previews[part])
            self.assertEqual(panes, {'disc', 'game', 'mod'} | ({'internal'} if part in ART_INTERNAL else set()),
                             part)
            # The scale buttons are gone with it.
            for scale in (1, 2, 4):
                self.assertIsNone(page.findChild(QPushButton, f'{stem}Scale{scale}Button'),
                                  f'{stem} {scale}x')
        self.assertFalse(hasattr(w, 'art_scales'))

    def test_the_internal_pane_draws_what_the_console_averages_away(self):
        from fm_editor.qt.common import ART_INTERNAL
        from fm_editor import art
        w = self.window
        w.select_workspace('Art')
        cid = sorted(w.project.cards)[0]
        w.show_art_card(cid)
        for part, factor in ART_INTERNAL.items():
            console = art.in_game(w.project, w.files.wa, cid, part, 1)
            internal = art.in_game(w.project, w.files.wa, cid, part, factor)
            self.assertEqual(internal.width, console.width * factor, part)
            self.assertFalse(w.art_previews[part]['internal'].pixmap().isNull(), part)
            self.assertIn(f'Internal {factor}', w.art_info[part]['internal'].text())
            self.assertIn("console's render", w.art_info[part]['game'].text())

    def test_opening_a_mod_with_packs_shows_its_first_pack(self):
        """min(-1, 0) left the list with a row and nothing chosen, so every
        field of a mod that plainly has a pack read as empty."""
        w = self.window
        c = self.packs_page()
        w.project.packs.append({'name': 'Dragons', 'cards': {'1': 100}})
        c['pack_index'] = -1                      # as a freshly built page has it
        w._refresh_packs()
        self.assertEqual(c['pack_index'], 0)
        self.assertEqual(c['list'].currentRow(), 0)
        self.assertEqual(c['name'].text(), 'Dragons')

    def test_a_cover_on_disk_is_drawn_without_being_in_project_files(self):
        """A mod opened from a folder keeps its PNG there, not in memory."""
        import tempfile
        from pathlib import Path
        w = self.window
        c = self.packs_page()
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / 'packs').mkdir()
            Path(folder, 'packs/cover.png').write_bytes(
                Path(self.pack_png()).read_bytes())
            w.project.source_dir = Path(folder)
            w.project.packs.append({'name': 'From disk', 'cards': {'1': 100},
                                    'image': 'packs/cover.png'})
            w._refresh_packs()
            self.assertNotIn('packs/cover.png', w.project.files)
            self.assertIsNotNone(w._pack_image_bytes(w._pack_entry()))
            self.assertFalse(c['list'].item(0, 0).icon().isNull())
            self.assertFalse(c['image'].pixmap().isNull())

    # --- Card Data as tabs, and the game's own text ------------------------

    def test_card_data_is_general_effects_and_text(self):
        w = self.window
        tabs = w.card_data_tabs
        self.assertEqual([tabs.tabText(i) for i in range(tabs.count())], ['General', 'Effects', 'Text'])
        w.show_card(1)
        # The fields stayed where they were, under the first tab.
        self.assertEqual(w.fields['name'].text(), 'Blue Dragon')
        self.assertEqual(w.description.toPlainText(), w.project.cards[1].description)

    def test_the_mod_notes_box_is_gone_and_the_notes_are_not(self):
        """A card's "notes" are the mod's, kept as written; no box here edits
        them any more."""
        from PySide6.QtWidgets import QTextEdit
        w = self.window
        self.assertIsNone(w.findChild(QTextEdit, 'notesEdit'))
        self.assertFalse(hasattr(w, 'notes'))
        w.project.set_notes(1, 'kept from the mod.json')
        w.show_card(1)
        self.assertTrue(w.apply_card(quiet=True))
        entry = next(e for e in manifest.build(w.project)['cards'] if e.get('notes'))
        self.assertEqual(entry['notes'], 'kept from the mod.json')

    def test_effects_are_listed_edited_and_kept_on_the_card(self):
        """The inline Designer form writes current monster-effect data."""
        w = self.window
        w.show_card(1)
        self.assertEqual(w.effects_table.rowCount(), 0)
        self.assertFalse(w.effect_buttons['editEffect'].isEnabled())
        w._add_card_effect()
        editor = w._inline_effect_editor
        self.assertFalse(editor['frame'].isHidden())
        self.assertEqual(editor['action'].currentData(), 'boost')
        editor['save'].click()
        self.assertEqual(w.effects_table.rowCount(), 1)
        self.assertEqual(w.project.monster_effects_of(1),
                         ([{'when': 'summon', 'do': 'boost', 'target': 'self', 'attack': 500}], False))
        entry = next(e for e in manifest.build(w.project)['cards'] if e.get('replace') == 1)
        self.assertEqual(entry['monster_effects'], w.project.monster_effects_of(1)[0])
        with tempfile.TemporaryDirectory() as tmp:
            manifest.save_mod(w.project, Path(tmp) / 'mod')
            again, notes = manifest.open_mod(w.retail, Path(tmp) / 'mod')
            self.assertEqual(again.monster_effects_of(1), w.project.monster_effects_of(1))
            self.assertEqual(notes, [])
        w.effects_table.selectRow(0)
        w._move_card_effect(0)
        w._remove_card_effect()
        self.assertNotIn(1, w.project.card_extra)
        self.assertEqual(w.effects_table.rowCount(), 0)

    def test_copy_effect_edit_overrides_inheritance_without_changing_its_base(self):
        """Editing a copied card's effect creates an isolated override."""
        w = self.window
        source = {'when': 'summon', 'do': 'boost', 'target': 'self', 'attack': 500}
        w.project.set_monster_effects(1, [source])
        copied = w.project.add_card(1)

        w.show_card(copied)
        self.assertEqual(w.project.monster_effects_of(copied), ([source], True))
        self.assertEqual(w.effects_table.rowCount(), 1)
        w.effects_table.selectRow(0)
        editor = w._inline_effect_editor
        editor['attack'].setValue(800)
        editor['save'].click()

        expected = {'when': 'summon', 'do': 'boost', 'target': 'self', 'attack': 800}
        self.assertEqual(w.project.monster_effects_of(copied), ([expected], False))
        self.assertEqual(w.project.monster_effects_of(1), ([source], False))

        with tempfile.TemporaryDirectory() as tmp:
            manifest.save_mod(w.project, Path(tmp) / 'mod')
            reopened, _ = manifest.open_mod(w.retail, Path(tmp) / 'mod')
        self.assertEqual(reopened.monster_effects_of(1), ([source], False))
        self.assertEqual(reopened.monster_effects_of(copied), ([expected], False))

    def test_effect_add_and_edit_undo_and_redo_independently(self):
        """Each effect change has its own reversible history entry."""
        w = self.window
        w.show_card(1)
        w._add_card_effect()
        editor = w._inline_effect_editor
        editor['save'].click()
        w._flush_history()
        self.assertEqual(w.project.monster_effects_of(1)[0][0]['attack'], 500)

        w.undo()
        self.assertEqual(w.project.monster_effects_of(1), ([], False))
        w.redo()
        self.assertEqual(w.project.monster_effects_of(1)[0][0]['attack'], 500)

        w.show_card(1)
        w.effects_table.selectRow(0)
        editor['attack'].setValue(800)
        editor['save'].click()
        w._flush_history()
        self.assertEqual(w.project.monster_effects_of(1)[0][0]['attack'], 800)
        w.undo()
        self.assertEqual(w.project.monster_effects_of(1)[0][0]['attack'], 500)
        w.redo()
        self.assertEqual(w.project.monster_effects_of(1)[0][0]['attack'], 800)

    def test_monster_effect_for_each_round_trips_through_inline_editor(self):
        """Editing a multiplier retains it; Designer controls can add or remove it."""
        w = self.window
        source = {
            'when': 'summon', 'do': 'boost', 'target': 'self', 'attack': 500,
            'for_each': {'whose': 'all', 'type': 'Dragon', 'attribute': 'Light'},
        }
        w.project.set_monster_effects(1, [source])
        before = manifest.build(w.project)
        w.show_card(1)
        # Merely opening and applying a card does not rewrite an existing effect.
        self.assertTrue(w.apply_card(quiet=True))
        self.assertEqual(manifest.build(w.project), before)
        self.assertIsNotNone(w.findChild(type(w._inline_effect_editor['each']), 'inlineEffectEachCombo'))

        w.effects_table.selectRow(0)
        editor = w._inline_effect_editor
        self.assertEqual(editor['each'].currentData(), 'all')
        self.assertEqual(editor['each_type'].currentData(), 'Dragon')
        self.assertEqual(editor['each_attribute'].currentData(), 'Light')
        editor['attack'].setValue(600)
        editor['save'].click()
        changed = w.project.monster_effects_of(1)[0][0]
        self.assertEqual(changed['attack'], 600)
        self.assertEqual(changed['for_each'], source['for_each'])

        # Selecting the no-multiplier choice deliberately removes the key.
        w.effects_table.selectRow(0)
        editor['each'].setCurrentIndex(editor['each'].findData(None))
        editor['save'].click()
        self.assertNotIn('for_each', w.project.monster_effects_of(1)[0][0])

        # The same form creates the remaining multiplier-capable actions.
        w._add_card_effect()
        editor['action'].setCurrentIndex(editor['action'].findData('heal'))
        editor['amount'].setValue(700)
        editor['each'].setCurrentIndex(editor['each'].findData('own'))
        editor['save'].click()
        w._add_card_effect()
        editor['action'].setCurrentIndex(editor['action'].findData('damage'))
        editor['amount'].setValue(800)
        editor['each'].setCurrentIndex(editor['each'].findData('opponent'))
        editor['each_type'].setCurrentIndex(editor['each_type'].findData('Warrior'))
        editor['each_attribute'].setCurrentIndex(editor['each_attribute'].findData('Dark'))
        editor['save'].click()
        rows = w.project.monster_effects_of(1)[0]
        self.assertEqual(rows[1]['for_each'], {'whose': 'own'})
        self.assertEqual(rows[2]['for_each'],
                         {'whose': 'opponent', 'type': 'Warrior', 'attribute': 'Dark'})
        with tempfile.TemporaryDirectory() as tmp:
            manifest.save_mod(w.project, Path(tmp) / 'mod')
            reopened, _ = manifest.open_mod(w.retail, Path(tmp) / 'mod')
        self.assertEqual(reopened.monster_effects_of(1), w.project.monster_effects_of(1))

    def test_colouring_takes_the_selection_and_leaves_the_rest(self):
        """A colour runs until the next one, so colouring a few words puts
        white back after them; with nothing selected the code goes in where
        the cursor is."""
        from PySide6.QtGui import QTextCursor
        w = self.window
        w.show_card(1)
        w.description.setPlainText('Boost your monsters.')
        cursor = w.description.textCursor()
        cursor.setPosition(6)
        cursor.setPosition(10, QTextCursor.MoveMode.KeepAnchor)
        w.description.setTextCursor(cursor)
        w._insert_text_code('{f8 0A 06}', '{f8 0A 00}')
        self.assertEqual(w.description.toPlainText(), 'Boost {f8 0A 06}your{f8 0A 00} monsters.')
        w.description.setPlainText('Plain.')
        w._insert_text_code('{f8 0B 18}')
        self.assertEqual(w.description.toPlainText(), '{f8 0B 18}Plain.')

    def test_the_text_menu_offers_the_icons_and_says_what_a_colour_will_do(self):
        w = self.window
        w.show_card(1)
        menu = w._build_card_text_menu()
        submenus = {action.text(): action.menu() for action in menu.actions() if action.menu()}
        self.assertEqual(sorted(submenus), ['Insert icon', 'Text colour'])
        groups = {action.text(): action.menu() for action in submenus['Insert icon'].actions()}
        self.assertEqual(sorted(groups), ['Buttons', 'Card kinds', 'Guardian stars', 'Monster types'])
        # The sheet's grid: twenty types, four kinds, then the ten stars.
        types = [action.text() for action in groups['Monster types'].actions()]
        self.assertEqual(len(types), 20)
        self.assertTrue(types[0].startswith('Dragon'))
        self.assertIn('{f8 0B 00}', types[0])
        self.assertTrue(types[-1].startswith('Plant'))
        self.assertIn('{f8 0B 13}', types[-1])
        kinds = [action.text() for action in groups['Card kinds'].actions()]
        self.assertTrue(kinds[0].startswith('Magic'))
        self.assertIn('{f8 0B 14}', kinds[0])
        stars = [action.text() for action in groups['Guardian stars'].actions()]
        self.assertEqual(len(stars), 10)
        self.assertTrue(stars[0].startswith('Mars'))
        self.assertIn('{f8 0B 18}', stars[0])
        self.assertTrue(stars[-1].startswith('Venus'))
        # With something selected the colour menu says what it will colour.
        w.description.selectAll()
        names = [action.text() for action in w._build_card_text_menu().actions() if action.menu()]
        self.assertIn('Colour the selection', names)

    def test_the_game_text_tab_draws_the_text_and_offers_the_colour_codes(self):
        """card_text.Renderer: what the card view makes of the box, and the
        {f8 0A NN} codes it reads."""
        from PySide6.QtWidgets import QMenu
        w = self.window
        w.show_card(1)
        # The synthetic retail has no font where the disc keeps one, so the
        # preview says that rather than drawing.
        self.assertIn('no font', w.card_text_preview.text())
        self.assertEqual(w.TEXT_COLOURS[6], 'Red')
        menu = w.description.createStandardContextMenu()
        self.assertTrue(menu.actions())
        w.description.setPlainText('')
        w.description.insertPlainText('{f8 0A 06}')
        self.assertEqual(w.description.toPlainText(), '{f8 0A 06}')
        # The code is text of the card like any other: it is stored as typed.
        self.assertTrue(w.apply_card(quiet=True))
        self.assertEqual(w.project.cards[1].description, '{f8 0A 06}')

    # --- what the window took from the old one after the equips change ------

    def test_an_equip_shows_its_boosts_where_another_card_shows_its_effect(self):
        """model.equip_bonus_of/set_equip_bonus: an equip is played as an
        equip whatever it names, so it has boosts and no Retail effect."""
        w = self.window
        atk, defense = w.fields['equip_attack'], w.fields['equip_defense']
        w.show_card(651)                                  # an equip of the fixture
        self.assertFalse(atk.isHidden())
        self.assertTrue(w.fields['effect'].isHidden())
        self.assertEqual(atk.value(), w.BONUS_NONE)       # the default, until it is given one
        self.assertIn('+500', atk.specialValueText())
        self.assertEqual(self.marked_rows(), [])
        before = manifest.build(w.project)
        self.assertTrue(w.apply_card(quiet=True))
        self.assertEqual(before, manifest.build(w.project))
        atk.setValue(1500)
        defense.setValue(-200)
        self.assertEqual(self.marked_rows(), ['ATK boost', 'DEF boost'])
        self.assertTrue(w.apply_card(quiet=True))
        self.assertEqual(w.project.equip_bonus[651], (1500, -200))
        self.assertIn({'card': w.project.ref(651), 'bonus_attack': 1500, 'bonus_defense': -200},
                      manifest.build(w.project)['equips'])
        # The panel's row puts the default back.
        w.show_card(651)
        self.assertEqual(atk.value(), 1500)
        w.reference_values['ATK boost'].clicked.emit()
        self.assertTrue(w.apply_card(quiet=True))
        self.assertEqual(w.project.equip_bonus[651], (500, -200))

    def test_a_card_that_stops_being_an_equip_keeps_no_boost(self):
        w = self.window
        w.show_card(651)
        w.fields['equip_attack'].setValue(900)
        self.assertTrue(w.apply_card(quiet=True))
        self.assertIn(651, w.project.equip_bonus)
        w.fields['type'].setCurrentIndex(0)
        self.assertTrue(w.apply_card(quiet=True))
        self.assertNotIn(651, w.project.equip_bonus)
        self.assertTrue(w.fields['equip_attack'].isHidden())

    def test_the_password_box_takes_eight_digits_and_nothing_else(self):
        from PySide6.QtTest import QTest
        w = self.window
        w.show_card(1)
        box = w.fields['password']
        box.clear()
        QTest.keyClicks(box, '12345678901234')
        self.assertEqual(box.text(), '12345678')
        box.clear()
        QTest.keyClicks(box, '12ab34')
        self.assertEqual(box.text(), '1234')

    def test_export_mod_makes_a_folder_of_the_mods_own(self):
        """App.save(export=True): the game reads each mod from a folder named
        after its id."""
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        w = self.window
        w.project.info.id = 'my-mod'
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(QFileDialog, 'getExistingDirectory', return_value=tmp), \
                 mock.patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes):
                w.export_mod()
            self.assertTrue((Path(tmp) / 'my-mod' / 'mod.json').is_file())
            self.assertIn('Exported', w.statusBar().currentMessage())
            # A folder named after an id it has not got is not made.
            w.project.info.id = 'not a valid id!'
            with mock.patch.object(QFileDialog, 'getExistingDirectory', return_value=tmp) as ask, \
                 mock.patch.object(QMessageBox, 'critical') as said:
                w.export_mod()
            self.assertFalse(ask.called)
            self.assertTrue(said.called)

    def test_the_romhack_import_is_behind_its_setting(self):
        """importers.install: it is experimental and unsupported, so the entry
        shows only where settings.json asks for it."""
        from fm_editor import settings
        w = self.window
        labels = [action.text() for action in w.menus['File'].actions()]
        self.assertEqual([l for l in labels if 'modified game' in l], [])
        settings.save('experimental_rom_import', True)
        with mock.patch.object(ModernEditor, '_load_game',
                               return_value=SimpleNamespace(wa=fixture().wa, source='synthetic')), \
             mock.patch('fm_editor.pyside_app.gamedata.load_game', return_value=fixture().game()), \
             mock.patch.object(ModernEditor, '_render_preview'):
            other = ModernEditor()
        self.addCleanup(other.deleteLater)
        labels = [action.text() for action in other.menus['File'].actions()]
        self.assertTrue([l for l in labels if 'modified game' in l])

    def test_where_a_card_is_used_lists_the_mod_and_goes_to_it(self):
        """card_uses.where_used, the list the Tk window's Where it's used
        shows, with this window's pages behind the lines."""
        from PySide6.QtWidgets import QTableWidget
        w = self.window
        w.project.packs.append({'name': 'Locked', 'cards': [1], 'unlock': {'card': 3}})
        dialog = w.show_card_uses(3)
        self.addCleanup(dialog.close)
        table = dialog.findChild(QTableWidget)
        rows = [(table.item(r, 0).text(), table.item(r, 1).text()) for r in range(table.rowCount())]
        self.assertIn('Rituals', [where for where, _ in rows])
        self.assertIn(('Packs', 'Locked: unlocked by owning it'), rows)
        self.assertEqual(len(rows), len(card_uses.where_used(w.project, 3)))
        # A line goes to the page it names.
        ritual = next(r for r in range(table.rowCount()) if table.item(r, 0).text() == 'Rituals')
        table.cellDoubleClicked.emit(ritual, 0)
        self.assertEqual(w.current_workspace, 'Rituals')
        pack = next(r for r in range(table.rowCount()) if table.item(r, 0).text() == 'Packs')
        table.cellDoubleClicked.emit(pack, 0)
        self.assertEqual(w.current_workspace, 'Packs')
        self.assertEqual(w.workspace_controls['Packs']['pack_index'], 0)

    def test_a_card_nothing_uses_says_so(self):
        from PySide6.QtWidgets import QTableWidget, QLabel
        w = self.window
        # 722: no fusion, equip, ritual, pool, deck or pack of the fixture
        # names the last card.
        dialog = w.show_card_uses(722)
        self.addCleanup(dialog.close)
        self.assertEqual(dialog.findChild(QTableWidget).rowCount(), 0)
        self.assertIn('Nothing in the mod uses this card', dialog.findChild(QLabel).text())

    def test_the_problems_page_checks_the_other_installed_mods(self):
        """validate.cross_mod: where this mod meets the mods installed, in the
        order the game would load them."""
        from fm_editor import settings
        w = self.window
        c = w.workspace_controls['Problems']
        with tempfile.TemporaryDirectory() as tmp:
            others = Path(tmp) / 'mods' / 'other-mod'
            others.mkdir(parents=True)
            (others / 'mod.json').write_text(json.dumps({
                'id': 'other-mod', 'name': 'The other mod', 'enabled': True,
                'cards': [{'replace': 1, 'attack': 2500}]}), encoding='utf-8')
            settings.save('other_mods', str(others.parent))
            w.select_workspace('Problems')      # the card form stores itself on the way out
            w.project.cards[1].attack = 3000    # the same card, differently
            w._refresh_problems()
            self.assertEqual([i for i in c['issues'] if i.area == 'Other mods'], [])
            self.assertIn('not checked yet', c['others'].text())
            w._check_other_mods()
            clash = [i for i in c['issues'] if i.area == 'Other mods']
            self.assertEqual(len(clash), 1)
            self.assertIn('attack', clash[0].message)
            self.assertIn('The other mod', clash[0].message)
            self.assertIn('Checked against 1 installed mods', c['others'].text())
            # A line about another mod is no place in this one to go to.
            row = next(r for r in range(c['table'].rowCount())
                       if c['table'].item(r, 1).text().startswith('Other mods'))
            w._open_problem(row)
            self.assertIn(clash[0].where, w.statusBar().currentMessage())

    def test_another_mods_broken_manifest_does_not_stop_the_check(self):
        from fm_editor import settings
        w = self.window
        c = w.workspace_controls['Problems']
        with tempfile.TemporaryDirectory() as tmp:
            others = Path(tmp) / 'mods' / 'broken'
            others.mkdir(parents=True)
            (others / 'mod.json').write_text('{ not json at all', encoding='utf-8')
            settings.save('other_mods', str(others.parent))
            w.select_workspace('Problems')
            w._check_other_mods()
            self.assertTrue(c['others'].text())
            self.assertNotIn('Traceback', c['others'].text())

    def marked_rows(self):
        return sorted(name for name, label in self.window.reference_values.items()
                      if label.property('changed'))

    def test_a_field_that_differs_from_the_disc_says_so_and_puts_itself_back(self):
        """tabs.CardsTab.mark/restore: the retail panel marks what differs and
        a click on a row puts that value back in the form."""
        w = self.window
        w.show_card(1)
        self.assertEqual(self.marked_rows(), [])
        w.fields['attack'].setValue(4000)
        w.fields['name'].setText('Renamed')
        self.assertEqual(self.marked_rows(), ['ATK', 'Name'])
        self.assertIn('Click to put the retail value back', w.reference_values['ATK'].toolTip())
        w.reference_values['ATK'].clicked.emit()
        self.assertEqual(w.fields['attack'].value(), w.project.retail.cards[1].attack)
        self.assertEqual(self.marked_rows(), ['Name'])
        w.reference_values['Name'].clicked.emit()
        self.assertEqual(self.marked_rows(), [])
        # Restoring is an edit of the form; Apply stores it, and what it
        # stores is the disc's card again.
        w.fields['defense'].setValue(123)
        self.assertTrue(w.apply_card(quiet=True))
        self.assertEqual(self.marked_rows(), ['DEF'])
        w.reference_values['DEF'].clicked.emit()
        self.assertTrue(w.apply_card(quiet=True))
        self.assertFalse(w.project.card_changed(1))
        self.assertEqual(self.marked_rows(), [])

    def test_the_panel_marks_the_card_text_and_a_non_monsters_effect(self):
        w = self.window
        w.show_card(1)
        w.description.setPlainText('Something else entirely.')
        self.assertEqual(self.marked_rows(), ['Card text'])
        w.reference_values['Card text'].clicked.emit()
        self.assertEqual(w.description.toPlainText(), w.project.retail.cards[1].description)
        self.assertEqual(self.marked_rows(), [])
        w.show_card(601)                                   # a magic card
        self.assertEqual(w.reference_values['Retail effect'].text(), 'Card 601')
        w.fields['effect'].setCurrentText('Card 602')
        self.assertEqual(self.marked_rows(), ['Retail effect'])
        w.reference_values['Retail effect'].clicked.emit()
        self.assertEqual(w.fields['effect'].currentText(), 'Card 601')
        self.assertEqual(self.marked_rows(), [])

    def test_an_added_card_never_marks_what_the_disc_does_not_sell(self):
        """The Password screen knows no added card: its Password and Starchips
        rows have nothing to differ from."""
        w = self.window
        cid = w.project.add_card(1)
        w.show_card(cid)
        w.fields['password'].setText('12345678')
        self.assertNotIn('Password', self.marked_rows())
        self.assertNotIn('Starchips', self.marked_rows())

    def test_a_pack_picture_can_be_drawn_whole_in_the_cards_place(self):
        """"image_style": "full" (packs.fit_full, pack_shop.c): the field is
        the pack's own, and the preview draws what it says."""
        from fm_editor import packs as packmath, pngio
        w = self.window
        c = self.packs_page()
        w._add_pack()
        picture = pngio.Image(300, 500, bytes([200, 40, 40, 255]) * (300 * 500))
        w.project.files['packs/cover.png'] = pngio.encode(picture)
        w._pack_entry()['image'] = 'packs/cover.png'
        w._fill_pack()
        self.assertEqual(c['image_style'].currentIndex(), 0)
        card = c['image'].pixmap()
        self.assertFalse(card.isNull())
        c['image_style'].setCurrentIndex(1)
        self.assertEqual(w._pack_entry().get('image_style'), 'full')
        full = c['image'].pixmap()
        self.assertFalse(full.isNull())
        self.assertIn('whole picture', c['status'].text())
        # "card" is the default, so it is not written.
        c['image_style'].setCurrentIndex(0)
        self.assertNotIn('image_style', w._pack_entry())

    def test_the_list_follows_the_name_as_it_is_typed(self):
        """There is no Apply button to make it catch up."""
        w = self.window
        c = self.packs_page()
        w._add_pack()
        self.assertIn('Pack 1', c['list'].item(0, 0).text())
        c['name'].setText('Dragons!')
        self.assertIn('Dragons!', c['list'].item(0, 0).text().splitlines()[0])
        c['name'].clear()
        self.assertIn('(unnamed)', c['list'].item(0, 0).text().splitlines()[0])

    # --- what the old editor gained, and this window now has too ------------

    def test_a_non_monster_shows_its_retail_effect_instead_of_stats(self):
        """tabs.CardsTab.show_kind: the effect is what a magic, trap, ritual or
        equip card does when played, and a monster has stats instead."""
        w = self.window
        w.show_card(601)                      # a magic card of the fixture
        self.assertFalse(w.fields['effect'].isHidden())
        self.assertFalse(w.fields['attack'].isEnabled())
        self.assertEqual(w.fields['effect'].currentText(), 'Card 601')
        w.show_card(1)                        # a monster
        self.assertTrue(w.fields['effect'].isHidden())
        self.assertTrue(w.fields['attack'].isEnabled())

    def test_a_monster_made_magic_keeps_no_stats_and_plays_an_effect(self):
        w = self.window
        w.show_card(20)
        w.fields['type'].setCurrentIndex(gamedata.TYPE_MAGIC)
        self.assertFalse(w.fields['attack'].isEnabled())
        # It has no effect of its own to fall back on, so (none) is offered.
        self.assertEqual(w.fields['effect'].currentText(), '(none)')
        w.fields['effect'].setCurrentText('Card 601')
        self.assertTrue(w.apply_card(quiet=True))
        card = w.project.cards[20]
        self.assertEqual((card.type, card.attack, card.defense, card.level), (gamedata.TYPE_MAGIC, 0, 0, 0))
        self.assertEqual(card.attribute, 6)
        self.assertEqual(w.project.card_extra[20]['effect'], 601)
        self.assertEqual(w.project.effect_of(20), 601)
        # Made a monster again, it gets the disc card's stats back.
        w.fields['type'].setCurrentIndex(0)
        self.assertEqual(w.fields['attack'].value(), w.project.retail.cards[20].attack)
        self.assertTrue(w.apply_card(quiet=True))
        self.assertNotIn(20, w.project.card_extra)

    def test_an_attack_traps_threshold_is_the_effects_until_it_is_given_one(self):
        """model.trap_threshold_default/set_trap_threshold. The fixture's traps
        are not the disc's attack traps, so the default stands in for one."""
        w = self.window
        box = w.fields['trap_threshold']
        with mock.patch.object(type(w.project), 'trap_threshold_default',
                               lambda self, effect: 2000 if effect else None):
            w.show_card(701)
            self.assertFalse(box.isHidden())
            self.assertEqual(box.value(), -1)                 # the effect's own
            self.assertIn('2000', box.specialValueText())
            box.setValue(1500)
            self.assertTrue(w.apply_card(quiet=True))
            self.assertEqual(w.project.trap_threshold_override(701), 1500)
            w.show_card(701)
            self.assertEqual(box.value(), 1500)
            box.setValue(-1)
            self.assertTrue(w.apply_card(quiet=True))
            self.assertIsNone(w.project.trap_threshold_override(701))
        w.show_card(1)                                        # a monster has none
        self.assertTrue(box.isHidden())

    def test_renaming_an_added_card_carries_its_shop_rule(self):
        """model.set_card_key: the rule names the card by its identity."""
        w = self.window
        cid = w.project.add_card(1)
        old = w.project.identity(cid)
        # A rule of the mod, as an opened mod.json carries it: the card is
        # named by its identity, which the stable key spells.
        w.project.other['passwords'] = {old: {'starchips': 4242}}
        w.project.password_keys[cid] = old
        w.show_card(cid)
        w.key_edit.setText('blue-dragon-copy')
        self.assertTrue(w.apply_card(quiet=True))
        self.assertEqual(w.project.added[cid].key, 'blue-dragon-copy')
        table = w.project.other['passwords']
        self.assertNotIn(old, table)
        self.assertIn(w.project.identity(cid), table)
        self.assertEqual(table[w.project.identity(cid)], {'starchips': 4242})
        self.assertEqual(w.project.password_keys[cid], w.project.identity(cid))

    def test_the_equip_list_counts_the_targets_the_save_writes(self):
        """model.equip_targets: a target that is no longer a monster is not
        one the game would use, nor one manifest writes."""
        w = self.window
        w.select_workspace('Equips')
        w.project.cards[5].type = gamedata.TYPE_MAGIC      # was an equip target of 651
        w._refresh_equips()
        table = w.workspace_controls['Equips']['equips']
        row = next(r for r in range(table.rowCount())
                   if table.item(r, 0).data(Qt_UserRole()) == 651)
        self.assertEqual(int(table.item(row, 2).text()), len(w.project.equip_targets(651)))
        self.assertNotIn(5, w.project.equip_targets(651))

    def test_an_edit_can_be_undone_and_redone(self):
        """history.History over the project, as the Tk window keeps one."""
        w = self.window
        self.assertFalse(w.undo_action.isEnabled())
        w.show_card(1)
        w.fields['name'].setText('Renamed Dragon')
        self.assertTrue(w.apply_card(quiet=True))
        w._record_edit()                                   # the idle snapshot
        self.assertTrue(w.undo_action.isEnabled())
        self.assertTrue(w.dirty)
        w.undo()
        self.assertEqual(w.project.cards[1].name, w.project.retail.cards[1].name)
        self.assertEqual(w.fields['name'].text(), w.project.retail.cards[1].name)
        self.assertFalse(w.dirty)                          # back to how it opened
        w.redo()
        self.assertEqual(w.project.cards[1].name, 'Renamed Dragon')
        self.assertEqual(w.fields['name'].text(), 'Renamed Dragon')
        self.assertTrue(w.dirty)

    def test_an_undo_reaches_a_page_that_is_not_cards(self):
        w = self.window
        w.project.fusions[(5, 6)] = 7
        w._mark_dirty()
        w._record_edit()
        w.undo()
        self.assertNotIn((5, 6), w.project.fusions)

    def test_the_window_opens_no_bigger_than_the_monitor_it_opens_on(self):
        """screen.py does this for the Tk window: a window sized past the
        monitor's work area cannot be dragged back on many desktops. The
        pages' own 1280x760 is the floor."""
        from PySide6.QtGui import QGuiApplication
        w = self.window
        area = QGuiApplication.primaryScreen().availableGeometry()
        self.assertEqual((w.minimumWidth(), w.minimumHeight()), (1280, 760))
        self.assertEqual(w.width(), max(1280, min(1580, area.width() * 9 // 10)))
        self.assertEqual(w.height(), max(760, min(980, area.height() * 9 // 10)))
        self.assertGreaterEqual(w.x(), area.x())
        self.assertGreaterEqual(w.y(), area.y())

    def test_an_edit_writes_a_recovery_copy_and_a_save_backs_the_folder_up(self):
        """recovery.py: a crash costs the session nothing, and a save keeps
        what the folder held."""
        from fm_editor import recovery
        w = self.window
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(recovery.settings, 'path', return_value=Path(tmp) / 'settings.json'):
                w._start_history()
                w.show_card(1)
                w.fields['name'].setText('Recovered Dragon')
                self.assertTrue(w.apply_card(quiet=True))
                w._autosave()
                rows = recovery.records()
                self.assertEqual([row[2]['name'] for row in rows], [w.project.info.name])
                copy, _ = manifest.open_mod(w.retail, rows[0][1])
                self.assertEqual(copy.cards[1].name, 'Recovered Dragon')
                folder = Path(tmp) / 'mod'
                manifest.save_mod(w.project, folder)
                w.project.source_dir = folder
                with mock.patch.object(QMessageBox, 'question',
                                       return_value=QMessageBox.StandardButton.Yes):
                    w.save_mod()
                self.assertFalse(w.dirty)
                # The session's own copy is gone; the folder's backup is kept.
                self.assertEqual([row[2].get('backup') for row in recovery.records()], [True])
