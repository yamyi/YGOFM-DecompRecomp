"""Unit tests for the pure TeaTools analysis foundation."""
from __future__ import annotations

import unittest

from fm_editor import gamedata
from fm_editor.tea_import import (
    AnalysisContext,
    BinaryReader,
    CoverageClaim,
    CoverageLedger,
    DetectionResult,
    DetectionStatus,
    PatchSignature,
    SignatureDecoder,
    SignatureProbe,
    TeaAnalyzer,
    TeaRegistry,
    analyze,
)
from fm_editor.disc import GameFiles
from fm_editor.tea_import.addresses import archive_range, slus_ram
from fm_editor.tea_import.decoders.initial_deck import InitialDeckDecoder, MIRROR, OFFSET, ROW_BYTES, SETS, TABLE_BYTES
from fm_editor.tea_import.decoders.phoenix import (
    DATA as PHOENIX_DATA, HOOKS as PHOENIX_HOOKS, PhoenixBattleEffectsDecoder, ROUTINE_PROBES,
)
from fm_editor.tea_import.decoders.ritual_engine import (
    COPIES, HOOKS as RITUAL_HOOKS, SCRIPT_OFFSET, SCRIPT_PROBES, STRIDE, TABLE, RitualEngineDecoder,
)


class BinaryReaderTest(unittest.TestCase):
    def test_little_endian_reads_are_bounded_and_source_labelled(self):
        reader = BinaryReader(b"\x01\x34\x12\x78\x56\x34\x12", "fixture.slus")
        self.assertEqual(reader.u8(0), 1)
        self.assertEqual(reader.u16(1), 0x1234)
        self.assertEqual(reader.u32(3), 0x12345678)
        with self.assertRaisesRegex(ValueError, "fixture.slus.*outside"):
            reader.u16(6)
        with self.assertRaisesRegex(ValueError, "negative"):
            reader.read(-1, 1)

    def test_address_spaces_are_explicit(self):
        address = gamedata.EXE_DELTA + 0x1234
        self.assertEqual(slus_ram(address, 4), (0x1234, 0x1238))
        self.assertEqual(archive_range(0x120, 8), (0x120, 0x128))
        with self.assertRaises(ValueError):
            slus_ram(gamedata.EXE_DELTA - 1)


class CoverageTest(unittest.TestCase):
    def test_coverage_does_not_double_count_or_silently_overlap(self):
        coverage = CoverageLedger()
        coverage.claim(CoverageClaim("SLUS_014.11", 4, 8, "patch-a", "hook"))
        coverage.claim(CoverageClaim("SLUS_014.11", 10, 12, "patch-b", "table"))
        self.assertEqual(coverage.owned_bytes("SLUS_014.11"), 6)
        self.assertEqual(coverage.covered_bytes("SLUS_014.11", [(0, 6), (10, 20)]), 4)
        self.assertEqual(coverage.uncovered("SLUS_014.11", [(0, 14)]), [(0, 4), (8, 10), (12, 14)])
        with self.assertRaisesRegex(ValueError, "coverage conflict"):
            coverage.claim(CoverageClaim("SLUS_014.11", 7, 11, "patch-c", "overlap"))


