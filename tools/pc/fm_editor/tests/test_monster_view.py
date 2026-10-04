"""Model record mapping, disc reads and a textured articulated HMD fixture."""
import struct
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fm_editor import monster_view as mv
from fm_editor.model import Project
from fm_editor.tests.test_data import fixture


def model_record():
    data = bytearray(mv.RECORD_SIZE)
    def words(at, *values):
        struct.pack_into("<" + "I" * len(values), data, at * 4, *values)
    words(0, 0x200, 0, 10, 3, 0, 80, 0)
    words(10, 1, 4, 0x80000078, 0x80000064, 0x80000070, 0x80000014)
    words(20, 1)
    struct.pack_into("<9h", data, 21 * 4 + 4, 4096, 0, 0, 0, 4096, 0, 0, 0, 4096)
    struct.pack_into("<3i", data, 21 * 4 + 24, 20, 0, 0)
    words(80, 0xffffffff, 11, 0x80000001, 0x800009, 0x80010002, 0)
    for i, vertex in enumerate(((-100, -100, 0), (100, -100, 0), (0, 100, 0))):
        struct.pack_into("<3h", data, 100 * 4 + i * 8, *vertex)
    struct.pack_into("<10H", data, 120 * 4, 0, 40, 32, 26, 0x2000, 0, 0, 0, 1, 2)
    data[96 * mv.SECTOR:112 * mv.SECTOR] = b"\x11" * (16 * mv.SECTOR)
    struct.pack_into("<H", data, 144 * mv.SECTOR + 2, 31)
    return bytes(data)


class MonsterViewTest(unittest.TestCase):
    def test_record_gaps_and_boundaries(self):
        ids = [cid for cid in range(1, 723) if mv.record_index(cid) is not None]
        self.assertEqual([mv.record_index(cid) for cid in ids], list(range(621)))
        for cid in (0, 301, 350, 651, 700, 721, 723):
            self.assertIsNone(mv.record_index(cid))
        self.assertEqual(mv.record_index(722), 620)

    def test_copy_and_replaced_base_model(self):
        project = Project(fixture().game())
        copied = project.add_card(1)
        self.assertEqual(mv.model_card(project, copied), 1)
        project.card_extra[1] = {"model": 35}
        self.assertEqual(mv.model_card(project, copied), 35)
        project.added[copied].extra["model"] = 7
        self.assertEqual(mv.model_card(project, copied), 7)

    def test_folder_read_and_truncation(self):
        with tempfile.TemporaryDirectory() as temp:
            archive = Path(temp) / "DATA" / "MODEL.MRG"
            archive.parent.mkdir()
            archive.write_bytes(model_record())
            self.assertEqual(mv.read_record(temp, 1), model_record())
            with self.assertRaisesRegex(mv.ModelError, "truncated"):
                mv.read_record(temp, 2)
            with self.assertRaisesRegex(mv.ModelError, "no in-game"):
                mv.read_record(temp, 301)

    def test_disc_record_is_read_by_sector_without_loading_archive(self):
        with tempfile.NamedTemporaryFile(suffix=".iso") as source:
            with mock.patch.object(mv.disc, "DiscImage") as reader:
                image = reader.return_value.__enter__.return_value
                image.find.return_value = (100, mv.RECORD_SIZE * 621)
                image.read.return_value = model_record()
                self.assertEqual(mv.read_record(source.name, 351), model_record())
                image.read.assert_called_once_with(100 + 300 * 276, mv.RECORD_SIZE)

    def test_pose_and_palette_relocation_render_coloured_geometry(self):
        model = mv.MonsterModel(model_record())
        self.assertEqual(model.polygons[0][0][0], (-80, -100, 0))
        self.assertEqual(model.polygons[0][2:], (240 * 64, 16))
        image = mv.render(model, yaw=0, pitch=0, size=(64, 64))
        self.assertGreater(image.rgba.count(bytes((248, 0, 0, 255))), 100)
        turned = mv.render(model, yaw=90, pitch=0, size=(64, 64))
        self.assertNotEqual(image.rgba, turned.rgba)

    def test_bad_records_report_model_error(self):
        for data in (b"", bytes(mv.RECORD_SIZE)):
            with self.assertRaises(mv.ModelError):
                mv.MonsterModel(data)
        data = bytearray(model_record())
        struct.pack_into("<I", data, 21 * 4 + 76, 21)
        with self.assertRaisesRegex(mv.ModelError, "Cyclic"):
            mv.MonsterModel(bytes(data))
