"""Read-only detector for TeaTools' mirrored starter-set table writer."""
from __future__ import annotations

from ..coverage import CoverageClaim
from ..results import Compatibility, DetectionResult, DetectionStatus, FeatureResult

WA = "DATA/WA_MRG.MRG"
OFFSET, MIRROR, ROW_BYTES, SETS, CARDS = 0xF92BD4, 0x2B000, 1464, 7, 722
TABLE_BYTES = ROW_BYTES * SETS


class InitialDeckDecoder:
    id = "initial_deck"

    def detect(self, context) -> DetectionResult:
        retail, modified = context.retail.get(WA), context.modified.get(WA)
        if retail is None or modified is None:
            return DetectionResult(self.id, DetectionStatus.INVALID, details="WA_MRG.MRG is required")
        try:
            first, second = modified.read(OFFSET, TABLE_BYTES), modified.read(OFFSET + MIRROR, TABLE_BYTES)
            changed = first != retail.read(OFFSET, TABLE_BYTES) or second != retail.read(OFFSET + MIRROR, TABLE_BYTES)
            if not changed:
                return DetectionResult(self.id, DetectionStatus.ABSENT, "v1")
            if first != second:
                return DetectionResult(self.id, DetectionStatus.VARIANT, "v1", "starter-set mirrors differ")
            records, issues = self._records(first)
            if issues:
                return DetectionResult(self.id, DetectionStatus.VARIANT, "v1", "; ".join(issues))
            return DetectionResult(self.id, DetectionStatus.RECOGNIZED, "v1", "7 mirrored weighted starter sets")
        except ValueError:
            return DetectionResult(self.id, DetectionStatus.INVALID, "v1", "truncated WA_MRG.MRG")

    @staticmethod
    def _records(data: bytes):
        records, issues, draws = [], [], 0
        for number in range(SETS):
            start = number * ROW_BYTES
            values = [int.from_bytes(data[start + index:start + index + 2], "little") for index in range(0, 2 * (CARDS + 1), 2)]
            count, weights = values[0], values[1:]
            draws += count
            if sum(weights) != 2048:
                issues.append(f"set {number + 1} weight total is {sum(weights)}, not 2048")
            if weights[720] or weights[721]:
                issues.append(f"set {number + 1} gives unreachable card 721 or 722 a weight")
            records.append({"draws": count, "weights": {index + 1: weight for index, weight in enumerate(weights) if weight}})
        if draws != 40:
            issues.insert(0, f"draw counts total {draws}, not 40")
        return records, issues

    def decode(self, context, detection: DetectionResult) -> FeatureResult:
        data = context.modified[WA].read(OFFSET, TABLE_BYTES)
        records, _issues = self._records(data)
        for offset in (OFFSET, OFFSET + MIRROR):
            context.coverage.claim(CoverageClaim(WA, offset, offset + TABLE_BYTES, self.id,
                                                 "mirrored starter-set records", "decoded"))
        return FeatureResult(self.id, "Starter decks", detection, Compatibility.SUPPORTED,
                             {"format": "weighted", "records": records, "mirrored": True})