class SignatureAndRegistryTest(unittest.TestCase):
    def test_signature_reports_recognized_variant_and_absent(self):
        signature = PatchSignature(
            "known-patch", "v1",
            (SignatureProbe("SLUS_014.11", 1, b"\xAA"), SignatureProbe("WA_MRG.MRG", 2, b"\xBB")),
            "synthetic test signature")
        both = {"SLUS_014.11": BinaryReader(b"\0\xAA"), "WA_MRG.MRG": BinaryReader(b"\0\0\xBB")}
        self.assertEqual(signature.detect(both).status, DetectionStatus.RECOGNIZED)
        self.assertEqual(signature.detect({"SLUS_014.11": both["SLUS_014.11"]}).status, DetectionStatus.VARIANT)
        self.assertEqual(signature.detect({"SLUS_014.11": BinaryReader(b"\0\0")}).status,
                         DetectionStatus.ABSENT)

    def test_registry_is_deterministic_and_a_bad_decoder_is_only_a_diagnostic(self):
        class Good:
            id = "good"

            def detect(self, _context):
                return DetectionResult(self.id, DetectionStatus.ABSENT)

            def decode(self, _context, _detection):
                raise AssertionError("decode must not run for absent detection")

        class Broken:
            id = "broken"

            def detect(self, _context):
                raise RuntimeError("bad fixture")

            def decode(self, _context, _detection):
                return None

        context = AnalysisContext({}, {})
        registry = TeaRegistry()
        registry.register(Good())
        registry.register(Broken())
        result = registry.analyze(context)
        self.assertEqual([item.patch_id for item in result.detections], ["good"])
        self.assertEqual(result.diagnostics[0].detector, "broken")
        self.assertIn("bad fixture", result.diagnostics[0].message)
        self.assertEqual(TeaAnalyzer().analyze(context).detections, [])
        with self.assertRaisesRegex(ValueError, "already registered"):
            registry.register(Good())

    def test_analysis_is_non_mutating_and_reports_unknown_diff_coverage(self):
        retail = GameFiles(b"\0" * 8, b"\0" * 8, "retail")
        modified = GameFiles(b"\0\0\x01\x01\0\0\0\0", b"\0" * 7 + b"\x02", "modified")
        result = analyze(retail, modified, TeaRegistry())
        self.assertEqual(result.detections, [])
        self.assertEqual(result.unknown_ranges["SLUS_014.11"], [(2, 4)])
        self.assertEqual(result.unknown_ranges["DATA/WA_MRG.MRG"], [(7, 8)])
        self.assertEqual(result.coverage_summary()["SLUS_014.11"],
                         {"changed": 2, "explained": 0, "unknown": 2})

    def test_recognized_signature_claims_only_its_declared_ranges(self):
        retail = GameFiles(b"\0" * 8, b"\0" * 8, "retail")
        modified = GameFiles(b"\0\xAA\0\xCC\0\0\0\0", b"\0" * 8, "modified")
        signature = PatchSignature("fixture-patch", "v1", (SignatureProbe("SLUS_014.11", 1, b"\xAA"),))
        registry = TeaRegistry()
        registry.register(SignatureDecoder(
            signature, "Cards", "unsupported",
            (CoverageClaim("SLUS_014.11", 1, 2, "fixture-patch", "hook"),)))
        result = analyze(retail, modified, registry)
        self.assertEqual([item.feature_id for item in result.features], ["fixture-patch"])
        self.assertEqual(result.unknown_ranges["SLUS_014.11"], [(3, 4)])
        self.assertEqual(result.coverage_summary()["SLUS_014.11"],
                         {"changed": 2, "explained": 1, "unknown": 1})


