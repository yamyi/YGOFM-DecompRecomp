"""Failure-isolated orchestration for TeaTools patch analysis."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from .binary import BinaryReader
from .coverage import CoverageLedger
from .results import AnalysisResult, DetectionResult, Diagnostic, FeatureResult


@dataclass
class AnalysisContext:
    retail: dict[str, BinaryReader]
    modified: dict[str, BinaryReader]
    coverage: CoverageLedger = field(default_factory=CoverageLedger)


class TeaDecoder(Protocol):
    id: str

    def detect(self, context: AnalysisContext) -> DetectionResult:
        ...

    def decode(self, context: AnalysisContext, detection: DetectionResult) -> FeatureResult | None:
        ...


class TeaAnalyzer:
    """Runs independent detectors; one malformed patch never aborts analysis."""

    def __init__(self, decoders: tuple[TeaDecoder, ...] | list[TeaDecoder] = ()):
        self.decoders = tuple(decoders)

    def analyze(self, context: AnalysisContext) -> AnalysisResult:
        result = AnalysisResult(coverage=context.coverage)
        for decoder in self.decoders:
            try:
                detection = decoder.detect(context)
                feature = decoder.decode(context, detection) if detection.is_recognized else None
                result.add(detection, feature)
            except Exception as error:
                result.diagnostics.append(Diagnostic(
                    f"{decoder.id}: {type(error).__name__}: {error}", "error", decoder.id))
        return result
