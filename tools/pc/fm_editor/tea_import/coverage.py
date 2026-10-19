"""Explicit changed-byte ownership for independent binary decoders."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class CoverageClaim:
    source: str
    start: int
    end: int
    owner: str
    purpose: str
    status: str = "explained"

    def __post_init__(self):
        if self.start < 0 or self.end <= self.start:
            raise ValueError("coverage range must have 0 <= start < end")

    @property
    def size(self) -> int:
        return self.end - self.start


class CoverageLedger:
    """Tracks ownership without double-counting bytes across detectors."""

    def __init__(self):
        self._claims: list[CoverageClaim] = []

    @property
    def claims(self) -> tuple[CoverageClaim, ...]:
        return tuple(sorted(self._claims))

    def claim(self, claim: CoverageClaim) -> None:
        for existing in self._claims:
            if existing.source == claim.source and existing.start < claim.end and claim.start < existing.end:
                raise ValueError(
                    f"coverage conflict in {claim.source}: {claim.owner} overlaps {existing.owner} "
                    f"at 0x{max(claim.start, existing.start):X}")
        self._claims.append(claim)

    def owned_bytes(self, source: str | None = None) -> int:
        return sum(claim.size for claim in self._claims if source is None or claim.source == source)

    def covered_bytes(self, source: str, changed: list[tuple[int, int]]) -> int:
        """Count only owned bytes that were actually changed in this import."""
        return sum(
            max(0, min(end, claim.end) - max(start, claim.start))
            for claim in self._claims if claim.source == source
            for start, end in changed
        )

    def uncovered(self, source: str, changed: list[tuple[int, int]]) -> list[tuple[int, int]]:
        """Subtract owned ranges from precomputed changed ranges."""
        owned = [(claim.start, claim.end) for claim in self._claims if claim.source == source]
        result = list(changed)
        for low, high in owned:
            next_result = []
            for start, end in result:
                if high <= start or end <= low:
                    next_result.append((start, end))
                else:
                    if start < low:
                        next_result.append((start, low))
                    if high < end:
                        next_result.append((high, end))
            result = next_result
        return result