class DocumentedTeaToolsDecodersTest(unittest.TestCase):
    @staticmethod
    def _write(data, offset, value):
        data[offset:offset + len(value)] = value

    def test_phoenix_detects_documented_hooks_routine_and_assignments(self):
        slus = bytearray(0x1C5A50)
        for offset, value in PHOENIX_HOOKS + ROUTINE_PROBES:
            self._write(slus, offset, value)
        self._write(slus, PHOENIX_DATA, (10 << 4 | 0).to_bytes(2, "little"))
        self._write(slus, PHOENIX_DATA + 2, (20 << 4 | 1).to_bytes(2, "little"))
        self._write(slus, PHOENIX_DATA + 4, b"\xff" * 28)
        self._write(slus, PHOENIX_DATA + 32, b"\xff" * 4)
        self._write(slus, PHOENIX_DATA + 36, (30).to_bytes(2, "little"))
        self._write(slus, PHOENIX_DATA + 38, b"\xff" * 30)
        context = AnalysisContext({}, {"SLUS_014.11": BinaryReader(slus, "SLUS_014.11")})
        decoder = PhoenixBattleEffectsDecoder()
        detection = decoder.detect(context)
        self.assertEqual(detection.status, DetectionStatus.RECOGNIZED)
        feature = decoder.decode(context, detection)
        self.assertEqual(feature.data["assignments"],
                         [{"card_id": 10, "effect": "marshmallon"}, {"card_id": 20, "effect": "exploder_dragon"}])
        self.assertEqual(feature.data["exploder_exceptions"], [30])
        self.assertEqual(context.coverage.owned_bytes("SLUS_014.11"), 664)
        result = TeaRegistry()
        result.register(decoder)
        analysis = result.analyze(AnalysisContext({}, {"SLUS_014.11": BinaryReader(slus)}))
        report = analysis.report()
        self.assertIn("Phoenix Battle Effects", report)
        self.assertIn("PC compatibility: needs_engine", report)
        self.assertIn('"card_id":10', report)
        slus[ROUTINE_PROBES[1][0]] ^= 1
        self.assertEqual(decoder.detect(context).status, DetectionStatus.VARIANT)

    def test_ritual_engine_requires_all_hooks_scripts_and_mirrored_records(self):
        wa_size = TABLE + STRIDE * (COPIES - 1) + SCRIPT_OFFSET + 560
        slus, wa = bytearray(max(offset + len(value) for offset, value in RITUAL_HOOKS)), bytearray(wa_size)
        for offset, value in RITUAL_HOOKS:
            self._write(slus, offset, value)
        record = (670).to_bytes(2, "little") + (27).to_bytes(2, "little") + (38).to_bytes(2, "little") + \
                 (58).to_bytes(2, "little") + (364).to_bytes(2, "little")
        for copy in range(COPIES):
            base = TABLE + STRIDE * copy
            self._write(wa, base, record)
            for offset, value in SCRIPT_PROBES:
                self._write(wa, base + SCRIPT_OFFSET + offset, value)
        context = AnalysisContext({}, {"SLUS_014.11": BinaryReader(slus), "DATA/WA_MRG.MRG": BinaryReader(wa)})
        decoder = RitualEngineDecoder()
        detection = decoder.detect(context)
        self.assertEqual(detection.status, DetectionStatus.RECOGNIZED)
        feature = decoder.decode(context, detection)
        self.assertEqual(feature.data["records"][0],
                         {"kind": "cards", "spell_id": 670, "requirements": [27, 38, 58], "result_id": 364})
        self.assertEqual(feature.data["terrain_copies"], 7)
        wa[TABLE + STRIDE + SCRIPT_OFFSET + SCRIPT_PROBES[1][0]] ^= 1
        self.assertEqual(decoder.detect(context).status, DetectionStatus.VARIANT)

    def test_initial_deck_requires_a_changed_valid_mirrored_table(self):
        size = OFFSET + MIRROR + TABLE_BYTES
        retail, modified = bytearray(size), bytearray(size)
        draws = (16, 16, 4, 1, 1, 1, 1)
        for copy_base in (OFFSET, OFFSET + MIRROR):
            for index, count in enumerate(draws):
                row = copy_base + index * ROW_BYTES
                self._write(modified, row, count.to_bytes(2, "little"))
                self._write(modified, row + 2, (2048).to_bytes(2, "little"))
        context = AnalysisContext({"DATA/WA_MRG.MRG": BinaryReader(retail)},
                                  {"DATA/WA_MRG.MRG": BinaryReader(modified)})
        decoder = InitialDeckDecoder()
        detection = decoder.detect(context)
        self.assertEqual(detection.status, DetectionStatus.RECOGNIZED)
        feature = decoder.decode(context, detection)
        self.assertEqual(feature.data["format"], "weighted")
        self.assertEqual([record["draws"] for record in feature.data["records"]], list(draws))
        modified[OFFSET + MIRROR] ^= 1
        self.assertEqual(decoder.detect(context).status, DetectionStatus.VARIANT)
        self.assertEqual(InitialDeckDecoder().detect(AnalysisContext(
            {"DATA/WA_MRG.MRG": BinaryReader(retail)}, {"DATA/WA_MRG.MRG": BinaryReader(retail)})).status,
            DetectionStatus.ABSENT)

    def test_truncated_documented_layouts_are_diagnostics_not_exceptions(self):
        self.assertEqual(PhoenixBattleEffectsDecoder().detect(AnalysisContext({}, {"SLUS_014.11": BinaryReader(b"")})).status,
                         DetectionStatus.INVALID)
        self.assertEqual(RitualEngineDecoder().detect(AnalysisContext(
            {}, {"SLUS_014.11": BinaryReader(b""), "DATA/WA_MRG.MRG": BinaryReader(b"")})).status,
            DetectionStatus.INVALID)
        self.assertEqual(InitialDeckDecoder().detect(AnalysisContext(
            {"DATA/WA_MRG.MRG": BinaryReader(b"")}, {"DATA/WA_MRG.MRG": BinaryReader(b"")})).status,
            DetectionStatus.INVALID)


if __name__ == "__main__":
    unittest.main()
