"""The retail-diff importer on synthetic files: a "community mod" made by
changing the fixture's tables, text and bytes, imported back as a port mod."""
import json
import random
import struct
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fm_editor import gamedata as g, importer, manifest, pngio, roster, teatools_import
from fm_editor.disc import GameFiles
from fm_editor.model import Project
from fm_editor.tests import fixtures
from fm_editor.tests.test_data import fixture, state


def modded():
    f = fixture()
    cards = {cid: card.copy() for cid, card in f.cards.items()}
    cards[5].attack += 100
    cards[6].name = "Dark Card"
    cards[7].description = "New text."
    fusions = dict(f.fusions)
    fusions[(1, 2)] = 4
    fusions[(598, 599)] = 600
    equips = {k: list(v) for k, v in f.equips.items()}
    equips[652].append(8)
    pools = [{p: dict(v) for p, v in d.items()} for d in f.pools]
    deck = pools[3]["deck"]
    first, second = sorted(deck)[:2]
    deck[first] -= 50
    deck[second] += 50
    slus = bytearray(fixtures.make_slus(cards, {0x330: "Heishin X"}))
    slus[g.slus_offset(0x800917F9)] = 9                      # an AI parameter (duelist 1: Simon Muran)
    wa = bytearray(fixtures.make_wa(fusions, equips, f.rituals, pools))
    wa[0x100:0x104] = b"\x01\x02\x03\x04"                     # a small patch
    wa[0x169000:0x169000 + 5000] = bytes([7]) * 5000          # a long run: sectors
    return GameFiles(bytes(slus), bytes(wa), "modded"), cards, fusions, equips, pools


class TeaToolsRegistryTest(unittest.TestCase):
    def test_registry_records_documented_sources_and_current_coverage(self):
        formats = {item.identifier: item for item in teatools_import.formats()}
        self.assertEqual(set(formats), {"cardsdata", "process-cardcolor", "image-cardsleeves",
                                        "image-minicardsleeves", "logo", "image-field",
                                        "image-gamefont", "initial-deck"})
        self.assertEqual(formats["logo"].source_files, ("DATA/SU.MRG",))
        self.assertEqual(formats["logo"].workspace, "UI > Title screen")
        self.assertEqual(formats["image-cardsleeves"].coverage, "partial")
        self.assertIs(teatools_import.format_named("missing"), None)


