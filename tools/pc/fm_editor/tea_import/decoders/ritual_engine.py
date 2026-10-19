"""Read-only detector for TeaTools' documented extended Ritual Engine."""
from __future__ import annotations

from ..coverage import CoverageClaim
from ..results import Compatibility, DetectionResult, DetectionStatus, FeatureResult

SLUS, WA = "SLUS_014.11", "DATA/WA_MRG.MRG"
HOOKS = ((0x1CFF4, bytes.fromhex("d2e6050800000000")),
         (0x1D0B0, bytes.fromhex("fae6050800000000")),
         (0x1D0D0, bytes.fromhex("d2e605080a008c25")))
TABLE, STRIDE, COPIES, TABLE_BYTES = 0xB97800, 0x75800, 7, 250
SCRATCH_OFFSET, SCRATCH_BYTES = 0x100, 112
SCRIPT_OFFSET, SCRIPT_BYTES = 0x170, 560
SCRIPT_PROBES = ((0, bytes.fromhex("1880023cd89a4224000052ac040053ac")),
                 (280, bytes.fromhex("21a083020000958e00000000821e1500")),
                 (544, bytes(16)))
KINDS = ("cards", "card_type", "attribute", "any_monster")


class RitualEngineDecoder:
    id = "extended_ritual_engine"

    def detect(self, context) -> DetectionResult:
        slus, wa = context.modified.get(SLUS), context.modified.get(WA)
        if slus is None or wa is None:
            return DetectionResult(self.id, DetectionStatus.INVALID, details="SLUS_014.11 and WA_MRG.MRG are required")
        try:
            hooks = all(slus.equals(offset, expected) for offset, expected in HOOKS)
            script_ok = all(
                all(wa.equals(TABLE + STRIDE * copy + SCRIPT_OFFSET + offset, expected)
                    for offset, expected in SCRIPT_PROBES)
                for copy in range(COPIES))
            records = self._records(wa) if hooks and script_ok else None
            if hooks and script_ok and records is not None:
                return DetectionResult(self.id, DetectionStatus.RECOGNIZED, "20251123",
                                       f"{len(records)} recipe records mirrored across {COPIES} terrain copies")
            matched = sum((hooks, script_ok))
            if matched:
                detail = "recipe table is malformed" if records is None else f"{matched} of 2 independent hook/script checks matched"
                return DetectionResult(self.id, DetectionStatus.VARIANT, "20251123", detail)
            return DetectionResult(self.id, DetectionStatus.ABSENT, "20251123")
        except ValueError:
            return DetectionResult(self.id, DetectionStatus.INVALID, "20251123", "truncated executable or archive")

    @staticmethod
    def _parse(table: bytes):
        records, ended = [], False
        for offset in range(0, 240, 10):
            words = tuple(int.from_bytes(table[offset + index:offset + index + 2], "little") for index in range(0, 10, 2))
            if words == (0, 0, 0, 0, 0):
                ended = True
                continue
            if ended:
                return None
            word, *requirements, result = words
            kind, spell = (word >> 10) & 3, word & 0x3FF
            if not 1 <= spell <= 722 or not 1 <= result <= 722:
                return None
            if kind == 0 and not all(1 <= item <= 722 for item in requirements):
                return None
            if kind == 1 and not all(0 <= item <= 23 for item in requirements):
                return None
            if kind == 2 and not all(0 <= item <= 7 for item in requirements):
                return None
            records.append({"kind": KINDS[kind], "spell_id": spell, "requirements": list(requirements), "result_id": result})
        return records

    def _records(self, wa):
        records = None
        for copy in range(COPIES):
            base = TABLE + STRIDE * copy
            if wa.read(base + SCRATCH_OFFSET, SCRATCH_BYTES) != bytes(SCRATCH_BYTES):
                return None
            parsed = self._parse(wa.read(base, TABLE_BYTES))
            if parsed is None or (records is not None and parsed != records):
                return None
            records = parsed
        return records

    def decode(self, context, detection: DetectionResult) -> FeatureResult:
        wa = context.modified[WA]
        records = self._records(wa)
        for offset, blob in HOOKS:
            context.coverage.claim(CoverageClaim(SLUS, offset, offset + len(blob), self.id, "ritual lookup hook", "known"))
        for copy in range(COPIES):
            base = TABLE + STRIDE * copy
            context.coverage.claim(CoverageClaim(WA, base, base + TABLE_BYTES, self.id, "extended ritual records", "decoded"))
            context.coverage.claim(CoverageClaim(WA, base + SCRATCH_OFFSET, base + SCRATCH_OFFSET + SCRATCH_BYTES,
                                                 self.id, "ritual engine scratch space", "known"))
            context.coverage.claim(CoverageClaim(WA, base + SCRIPT_OFFSET, base + SCRIPT_OFFSET + SCRIPT_BYTES,
                                                 self.id, "ritual engine routine", "known"))
        return FeatureResult(self.id, "Rituals", detection, Compatibility.NEEDS_ENGINE,
                             {"records": records, "terrain_copies": COPIES},
                             ("Extended ingredients are decoded but the PC engine has no equivalent runtime yet.",))
