"""Declarative probes for supported TeaTools patch layouts."""
from __future__ import annotations

from dataclasses import dataclass

from .binary import BinaryReader
from .coverage import CoverageClaim
from .results import Compatibility, DetectionResult, DetectionStatus, FeatureResult


@dataclass(frozen=True)
class SignatureProbe:
    source: str
    offset: int
    expected: bytes
    kind: str = "bytes"

    def matches(self, sources: dict[str, BinaryReader]) -> bool:
        reader = sources.get(self.source)
        if reader is None:
            return False
        try:
            return reader.equals(self.offset, self.expected)
        except ValueError:
            return False


@dataclass(frozen=True)
class PatchSignature:
    patch_id: str
    version: str
    probes: tuple[SignatureProbe, ...]
    details: str = ""

    def detect(self, sources: dict[str, BinaryReader]) -> DetectionResult:
        if not self.probes:
            return DetectionResult(self.patch_id, DetectionStatus.INVALID, self.version,
                                   "signature has no probes")
        matched = sum(probe.matches(sources) for probe in self.probes)
        if matched == len(self.probes):
            return DetectionResult(self.patch_id, DetectionStatus.RECOGNIZED, self.version, self.details)
        if matched:
            return DetectionResult(self.patch_id, DetectionStatus.VARIANT, self.version,
                                   f"{matched} of {len(self.probes)} signature probes matched")
        return DetectionResult(self.patch_id, DetectionStatus.ABSENT, self.version)


@dataclass(frozen=True)
class SignatureDecoder:
    """A non-mutating decoder for a fixed, already-understood patch layout.

    It intentionally converts no game state.  Its job is to establish exact
    recognition and byte ownership before a feature-specific decoder is
    allowed to stage data for the importer.
    """

    signature: PatchSignature
    category: str
    compatibility: Compatibility
    ranges: tuple[CoverageClaim, ...] = ()

    @property
    def id(self) -> str:
        return self.signature.patch_id

    def detect(self, context) -> DetectionResult:
        return self.signature.detect(context.modified)

    def decode(self, context, detection: DetectionResult) -> FeatureResult:
        for claim in self.ranges:
            context.coverage.claim(claim)
        return FeatureResult(self.id, self.category, detection, self.compatibility)
