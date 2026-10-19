"""Read-only detector for TeaTools' mirrored starter-set table writer."""
from __future__ import annotations

from ..coverage import CoverageClaim
from ..results import Compatibility, DetectionResult, DetectionStatus, FeatureResult

WA = "DATA/WA_MRG.MRG"
OFFSET, MIRROR, ROW_BYTES, SETS, CARDS = 0xF92BD4, 0x2B000, 1464, 7, 722
TABLE_BYTES = ROW_BYTES * SETS
# Both tables are embedded in independently loaded text-entry modules.  The
# documented Name Entry path calls the generator and therefore owns copy A;
# copy B belongs to the Password screen.  The data loader can state this
# provenance even if a mod changes either module's code.
MODULE_BASE = OFFSET - 0x2BD4
MODULE_BYTES = 0x7326
GENERATOR_OFFSET = 0x2930
GENERATOR_WINDOW = 0x300
POINTER_OFFSET = 0x53DC


class InitialDeckDecoder:
    id = "initial_deck"

    @staticmethod
    def _summaries(records):
        return [{"record": number + 1, "draws": record["draws"],
                 "weight_total": sum(record["weights"].values()),
                 "nonzero_cards": len(record["weights"])}
                for number, record in enumerate(records)]

    @staticmethod
    def _different_records(first: bytes, second: bytes):
        return [{"record": index + 1,
                 "different_bytes": sum(left != right for left, right in zip(
                     first[index * ROW_BYTES:(index + 1) * ROW_BYTES],
                     second[index * ROW_BYTES:(index + 1) * ROW_BYTES]))}
                for index in range(SETS)
                if first[index * ROW_BYTES:(index + 1) * ROW_BYTES] !=
                second[index * ROW_BYTES:(index + 1) * ROW_BYTES]]

    @staticmethod
    def _module_evidence(retail, modified):
        """Report whether the documented name-entry generator itself changed."""
        start, end = MODULE_BASE, MODULE_BASE + MODULE_BYTES
        if end > len(retail) or end > len(modified):
            return {"available": False}
        generator = MODULE_BASE + GENERATOR_OFFSET
        window_end = min(generator + GENERATOR_WINDOW, end)
        pointer = MODULE_BASE + POINTER_OFFSET
        expected_pointers = b"".join((0x8016ABD4 + ROW_BYTES * index).to_bytes(4, "little")
                                      for index in range(SETS)) + b"\0" * 4
        module_changed = sum(a != b for a, b in zip(retail.read(start, end - start),
                                                    modified.read(start, end - start)))
        generator_changed = sum(a != b for a, b in zip(
            retail.read(generator, window_end - generator), modified.read(generator, window_end - generator)))
        pointers_match = modified.read(pointer, len(expected_pointers)) == expected_pointers
        active_source = "A" if not generator_changed and pointers_match else "unknown"
        return {
            "available": True,
            "name_entry_copy": "A",
            "password_copy": "B",
            "documented_source": "A",
            "active_source": active_source,
            "reason": ("the documented Name Entry module calls the starter generator; copy B is Password data"
                       if active_source == "A" else
                       "the documented Name Entry module uses copy A, but its generator or pointer list changed"),
            "module_changed_bytes": module_changed,
            "generator_window_changed_bytes": generator_changed,
            "pointer_list_matches_documented": pointers_match,
        }

    def detect(self, context) -> DetectionResult:
        retail, modified = context.retail.get(WA), context.modified.get(WA)
        if retail is None or modified is None:
            return DetectionResult(self.id, DetectionStatus.INVALID, details="WA_MRG.MRG is required")
        try:
            first, second = modified.read(OFFSET, TABLE_BYTES), modified.read(OFFSET + MIRROR, TABLE_BYTES)
            retail_first = retail.read(OFFSET, TABLE_BYTES)
            # Some compact test or user-supplied retail archives end between
            # the two copies.  Copy A is sufficient to establish a change;
            # retain that uncertainty in the evidence instead of making the
            # otherwise readable modified table invalid.
            retail_second = retail.read(OFFSET + MIRROR, TABLE_BYTES) \
                if OFFSET + MIRROR + TABLE_BYTES <= len(retail) else None
            changed = first != retail_first or retail_second is None or second != retail_second
            records_a, issues_a = self._records(first)
            records_b, issues_b = self._records(second)
            evidence = {
                "copy_a": {"offset": OFFSET, "changed_from_retail": first != retail_first,
                           "issues": issues_a, "records": self._summaries(records_a)},
                "copy_b": {"offset": OFFSET + MIRROR,
                           "changed_from_retail": None if retail_second is None else second != retail_second,
                           "issues": issues_b, "records": self._summaries(records_b)},
                "mirrors": {"identical": first == second, "different_records": self._different_records(first, second)},
                "runtime_source": self._module_evidence(retail, modified),
            }
            if not changed:
                return DetectionResult(self.id, DetectionStatus.ABSENT, "v1", evidence=evidence)
            if first != second:
                return DetectionResult(self.id, DetectionStatus.VARIANT, "v1",
                                       "starter-set mirrors differ; copy A is the documented Name Entry source, "
                                       "but the active source may be custom", evidence=evidence)
            if issues_a:
                return DetectionResult(self.id, DetectionStatus.VARIANT, "v1", "; ".join(issues_a), evidence=evidence)
            return DetectionResult(self.id, DetectionStatus.RECOGNIZED, "v1", "7 mirrored weighted starter sets", evidence=evidence)
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