class ImporterTest(unittest.TestCase):
    def test_import(self):
        f = fixture()
        retail_files = GameFiles(f.slus, f.wa, "retail")
        modded_files, cards, fusions, equips, pools = modded()
        modded_files.wa_lba = 9173        # a modified disc lays its files out elsewhere: the lba stays retail's
        result = importer.import_modded(retail_files, modded_files, "community")
        report = "\n".join(result.report)
        # The one duelist whose AI byte the fixture changes (0x800917F9,
        # Simon Muran) is read as a plain data edit and written as an "ai"
        # rule, not left as an unimportable executable byte range.
        self.assertIn('"ai" (Simon Muran)', report)
        self.assertNotIn("AI parameters", report)
        simon = roster.replacement(result.project, 1)
        self.assertIsNotNone(simon)
        self.assertEqual(simon.extra.get("ai"), [9, 0, 0, 0, 0, 0, 0, 0, 0])
        self.assertIn("cards: 3 changed", report)
        self.assertNotIn("in the names bank", report)               # the changed names are text, not code
        self.assertIn("where the retail text was", report)     # card 7's shorter text leaves old bytes behind
        project = result.project
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "community"
            importer.save(result, folder)
            data = manifest.read_json(folder / "mod.json")
            text = (folder / "text.txt").read_text(encoding="utf-8")
            self.assertIn("[8330]", text)
            self.assertIn("Heishin X", text)
            self.assertNotIn("Dark Card", text)          # card names go in cards[]
            self.assertEqual(data["text"], "text.txt")
            patch = data["data"][0]
            self.assertEqual(patch["patch"], [{"at": "0x100", "bytes": "01 02 03 04"}])
            sectors = data["data"][1]
            self.assertEqual((sectors["lba"], sectors["sectors"]), (10102 + 0x169000 // 2048, 3))
            self.assertEqual((folder / sectors["replace"]).read_bytes(), modded_files.wa[0x169000:0x169000 + 3 * 2048])
            self.assertTrue((folder / "import-report.txt").exists())
            # Opened over retail, the mod is the modified game's tables.
            opened, messages = manifest.open_mod(f.game(), folder)
            self.assertEqual(messages, [])
            expected = g.read_game(modded_files.slus, modded_files.wa)
            for cid in (5, 6, 7):
                self.assertTrue(opened.cards[cid].same(expected.cards[cid]))
            self.assertEqual(opened.fusions, expected.fusions)
            # The editor lists every equip card, those equipping nothing included.
            self.assertEqual({e: set(m) for e, m in expected.equips.items()},
                             {e: m for e, m in opened.equips.items() if m or e in expected.equips})
            self.assertEqual(opened.pools, expected.pools)
        self.assertEqual(state(project)[2], expected.fusions)

    def test_same_game_imports_nothing(self):
        f = fixture()
        files = GameFiles(f.slus, f.wa, "retail")
        result = importer.import_modded(files, files, "same")
        built = manifest.build(result.project)
        self.assertEqual(set(built) - {"id", "name", "version", "description"}, set())
        self.assertEqual(result.findings, [])

    def test_teatools_starter_analysis_uses_the_existing_starter_import(self):
        """A decoded TeaTools layout must not create a second deck format.

        The normal importer owns ``starter_pools``.  TeaTools validates the
        duplicate table and records why no separate conversion was needed.
        """
        f = fixture()
        retail = GameFiles(f.slus, f.wa, "retail")
        wa = bytearray(f.wa)
        start, end = g.STARTER_BASE, g.STARTER_BASE + g.STARTER_LENGTH
        table = bytearray(g.STARTER_LENGTH)
        row_bytes = g.STARTER_LENGTH // 7
        for number, draws in enumerate((6, 6, 6, 6, 6, 5, 5)):
            row = number * row_bytes
            struct.pack_into("<H", table, row, draws)
            struct.pack_into("<H", table, row + 2, 2048)
        for offset in (start, start + 0x2B000):
            wa[offset:offset + len(table)] = table

        result = importer.import_modded(retail, GameFiles(f.slus, bytes(wa), "modified"), "starter-analysis")

        self.assertEqual(result.analysis_status, {"initial_deck": "already_imported"})
        report = "\n".join(result.report)
        self.assertIn("starter decks: imported seven weighted starter pools", report)
        self.assertIn("initial_deck: already imported", report)
        analysis = json.loads(result.project.files["import-analysis.json"])
        self.assertEqual(analysis["import_status"], {"initial_deck": "already_imported"})
        self.assertTrue(any(item["owner"] == "initial_deck" for item in analysis["claims"]))
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "starter-analysis"
            importer.save(result, folder)
            saved = json.loads((folder / "import-analysis.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["import_status"], analysis["import_status"])
            opened, messages = manifest.open_mod(f.game(), folder)
            self.assertEqual(messages, [])
            self.assertEqual(opened.other["starter_pools"], result.project.other["starter_pools"])

    def test_teatools_analysis_failure_does_not_stop_a_normal_import(self):
        f = fixture()
        files = GameFiles(f.slus, f.wa, "retail")

        with mock.patch("fm_editor.importer.tea_import.analyze", side_effect=RuntimeError("broken decoder")):
            result = importer.import_modded(files, files, "analysis-failure")

        self.assertIsNone(result.analysis)
        self.assertIn("TeaTools analysis: unavailable (RuntimeError: broken decoder)", result.report)
        self.assertIn("import-report.txt", result.project.files)
        self.assertNotIn("import-analysis.json", result.project.files)

    def test_preview_archive_replays_saved_wa_patches_and_sectors(self):
        """A reopened BIN import must preview its raw UI/frame graphics.

        ``manifest.open_mod`` intentionally does not load arbitrary data
        files into Project.files.  The preview therefore has to read a raw
        sector replacement from the mod folder as well as apply inline
        patches from mod.json.
        """
        f = fixture()
        project = Project(f.game())
        with tempfile.TemporaryDirectory() as tmp:
            project.source_dir = Path(tmp)
            raw = Path(tmp) / "data" / "frame-atlas.bin"
            raw.parent.mkdir()
            raw.write_bytes(b"XYZ" + bytes(2045))
            project.other["data"] = [
                {"file": importer.WA_FILE, "patch": [{"at": "0x10", "bytes": "A1 B2"}]},
                {"lba": 10103, "sectors": 1, "replace": "data/frame-atlas.bin"},
            ]
            preview = importer.preview_archive(project, f.wa, 10102)
        self.assertEqual(preview[0x10:0x12], b"\xA1\xB2")
        self.assertEqual(preview[2048:2051], b"XYZ")

    def test_import_card_layout_creates_editable_frame_styles(self):
        """Known card-view immediates become Frames-page style properties.

        This models the TLM patch: its frame atlas is changed, its ATK/DEF
        rows move to one horizontal line, and the original label sprites are
        deliberately suppressed by loading their Y positions into ``$zero``.
        """
        f = fixture()
        retail_slus, wa = bytearray(f.slus), bytearray(f.wa)
        opcodes = {"art_y": 0x24630000, "title_x": 0x24420000,
                   "atk_x": 0x24420000, "atk_y": 0x24420000,
                   "def_x": 0x24420000, "def_y": 0x24420000,
                   "attribute_x": 0x24420000, "attribute_y": 0x24420000}
        for key, opcode in opcodes.items():
            struct.pack_into("<I", retail_slus, g.slus_offset(importer.CARD_LAYOUT_IMMEDIATES[key]), opcode)
        struct.pack_into("<I", retail_slus, g.slus_offset(0x80028D44), 0x96420032)
        struct.pack_into("<I", retail_slus, g.slus_offset(0x80028D48), 0x96630032)
        slus = bytearray(retail_slus)
        for key, value in {"art_y": 46, "title_x": 21, "atk_x": 17,
                           "atk_y": 162, "def_x": 87, "def_y": 162,
                           "attribute_x": 62, "attribute_y": 160}.items():
            at = g.slus_offset(importer.CARD_LAYOUT_IMMEDIATES[key])
            word = struct.unpack_from("<I", slus, at)[0]
            struct.pack_into("<I", slus, at, word & 0xFFFF0000 | value)
        for address in (0x80028D44, 0x80028D48):
            at = g.slus_offset(address)
            word = struct.unpack_from("<I", slus, at)[0]
            struct.pack_into("<I", slus, at, word & 0xFFFF | 0x96000000)
        wa[importer.CARD_FRAME_LEFT] ^= 1
        retail = GameFiles(bytes(retail_slus), f.wa, "retail")
        modded = GameFiles(bytes(slus), bytes(wa), "modded")
        project, report = Project(f.game()), []

        handled = importer.import_card_layout(project, retail, modded, report)

        monster = project.other["card_layout"]["frame_styles"]["imported-monster"]
        self.assertEqual(monster["digits"], {"atk": {"x": 29, "y": 168}, "def": {"x": 99, "y": 168}})
        self.assertEqual(monster["art"], {"x": 19, "y": 46, "width": 102, "height": 96})
        self.assertEqual(monster["attribute"], {"x": 62, "y": 160, "width": 16, "height": 16})
        self.assertEqual(monster["atk_label"], {"hide": True})
        self.assertEqual(monster["dfd_label"], {"hide": True})
        frame = pngio.decode(project.files["frames/imported-monster.png"])
        self.assertEqual(frame.size, (140, 196))
        self.assertEqual(frame.pixel(70, 90)[3], 0)
        self.assertEqual(project.other["card_layout"]["default_styles"]["kinds"]["monster"], "imported-monster")
        self.assertTrue(any(item[0] == g.slus_offset(importer.CARD_LAYOUT_IMMEDIATES["atk_x"])
                            for item in handled))
        self.assertIn("ATK and DEF labels are hidden", "\n".join(report))

    def test_recognized_frame_layout_keeps_changed_frame_bytes_in_raw_fallback(self):
        """Editable layout import must not discard its partially decoded atlas."""
        f = fixture()
        retail_slus, modded_slus = bytearray(f.slus), bytearray(f.slus)
        # Give the known immediate a stable retail opcode then change only its
        # literal, which is exactly the conservative layout recognizer rule.
        at = g.slus_offset(importer.CARD_LAYOUT_IMMEDIATES["atk_x"])
        struct.pack_into("<I", retail_slus, at, 0x24420010)
        struct.pack_into("<I", modded_slus, at, 0x2442001A)
        retail_wa, modded_wa = f.wa, bytearray(f.wa)
        modded_wa[importer.CARD_FRAME_LEFT] ^= 1
        retail = GameFiles(bytes(retail_slus), retail_wa, "retail")
        modded = GameFiles(bytes(modded_slus), bytes(modded_wa), "modified")
        project, report = Project(f.game()), []

        self.assertTrue(importer.import_card_layout(project, retail, modded, report))
        data = importer.wa_data(project, retail, modded, report)

        patches = [patch for entry in data if entry.get("file") == importer.WA_FILE
                   for patch in entry.get("patch", [])]
        self.assertTrue(any(int(patch["at"], 0) <= importer.CARD_FRAME_LEFT <
                            int(patch["at"], 0) + len(bytes.fromhex(patch["bytes"]))
                            for patch in patches))

    def test_import_title_and_menu_assets_from_su(self):
        """Changed SU.MRG sprites become title/menu PNG entries, not raw bytes.

        The synthetic texture changes target the same 8-bit pages as the
        title logo and NEW GAME's normal/selected entry sprites.
        """
        f = fixture()
        retail_su = bytearray(0x31000)
        # Palette row 240 colours menu entries; row 241 colours the logo.
        struct.pack_into("<H", retail_su, 0x30000 + 2, 0x801F)
        struct.pack_into("<H", retail_su, 0x30000 + 0x200 + 2, 0x83E0)
        modded_su = bytearray(retail_su)
        modded_su[32 * importer.SECTOR] = 1       # page (640,256), u/v (0,0): logo
        modded_su[26 * importer.SECTOR] = 1       # page (512,256), u/v (128,160): NEW GAME
        modded_su[10 * importer.SECTOR] = 1       # selected NEW GAME, u/v (0,160)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "DATA").mkdir()
            (root / "DATA" / "SU.MRG").write_bytes(retail_su)
            retail = GameFiles(f.slus, f.wa, str(root))
            modified = root / "modified"
            (modified / "DATA").mkdir(parents=True)
            (modified / "DATA" / "SU.MRG").write_bytes(modded_su)
            modded = GameFiles(f.slus, f.wa, str(modified))
            project, report = Project(f.game()), []

            title_layers, menu_entries, missing = importer.import_title_and_menu_assets(project, retail, modded, report)

        self.assertEqual((title_layers, menu_entries, missing), (["logo"], ["new_game"], None))
        self.assertEqual(project.other["title"]["logo"]["image"], "ui/title-logo.png")
        self.assertEqual(project.other["menu"]["entries"]["new_game"],
                         {"image": "ui/menu-new_game.png", "selected_image": "ui/menu-new_game-selected.png"})
        self.assertEqual(pngio.decode(project.files["ui/title-logo.png"]).size, (320, 168))
        self.assertIn("title: imported logo image", "\n".join(report))
        self.assertIn("menus: imported 1 changed retail menu entry", "\n".join(report))
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "ui-import"
            importer.save(importer.ImportResult(project, report), folder)
            opened, messages = manifest.open_mod(f.game(), folder)
            self.assertEqual(messages, [])
            self.assertEqual(opened.other["title"], project.other["title"])
            self.assertEqual(opened.other["menu"], project.other["menu"])
            # UI images are deliberately loaded from ``source_dir`` on demand
            # rather than all being retained in memory after reopen.
            self.assertTrue((folder / "ui/menu-new_game-selected.png").is_file())

    def test_title_import_distinguishes_missing_archive_from_absent_archives(self):
        f = fixture()
        project, report = Project(f.game()), []
        retail = GameFiles(f.slus, f.wa, "retail")
        modded = GameFiles(f.slus, f.wa, "modded")
        self.assertEqual(importer.import_title_and_menu_assets(project, retail, modded, report), ([], [], None))
        self.assertEqual(report, [])

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "DATA").mkdir()
            (root / "DATA" / "SU.MRG").write_bytes(bytes(0x31000))
            project, report = Project(f.game()), []
            self.assertEqual(importer.import_title_and_menu_assets(
                project, GameFiles(f.slus, f.wa, str(root)), modded, report),
                ([], [], "DATA/SU.MRG"))
        self.assertIn("missing from one source", report[0])

    def test_runs(self):
        a = bytes(100)
        b = bytearray(a)
        b[10] = 1
        b[20] = 1
        b[90] = 1
        self.assertEqual(importer._runs(a, bytes(b), 0, 100), [(10, 21), (90, 91)])
        self.assertEqual(importer._subtract([(0, 100)], [(10, 20), (50, 60)]), [(0, 10), (20, 50), (60, 100)])


# --- encoded drop pools, text-bank code, WA runs, spaces ------------------------------

def _word_at(slus: bytearray, address: int, word: int):
    struct.pack_into("<I", slus, g.slus_offset(address), word)


def encoded_mod(bias: int, shift: int, code: bool):
    """The fixture with every drop pool of opponents 1-39 written as
    bias + (weight << shift) + noise (opponent 0 left alone), and, with
    `code`, the draw's add replaced by a jump to code in the dialog bank
    that undoes it (addiu v0, v0, -bias; sra v0, v0, shift)."""
    f = fixture()
    rng = random.Random(7)
    pools = [{p: dict(v) for p, v in d.items()} for d in f.pools]
    pools[1]["pow"] = {10: 1024, 11: 1000, 12: 24}
    wa = bytearray(f.wa)
    for d in range(1, g.DUELIST_COUNT):
        for p in importer.DROP_POOLS:
            raw = [bias + (pools[d][p].get(cid, 0) << shift) + rng.randrange(1 << shift)
                   for cid in range(1, g.CARD_COUNT + 1)]
            struct.pack_into("<%dH" % g.CARD_COUNT, wa, g.DUELIST_BASE + d * g.DUELIST_STRIDE + g.POOL_OFFSETS[p], *raw)
    slus = bytearray(f.slus)
    if code:
        cave = 0x801BFFD0
        _word_at(slus, importer.DRAW_ADD, (2 << 26) | ((cave >> 2) & 0x3FFFFFF))            # j cave
        _word_at(slus, cave, (9 << 26) | (2 << 21) | (2 << 16) | (-bias & 0xFFFF))          # addiu v0, v0, -bias
        _word_at(slus, cave + 4, (2 << 16) | (2 << 11) | (shift << 6) | 3)                  # sra v0, v0, shift
        _word_at(slus, cave + 8, 0x00822021)                                                 # addu a0, a0, v0
        _word_at(slus, cave + 12, (2 << 26) | (((importer.DRAW_ADD + 8) >> 2) & 0x3FFFFFF))  # j back
    return f, GameFiles(bytes(slus), bytes(wa), "modded"), pools


class ModdedGameTest(unittest.TestCase):
    def imported(self, f, modded_files):
        result = importer.import_modded(GameFiles(f.slus, f.wa, "retail"), modded_files, "community")
        return result.project, "\n".join(result.report)

    def test_encoded_pools_with_the_draw_code(self):
        f, files, pools = encoded_mod(1000, 2, code=True)       # not the tool's values: they come from the code
        project, report = self.imported(f, files)
        self.assertEqual(project.pools, pools)
        self.assertIn("jumps to the mod's code at 0x801BFFD0", report)
        self.assertIn("max(0, (raw - 1000) >> 2)", report)
        self.assertNotIn("scaled", report)
        # The code is reported where it is, with the jump that reaches it.
        self.assertIn("0x801BFFD0-0x801BFFE0 (13 bytes, in the dialog bank; reached by j at 0x80021860 (patched))",
                      report)

    def test_encoded_pools_without_recognized_code(self):
        for bias, shift in ((2512, 3), (3000, 3)):
            with self.subTest(bias=bias):
                f, files, pools = encoded_mod(bias, shift, code=False)
                project, report = self.imported(f, files)
                self.assertEqual(project.pools, pools)
                self.assertIn(f"max(0, (raw - {bias}) >> {shift})", report)
                self.assertIn("was not recognized", report)
                self.assertNotIn("scaled", report)

    def test_pools_off_2048_otherwise_are_scaled(self):
        f = fixture()
        pools = [{p: dict(v) for p, v in d.items()} for d in f.pools]
        pools[2]["bcd"] = {10: 3000, 11: 3000}
        project, report = self.imported(f, GameFiles(f.slus, fixtures.make_wa(f.fusions, f.equips, f.rituals, pools),
                                                     "modded"))
        self.assertEqual(project.pools[2]["bcd"], {10: 1024, 11: 1024})
        self.assertIn("scaled to 2048", report)

    def test_changes_beside_the_pools(self):
        f = fixture()
        pools = [{p: dict(v) for p, v in d.items()} for d in f.pools]
        for d, p, cid in ((5, "pow", g.CARD_COUNT), (5, "bcd", 1), (7, "deck", g.CARD_COUNT)):
            top = max(pools[d][p], key=pools[d][p].get)
            pools[d][p][top] -= 50
            pools[d][p][cid] = pools[d][p].get(cid, 0) + 50
        wa = bytearray(fixtures.make_wa(f.fusions, f.equips, f.rituals, pools))
        beside = g.DUELIST_BASE + 7 * g.DUELIST_STRIDE + g.POOL_OFFSETS["pow"] - 4    # between two pools
        wa[beside] = 0x5A
        project, report = self.imported(f, GameFiles(f.slus, bytes(wa), "modded"))
        self.assertEqual(project.pools, pools)
        # One patch of the one byte, none for the bytes between the changed pools.
        self.assertEqual(manifest.build(project)["data"], [{"file": importer.WA_FILE,
                                                            "patch": [{"at": f"0x{beside:X}", "bytes": "5A"}]}])

    def test_spaces_at_line_ends(self):
        f = fixture()
        cards = {cid: card.copy() for cid, card in f.cards.items()}
        cards[5].attack += 100
        cards[8].description = cards[8].description.replace("\n", "  \n") + " "
        cards[9].name += " "
        project, report = self.imported(f, GameFiles(fixtures.make_slus(cards, f.other_names), f.wa, "modded"))
        self.assertIn("cards: 1 changed", report)
        self.assertIn("2 names or texts differ from retail only by spaces", report)
        self.assertEqual(project.cards[8].description, f.cards[8].description)
        self.assertEqual(project.cards[9].name, f.cards[9].name)


# --- the TeaOnline card-colour patch, both layouts it has shipped --------------------
#
# Bytes verified byte-for-byte against the tool's own saved samples in
# teatools/process-cardcolor/patch/ (not checked into this repo; see
# importer.card_frame_table and card_frame_table_old, and
# process-cardcolor/README.md #4 for the v1/v2 layout history).

CARD_COLOR_V2_LIBRARY_LOOP = bytes.fromhex(
    "0180023c50214224560080a05400a0a6ffff712642881100218851000000319201007232020040120f00"
    "3232029111000600512a0200201600000000000000000091120060011124218832025400"
    "91a40400842401007326d302712aeaff20160400a524000000000000000000000000")
CARD_COLOR_V1_BIG_HOOK = bytes.fromhex("786b0708ffff9324")
CARD_COLOR_V1_SMALL_HOOK = bytes.fromhex("e46b0708")


def _card_color_table(slots: dict) -> bytes:
    """One nibble pair per two cards, card 2n+1 in the high nibble and card
    2n+2 in the low (the tool's own packing)."""
    raw = bytearray((g.CARD_COUNT + 1) // 2)
    for cid, slot in slots.items():
        i = (cid - 1) // 2
        raw[i] = (raw[i] & 0x0F) | (slot << 4) if cid % 2 else (raw[i] & 0xF0) | slot
    return bytes(raw)


class CardFrameImportTest(unittest.TestCase):
    def imported(self, slus):
        f = fixture()
        result = importer.import_modded(GameFiles(f.slus, f.wa, "retail"),
                                         GameFiles(bytes(slus), f.wa, "modded"), "community")
        return result.project, "\n".join(result.report)

    def test_the_current_layout_imports_frame_colours(self):
        f = fixture()
        slus = bytearray(f.slus)
        at = g.slus_offset(importer.CARD_FRAME)
        slus[at:at + len(CARD_COLOR_V2_LIBRARY_LOOP)] = CARD_COLOR_V2_LIBRARY_LOOP
        slus[0x2950:0x2950 + 361] = _card_color_table({5: 4, 6: 4})
        project, report = self.imported(slus)
        self.assertEqual(project.cards[5].frame, 4)
        self.assertEqual(project.cards[6].frame, 4)
        self.assertIn("frame colours imported", report)

    def test_the_older_layout_imports_frame_colours_too(self):
        """process-cardcolor/README.md #4: a game patched before the tool
        also redirected the Library setup loop -- card_frame_table_old()."""
        f = fixture()
        slus = bytearray(f.slus)
        big, small = g.slus_offset(importer.CARD_FRAME_OLD_BIG), g.slus_offset(importer.CARD_FRAME_OLD_SMALL)
        table = g.slus_offset(importer.CARD_FRAME_OLD_TABLE)
        slus[big:big + len(CARD_COLOR_V1_BIG_HOOK)] = CARD_COLOR_V1_BIG_HOOK
        slus[small:small + len(CARD_COLOR_V1_SMALL_HOOK)] = CARD_COLOR_V1_SMALL_HOOK
        slus[table:table + 361] = _card_color_table({5: 4, 6: 4})
        project, report = self.imported(slus)
        self.assertEqual(project.cards[5].frame, 4)
        self.assertEqual(project.cards[6].frame, 4)
        self.assertIn("frame colours imported", report)

    def test_an_unrecognized_frame_patch_is_not_claimed_as_imported(self):
        """Only one of the two hooks present (a different, unrecognized
        tool, or a half-applied patch): no frame colours are invented."""
        f = fixture()
        slus = bytearray(f.slus)
        big = g.slus_offset(importer.CARD_FRAME_OLD_BIG)
        slus[big:big + len(CARD_COLOR_V1_BIG_HOOK)] = CARD_COLOR_V1_BIG_HOOK
        project, report = self.imported(slus)
        for cid in (5, 6):
            self.assertEqual(project.cards[cid].frame, f.cards[cid].frame)
        self.assertNotIn("frame colours imported", report)


if __name__ == "__main__":
    unittest.main()
