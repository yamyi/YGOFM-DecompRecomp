"""Read-only detector for TeaTools' Phoenix Battle Effects layout."""
from __future__ import annotations

from ... import gamedata as g
from ..coverage import CoverageClaim
from ..results import Compatibility, DetectionResult, DetectionStatus, FeatureResult

SLUS = "SLUS_014.11"
HOOKS = ((0x10E30, bytes.fromhex("f553070cf09e11266854070c80008234")),
         (0x10EB0, bytes.fromhex("7454070c1d80073c")))
ROUTINE = (0x1C57D0, 552)
TAIL = (0x1C5A3C, 20)
ROUTINE_PROBES = ((0x1C57D0, bytes.fromhex("000000000400228e1d80073c03004014")),
                  (0x1C57D0 + 276, bytes.fromhex("d04fe0a41d800d3c3253ad252168aa01")),
                  (0x1C57D0 + 536, bytes.fromhex("00000000000002240800e00300000000")),
                  (0x1C5A3C, bytes.fromhex("b202052478ffa214000000000800e003")),
                  (0x1C5A3C + 4, bytes.fromhex("78ffa214000000000800e00300000000")))
DATA, DATA_LEN, EFFECT_SLOTS, EXCEPTION_SLOTS = 0x1C59F8, 68, 16, 14
EFFECTS = {0: "marshmallon", 1: "exploder_dragon", 2: "dd_warrior_lady"}


class PhoenixBattleEffectsDecoder:
    id = "phoenix_battle_effects"

    @staticmethod
    def _probe_data(slus, probes):
        """Exact byte evidence, including MIPS jump targets at hook sites."""
        evidence = []
        for offset, expected in probes:
            actual = slus.read(offset, len(expected))
            item = {"offset": offset, "expected": expected.hex(), "actual": actual.hex(),
                    "matched": actual == expected}
            if len(expected) % 4 == 0:
                jumps = []
                for index in range(0, len(expected), 4):
                    word = slus.u32(offset + index)
                    opcode = word >> 26
                    if opcode in (2, 3):  # j / jal
                        pc = g.EXE_DELTA + offset + index
                        target = ((pc + 4) & 0xF0000000) | ((word & 0x03FFFFFF) << 2)
                        jumps.append({"offset": offset + index, "instruction": "jal" if opcode == 3 else "j",
                                      "target_ram": f"0x{target:08X}",
                                      "target_offset": target - g.EXE_DELTA})
                if jumps:
                    item["jumps"] = jumps
            evidence.append(item)
        return evidence

    @staticmethod
    def _leading_records(slus):
        """Describe valid leading v1 records without accepting altered padding."""
        assignments, exceptions = [], []
        for index in range(EFFECT_SLOTS):
            word = slus.u16(DATA + 2 * index)
            if word == 0xFFFF:
                break
            card, effect = word >> 4, word & 0xF
            if not 1 <= card <= 722 or effect not in EFFECTS:
                break
            assignments.append({"card_id": card, "effect": EFFECTS[effect]})
        for index in range(EXCEPTION_SLOTS):
            card = slus.u16(DATA + 36 + 2 * index)
            if card == 0xFFFF or not 1 <= card <= 722:
                break
            exceptions.append(card)
        return assignments, exceptions

    def detect(self, context) -> DetectionResult:
        slus = context.modified.get(SLUS)
        if slus is None:
            return DetectionResult(self.id, DetectionStatus.INVALID, details="SLUS_014.11 was not supplied")
        try:
            hook_data = self._probe_data(slus, HOOKS)
            routine_data = self._probe_data(slus, ROUTINE_PROBES)
            hooks = all(item["matched"] for item in hook_data)
            routine = all(item["matched"] for item in routine_data)
            evidence = {"hooks": hook_data, "routine": routine_data}
            if hooks and routine:
                records = self._records(slus)
                if records is None:
                    return DetectionResult(self.id, DetectionStatus.INVALID, "v1",
                                           "effect table does not have the documented sentinel structure", evidence=evidence)
                return DetectionResult(self.id, DetectionStatus.RECOGNIZED, "v1",
                                       f"{len(records[0])} effect assignments; {len(records[1])} exceptions", evidence=evidence)
            matched = sum(item["matched"] for item in hook_data + routine_data)
            if matched:
                assignments, exceptions = self._leading_records(slus)
                evidence["leading_table"] = {"assignments": assignments, "exploder_exceptions": exceptions,
                                             "documented_padding": self._records(slus) is not None}
                return DetectionResult(self.id, DetectionStatus.VARIANT, "v1",
                                       f"{matched} of {len(hook_data) + len(routine_data)} probes matched; "
                                       "the documented Phoenix layout was modified", evidence=evidence)
            return DetectionResult(self.id, DetectionStatus.ABSENT, "v1", evidence=evidence)
        except ValueError:
            return DetectionResult(self.id, DetectionStatus.INVALID, "v1", "truncated SLUS_014.11")

    @staticmethod
    def _records(slus):
        effects, exceptions = [], []
        ended = False
        for index in range(EFFECT_SLOTS):
            word = slus.u16(DATA + 2 * index)
            if word == 0xFFFF:
                ended = True
                continue
            if ended:
                return None
            card, effect = word >> 4, word & 0xF
            if not 1 <= card <= 722 or effect not in EFFECTS:
                return None
            effects.append((card, effect))
        if slus.read(DATA + 32, 4) != b"\xff" * 4:
            return None
        ended = False
        for index in range(EXCEPTION_SLOTS):
            card = slus.u16(DATA + 36 + 2 * index)
            if card == 0xFFFF:
                ended = True
                continue
            if ended or not 1 <= card <= 722:
                return None
            exceptions.append(card)
        if slus.read(DATA + 64, 4) != b"\xff" * 4:
            return None
        return effects, exceptions

    def decode(self, context, detection: DetectionResult) -> FeatureResult:
        slus = context.modified[SLUS]
        effects, exceptions = self._records(slus)
        for offset, blob in HOOKS:
            context.coverage.claim(CoverageClaim(SLUS, offset, offset + len(blob), self.id, "battle hook", "known"))
        for offset, length in (ROUTINE, TAIL):
            context.coverage.claim(CoverageClaim(SLUS, offset, offset + length, self.id, "injected battle routine", "known"))
        context.coverage.claim(CoverageClaim(SLUS, DATA, DATA + DATA_LEN, self.id, "effect assignments", "decoded"))
        return FeatureResult(self.id, "Monster effects", detection, Compatibility.NEEDS_ENGINE,
                             {"assignments": [{"card_id": card, "effect": EFFECTS[effect]} for card, effect in effects],
                              "exploder_exceptions": exceptions},
                             ("Recognized data is not yet converted or implemented by the PC engine.",))
