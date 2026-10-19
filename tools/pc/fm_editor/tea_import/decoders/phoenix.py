"""Read-only detector for TeaTools' Phoenix Battle Effects layout."""
from __future__ import annotations

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

    def detect(self, context) -> DetectionResult:
        slus = context.modified.get(SLUS)
        if slus is None:
            return DetectionResult(self.id, DetectionStatus.INVALID, details="SLUS_014.11 was not supplied")
        try:
            hooks = all(slus.equals(offset, expected) for offset, expected in HOOKS)
            routine = all(slus.equals(offset, expected) for offset, expected in ROUTINE_PROBES)
            if hooks and routine:
                records = self._records(slus)
                if records is None:
                    return DetectionResult(self.id, DetectionStatus.INVALID, "v1",
                                           "effect table does not have the documented sentinel structure")
                return DetectionResult(self.id, DetectionStatus.RECOGNIZED, "v1",
                                       f"{len(records[0])} effect assignments; {len(records[1])} exceptions")
            matched = sum((hooks, routine))
            if matched:
                return DetectionResult(self.id, DetectionStatus.VARIANT, "v1",
                                       f"{matched} of 2 independent hook/routine checks matched")
            return DetectionResult(self.id, DetectionStatus.ABSENT, "v1")
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
